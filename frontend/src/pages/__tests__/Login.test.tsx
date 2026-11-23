/**
 * ログイン画面の「パスキーでログイン」（I619・TC-20）
 * 失敗の知らせの文は AuthContext のテスト（contexts/__tests__/AuthContext.passkey.test.tsx）で確かめる
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { browserSupportsWebAuthn } from '@simplewebauthn/browser';
import Login from '../Login';

const mockLoginWithPasskey = jest.fn();

jest.mock('@simplewebauthn/browser', () => ({ browserSupportsWebAuthn: jest.fn() }));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ login: jest.fn(), loginWithPasskey: mockLoginWithPasskey }),
}));

const mockSupported = browserSupportsWebAuthn as jest.Mock;

const mount = () =>
  render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<p>ダッシュボードの画面</p>} />
      </Routes>
    </MemoryRouter>
  );

describe('Login のパスキー', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSupported.mockReturnValue(true);
  });

  it('TC-20a: 「パスキーでログイン」が ID・パスワードの欄より前にあり、間に「または」', () => {
    mount();
    const button = screen.getByRole('button', { name: 'パスキーでログイン' });
    const idField = screen.getByLabelText('ユーザーIDまたはメールアドレス');
    const divider = screen.getByText('または');
    // eslint-disable-next-line no-bitwise
    expect(button.compareDocumentPosition(divider) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    // eslint-disable-next-line no-bitwise
    expect(divider.compareDocumentPosition(idField) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('TC-20b: 成功すると /dashboard へ移る', async () => {
    mockLoginWithPasskey.mockResolvedValue(undefined);
    mount();
    userEvent.click(screen.getByRole('button', { name: 'パスキーでログイン' }));
    expect(await screen.findByText('ダッシュボードの画面')).toBeInTheDocument();
  });

  it('TC-20c・d・f: 押している間は押せず、失敗しても画面は移らず入力欄の値は消えない', async () => {
    let fail: (error: Error) => void = () => undefined;
    mockLoginWithPasskey.mockReturnValue(new Promise((_, reject) => { fail = reject; }));
    mount();
    userEvent.type(screen.getByLabelText('ユーザーIDまたはメールアドレス'), 'alice');
    userEvent.click(screen.getByRole('button', { name: 'パスキーでログイン' }));
    await waitFor(() => expect(screen.getByTestId('passkey-login-button')).toBeDisabled());

    fail(new Error('NotAllowedError'));
    await waitFor(() => expect(screen.getByTestId('passkey-login-button')).toBeEnabled());
    expect(screen.queryByText('ダッシュボードの画面')).not.toBeInTheDocument();
    expect(screen.getByLabelText('ユーザーIDまたはメールアドレス')).toHaveValue('alice');
  });

  it('TC-20e: 非対応のブラウザではボタンを押せず、理由を出す', () => {
    mockSupported.mockReturnValue(false);
    mount();
    expect(screen.getByRole('button', { name: 'パスキーでログイン' })).toBeDisabled();
    expect(screen.getByText('このブラウザはパスキーに未対応です')).toBeInTheDocument();
  });
});
