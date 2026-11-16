/**
 * 設定画面の「学ぶ科目」のカード（I494・TC-20〜TC-28）
 * 組織の科目をチェックで選び、保存の応答でダッシュボードが使うキャッシュを書き換える
 */
import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { AxiosError, AxiosHeaders } from 'axios';
import toast from 'react-hot-toast';
import LearningSubjectsCard from '../LearningSubjectsCard';
import SubjectService from '../../../services/subjectService';
import { userSubjectsKey } from '../../../hooks/useUserSubjects';

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { error: jest.fn(), success: jest.fn() },
}));

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user-1' } }),
}));

jest.mock('../../../services/subjectService', () => ({
  __esModule: true,
  default: { getUserSubjects: jest.fn(), getAvailableSubjects: jest.fn(), updateUserSubjects: jest.fn() },
}));

const mockGetUserSubjects = SubjectService.getUserSubjects as jest.Mock;
const mockGetAvailable = SubjectService.getAvailableSubjects as jest.Mock;
const mockUpdate = SubjectService.updateUserSubjects as jest.Mock;

const AVAILABLE = [
  { id: 1, name: '数学', description: '' },
  { id: 2, name: '英語', description: '英文法' },
  { id: 3, name: '物理', description: '' },
];
const SAVE = '学ぶ科目を保存';

const axiosError = (status: number, data: unknown) =>
  new AxiosError('failed', String(status), undefined, undefined, {
    status, statusText: '', headers: {}, config: { headers: new AxiosHeaders() }, data,
  });

const mountCard = (path = '/settings') => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <LearningSubjectsCard />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return queryClient;
};

const checkbox = (name: string) => screen.findByRole('checkbox', { name });

