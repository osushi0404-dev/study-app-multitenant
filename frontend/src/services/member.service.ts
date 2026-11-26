/**
 * メンバー管理と登録用リンクの API（I620）
 * - 発行・失効・パスキーの削除は本人確認の印（X-Reauth-Token）を付ける
 * - credentialApi は、組織の管理者（/api/members/）と運営（/api/admin/users/）で同じ形の操作を作る
 */
import { apiClient } from './api';
import { CredentialJSON, reauthHeaders } from './passkey.service';
import {
  LoginResponse,
  Member,
  PaginatedMemberList,
  PaginatedPasskeyList,
  RegistrationLinkIssued,
  RegistrationLinkOptions,
} from '../types/api';

export const MEMBERS_BASE = '/api/members/';
export const ADMIN_USERS_BASE = '/api/admin/users/';
export type CredentialBase = typeof MEMBERS_BASE | typeof ADMIN_USERS_BASE;

export const memberService = {
  async list(page: number): Promise<PaginatedMemberList> {
    return (await apiClient.get<PaginatedMemberList>(MEMBERS_BASE, { params: { page } })).data;
  },

  async create(userId: string): Promise<Member> {
    return (await apiClient.post<Member>(MEMBERS_BASE, { user_id: userId })).data;
  },
};

export const credentialApi = (base: CredentialBase) => ({
  async passkeys(memberId: string): Promise<PaginatedPasskeyList> {
    return (await apiClient.get<PaginatedPasskeyList>(`${base}${memberId}/passkeys/`)).data;
  },

  async deletePasskey(reauthToken: string, memberId: string, passkeyId: string): Promise<void> {
    await apiClient.delete(`${base}${memberId}/passkeys/${passkeyId}/`, reauthHeaders(reauthToken));
  },

  async issueLink(reauthToken: string, memberId: string): Promise<RegistrationLinkIssued> {
    return (
      await apiClient.post<RegistrationLinkIssued>(
        `${base}${memberId}/registration-link/`,
        undefined,
        reauthHeaders(reauthToken)
      )
    ).data;
  },

  async revokeLink(reauthToken: string, memberId: string): Promise<void> {
    await apiClient.delete(`${base}${memberId}/registration-link/`, reauthHeaders(reauthToken));
  },
});

/** 登録用リンクから開く画面（ログインの前に呼ぶ） */
export const registrationLinkService = {
  async options(token: string): Promise<RegistrationLinkOptions> {
    return (await apiClient.post<RegistrationLinkOptions>('/api/auth/registration-links/options/', { token })).data;
  },

  async complete(token: string, challengeId: string, credential: CredentialJSON): Promise<LoginResponse> {
    return (
      await apiClient.post<LoginResponse>('/api/auth/registration-links/complete/', {
        token,
        challenge_id: challengeId,
        credential,
      })
    ).data;
  },
};
