/**
 * パスキー（WebAuthn）の API（I619）
 * 登録・削除は本人確認の印（ReauthToken.reauth_token）をヘッダー X-Reauth-Token で送る
 */
import {
  PublicKeyCredentialCreationOptionsJSON,
  PublicKeyCredentialRequestOptionsJSON,
  startAuthentication,
  startRegistration,
} from '@simplewebauthn/browser';
import { apiClient } from './api';
import {
  LoginResponse,
  PaginatedPasskeyList,
  Passkey,
  ReauthToken,
  WebAuthnOptions,
} from '../types/api';

const BASE = '/api/auth/passkeys/';
const REAUTH_HEADER = 'X-Reauth-Token';

/** ブラウザの PublicKeyCredential.toJSON() の結果（中身はサーバーの py_webauthn が確かめる） */
export type CredentialJSON = Record<string, unknown>;

export const reauthHeaders = (reauthToken: string) => ({ headers: { [REAUTH_HEADER]: reauthToken } });

/** サーバーの options（中身は py_webauthn が作る WebAuthn の JSON）を、challenge があることを確かめてから渡す */
const hasChallenge = (options: Record<string, unknown>) => typeof options.challenge === 'string';

/** ブラウザでパスキーを確かめる（ログイン・本人確認） */
export async function getPasskeyAssertion(options: WebAuthnOptions): Promise<CredentialJSON> {
  if (!hasChallenge(options.options)) throw new Error('invalid WebAuthn options');
  const credential = await startAuthentication({
    optionsJSON: options.options as unknown as PublicKeyCredentialRequestOptionsJSON,
  });
  return credential as unknown as CredentialJSON;
}

/** ブラウザでパスキーを作る（登録） */
export async function createPasskeyCredential(options: WebAuthnOptions): Promise<CredentialJSON> {
  if (!hasChallenge(options.options)) throw new Error('invalid WebAuthn options');
  const credential = await startRegistration({
    optionsJSON: options.options as unknown as PublicKeyCredentialCreationOptionsJSON,
  });
  return credential as unknown as CredentialJSON;
}

export const passkeyService = {
  async list(): Promise<Passkey[]> {
    const response = await apiClient.get<PaginatedPasskeyList>(BASE);
    return response.data.results;
  },

  async loginOptions(): Promise<WebAuthnOptions> {
    return (await apiClient.post<WebAuthnOptions>(`${BASE}login/options/`)).data;
  },

  async login(challengeId: string, credential: CredentialJSON): Promise<LoginResponse> {
    return (await apiClient.post<LoginResponse>(`${BASE}login/`, { challenge_id: challengeId, credential })).data;
  },

  async reauthOptions(): Promise<WebAuthnOptions> {
    return (await apiClient.post<WebAuthnOptions>(`${BASE}reauth/options/`)).data;
  },

  async reauthWithPassword(password: string): Promise<ReauthToken> {
    return (await apiClient.post<ReauthToken>(`${BASE}reauth/`, { password })).data;
  },

  async reauthWithPasskey(challengeId: string, credential: CredentialJSON): Promise<ReauthToken> {
    return (await apiClient.post<ReauthToken>(`${BASE}reauth/`, { challenge_id: challengeId, credential })).data;
  },

  async registerOptions(reauthToken: string): Promise<WebAuthnOptions> {
    return (await apiClient.post<WebAuthnOptions>(`${BASE}register/options/`, undefined, reauthHeaders(reauthToken)))
      .data;
  },

  async register(reauthToken: string, challengeId: string, credential: CredentialJSON): Promise<Passkey> {
    return (
      await apiClient.post<Passkey>(
        `${BASE}register/`,
        { challenge_id: challengeId, credential },
        reauthHeaders(reauthToken)
      )
    ).data;
  },

  async rename(id: string, name: string): Promise<Passkey> {
    return (await apiClient.patch<Passkey>(`${BASE}${id}/`, { name })).data;
  },

  async remove(reauthToken: string, id: string): Promise<void> {
    await apiClient.delete(`${BASE}${id}/`, reauthHeaders(reauthToken));
  },
};

export default passkeyService;
