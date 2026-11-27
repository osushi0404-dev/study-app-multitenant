/**
 * メンバー管理（I620・TC-20〜TC-23）
 * 一覧の 4 つの状態・自分の行・キャッシュのキー・発行と取り消し・リンクの表示・追加・パスキーの削除
 */
import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AxiosError, AxiosHeaders } from 'axios';
import toast from 'react-hot-toast';
import MemberManagement from '../MemberManagement';
import { credentialApi, memberService } from '../../services/member.service';
import passkeyService from '../../services/passkey.service';
import { Member } from '../../types/api';

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { error: jest.fn(), success: jest.fn() },
}));

// QR の描き方はライブラリの責任。ここでは QR に入る値だけを確かめる
jest.mock('qrcode.react', () => ({
  QRCodeSVG: ({ value, ...rest }: { value: string; 'aria-label'?: string }) => (
    <svg data-testid="qr" data-value={value} aria-label={rest['aria-label']} />
  ),
}));

let mockUser: { id: string; role: string; can_manage_members: boolean } = {
  id: 'viewer-1', role: 'admin', can_manage_members: true,
};
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: mockUser }),
}));

const mockApi = {
  passkeys: jest.fn(),
  deletePasskey: jest.fn(),
  issueLink: jest.fn(),
  revokeLink: jest.fn(),
};
jest.mock('../../services/member.service', () => ({
  MEMBERS_BASE: '/api/members/',
  ADMIN_USERS_BASE: '/api/admin/users/',
  memberService: { list: jest.fn(), create: jest.fn() },
  credentialApi: jest.fn(() => mockApi),
}));

jest.mock('../../services/passkey.service', () => ({
  __esModule: true,
  default: { list: jest.fn(), reauthWithPassword: jest.fn(), reauthOptions: jest.fn(), reauthWithPasskey: jest.fn() },
  createPasskeyCredential: jest.fn(),
  getPasskeyAssertion: jest.fn(),
}));

const members = memberService as jest.Mocked<typeof memberService>;
const passkeys = passkeyService as jest.Mocked<typeof passkeyService>;

const SELF: Member = {
  id: 'viewer-1', user_id: 'admin_self', role: 'admin', is_active: true, last_login: null,
  created_at: '2026-11-01T00:00:00Z', passkey_count: 1, registration_link_expires_at: null, is_self: true,
};
const TARO: Member = { ...SELF, id: 'm-1', user_id: 'taro', role: 'user', passkey_count: 2, is_self: false };
const HANAKO: Member = {
  ...SELF, id: 'm-2', user_id: 'hanako', role: 'admin', passkey_count: 0, is_self: false,
  registration_link_expires_at: '2026-11-26T06:30:00Z',
};
const page = <T,>(results: T[]) => ({ count: results.length, next: null, previous: null, results });
const LINK = { url: 'http://localhost:3000/passkey-setup#token=abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG', expires_at: '2026-11-26T06:30:00Z' };
const TOKEN = { reauth_token: 'reauth-1', expires_in: 300 };

const axiosError = (status: number, data: unknown = {}) =>
  new AxiosError('failed', String(status), undefined, undefined, {
    status, statusText: '', headers: {}, config: { headers: new AxiosHeaders() }, data,
  });

let queryClient: QueryClient;
const mountPage = () => {
  queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemberManagement />
    </QueryClientProvider>
  );
};

const confirmWithPassword = async () => {
  const dialog = await screen.findByRole('dialog', { name: '本人の確認' });
  userEvent.type(within(dialog).getByLabelText('パスワード'), 'secret');
  userEvent.click(within(dialog).getByRole('button', { name: '確かめる' }));
};

const rowOf = (userId: string) =>
  screen.findByRole('row', { name: (accessibleName) => accessibleName.startsWith(`${userId} `) });

