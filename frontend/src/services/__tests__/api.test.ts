/**
 * I132: handleApiError のトースト分岐の回帰テスト（実リクエスト経路）。
 *
 * axios-mock-adapter を装着したインスタンスを ApiClient に注入し、
 * インターセプタ連鎖（401 リフレッシュ分岐→handleApiError）を実経路で通して検証する。
 * TC 詳細: docs/tests/open/I132_auto_test.md
 */
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { toast } from 'react-hot-toast';

import { ApiClient } from '../api';

// jest.mock は babel-jest により import より先に巻き上げられる
jest.mock('react-hot-toast', () => ({
  toast: { error: jest.fn() },
}));

describe('api client handleApiError (I132)', () => {
  let mock: MockAdapter;
  let client: ApiClient;

  beforeEach(() => {
    const instance = axios.create();
    mock = new MockAdapter(instance);
    client = new ApiClient(instance);
    (toast.error as jest.Mock).mockClear();
  });

  afterEach(() => {
    mock.restore();
  });

  it('TC-01: 429 でレート制限トーストを表示する', async () => {
    mock.onGet('/api/subjects/').reply(429);
    await expect(client.get('/api/subjects/')).rejects.toMatchObject({
      response: { status: 429 },
    });
    expect(toast.error).toHaveBeenCalledTimes(1);
    expect(toast.error).toHaveBeenCalledWith(
      'リクエストが多すぎます。しばらく待ってから再試行してください'
    );
  });

  it('TC-02: 既存の 500 トーストが退行しない', async () => {
    mock.onGet('/api/subjects/').reply(500);
    await expect(client.get('/api/subjects/')).rejects.toMatchObject({
      response: { status: 500 },
    });
    expect(toast.error).toHaveBeenCalledTimes(1);
    expect(toast.error).toHaveBeenCalledWith('サーバーエラーが発生しました');
  });

  it('TC-03: /auth/ URL のエラーではトーストを表示しない', async () => {
    mock.onPost('/api/auth/login/').reply(500);
    await expect(client.post('/api/auth/login/')).rejects.toMatchObject({
      response: { status: 500 },
    });
    expect(toast.error).not.toHaveBeenCalled();
  });
});
