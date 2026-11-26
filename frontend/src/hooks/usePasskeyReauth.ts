/**
 * パスキーの登録・削除の前の本人確認（I619）
 *
 * - 印（reauth token）は画面のメモリ（useRef）にだけ置く。localStorage に置かない（React 規約 §11）
 * - 有効は「受け取った時刻＋expires_in−10 秒」（時計のずれで 403 を受けにくくする）
 * - 有効な印が無ければダイアログを開き、確かめ終わるまで待つ。API が 403 を返したら印を捨てて 1 回だけ確かめ直す
 */
import { useCallback, useRef, useState } from 'react';
import { ReauthToken } from '../types/api';
import { isReauthRequired } from '../utils/passkeyErrors';

const CLOCK_MARGIN_MS = 10_000;

/** 本人確認のダイアログを閉じた（操作を取り消した） */
export class ReauthCancelledError extends Error {
  constructor() {
    super('reauth cancelled');
    this.name = 'ReauthCancelledError';
  }
}

type Pending = { resolve: (token: string) => void; reject: (error: Error) => void };

export const usePasskeyReauth = () => {
  const tokenRef = useRef<{ token: string; expiresAt: number } | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);

  const ensureReauth = useCallback((): Promise<string> => {
    const current = tokenRef.current;
    if (current && Date.now() < current.expiresAt) return Promise.resolve(current.token);
    tokenRef.current = null;
    return new Promise((resolve, reject) => setPending({ resolve, reject }));
  }, []);

  const complete = (result: ReauthToken) => {
    tokenRef.current = {
      token: result.reauth_token,
      expiresAt: Date.now() + result.expires_in * 1000 - CLOCK_MARGIN_MS,
    };
    pending?.resolve(result.reauth_token);
    setPending(null);
  };

  const cancel = () => {
    pending?.reject(new ReauthCancelledError());
    setPending(null);
  };

  /** 本人確認の印を付けて操作する。403（印が無い・切れた）なら印を捨てて確かめ直す */
  const withReauth = async <T,>(action: (token: string) => Promise<T>): Promise<T> => {
    try {
      return await action(await ensureReauth());
    } catch (error) {
      if (!isReauthRequired(error)) throw error;
      tokenRef.current = null;
      return action(await ensureReauth());
    }
  };

  return { dialogOpen: pending !== null, complete, cancel, withReauth };
};
