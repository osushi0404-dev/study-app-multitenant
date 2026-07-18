/**
 * I127: handleApiError の 429 分岐（レート制限トースト）の回帰テスト。
 *
 * axios モックライブラリ未導入のため、レスポンスインターセプタの rejected
 * ハンドラを直接呼び出して検証する（TC-FE-01/02・docs/tests/open/I127_auto_test.md）。
 * url は /auth/ スキップ（api.ts の handleApiError 冒頭）を踏まない /api/subjects/ を使う。
 */
import { toast } from 'react-hot-toast';

import apiClient from '../api';

// jest.mock は babel-jest により import より先に巻き上げられる
jest.mock('react-hot-toast', () => ({
  toast: { error: jest.fn() },
}));

describe('api client handleApiError (I127)', () => {
  const rejected = (apiClient as any).instance.interceptors.response.handlers[0]
    .rejected as (error: unknown) => Promise<never>;

  beforeEach(() => {
    (toast.error as jest.Mock).mockClear();
  });

  it('TC-FE-01: 429 でレート制限トーストを表示する', async () => {
    const error = { response: { status: 429 }, config: { url: '/api/subjects/' } };
    await expect(rejected(error)).rejects.toBe(error);
    expect(toast.error).toHaveBeenCalledTimes(1);
    expect(toast.error).toHaveBeenCalledWith(
      'リクエストが多すぎます。しばらく待ってから再試行してください'
    );
  });

  it('TC-FE-02: 既存の 500 トーストが退行しない', async () => {
    const error = { response: { status: 500 }, config: { url: '/api/subjects/' } };
    await expect(rejected(error)).rejects.toBe(error);
    expect(toast.error).toHaveBeenCalledWith('サーバーエラーが発生しました');
  });
});