describe('MemberManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUser = { id: 'viewer-1', role: 'admin', can_manage_members: true };
    // CRA の resetMocks が差し替えの中身を毎回空にするので、ここで設定し直す
    (credentialApi as jest.Mock).mockReturnValue(mockApi);
    members.list.mockResolvedValue(page([SELF, HANAKO, TARO]));
    passkeys.list.mockResolvedValue([]);
    passkeys.reauthWithPassword.mockResolvedValue(TOKEN);
    mockApi.issueLink.mockResolvedValue(LINK);
    mockApi.revokeLink.mockResolvedValue(undefined);
    mockApi.passkeys.mockResolvedValue(page([
      { id: 'pk-1', name: '会社の PC', created_at: '2026-11-20T00:00:00Z', last_used_at: null },
    ]));
    mockApi.deletePasskey.mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText: jest.fn().mockResolvedValue(undefined) } });
  });

  // ------------------------------------------------------------- TC-20 ----
  it('TC-20: 行の中身・自分の行・キャッシュのキーに見ている人が入る', async () => {
    mountPage();
    const taro = await rowOf('taro');
    expect(within(taro).getByText('メンバー')).toBeInTheDocument();
    expect(within(taro).getByText('2 個')).toBeInTheDocument();
    expect(within(taro).getByText('なし')).toBeInTheDocument();
    const hanako = await rowOf('hanako');
    expect(within(hanako).getByText('管理者')).toBeInTheDocument();
    expect(within(hanako).getByText('有効（15:30 まで）')).toBeInTheDocument();
    expect(within(hanako).getByRole('button', { name: 'リンクを取り消す' })).toBeInTheDocument();
    expect(within(taro).queryByRole('button', { name: 'リンクを取り消す' })).not.toBeInTheDocument();
    const self = await rowOf('admin_self');
    expect(within(self).getByText('（自分は操作できません）')).toBeInTheDocument();
    expect(within(self).queryByRole('button')).not.toBeInTheDocument();
    const keys = queryClient.getQueryCache().getAll().map((query) => query.queryKey);
    expect(keys).toContainEqual(['members', 'viewer-1', 1]);
  });

  it('TC-20: 読み込み中・失敗・空', async () => {
    members.list.mockReturnValue(new Promise(() => {}));
    mountPage();
    expect(await screen.findByLabelText('メンバーを読み込み中')).toBeInTheDocument();
  });

  it('TC-20: 失敗は再読み込みの操作を出す', async () => {
    members.list.mockRejectedValueOnce(axiosError(500)).mockResolvedValue(page([TARO]));
    mountPage();
    expect(await screen.findByText('メンバーを読み込めませんでした')).toBeInTheDocument();
    userEvent.click(screen.getByRole('button', { name: '再読み込み' }));
    expect(await screen.findByText('taro')).toBeInTheDocument();
  });

  it('TC-20: 空', async () => {
    members.list.mockResolvedValue(page([]));
    mountPage();
    expect(await screen.findByText('メンバーはまだいません')).toBeInTheDocument();
  });

  it('I636 TC-10: メンバー管理を使えない管理者（本人ひとり・無効・共有の personal の組織）には出さない', async () => {
    mockUser = { id: 'solo', role: 'admin', can_manage_members: false };
    mountPage();
    expect(screen.getByText('このページにアクセスする権限がありません')).toBeInTheDocument();
    expect(members.list).not.toHaveBeenCalled();
  });

  // ------------------------------------------------------------- TC-21 ----
  it('TC-21: 確認 → 本人確認 → リンクの表示（QR の値・期限・警告）→ コピー → 閉じると消える', async () => {
    mountPage();
    const taro = await rowOf('taro');
    userEvent.click(within(taro).getByRole('button', { name: '登録用リンク' }));
    const confirm = await screen.findByRole('dialog', { name: '登録用リンクの発行' });
    expect(within(confirm).getByText('『taro』の登録用リンクを発行しますか？')).toBeInTheDocument();
    expect(within(confirm).getByText('今のパスキーはすべて使えなくなり、ログイン中の端末もログアウトされます。'))
      .toBeInTheDocument();
    userEvent.click(within(confirm).getByRole('button', { name: 'キャンセル' }));
    await waitFor(() => expect(screen.queryByRole('dialog', { name: '登録用リンクの発行' })).not.toBeInTheDocument());
    expect(mockApi.issueLink).not.toHaveBeenCalled();

    userEvent.click(within(taro).getByRole('button', { name: '登録用リンク' }));
    userEvent.click(within(await screen.findByRole('dialog', { name: '登録用リンクの発行' }))
      .getByRole('button', { name: '発行する' }));
    await confirmWithPassword();

    const dialog = await screen.findByRole('dialog', { name: '『taro』の登録用リンク' });
    expect(mockApi.issueLink).toHaveBeenCalledWith('reauth-1', 'm-1');
    expect(within(dialog).getByTestId('qr')).toHaveAttribute('data-value', LINK.url);
    expect(within(dialog).getByTestId('qr')).toHaveAttribute('aria-label', '登録用リンクの QR コード');
    expect(within(dialog).getByLabelText('リンク')).toHaveValue(LINK.url);
    expect(within(dialog).getByText('有効期限: 2026/11/26 15:30（1 時間・1 回だけ）')).toBeInTheDocument();
    expect(within(dialog).getByText('この画面を閉じると、リンクは二度と表示できません')).toBeInTheDocument();
    expect(toast.success).toHaveBeenCalledWith('登録用リンクを発行しました');

    userEvent.click(within(dialog).getByRole('button', { name: 'コピー' }));
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith(LINK.url));
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('リンクをコピーしました'));

    userEvent.click(within(dialog).getByRole('button', { name: '閉じる' }));
    await waitFor(() => expect(screen.queryByDisplayValue(LINK.url)).not.toBeInTheDocument());
  });

  it('TC-21: コピーに失敗したら選んでコピーするよう案内する', async () => {
    (navigator.clipboard.writeText as jest.Mock).mockRejectedValue(new Error('denied'));
    mountPage();
    userEvent.click(within(await rowOf('taro')).getByRole('button', { name: '登録用リンク' }));
    userEvent.click(within(await screen.findByRole('dialog', { name: '登録用リンクの発行' }))
      .getByRole('button', { name: '発行する' }));
    await confirmWithPassword();
    const dialog = await screen.findByRole('dialog', { name: '『taro』の登録用リンク' });
    userEvent.click(within(dialog).getByRole('button', { name: 'コピー' }));
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('コピーできませんでした。リンクを選んでコピーしてください'));
  });

  it('TC-21: リンクの取り消し', async () => {
    mountPage();
    userEvent.click(within(await rowOf('hanako')).getByRole('button', { name: 'リンクを取り消す' }));
    const confirm = await screen.findByRole('dialog', { name: '登録用リンクの取り消し' });
    expect(within(confirm).getByText('『hanako』の登録用リンクを取り消しますか？')).toBeInTheDocument();
    userEvent.click(within(confirm).getByRole('button', { name: '取り消す' }));
    await confirmWithPassword();
    await waitFor(() => expect(mockApi.revokeLink).toHaveBeenCalledWith('reauth-1', 'm-2'));
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('登録用リンクを取り消しました'));
  });

  it('TC-21: 発行の 400 はサーバーの文を出す', async () => {
    mockApi.issueLink.mockRejectedValue(axiosError(400, {
      error: { main_message: '入力内容にエラーがあります', sub_message: '無効の利用者には発行できません', details: {} },
    }));
    mountPage();
    userEvent.click(within(await rowOf('taro')).getByRole('button', { name: '登録用リンク' }));
    userEvent.click(within(await screen.findByRole('dialog', { name: '登録用リンクの発行' }))
      .getByRole('button', { name: '発行する' }));
    await confirmWithPassword();
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('無効の利用者には発行できません'));
  });

  // ------------------------------------------------------------- TC-22 ----
  it('TC-22: 追加の欄の検証', async () => {
    mountPage();
    userEvent.click(await screen.findByRole('button', { name: 'メンバーを追加' }));
    const dialog = await screen.findByRole('dialog', { name: 'メンバーを追加' });
    const input = within(dialog).getByLabelText('ユーザーID');
    userEvent.click(input);
    userEvent.tab();
    expect(await within(dialog).findByText('ユーザーIDを入力してください')).toBeInTheDocument();
    userEvent.type(input, 'ab');
    expect(await within(dialog).findByText('3文字以上で入力してください')).toBeInTheDocument();
    userEvent.clear(input);
    userEvent.type(input, 'bad-id');
    expect(await within(dialog).findByText('半角英数字とアンダースコアのみ使用できます')).toBeInTheDocument();
    expect(members.create).not.toHaveBeenCalled();
  });

  it('TC-22: サーバーの誤りは欄の下に出る', async () => {
    members.create.mockRejectedValue(axiosError(400, {
      error: { main_message: '入力内容にエラーがあります', sub_message: 'このユーザーIDは既に使用されています', details: {} },
    }));
    mountPage();
    userEvent.click(await screen.findByRole('button', { name: 'メンバーを追加' }));
    const dialog = await screen.findByRole('dialog', { name: 'メンバーを追加' });
    userEvent.type(within(dialog).getByLabelText('ユーザーID'), 'taro');
    userEvent.click(within(dialog).getByRole('button', { name: '追加してリンクを発行' }));
    expect(await within(dialog).findByText('このユーザーIDは既に使用されています')).toBeInTheDocument();
  });

  it('TC-22: 追加 → 本人確認 → 発行 → リンクの表示（追加した人が今のページに無くても・F1）', async () => {
    const NEW: Member = { ...TARO, id: 'm-9', user_id: 'zzz_member', passkey_count: 0 };
    members.create.mockResolvedValue(NEW);
    // 追加した人は別のページに載る（今のページの一覧には出てこない）
    members.list.mockResolvedValue(page([SELF, TARO]));
    mountPage();
    userEvent.click(await screen.findByRole('button', { name: 'メンバーを追加' }));
    const dialog = await screen.findByRole('dialog', { name: 'メンバーを追加' });
    userEvent.type(within(dialog).getByLabelText('ユーザーID'), 'zzz_member');
    userEvent.click(within(dialog).getByRole('button', { name: '追加してリンクを発行' }));
    await waitFor(() => expect(members.create).toHaveBeenCalledWith('zzz_member'));
    await confirmWithPassword();
    expect(await screen.findByRole('dialog', { name: '『zzz_member』の登録用リンク' })).toBeInTheDocument();
    expect(screen.queryByText('zzz_member', { selector: 'td' })).not.toBeInTheDocument();
    expect(mockApi.issueLink).toHaveBeenCalledWith('reauth-1', 'm-9');
  });

  // ------------------------------------------------------- I636 TC-09（F8） ----
  it('I636 TC-09: 行の発行のダイアログは、閉じる間も中身を残し、閉じ終わったら値を捨てる', async () => {
    mountPage();
    userEvent.click(within(await rowOf('taro')).getByRole('button', { name: '登録用リンク' }));
    userEvent.click(within(await screen.findByRole('dialog', { name: '登録用リンクの発行' }))
      .getByRole('button', { name: '発行する' }));
    await confirmWithPassword();
    const dialog = await screen.findByRole('dialog', { name: '『taro』の登録用リンク' });
    // fireEvent は act の中で動くので、押した後の描き直しが終わってから確かめられる（閉じるアニメーションは終わる前）
    fireEvent.click(within(dialog).getByRole('button', { name: '閉じる' }));
    // 閉じるアニメーションの間（閉じ終わる前）も、見出しとリンクの欄が残る
    expect(screen.getByText('『taro』の登録用リンク')).toBeInTheDocument();
    expect(screen.getByDisplayValue(LINK.url)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText('『taro』の登録用リンク')).not.toBeInTheDocument());
    expect(screen.queryByDisplayValue(LINK.url)).not.toBeInTheDocument();
  });

  it('I636 TC-09: 追加の流れの発行の間は、その人の［登録用リンク］と［メンバーを追加］を押せず、発行は 1 回', async () => {
    const NEW: Member = { ...TARO, id: 'm-9', user_id: 'zzz_member', passkey_count: 0 };
    members.create.mockResolvedValue(NEW);
    members.list.mockResolvedValueOnce(page([SELF, TARO])).mockResolvedValue(page([SELF, TARO, NEW]));
    let resolveIssue: (link: typeof LINK) => void = () => undefined;
    mockApi.issueLink.mockReturnValue(new Promise((resolve) => { resolveIssue = resolve; }));
    mountPage();
    userEvent.click(await screen.findByRole('button', { name: 'メンバーを追加' }));
    const add = await screen.findByRole('dialog', { name: 'メンバーを追加' });
    userEvent.type(within(add).getByLabelText('ユーザーID'), 'zzz_member');
    userEvent.click(within(add).getByRole('button', { name: '追加してリンクを発行' }));
    await confirmWithPassword();
    await waitFor(() => expect(mockApi.issueLink).toHaveBeenCalledTimes(1));
    const row = await rowOf('zzz_member');
    expect(within(row).getByRole('button', { name: '登録用リンク' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'メンバーを追加' })).toBeDisabled();

    resolveIssue(LINK);
    const dialog = await screen.findByRole('dialog', { name: '『zzz_member』の登録用リンク' });
    expect(mockApi.issueLink).toHaveBeenCalledTimes(1);
    // ダイアログの裏（aria-hidden）にあるので hidden を付けて探す
    await waitFor(() => expect(screen.getByRole('button', { name: 'メンバーを追加', hidden: true })).toBeEnabled());

    // 閉じる間も見出しが『』にならない
    fireEvent.click(within(dialog).getByRole('button', { name: '閉じる' }));
    expect(screen.getByText('『zzz_member』の登録用リンク')).toBeInTheDocument();
    expect(screen.queryByText('『』の登録用リンク')).not.toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText('『zzz_member』の登録用リンク')).not.toBeInTheDocument());
  });

  // ------------------------------------------------------ I636 TC-11（F12） ----
  it('I636 TC-11: 表の中では操作のボタンを横に並べ、ユーザー ID の欄は最小の幅を持つ', async () => {
    mountPage();
    const taro = await rowOf('taro');
    expect(within(taro).getByRole('group', { name: '『taro』の操作' })).toHaveStyle({ flexWrap: 'nowrap' });
    expect(within(taro).getByText('taro')).toHaveStyle({ minWidth: '120px' });
    expect(screen.getByRole('region', { name: 'メンバーの一覧の表（横に動かせます）' })).toHaveAttribute('tabindex', '0');
  });

  // ------------------------------------------------------------- TC-23 ----
  it('TC-23: パスキーの一覧と削除（確認 → 本人確認）', async () => {
    mountPage();
    userEvent.click(within(await rowOf('taro')).getByRole('button', { name: 'パスキー' }));
    const dialog = await screen.findByRole('dialog', { name: '『taro』のパスキー' });
    expect(await within(dialog).findByText('会社の PC')).toBeInTheDocument();
    expect(within(dialog).getByText('最後に使った日 まだ使っていません')).toBeInTheDocument();
    userEvent.click(within(dialog).getByRole('button', { name: '『会社の PC』を削除' }));
    const confirm = await screen.findByRole('dialog', { name: 'パスキーの削除' });
    expect(within(confirm).getByText('『会社の PC』を削除しますか？このパスキーではログインできなくなります'))
      .toBeInTheDocument();
    userEvent.click(within(confirm).getByRole('button', { name: '削除' }));
    await confirmWithPassword();
    await waitFor(() => expect(mockApi.deletePasskey).toHaveBeenCalledWith('reauth-1', 'm-1', 'pk-1'));
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('パスキーを削除しました'));
    expect(credentialApi).toHaveBeenCalledWith('/api/members/');
    const keys = queryClient.getQueryCache().getAll().map((query) => query.queryKey);
    expect(keys).toContainEqual(['member-passkeys', 'viewer-1', '/api/members/', 'm-1']);
  });

  it('TC-23: パスキーの一覧が空', async () => {
    mockApi.passkeys.mockResolvedValue(page([]));
    mountPage();
    userEvent.click(within(await rowOf('taro')).getByRole('button', { name: 'パスキー' }));
    const dialog = await screen.findByRole('dialog', { name: '『taro』のパスキー' });
    expect(await within(dialog).findByText('パスキーはまだありません')).toBeInTheDocument();
  });
});
