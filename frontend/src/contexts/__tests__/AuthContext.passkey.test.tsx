/**
 * AuthContext の loginWithPasskey（I619・TC-20 の知らせの文と保存）
 * 成功はパスワードのログインと同じ保存（establishSession）を通り、失敗は決まった文を出す
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'react-hot-toast';
import { AuthProvider, useAuth } from '../AuthContext';
import passkeyService, { getPasskeyAssertion } from '../../services/passkey.service';
import apiClient from '../../services/api';
import { showSuccessToast } from '../../components/ErrorToast';

jest.mock('react-hot-toast', () => ({ toast: Object.assign(jest.fn(), { error: jest.fn(), dismiss: jest.fn() }) }));
jest.mock('../../components/ErrorToast', () => ({ showErrorToast: jest.fn(), showSuccessToast: jest.fn() }));
jest.mock('../../services/api', () => ({
  __esModule: true,
  default: { setAuthToken: jest.fn(), removeAuthToken: jest.fn() },
}));
jest.mock('../../services/auth.service', () => ({
  __esModule: true,
  default: { getStoredUser: () => null, getAccessToken: () => null },
}));
jest.mock('../../services/passkey.service', () => ({
  __esModule: true,
  default: { loginOptions: jest.fn(), login: jest.fn() },
  getPasskeyAssertion: jest.fn(),
}));

const service = passkeyService as jest.Mocked<typeof passkeyService>;
const mockAssertion = getPasskeyAssertion as jest.Mock;
const USER = { id: 'u-1', user_id: 'alice', email: null, role: 'user' };

function Probe() {
  const { user, loginWithPasskey } = useAuth();
  return (
    <>
      <p>{user ? `ログイン中: ${user.user_id}` : '未ログイン'}</p>
      <button type="button" onClick={() => loginWithPasskey().catch(() => undefined)}>試す</button>
    </>
  );
}

const mount = () => render(<AuthProvider><Probe /></AuthProvider>);

describe('AuthContext.loginWithPasskey', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    service.loginOptions.mockResolvedValue({ challenge_id: 'c-1', options: { challenge: 'abc' } });
    mockAssertion.mockResolvedValue({ id: 'cred' });
  });

  it('TC-20b: 成功するとパスワードのログインと同じく保存し「ログインしました」', async () => {
    service.login.mockResolvedValue({ access: 'a', refresh: 'r', user: USER as never });
    mount();
    userEvent.click(await screen.findByRole('button', { name: '試す' }));

    expect(await screen.findByText('ログイン中: alice')).toBeInTheDocument();
    expect(service.login).toHaveBeenCalledWith('c-1', { id: 'cred' });
    expect(localStorage.getItem('accessToken')).toBe('a');
    expect(localStorage.getItem('refreshToken')).toBe('r');
    expect(apiClient.setAuthToken).toHaveBeenCalledWith('a');
    expect(showSuccessToast).toHaveBeenCalledWith('ログインしました');
  });

  it('TC-20c・d: 取り消し・API の失敗はどちらも決まった文を出し、ログインしない', async () => {
    mockAssertion.mockRejectedValueOnce(Object.assign(new Error('cancel'), { name: 'NotAllowedError' }));
    service.login.mockRejectedValueOnce(new Error('400'));
    mount();
    const button = await screen.findByRole('button', { name: '試す' });

    userEvent.click(button);
    await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1));
    userEvent.click(button);
    await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(2));

    expect(toast.error).toHaveBeenCalledWith(
      'パスキーでログインできませんでした。もう一度試すか、パスワードでログインしてください');
    expect(screen.getByText('未ログイン')).toBeInTheDocument();
    expect(localStorage.getItem('accessToken')).toBeNull();
  });
});