describe('LearningSubjectsCard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetAvailable.mockResolvedValue(AVAILABLE);
    mockGetUserSubjects.mockResolvedValue([{ id: 1, name: '数学' }]);
  });

  it('TC-20: 組織の科目を並べ、選んだ科目にチェックを付ける。変えていなければ保存できない', async () => {
    mountCard();

    expect(screen.getByRole('heading', { name: '学ぶ科目' })).toBeInTheDocument();
    expect(screen.getByText('ダッシュボード・クイズ・学習統計に出す科目です。最低1つ選んでください')).toBeInTheDocument();
    expect(await checkbox('数学')).toBeChecked();
    expect(await checkbox('英語')).not.toBeChecked();
    expect(await checkbox('物理')).not.toBeChecked();
    expect(screen.getByText('英文法')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: SAVE })).toBeDisabled();
  });

  it('TC-20b: チェックボックスのまとまりが「学ぶ科目」という名前のグループで、説明と（0 件にしたときは）注意が結び付く', async () => {
    mountCard();

    await checkbox('数学');
    const group = screen.getByRole('group', { name: '学ぶ科目' });
    expect(within(group).getAllByRole('checkbox')).toHaveLength(3);
    expect(group).toHaveAccessibleDescription('ダッシュボード・クイズ・学習統計に出す科目です。最低1つ選んでください');

    await userEvent.click(await checkbox('数学'));
    expect(group).toHaveAccessibleDescription(
      'ダッシュボード・クイズ・学習統計に出す科目です。最低1つ選んでください 科目を最低1つ選択してください'
    );
  });

  it('TC-21:足して保存すると、応答で選んだ科目のキャッシュを書き換え、ダッシュボードを古いことにする', async () => {
    const saved = [{ id: 1, name: '数学' }, { id: 2, name: '英語' }];
    mockUpdate.mockResolvedValue(saved);
    const queryClient = mountCard();
    const invalidate = jest.spyOn(queryClient, 'invalidateQueries');

    await userEvent.click(await checkbox('英語'));
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('学ぶ科目を保存しました'));
    expect(mockUpdate).toHaveBeenCalledTimes(1);
    expect(mockUpdate).toHaveBeenCalledWith([1, 2]);
    expect(queryClient.getQueryData(userSubjectsKey('user-1'))).toEqual(saved);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['dashboard', 'overview'] });
    await waitFor(() => expect(screen.getByRole('button', { name: SAVE })).toBeDisabled());
    expect(await checkbox('英語')).toBeChecked();
  });

  it('TC-22: 0 件にすると注意を出し、保存できない', async () => {
    mountCard();

    await userEvent.click(await checkbox('数学'));

    expect(screen.getByText('科目を最低1つ選択してください')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: SAVE })).toBeDisabled();
    expect(mockUpdate).not.toHaveBeenCalled();
  });

  it('TC-23: 保存に失敗したら、カードの中に残る表示で伝え、チェックは消さない', async () => {
    mockUpdate.mockRejectedValue(axiosError(500, {}));
    mountCard();

    await userEvent.click(await checkbox('英語'));
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '学ぶ科目を保存できませんでした。時間をおいてもう一度お試しください'
    );
    expect(await checkbox('英語')).toBeChecked();
    expect(await checkbox('数学')).toBeChecked();
  });

  it('TC-24: 400 なら理由を出し、組織の科目を取り直す。チェックを変えると表示が消える', async () => {
    mockUpdate.mockRejectedValue(
      axiosError(400, { error: { main_message: '入力内容にエラーがあります', sub_message: '選択された科目の一部が無効です' } })
    );
    mountCard();

    await userEvent.click(await checkbox('英語'));
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    expect(await screen.findByRole('alert')).toHaveTextContent('選択された科目の一部が無効です');
    await waitFor(() => expect(mockGetAvailable).toHaveBeenCalledTimes(2));

    await userEvent.click(await checkbox('物理'));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('TC-24b: 400 の後に取り直した一覧から消えた科目は、見えないまま送らず、次の保存が成功する（F1）', async () => {
    mockUpdate
      .mockRejectedValueOnce(
        axiosError(400, { error: { main_message: '入力内容にエラーがあります', sub_message: '選択された科目の一部が無効です' } })
      )
      .mockResolvedValueOnce([{ id: 1, name: '数学' }, { id: 2, name: '英語' }]);
    // 1 回目は 3 科目、取り直した 2 回目からは「物理」が消えている
    mockGetAvailable.mockResolvedValueOnce(AVAILABLE).mockResolvedValue(AVAILABLE.slice(0, 2));
    mountCard();

    await userEvent.click(await checkbox('物理'));
    await userEvent.click(screen.getByRole('button', { name: SAVE }));
    expect(await screen.findByRole('alert')).toHaveTextContent('選択された科目の一部が無効です');
    await waitFor(() => expect(screen.queryByRole('checkbox', { name: '物理' })).not.toBeInTheDocument());

    await userEvent.click(await checkbox('英語'));
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('学ぶ科目を保存しました'));
    expect(mockUpdate).toHaveBeenLastCalledWith([1, 2]);
  });

  it('TC-22b: 科目 0 件で開いた直後は赤い注意を出さず（触る前は責めない）、保存もできない', async () => {
    mockGetUserSubjects.mockResolvedValue([]);
    mountCard();

    expect(await checkbox('数学')).not.toBeChecked();
    expect(screen.queryByText('科目を最低1つ選択してください')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: SAVE })).toBeDisabled();
  });

  it('TC-25:組織の科目が 0 件なら管理者への依頼を案内し、保存のボタンを出さない', async () => {
    mockGetAvailable.mockResolvedValue([]);
    mountCard();

    expect(
      await screen.findByText('この組織には選べる科目がありません。組織の管理者に科目の登録を依頼してください')
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: SAVE })).not.toBeInTheDocument();
  });

  it('TC-26: 読み込みに失敗したら再読み込みを出し、押すと取り直す', async () => {
    mockGetAvailable.mockRejectedValueOnce(new Error('network')).mockResolvedValue(AVAILABLE);
    mountCard();

    expect(await screen.findByText('科目を読み込めませんでした')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '再読み込み' }));

    expect(await checkbox('数学')).toBeChecked();
    expect(mockGetAvailable).toHaveBeenCalledTimes(2);
  });

  it('TC-27: 組織の科目に無い番号は、チェックにも保存にも使わない', async () => {
    mockGetUserSubjects.mockResolvedValue([{ id: 1, name: '数学' }, { id: 99, name: '他' }]);
    mockUpdate.mockResolvedValue([{ id: 1, name: '数学' }, { id: 2, name: '英語' }]);
    mountCard();

    const card = screen.getByTestId('learning-subjects-card');
    await checkbox('数学');
    expect(within(card).getAllByRole('checkbox').filter((box) => (box as HTMLInputElement).checked)).toHaveLength(1);

    await userEvent.click(await checkbox('英語'));
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() => expect(mockUpdate).toHaveBeenCalledWith([1, 2]));
  });

  it('TC-28: #learning-subjects で開いたら、カードまで送り見出しにフォーカスを移す', async () => {
    const scrollIntoView = jest.fn();
    Element.prototype.scrollIntoView = scrollIntoView;
    mountCard('/settings#learning-subjects');

    await checkbox('数学');
    await waitFor(() => expect(scrollIntoView).toHaveBeenCalled());
    expect(screen.getByRole('heading', { name: '学ぶ科目' })).toHaveFocus();
  });

  it('TC-28b: ハッシュが無ければ送らない', async () => {
    const scrollIntoView = jest.fn();
    Element.prototype.scrollIntoView = scrollIntoView;
    mountCard();

    await checkbox('数学');
    expect(scrollIntoView).not.toHaveBeenCalled();
  });
});
