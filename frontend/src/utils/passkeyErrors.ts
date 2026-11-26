/**
 * パスキー（I619）の画面の文と、ブラウザ・API の失敗を文に変える関数
 */
import axios from 'axios';
import { extractApiErrorMessage } from './apiError';

export const PASSKEY_UNSUPPORTED = 'このブラウザはパスキーに未対応です';
export const PASSKEY_LOGIN_FAILED = 'パスキーでログインできませんでした。もう一度試すか、パスワードでログインしてください';
const PASSKEY_ALREADY_REGISTERED = 'この端末のパスキーはすでに登録されています';
export const PASSKEY_VERIFY_FAILED = 'パスキーを確かめられませんでした。もう一度お試しください';
export const PASSKEY_REGISTER_FAILED = 'パスキーを登録できませんでした。もう一度お試しください';
export const PASSKEY_DELETE_FAILED = 'パスキーを削除できませんでした。もう一度お試しください';
export const PASSKEY_RENAME_FAILED = '名前を変えられませんでした。もう一度お試しください';

const errorName = (error: unknown): string | undefined =>
  typeof error === 'object' && error !== null && 'name' in error ? String((error as { name: unknown }).name) : undefined;

const errorCode = (error: unknown): string | undefined =>
  typeof error === 'object' && error !== null && 'code' in error ? String((error as { code: unknown }).code) : undefined;

/** 同じ端末のパスキーをもう一度登録しようとした（ブラウザが excludeCredentials で止めた） */
const isAlreadyRegistered =(error: unknown): boolean =>
  errorCode(error) === 'ERROR_AUTHENTICATOR_PREVIOUSLY_REGISTERED' || errorName(error) === 'InvalidStateError';

/** 本人確認の印が無い・切れた（登録・削除の API の 403） */
export const isReauthRequired = (error: unknown): boolean =>
  axios.isAxiosError(error) && error.response?.status === 403;

/** API の 400 ならサーバーの文、それ以外は決まった文 */
export const apiErrorText = (error: unknown, fallback: string): string =>
  axios.isAxiosError(error) && error.response?.status === 400
    ? extractApiErrorMessage(error.response.data, fallback)
    : fallback;

/** 登録の失敗の文 */
export const registrationErrorText = (error: unknown): string =>
  isAlreadyRegistered(error) ? PASSKEY_ALREADY_REGISTERED : apiErrorText(error, PASSKEY_REGISTER_FAILED);
