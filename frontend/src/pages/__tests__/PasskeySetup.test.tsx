/**
 * 登録用リンクで開くパスキーの登録画面（I620・TC-24）
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { AxiosError, AxiosHeaders } from 'axios';
import toast from 'react-hot-toast';
import { browserSupportsWebAuthn } from '@simplewebauthn/browser';
import PasskeySetup from '../PasskeySetup';
import { registrationLinkService } from '../../services/member.service';
import { createPasskeyCredential } from '../../services/passkey.service';

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { error: jest.fn(), success: jest.fn() },
}));

jest.mock('@simplewebauthn/browser', () => ({ browserSupportsWebAuthn: jest.fn() }));

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const mockComplete = jest.fn();
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ completeRegistrationLink: mockComplete }),
}));

jest.mock('../../services/member.service', () => ({
  registrationLinkService: { options: jest.fn(), complete: jest.fn() },
}));

jest.mock('../../services/passkey.service', () => ({
  createPasskeyCredential: jest.fn(),
}));

const service = registrationLinkService as jest.Mocked<typeof registrationLinkService>;
const mockCreate = createPasskeyCredential as jest.Mock;
const mockSupported = browserSupportsWebAuthn as jest.Mock;

const TOKEN = 'abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG';
const OPTIONS = { challenge_id: 'c-1', options: { challenge: 'abc' }, user_id: 'alice' };
const CREDENTIAL = { id: 'cred-1' };
const UNUSABLE = 'このリンクは使えません。管理者に新しいリンクを発行してもらってください';

const axiosError = (status: number, data: unknown = {}) =>
  new AxiosError('failed', String(status), undefined, undefined, {
    status, statusText: '', headers: {}, config: { headers: new AxiosHeaders() }, data,
  });

const mountAt = (hash: string) => {
  window.history.replaceState(null, '', `/passkey-setup${hash}`);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <PasskeySetup />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('PasskeySetup', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSupported.mockReturnValue(true);
    service.options.mockResolvedValue(OPTIONS);
    mockCreate.mockResolvedValue(CREDENTIAL);
    mockComplete.mockResolvedValue(undefined);
  });

  it('TC-24: 値を読んだらすぐアドレスバーから消し、ユーザー ID と案内を出す', async () => {
    mountAt(`#token=${TOKEN}`);
    expect(window.location.hash).toBe('');
    expect(window.location.href).not.toContain(TOKEN);
    expect(window.location.pathname).toBe('/passkey-setup');
    expect(await screen.findByText('ユーザーID『alice』のパスキーを登録します')).toBeInTheDocument();
    expect(screen.getByText(/2 台以上の端末で使えるようにしてください/)).toBeInTheDocument();
    expect(service.options).toHaveBeenCalledWith(TOKEN);
  });

  it('TC-24: 登録が通ればログインした状態でダッシュボードへ（押したときに challenge を取り直す・F2）', async () => {
    mountAt(`#token=${TOKEN}`);
    userEvent.click(await screen.findByRole('button', { name: 'パスキーを登録' }));
    await waitFor(() => expect(mockComplete).toHaveBeenCalledWith(
      { token: TOKEN, challengeId: 'c-1', credential: CREDENTIAL }));
    // 開いたときに 1 回・押したときにもう 1 回（開いたときの challenge は期限切れになりうるので使わない）
    expect(service.options).toHaveBeenCalledTimes(2);
    expect(toast.success).toHaveBeenCalledWith('パスキーを登録しました');
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true });
  });

  it('TC-24: # が無いリンクは使えない（API も呼ばない）', async () => {
    mountAt('');
    expect(screen.getByText(UNUSABLE)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'パスキーを登録' })).not.toBeInTheDocument();
    expect(service.options).not.toHaveBeenCalled();
  });

  it('TC-24: 使えないリンク（400）', async () => {
    service.options.mockRejectedValue(axiosError(400));
    mountAt(`#token=${TOKEN}`);
    expect(await screen.findByText(UNUSABLE)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'パスキーを登録' })).not.toBeInTheDocument();
  });

  it('TC-24: 非対応のブラウザでは押せない', async () => {
    mockSupported.mockReturnValue(false);
    mountAt(`#token=${TOKEN}`);
    expect(await screen.findByRole('button', { name: 'パスキーを登録' })).toBeDisabled();
    expect(screen.getByText('このブラウザはパスキーに未対応です')).toBeInTheDocument();
  });

  it('I636 TC-08: 押したときにリンクが使えなくなっていたら（取り直しが 400）、使えないリンクの表示に切り替える', async () => {
    service.options.mockResolvedValueOnce(OPTIONS).mockRejectedValueOnce(axiosError(400));
    mountAt(`#token=${TOKEN}`);
    userEvent.click(await screen.findByRole('button', { name: 'パスキーを登録' }));
    expect(await screen.findByText(UNUSABLE)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'パスキーを登録' })).not.toBeInTheDocument();
    expect(screen.queryByText('ユーザーID『alice』のパスキーを登録します')).not.toBeInTheDocument();
    expect(mockCreate).not.toHaveBeenCalled();
  });

  it.each([429, 500])('I636 TC-08: 押したときの取り直しが %i なら一般の失敗の文で、もう一度押せる', async (status) => {
    service.options.mockResolvedValueOnce(OPTIONS).mockRejectedValueOnce(axiosError(status));
    mountAt(`#token=${TOKEN}`);
    userEvent.click(await screen.findByRole('button', { name: 'パスキーを登録' }));
    expect(await screen.findByText('パスキーを登録できませんでした。もう一度お試しください')).toBeInTheDocument();
    expect(screen.queryByText(UNUSABLE)).not.toBeInTheDocument();
    expect(mockCreate).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByRole('button', { name: 'パスキーを登録' })).toBeEnabled());
    userEvent.click(screen.getByRole('button', { name: 'パスキーを登録' }));
    await waitFor(() => expect(mockComplete).toHaveBeenCalled());
    expect(service.options).toHaveBeenCalledTimes(3);
  });

  it('TC-24: 取り消したら文を出し、もう一度押せる', async () => {
    mockCreate.mockRejectedValueOnce(Object.assign(new Error('cancelled'), { name: 'NotAllowedError' }));
    mountAt(`#token=${TOKEN}`);
    userEvent.click(await screen.findByRole('button', { name: 'パスキーを登録' }));
    expect(await screen.findByText('パスキーを登録できませんでした。もう一度お試しください')).toBeInTheDocument();
    expect(mockComplete).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'パスキーを登録' })).toBeEnabled();
    // やり直しでは challenge を取り直す
    userEvent.click(screen.getByRole('button', { name: 'パスキーを登録' }));
    await waitFor(() => expect(mockComplete).toHaveBeenCalled());
    expect(service.options).toHaveBeenCalledTimes(3);
  });
});
