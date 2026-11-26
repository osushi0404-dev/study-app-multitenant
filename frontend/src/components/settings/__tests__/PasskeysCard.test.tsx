/**
 * 設定画面の「パスキー」の欄（I619・TC-21）
 * 一覧・登録・名前の変更・削除と、登録・削除の前の本人の確認
 */
import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AxiosError, AxiosHeaders } from 'axios';
import toast from 'react-hot-toast';
import { browserSupportsWebAuthn } from '@simplewebauthn/browser';
import PasskeysCard from '../PasskeysCard';
import passkeyService, { createPasskeyCredential } from '../../../services/passkey.service';

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { error: jest.fn(), success: jest.fn() },
}));

jest.mock('@simplewebauthn/browser', () => ({ browserSupportsWebAuthn: jest.fn() }));

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user-1' } }),
}));

jest.mock('../../../services/passkey.service', () => ({
  __esModule: true,
  default: {
    list: jest.fn(),
    registerOptions: jest.fn(),
    register: jest.fn(),
    rename: jest.fn(),
    remove: jest.fn(),
    reauthWithPassword: jest.fn(),
    reauthOptions: jest.fn(),
    reauthWithPasskey: jest.fn(),
  },
  createPasskeyCredential: jest.fn(),
  getPasskeyAssertion: jest.fn(),
}));

const service = passkeyService as jest.Mocked<typeof passkeyService>;
const mockCreate = createPasskeyCredential as jest.Mock;
const mockSupported = browserSupportsWebAuthn as jest.Mock;

const WINDOWS = { id: 'pk-1', name: 'Windows の Chrome', created_at: '2026-11-22T01:00:00Z', last_used_at: '2026-11-23T02:00:00Z' };
const IPHONE = { id: 'pk-2', name: 'iPhone の Safari', created_at: '2026-11-20T01:00:00Z', last_used_at: null };
const OPTIONS = { challenge_id: 'c-1', options: { challenge: 'abc' } };
const TOKEN = { reauth_token: 'token-1', expires_in: 300 };

const axiosError = (status: number, data: unknown = {}) =>
  new AxiosError('failed', String(status), undefined, undefined, {
    status, statusText: '', headers: {}, config: { headers: new AxiosHeaders() }, data,
  });

const mountCard = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <PasskeysCard />
    </QueryClientProvider>
  );
};

const confirmWithPassword = async () => {
  const dialog = await screen.findByRole('dialog', { name: '本人の確認' });
  userEvent.type(within(dialog).getByLabelText('パスワード'), 'secret');
  userEvent.click(within(dialog).getByRole('button', { name: '確かめる' }));
};

