/**
 * 会員登録の画面（I539）
 * - TC-30: 招待なしは科目選びの段を出さず「登録する」で科目なしの登録
 * - TC-31: 招待先に科目が無ければ同じく段を出さない
 * - TC-32: 招待先に科目があれば今のまま 2 段（回帰）
 * - TC-33: 招待先の科目を読めなければ、科目なしで送らせず再読み込みを出す
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Register from '../Register';
import apiClient from '../../services/api';
import SubjectService from '../../services/subjectService';

jest.mock('../../services/api');

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { error: jest.fn(), success: jest.fn() },
}));

const mockRegister = jest.fn();
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ register: mockRegister }),
}));

jest.mock('../../services/subjectService', () => ({
  __esModule: true,
  default: { getSubjects: jest.fn() },
}));

jest.mock('../../utils/validation', () => ({
  checkEmailAvailability: () => Promise.resolve({ valid: true }),
  checkUserIdAvailability: () => Promise.resolve({ valid: true }),
  passwordStrengthCheck: () => ({ score: 4, feedback: [] }),
}));

jest.mock('../../components/PasswordStrengthIndicator', () => ({
  PasswordStrengthIndicator: () => null,
}));

const mockGet = apiClient.get as jest.Mock;
const mockGetSubjects = SubjectService.getSubjects as jest.Mock;
const PASSWORD = 'Passw0rdI539'; // pragma: allowlist secret（テスト用ダミー値）

const renderAt = (path: string) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/register" element={<Register />} />
          <Route path="/register/:organizationSlug" element={<Register />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

const fillBasicInfo = async () => {
  await userEvent.type(screen.getByLabelText('メールアドレス'), 'i539@example.com');
  await userEvent.type(screen.getByLabelText('ユーザーID'), 'i539_user');
  await userEvent.type(screen.getByLabelText('パスワード'), PASSWORD);
  await userEvent.type(screen.getByLabelText('パスワード確認'), PASSWORD);
};

const validOrg = () =>
  mockGet.mockImplementation((url: string) =>
    url.startsWith('/api/organizations/validate-slug/')
      ? Promise.resolve({ data: { valid: true, organization_name: '組織X' } })
      : Promise.resolve({ data: {} })
  );

describe('Register', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRegister.mockResolvedValue(undefined);
  });

  it('TC-30: 招待なしは段を出さず、「登録する」で科目なしの登録をする', async () => {
    renderAt('/register');

    expect(screen.queryByText('科目選択')).not.toBeInTheDocument();
    await fillBasicInfo();
    await userEvent.click(screen.getByRole('button', { name: '登録する' }));

    await waitFor(() => expect(mockRegister).toHaveBeenCalledTimes(1));
    expect(mockRegister).toHaveBeenCalledWith(
      'i539@example.com', 'i539_user', PASSWORD, '', '', undefined, []
    );
    expect(
      await screen.findByText('登録が完了しました。メール認証を行ってからログインしてください。')
    ).toBeInTheDocument();
    expect(mockGetSubjects).not.toHaveBeenCalled();
  });

  it('TC-31: 招待先に科目が無ければ、段を出さず「登録する」で科目なしの登録をする', async () => {
    validOrg();
    mockGetSubjects.mockResolvedValue([]);
    renderAt('/register/org-x');

    const submit = await screen.findByRole('button', { name: '登録する' });
    expect(screen.queryByText('科目選択')).not.toBeInTheDocument();
    await fillBasicInfo();
    await userEvent.click(submit);

    await waitFor(() => expect(mockRegister).toHaveBeenCalledTimes(1));
    expect(mockRegister).toHaveBeenCalledWith(
      'i539@example.com', 'i539_user', PASSWORD, '', '', 'org-x', []
    );
    expect(screen.queryByText(/利用可能な科目がありません/)).not.toBeInTheDocument();
  });

  it('TC-32: 招待先に科目があれば、2 段目で選んでから登録する', async () => {
    validOrg();
    mockGetSubjects.mockResolvedValue([{ id: 1, name: '英語' }, { id: 2, name: '数学' }]);
    renderAt('/register/org-x');

    await userEvent.click(await screen.findByRole('button', { name: '登録して次へ' }));
    expect(mockRegister).not.toHaveBeenCalled(); // 入力の誤りで 2 段目に進まない
    await fillBasicInfo();
    expect(screen.getByText('科目選択')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '登録して次へ' }));

    const finish = await screen.findByRole('button', { name: '登録を完了' });
    expect(screen.getAllByRole('checkbox')).toHaveLength(2);
    expect(finish).toBeDisabled();
    await userEvent.click(screen.getByLabelText('英語'));
    await userEvent.click(finish);

    await waitFor(() => expect(mockRegister).toHaveBeenCalledTimes(1));
    expect(mockRegister).toHaveBeenCalledWith(
      'i539@example.com', 'i539_user', PASSWORD, '', '', 'org-x', [1]
    );
  });

  it('TC-33: 招待先の科目を読めなければ、送らせずに再読み込みを出し、読めたら進める', async () => {
    validOrg();
    mockGetSubjects.mockRejectedValueOnce(new Error('500'));
    renderAt('/register/org-x');

    expect(await screen.findByText('科目を読み込めませんでした')).toBeInTheDocument();
    await fillBasicInfo();
    const submit = screen.getByRole('button', { name: '登録する' });
    expect(submit).toBeDisabled();
    // 入力欄で Enter を押しても送られない（ボタンが無効でも Enter の送信は起きうるので、送信の処理でも止める）
    await userEvent.type(screen.getByLabelText('パスワード確認'), '{enter}');
    await new Promise((resolve) => setTimeout(resolve, 50)); // 送信の非同期の確かめ（入力の検証など）を待つ
    expect(mockRegister).not.toHaveBeenCalled();
    expect(screen.queryByText(/登録が完了しました/)).not.toBeInTheDocument();

    mockGetSubjects.mockResolvedValueOnce([{ id: 1, name: '英語' }, { id: 2, name: '数学' }]);
    await userEvent.click(screen.getByRole('button', { name: '再読み込み' }));
    expect(await screen.findByRole('button', { name: '登録して次へ' })).toBeEnabled();
  });
});
