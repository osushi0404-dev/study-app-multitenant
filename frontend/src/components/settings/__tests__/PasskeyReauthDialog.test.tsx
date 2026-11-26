/**
 * 「本人の確認」のダイアログ（I619・TC-22）
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError, AxiosHeaders } from 'axios';
import PasskeyReauthDialog from '../PasskeyReauthDialog';
import passkeyService, { getPasskeyAssertion } from '../../../services/passkey.service';

jest.mock('../../../services/passkey.service', () => ({
  __esModule: true,
  default: { reauthWithPassword: jest.fn(), reauthOptions: jest.fn(), reauthWithPasskey: jest.fn() },
  getPasskeyAssertion: jest.fn(),
}));

const service = passkeyService as jest.Mocked<typeof passkeyService>;
const mockAssertion = getPasskeyAssertion as jest.Mock;
const TOKEN = { reauth_token: 'token-1', expires_in: 300 };

const badRequest = (subMessage: string) =>
  new AxiosError('failed', '400', undefined, undefined, {
    status: 400, statusText: '', headers: {}, config: { headers: new AxiosHeaders() },
    data: { error: { main_message: '入力内容にエラーがあります', sub_message: subMessage, details: {} } },
  });

const mount = (hasPasskeys: boolean) => {
  const onSuccess = jest.fn();
  const onCancel = jest.fn();
  render(<PasskeyReauthDialog open hasPasskeys={hasPasskeys} onSuccess={onSuccess} onCancel={onCancel} />);
  return { onSuccess, onCancel };
};

describe('PasskeyReauthDialog', () => {
  beforeEach(() => jest.clearAllMocks());

  it('TC-22a: パスキーが 0 個なら「パスキーで確かめる」は無く、パスワードで確かめる', async () => {
    service.reauthWithPassword.mockResolvedValue(TOKEN);
    const { onSuccess } = mount(false);
    expect(screen.getByRole('dialog', { name: '本人の確認' })).toBeInTheDocument();
    expect(screen.getByText('続けるには、本人であることを確かめます')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'パスキーで確かめる' })).not.toBeInTheDocument();

    userEvent.type(screen.getByLabelText('パスワード'), 'secret');
    userEvent.click(screen.getByRole('button', { name: '確かめる' }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(TOKEN));
    expect(service.reauthWithPassword).toHaveBeenCalledWith('secret');
  });

  it('TC-22b: パスキーがあれば「パスキーで確かめる」で options と assertion を使う', async () => {
    service.reauthOptions.mockResolvedValue({ challenge_id: 'c-1', options: { challenge: 'abc' } });
    mockAssertion.mockResolvedValue({ id: 'cred' });
    service.reauthWithPasskey.mockResolvedValue(TOKEN);
    const { onSuccess } = mount(true);

    userEvent.click(screen.getByRole('button', { name: 'パスキーで確かめる' }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(TOKEN));
    expect(service.reauthWithPasskey).toHaveBeenCalledWith('c-1', { id: 'cred' });
  });

  it('TC-22c: 誤ったパスワードは欄の下に理由を出し、入力を消さない', async () => {
    service.reauthWithPassword.mockRejectedValue(badRequest('パスワードが正しくありません'));
    const { onSuccess } = mount(false);
    userEvent.type(screen.getByLabelText('パスワード'), 'wrong');
    userEvent.click(screen.getByRole('button', { name: '確かめる' }));
    expect(await screen.findByText('パスワードが正しくありません')).toBeInTheDocument();
    expect(screen.getByLabelText('パスワード')).toHaveValue('wrong');
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it('TC-22d: Esc で閉じると取り消し（API を呼ばない）', async () => {
    const { onCancel } = mount(true);
    userEvent.keyboard('{Escape}');
    await waitFor(() => expect(onCancel).toHaveBeenCalled());
    expect(service.reauthWithPassword).not.toHaveBeenCalled();
    expect(service.reauthOptions).not.toHaveBeenCalled();
  });
});