describe('PasskeysCard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSupported.mockReturnValue(true);
    service.list.mockResolvedValue([WINDOWS, IPHONE]);
    service.registerOptions.mockResolvedValue(OPTIONS);
    service.register.mockResolvedValue(WINDOWS);
    service.reauthWithPassword.mockResolvedValue(TOKEN);
    service.remove.mockResolvedValue(undefined);
    service.rename.mockResolvedValue({ ...WINDOWS, name: '会社の PC' });
    mockCreate.mockResolvedValue({ id: 'cred' });
  });

  it('TC-21a・b: 読み込み中の後、失敗なら「再読み込み」で取り直す', async () => {
    service.list.mockRejectedValueOnce(axiosError(500));
    mountCard();
    expect(screen.getByLabelText('パスキーを読み込み中')).toBeInTheDocument();
    expect(await screen.findByText('パスキーを読み込めませんでした')).toBeInTheDocument();
    userEvent.click(screen.getByRole('button', { name: '再読み込み' }));
    expect(await screen.findByText('Windows の Chrome')).toBeInTheDocument();
    expect(service.list).toHaveBeenCalledTimes(2);
  });

  it('TC-21c: 0 個なら「パスキーはまだありません」と「パスキーを登録」', async () => {
    service.list.mockResolvedValue([]);
    mountCard();
    expect(await screen.findByText('パスキーはまだありません')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'パスキーを登録' })).toBeEnabled();
  });

  it('TC-21d: 名前・登録日・最後に使った日（無ければ「まだ使っていません」）と、どのパスキーかが分かるボタン', async () => {
    mountCard();
    expect(await screen.findByText('Windows の Chrome')).toBeInTheDocument();
    expect(screen.getByText('登録 2026/11/22')).toBeInTheDocument();
    expect(screen.getByText('最後に使った日 2026/11/23')).toBeInTheDocument();
    expect(screen.getByText('最後に使った日 まだ使っていません')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '『Windows の Chrome』の名前を変える' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '『iPhone の Safari』を削除' })).toBeInTheDocument();
    expect(screen.getByText('指紋・顔・PIN でパスワードなしにログインできます')).toBeInTheDocument();
  });

  it('TC-21e・f: 本人の確認の後に登録し、5 分以内の 2 回目は確認を出さない', async () => {
    mountCard();
    await screen.findByText('Windows の Chrome');
    userEvent.click(screen.getByRole('button', { name: 'パスキーを登録' }));
    await confirmWithPassword();

    await waitFor(() => expect(service.register).toHaveBeenCalledWith('token-1', 'c-1', { id: 'cred' }));
    expect(service.reauthWithPassword).toHaveBeenCalledWith('secret');
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('パスキーを登録しました'));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    userEvent.click(await screen.findByRole('button', { name: 'パスキーを登録' }));
    await waitFor(() => expect(service.register).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole('dialog', { name: '本人の確認' })).not.toBeInTheDocument();
    expect(service.reauthWithPassword).toHaveBeenCalledTimes(1);
  });

  it('TC-21g: 同じ端末で 2 回目は「この端末のパスキーはすでに登録されています」', async () => {
    mockCreate.mockRejectedValue(Object.assign(new Error('dup'), { name: 'InvalidStateError' }));
    mountCard();
    await screen.findByText('Windows の Chrome');
    userEvent.click(screen.getByRole('button', { name: 'パスキーを登録' }));
    await confirmWithPassword();
    expect(await screen.findByText('この端末のパスキーはすでに登録されています')).toBeInTheDocument();
    expect(service.register).not.toHaveBeenCalled();
  });

  it('TC-21h: 削除は確認の文 →「削除」→ 本人の確認 → 印つきで削除', async () => {
    mountCard();
    userEvent.click(await screen.findByRole('button', { name: '『Windows の Chrome』を削除' }));
    const confirm = await screen.findByRole('dialog', { name: 'パスキーの削除' });
    expect(within(confirm).getByText('『Windows の Chrome』を削除しますか？このパスキーではログインできなくなります'))
      .toBeInTheDocument();
    userEvent.click(within(confirm).getByRole('button', { name: '削除' }));
    await confirmWithPassword();

    await waitFor(() => expect(service.remove).toHaveBeenCalledWith('token-1', 'pk-1'));
    expect(toast.success).toHaveBeenCalledWith('パスキーを削除しました');
  });

  it('TC-21i: 確認のダイアログで「キャンセル」なら消さない', async () => {
    mountCard();
    userEvent.click(await screen.findByRole('button', { name: '『Windows の Chrome』を削除' }));
    userEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'キャンセル' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(service.remove).not.toHaveBeenCalled();
  });

  it('TC-21j: 名前は空・65 文字なら保存しない。「会社の PC」は保存して知らせる', async () => {
    mountCard();
    userEvent.click(await screen.findByRole('button', { name: '『Windows の Chrome』の名前を変える' }));
    const dialog = await screen.findByRole('dialog', { name: '名前を変える' });
    const field = within(dialog).getByLabelText('名前');

    userEvent.clear(field);
    userEvent.click(within(dialog).getByRole('button', { name: '保存' }));
    expect(await within(dialog).findByText('名前を入力してください')).toBeInTheDocument();
    userEvent.type(field, 'あ'.repeat(65));
    userEvent.click(within(dialog).getByRole('button', { name: '保存' }));
    expect(await within(dialog).findByText('名前は64文字までです')).toBeInTheDocument();
    expect(service.rename).not.toHaveBeenCalled();

    userEvent.clear(field);
    userEvent.type(field, '会社の PC');
    userEvent.click(within(dialog).getByRole('button', { name: '保存' }));
    await waitFor(() => expect(service.rename).toHaveBeenCalledWith('pk-1', '会社の PC'));
    expect(toast.success).toHaveBeenCalledWith('名前を変えました');
  });

  it('TC-21k: 削除が 403 なら印を捨てて本人の確認をもう一度出す', async () => {
    service.remove.mockRejectedValueOnce(axiosError(403)).mockResolvedValueOnce(undefined);
    service.reauthWithPassword.mockResolvedValueOnce(TOKEN).mockResolvedValueOnce({ ...TOKEN, reauth_token: 'token-2' });
    mountCard();
    userEvent.click(await screen.findByRole('button', { name: '『Windows の Chrome』を削除' }));
    userEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: '削除' }));
    await confirmWithPassword();
    await confirmWithPassword();
    await waitFor(() => expect(service.remove).toHaveBeenLastCalledWith('token-2', 'pk-1'));
  });

  it('TC-21l: 非対応のブラウザでは「パスキーを登録」を押せず、理由を出す', async () => {
    mockSupported.mockReturnValue(false);
    mountCard();
    expect(await screen.findByText('Windows の Chrome')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'パスキーを登録' })).toBeDisabled();
    expect(screen.getByText('このブラウザはパスキーに未対応です')).toBeInTheDocument();
  });
});
