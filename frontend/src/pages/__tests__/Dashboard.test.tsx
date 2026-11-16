/**
 * ダッシュボード
 * - I473（TC-20〜TC-28）: 契約どおりのキーを読む・データ無し・形の違い/失敗はエラー（0 で埋めない）・科目の選択・苦手 0 件
 * - I487（TC-01〜TC-11・TC-16）: 並び順・状態ごとの表示・クイズの行き先・科目 0 件・目標時間・取得の回数
 */
import React from 'react';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Dashboard from '../Dashboard';
import apiClient from '../../services/api';
import SubjectService from '../../services/subjectService';
import { DashboardOverview } from '../../types/api';
import { toast } from 'react-hot-toast';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('../../services/api');

jest.mock('react-hot-toast', () => ({
  toast: { error: jest.fn(), success: jest.fn() },
}));

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// 既定は管理者でない利用者。I539 の TC-43・TC-44 だけ role を 'admin' に替える
const DEFAULT_USER = { id: 'user-1', user_id: 'u_i473' };
let mockUser: { id: string; user_id: string; role?: string } = DEFAULT_USER;
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: mockUser }),
}));

// 既定では毎回同じ関数を返す。TC-16 だけ、描くたびに新しい関数を返すように替える
const mockShowAchievement = jest.fn();
const mockShowStreakNotification = jest.fn();
let mockFreshNotificationFunctions = false;
jest.mock('../../contexts/NotificationContext', () => ({
  useNotifications: () =>
    mockFreshNotificationFunctions
      ? { showAchievement: jest.fn(), showStreakNotification: jest.fn() }
      : { showAchievement: mockShowAchievement, showStreakNotification: mockShowStreakNotification },
}));

jest.mock('../../services/subjectService', () => ({
  __esModule: true,
  default: { getUserSubjects: jest.fn(), getAvailableSubjects: jest.fn() },
}));

jest.mock('../../components/SubjectSelector', () => ({
  SubjectSelector: ({ onChange }: { onChange: (value: string) => void }) => (
    <>
      <button type="button" onClick={() => onChange('5')}>科目5を選ぶ</button>
      <button type="button" onClick={() => onChange('all')}>すべてを選ぶ</button>
      {/* 科目 5 を選んだ直後に「すべて」へ切り替える動きをまとめて起こす */}
      <button
        type="button"
        onClick={() => {
          onChange('5');
          setTimeout(() => onChange('all'), 0);
        }}
      >
        科目5の直後にすべてへ
      </button>
    </>
  ),
}));

jest.mock('../../components/TodayReviewCard', () => ({
  __esModule: true,
  default: () => <div>今日の復習のカード</div>,
}));

let mockBarOptions: unknown = null;
jest.mock('react-chartjs-2', () => ({
  Bar: ({ data, options, ...rest }: {
    data: { datasets: Array<{ data: number[] }> };
    options: unknown;
    'aria-label'?: string;
  }) => {
    mockBarOptions = options;
    return (
      <div data-testid="bar-chart" data-points={data.datasets[0].data.join(',')} aria-label={rest['aria-label']} />
    );
  },
  Doughnut: () => <div data-testid="doughnut-chart" />,
}));

interface BarOptions {
  interaction: { mode: string; intersect: boolean };
  scales: { y: { beginAtZero: boolean; ticks: { precision: number } } };
  plugins: {
    tooltip: {
      callbacks: {
        title: (items: Array<{ dataIndex: number }>) => string;
        label: (item: { dataIndex: number }) => string[];
      };
    };
  };
}
const barOptions = () => mockBarOptions as BarOptions;

const URL = '/api/dashboard/overview/';
const SETTINGS_URL = '/api/settings/';
const mockGet = apiClient.get as jest.Mock;
const mockGetUserSubjects = SubjectService.getUserSubjects as jest.Mock;
const mockGetAvailableSubjects = SubjectService.getAvailableSubjects as jest.Mock;

const days = (seconds: number[]) =>
  seconds.map((s, i) => ({
    date: `2026-11-${String(7 + i).padStart(2, '0')}`,
    study_seconds: s,
    answered_count: s > 0 ? 1 : 0,
    correct_count: 0,
  }));

const overview = (patch: Partial<DashboardOverview> = {}): DashboardOverview => ({
  has_data: true,
  today: { study_seconds: 330, answered_count: 3, correct_count: 2, accuracy_rate: 0.6667 },
  streak: { current_days: 2 },
  totals: { answered_count: 12, correct_count: 9, accuracy_rate: 0.75 },
  last_7_days: days([0, 0, 0, 0, 0, 120, 330]),
  weak_subjects: [
    { subject_id: 3, subject_name: '英語', answered_count: 10, accuracy_rate: 0.5 },
  ],
  recommendations: [
    { kind: 'unstudied_subject', subject_id: 4, subject_name: '数学', reason: 'この 7 日間、解いていません' },
  ],
  ...patch,
});

const emptyOverview = (): DashboardOverview => overview({
  has_data: false,
  today: { study_seconds: 0, answered_count: 0, correct_count: 0, accuracy_rate: null },
  streak: { current_days: 0 },
  totals: { answered_count: 0, correct_count: 0, accuracy_rate: null },
  last_7_days: days([0, 0, 0, 0, 0, 0, 0]),
  weak_subjects: [],
  recommendations: [],
});

const respond = (data: unknown, settings: unknown = {}) => {
  mockGet.mockImplementation((url: string) => {
    if (url === URL) return Promise.resolve({ data });
    if (url === SETTINGS_URL) return Promise.resolve({ data: settings });
    return Promise.resolve({ data: {} });
  });
};

/** 「すべて」と科目 5 で違う応答を返す（I513） */
const respondBySubject = (all: unknown, subject: unknown, settings: unknown = {}) => {
  mockGet.mockImplementation((url: string, config?: { params: Record<string, string> }) => {
    if (url === URL) return Promise.resolve({ data: config?.params.subject_id ? subject : all });
    if (url === SETTINGS_URL) return Promise.resolve({ data: settings });
    return Promise.resolve({ data: {} });
  });
};

const withToday = (seconds: number) =>
  overview({ today: { study_seconds: seconds, answered_count: 3, correct_count: 2, accuracy_rate: 0.6667 } });

const overviewCalls = () => mockGet.mock.calls.filter(([url]) => url === URL).length;
const overviewCallsWith = (params: Record<string, string>) =>
  mockGet.mock.calls.filter(
    ([url, config]) => url === URL && JSON.stringify(config?.params) === JSON.stringify(params)
  ).length;

const isBefore = (a: Element, b: Element) =>
  Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);

// 「統計を見る」のリンクのため Router の中で、取得のため React Query の中で描く。
// QueryClient は描くたびに新しくする（テストの間でキャッシュを持ち越さない・失敗をすぐ出す）。rerender でも同じ包みを使う
const renderDashboard = (ui: React.ReactElement = <Dashboard />) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  return render(ui, { wrapper: Wrapper });
};

// problem_count が 0 の科目ではクイズを始められない（I539）。問題のある科目として差し替える
const SUBJECTS = [{ id: 5, name: '英語', problem_count: 3 }, { id: 6, name: '数学', problem_count: 2 }];

describe('Dashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    mockFreshNotificationFunctions = false;
    mockBarOptions = null;
    mockUser = DEFAULT_USER;
    // CRA の Jest は各テストの前にモックの実装を消す（resetMocks）ので、ここで入れ直す
    mockGetUserSubjects.mockResolvedValue([]);
    // 既定は組織の科目も 0 件（管理者への依頼の案内・I494）
    mockGetAvailableSubjects.mockResolvedValue([]);
  });

  it('TC-20: 契約どおりの応答の数字・推移・苦手・おすすめを出し、「練習する」でその科目へ進む', async () => {
    respond(overview());
    renderDashboard();

    expect(await screen.findByText('5分')).toBeInTheDocument();
    expect(screen.getByText('2日')).toBeInTheDocument();
    expect(screen.getByTestId('stat-answered-count')).toHaveTextContent('12');
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('直近 7 日の学習時間')).toBeInTheDocument();
    expect(screen.getByTestId('bar-chart')).toHaveAttribute('data-points', '0,0,0,0,0,2,5');
    expect(screen.getByTestId('doughnut-chart')).toBeInTheDocument();
    expect(screen.getByText('英語')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText('解答数: 10問')).toBeInTheDocument();
    expect(screen.getByText('この 7 日間、解いていません')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: '練習する' }));
    expect(mockNavigate).toHaveBeenCalledWith('/quiz?subject=4');
  });

  it('TC-21: データ無しなら赤い円を出さない', async () => {
    respond(emptyOverview());
    renderDashboard();

    expect((await screen.findAllByText('まだ記録がありません')).length).toBeGreaterThan(0);
    expect(screen.queryByTestId('doughnut-chart')).not.toBeInTheDocument();
    expect(screen.getByText('データがありません。まずは問題を解いてみましょう！')).toBeInTheDocument();
  });

  it.each([
    // last_7_days を欠いても画面は落ちずに描けてしまう（?? [] で空のグラフになる）ので、
    // 形の確かめ（isDashboardOverview）が無いと 0 埋めと同じ見え方になる。その確かめを固定する
    ['形の違う応答（last_7_days が無い）', () => {
      const { last_7_days: _omitted, ...broken } = overview();
      respond(broken);
    }],
    ['形の違う応答（totals が無い）', () => {
      const { totals: _omitted, ...broken } = overview();
      respond(broken);
    }],
    ['取得の失敗', () => {
      mockGet.mockImplementation((url: string) =>
        url === URL ? Promise.reject(new Error('network')) : Promise.resolve({ data: {} })
      );
    }],
  ])('TC-22: %s はエラーの文を出し、0 で埋めた数字を出さない', async (_label, arrange) => {
    arrange();
    renderDashboard();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'ダッシュボードの数字を読み込めませんでした'
    );
    expect(screen.queryByText('0分')).not.toBeInTheDocument();
    expect(screen.queryByText('0日')).not.toBeInTheDocument();
    expect(screen.queryByText('0%')).not.toBeInTheDocument();
    expect(screen.queryByTestId('stat-answered-count')).not.toBeInTheDocument();
    expect(screen.getByText('今日の復習のカード')).toBeInTheDocument();
  });

  it('TC-23: 科目を選ぶと subject_id 付きで取り直し、「すべて」なら付けない', async () => {
    respond(overview());
    renderDashboard();
    await screen.findByText('5分');
    expect(mockGet).toHaveBeenCalledWith(URL, { params: {} });

    await userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));
    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(URL, { params: { subject_id: '5' } });
    });
  });

  it('TC-25: 一覧が空なら、一覧に入る条件（5 問以上）を含めて伝える（F4）', async () => {
    respond(overview({ weak_subjects: [] }));
    renderDashboard();

    expect(
      await screen.findByText('5 問以上解いた科目のうち、正答率が 70% 未満の科目はありません')
    ).toBeInTheDocument();
  });

  it('TC-26: 科目で絞って has_data が false でも、全科目の間違いやすい分野は出す（F1）', async () => {
    const empty = {
      has_data: false,
      totals: { answered_count: 0, correct_count: 0, accuracy_rate: null },
    };
    mockGet.mockImplementation((url: string, config: { params: Record<string, string> }) =>
      url === URL
        ? Promise.resolve({ data: overview(config.params.subject_id ? empty : {}) })
        : Promise.resolve({ data: {} })
    );
    renderDashboard();
    await screen.findByText('5分');

    await userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));

    expect(
      await screen.findByText('この科目はまだ解答がありません。まずは問題を解いてみましょう！')
    ).toBeInTheDocument();
    expect(screen.getByText('英語')).toBeInTheDocument();
    expect(
      screen.queryByText('データがありません。まずは問題を解いてみましょう！')
    ).not.toBeInTheDocument();
  });

  it('TC-27: 達成のお知らせは「すべて」の応答だけで判定し、科目で絞った応答では出さない（F2）', async () => {
    const milestone = { totals: { answered_count: 10, correct_count: 5, accuracy_rate: 0.5 } };
    respond(overview(milestone));
    renderDashboard();
    await screen.findByText('5分');
    await waitFor(() => expect(mockShowAchievement).toHaveBeenCalledTimes(1));
    expect(mockShowAchievement).toHaveBeenCalledWith('10問解答達成！おめでとうございます！🎉');

    mockShowAchievement.mockClear();
    await userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));
    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(URL, { params: { subject_id: '5' } });
    });
    await screen.findByText('5分');
    expect(mockShowAchievement).not.toHaveBeenCalled();
  });

  it('TC-28: 科目を切り替えた後に届いた古い応答で、今の数字を上書きしない（F3）', async () => {
    let resolveOld: (value: unknown) => void = () => {};
    mockGet.mockImplementation((url: string, config: { params: Record<string, string> }) => {
      if (url !== URL) return Promise.resolve({ data: {} });
      if (config.params.subject_id === '5') {
        return new Promise((resolve) => { resolveOld = resolve; });
      }
      return Promise.resolve({ data: overview() });
    });
    renderDashboard();
    await screen.findByText('5分');

    await userEvent.click(screen.getByRole('button', { name: '科目5の直後にすべてへ' }));
    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(URL, { params: { subject_id: '5' } });
    });
    expect(await screen.findByTestId('stat-answered-count')).toHaveTextContent('12');

    await act(async () => {
      resolveOld({ data: overview({ totals: { answered_count: 99, correct_count: 0, accuracy_rate: 0 } }) });
    });
    expect(screen.getByTestId('stat-answered-count')).toHaveTextContent('12');
  });

  // ---- I487 ----

  it('TC-01: 上から 挨拶 → 科目の選択 → クイズ・今日の復習 → 数字 → グラフ → 苦手・おすすめ → 統計を見る', async () => {
    respond(overview());
    renderDashboard();
    await screen.findByText('5分');

    const order = [
      screen.getByRole('heading', { level: 1, name: 'おかえりなさい、u_i473さん！' }),
      screen.getByRole('button', { name: '科目5を選ぶ' }),
      screen.getByTestId('start-quiz-button'),
      screen.getByText('今日の復習のカード'),
      screen.getByTestId('stat-answered-count'),
      screen.getByRole('heading', { name: '直近 7 日の学習時間' }),
      screen.getByRole('heading', { name: '間違いやすい分野（全科目）' }),
      screen.getByRole('heading', { name: 'おすすめ練習問題（全科目）' }),
      screen.getByRole('link', { name: '統計を見る' }),
    ];
    // 隣り合う 2 つずつ、前が後より先に並ぶ
    order.reduce((previous, element) => {
      expect(isBefore(previous, element)).toBe(true);
      return element;
    });
    expect(screen.getByRole('link', { name: '統計を見る' })).toHaveAttribute('href', '/statistics');
    expect(screen.queryByText(/今日も学習を頑張りましょう/)).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '詳細統計' })).not.toBeInTheDocument();
  });

  it('TC-02: データ 0 件なら、数字 4 枚とグラフ 2 つに「まだ記録がありません」を出し、グラフ・目標を出さない', async () => {
    respond(emptyOverview(), { daily_study_goal_minutes: 30 });
    renderDashboard();

    expect(await screen.findAllByText('まだ記録がありません')).toHaveLength(6);
    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();
    expect(screen.queryByTestId('doughnut-chart')).not.toBeInTheDocument();
    expect(screen.queryByTestId('weekly-total')).not.toBeInTheDocument();
    expect(screen.queryByText(/目標（全科目）/)).not.toBeInTheDocument();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    expect(screen.getByText('データがありません。まずは問題を解いてみましょう！')).toBeInTheDocument();
  });

  it('TC-03: 選んだ科目だけ 0 件なら、案内を一番上に出し、その下に全科目の一覧を出す', async () => {
    mockGet.mockImplementation((url: string, config: { params: Record<string, string> }) =>
      url === URL
        ? Promise.resolve({ data: config.params.subject_id ? { ...emptyOverview(), weak_subjects: overview().weak_subjects } : overview() })
        : Promise.resolve({ data: {} })
    );
    renderDashboard();
    await screen.findByText('5分');
    await userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));

    const notice = await screen.findByText('この科目はまだ解答がありません。まずは問題を解いてみましょう！');
    expect(isBefore(notice, screen.getByText('英語'))).toBe(true);
    expect(screen.queryByText(/5 問以上解いた科目のうち/)).not.toBeInTheDocument();
    expect(screen.queryByText('データがありません。まずは問題を解いてみましょう！')).not.toBeInTheDocument();
  });

  it('TC-03b: 選んだ科目だけ 0 件で一覧も空なら、案内だけを出す', async () => {
    mockGet.mockImplementation((url: string, config: { params: Record<string, string> }) =>
      url === URL
        ? Promise.resolve({ data: config.params.subject_id ? emptyOverview() : overview() })
        : Promise.resolve({ data: {} })
    );
    renderDashboard();
    await screen.findByText('5分');
    await userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));

    expect(
      await screen.findByText('この科目はまだ解答がありません。まずは問題を解いてみましょう！')
    ).toBeInTheDocument();
    expect(screen.queryByText(/5 問以上解いた科目のうち/)).not.toBeInTheDocument();
  });

  it('TC-04a: 「すべて」で科目が 2 件なら、科目を選ぶダイアログを出す', async () => {
    respond(overview());
    mockGetUserSubjects.mockResolvedValue(SUBJECTS);
    renderDashboard();
    await waitFor(() => expect(screen.getByTestId('start-quiz-button')).toBeEnabled());

    await userEvent.click(screen.getByTestId('start-quiz-button'));
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('TC-04b: 科目を選んでいれば、ダイアログを出さずにその科目のクイズへ進む', async () => {
    respond(overview());
    mockGetUserSubjects.mockResolvedValue(SUBJECTS);
    renderDashboard();
    await waitFor(() => expect(screen.getByTestId('start-quiz-button')).toBeEnabled());

    await userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));
    await userEvent.click(screen.getByTestId('start-quiz-button'));
    expect(mockNavigate).toHaveBeenCalledWith('/quiz?subject=5');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('TC-04c: 「すべて」で科目が 1 件なら、その科目のクイズへ進む', async () => {
    respond(overview());
    mockGetUserSubjects.mockResolvedValue([{ id: 7, name: '数学', problem_count: 1 }]);
    renderDashboard();
    await waitFor(() => expect(screen.getByTestId('start-quiz-button')).toBeEnabled());

    await userEvent.click(screen.getByTestId('start-quiz-button'));
    expect(mockNavigate).toHaveBeenCalledWith('/quiz?subject=7');
  });

  it('TC-05: 管理者でなく、選んだ科目も組織の科目も 0 件なら、管理者が用意するのを待つ案内を出し、クイズを始められない（I539）', async () => {
    respond(overview(), { daily_study_goal_minutes: 30 });
    renderDashboard();
    await screen.findByText('5分');

    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent(
      '科目がまだ用意されていません。管理者が科目を用意するまでお待ちください'
    );
    expect(screen.getByTestId('start-quiz-button')).toBeDisabled();
    expect(toast.error).not.toHaveBeenCalled();
    expect(screen.queryByText(/組織の管理者に科目の登録を依頼してください/)).not.toBeInTheDocument();
    expect(screen.queryByText(/今日の目標/)).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: '学ぶ科目を選ぶ' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: '科目を作る' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: '問題を作る' })).not.toBeInTheDocument();
  });

  it('TC-43: 管理者で、選んだ科目も組織の科目も 0 件なら、科目を作る案内と目立つボタンを 1 つ出す（I539）', async () => {
    mockUser = { ...DEFAULT_USER, role: 'admin' };
    respond(overview());
    renderDashboard();

    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent(
      'まず科目と問題を作りましょう。科目管理で科目を作り、問題管理でその科目の問題を作ると、クイズを始められます'
    );
    const createSubject = screen.getByRole('link', { name: '科目を作る' });
    expect(createSubject).toHaveAttribute('href', '/subject-management');
    expect(createSubject).toHaveClass('MuiButton-contained');
    // 科目が無いうちは問題を作れないので、問題を作る行き先は出さない
    expect(screen.queryByRole('link', { name: '問題を作る' })).not.toBeInTheDocument();
    expect(screen.getByTestId('start-quiz-button')).toBeDisabled();
    expect(screen.queryByText(/管理者が科目を用意するまでお待ちください/)).not.toBeInTheDocument();
  });

  it('TC-45: 管理者で、学ぶ科目に問題が無ければ、問題を作る案内と目立つボタンを出し、クイズを始められない（I539）', async () => {
    mockUser = { ...DEFAULT_USER, role: 'admin' };
    respond(overview());
    mockGetUserSubjects.mockResolvedValue([{ id: 5, name: '英語', problem_count: 0 }]);
    renderDashboard();

    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent(
      '問題を作りましょう。問題管理で学ぶ科目の問題を作ると、クイズを始められます'
    );
    const createProblem = screen.getByRole('link', { name: '問題を作る' });
    expect(createProblem).toHaveAttribute('href', '/quiz-management');
    expect(createProblem).toHaveClass('MuiButton-contained');
    expect(screen.queryByRole('link', { name: '科目を作る' })).not.toBeInTheDocument();
    expect(screen.getByTestId('start-quiz-button')).toBeDisabled();

    // 科目を選ぶと「この科目」の文言になる
    await userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));
    expect(await screen.findByRole('status')).toHaveTextContent(
      '問題を作りましょう。問題管理でこの科目の問題を作ると、クイズを始められます'
    );
    expect(screen.getByTestId('start-quiz-button')).toBeDisabled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('TC-46: 管理者でなく、学ぶ科目に問題が無ければ、管理者が用意するのを待つ案内を出す（I539）', async () => {
    respond(overview());
    mockGetUserSubjects.mockResolvedValue([{ id: 5, name: '英語', problem_count: 0 }]);
    renderDashboard();

    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent(
      '学ぶ科目にまだ問題がありません。管理者が問題を用意するまでお待ちください'
    );
    expect(screen.queryByRole('link', { name: '問題を作る' })).not.toBeInTheDocument();
    expect(screen.getByTestId('start-quiz-button')).toBeDisabled();
  });

  it('TC-47: 「すべて」では問題のある科目だけから始める（I539）', async () => {
    respond(overview());
    mockGetUserSubjects.mockResolvedValue([
      { id: 5, name: '英語', problem_count: 3 },
      { id: 6, name: '数学', problem_count: 0 },
    ]);
    const { unmount } = renderDashboard();
    await waitFor(() => expect(screen.getByTestId('start-quiz-button')).toBeEnabled());
    expect(screen.queryByText(/問題を作りましょう|まだ問題がありません/)).not.toBeInTheDocument();

    // 問題のある科目が 1 件なら、ダイアログを出さずにその科目へ
    await userEvent.click(screen.getByTestId('start-quiz-button'));
    expect(mockNavigate).toHaveBeenCalledWith('/quiz?subject=5');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    unmount();

    // 問題のある科目が 2 件なら、ダイアログにはその 2 件だけを出す
    mockNavigate.mockClear();
    mockGetUserSubjects.mockResolvedValue([
      { id: 5, name: '英語', problem_count: 3 },
      { id: 6, name: '数学', problem_count: 0 },
      { id: 8, name: '理科', problem_count: 1 },
    ]);
    renderDashboard();
    await waitFor(() => expect(screen.getByTestId('start-quiz-button')).toBeEnabled());
    await userEvent.click(screen.getByTestId('start-quiz-button'));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByRole('button', { name: '英語のクイズを開始' })).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: '理科のクイズを開始' })).toBeInTheDocument();
    expect(within(dialog).queryByRole('button', { name: '数学のクイズを開始' })).not.toBeInTheDocument();
  });

  it('TC-44: 管理者でも、組織に科目があれば、作る案内ではなく学ぶ科目を選ぶ案内を出す（I539）', async () => {
    mockUser = { ...DEFAULT_USER, role: 'admin' };
    mockGetAvailableSubjects.mockResolvedValue([{ id: 9, name: '国語' }]);
    respond(overview());
    renderDashboard();

    expect(await screen.findByRole('link', { name: '学ぶ科目を選ぶ' })).toBeInTheDocument();
    expect(screen.queryByText(/まず科目と問題を作りましょう/)).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: '科目を作る' })).not.toBeInTheDocument();
  });

  it('TC-40: 選んだ科目が 0 件で組織に科目があれば、設定画面の「学ぶ科目」へ案内する（I494）', async () => {
    respond(overview());
    mockGetAvailableSubjects.mockResolvedValue([{ id: 7, name: '数学', description: '' }]);
    renderDashboard();

    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent('学ぶ科目がまだ選ばれていません。設定画面で学ぶ科目を選んでください');
    expect(screen.getByRole('link', { name: '学ぶ科目を選ぶ' })).toHaveAttribute(
      'href', '/settings#learning-subjects'
    );
    expect(screen.queryByText(/組織の管理者に科目の登録を依頼してください/)).not.toBeInTheDocument();
    expect(screen.getByTestId('start-quiz-button')).toBeDisabled();
  });

  it('TC-41: 選んだ科目が 0 件で組織の科目の取得に失敗したら、再読み込みを出す（I494）', async () => {
    respond(overview());
    mockGetAvailableSubjects
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce([{ id: 7, name: '数学', description: '' }]);
    renderDashboard();

    const card = screen.getByTestId('start-quiz-card');
    expect(await within(card).findByText('科目を読み込めませんでした')).toBeInTheDocument();
    expect(screen.queryByText(/組織の管理者に科目の登録を依頼してください/)).not.toBeInTheDocument();

    await userEvent.click(within(card).getByRole('button', { name: '再読み込み' }));
    expect(await screen.findByRole('link', { name: '学ぶ科目を選ぶ' })).toBeInTheDocument();
    expect(mockGetAvailableSubjects).toHaveBeenCalledTimes(2);
  });

  it('TC-42: 選んだ科目が 1 件以上なら、組織の科目を読まない（I494）', async () => {
    respond(overview());
    mockGetUserSubjects.mockResolvedValue(SUBJECTS);
    renderDashboard();

    await screen.findByText('5分');
    await waitFor(() => expect(mockGetUserSubjects).toHaveBeenCalled());
    expect(screen.getByTestId('start-quiz-button')).toBeEnabled();
    expect(mockGetAvailableSubjects).not.toHaveBeenCalled();
  });

  it('TC-06: 科目の一覧の取得に失敗したら、0 件と取り違えずに再読み込みを出す', async () => {
    respond(overview());
    mockGetUserSubjects
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce([{ id: 7, name: '数学', problem_count: 1 }]);
    renderDashboard();

    const card = screen.getByTestId('start-quiz-card');
    expect(await within(card).findByText('科目を読み込めませんでした')).toBeInTheDocument();
    expect(screen.getByTestId('start-quiz-button')).toBeDisabled();
    expect(screen.queryByText(/科目がまだ登録されていません/)).not.toBeInTheDocument();

    await userEvent.click(within(card).getByRole('button', { name: '再読み込み' }));
    await waitFor(() => expect(screen.getByTestId('start-quiz-button')).toBeEnabled());
    expect(screen.queryByText('科目を読み込めませんでした')).not.toBeInTheDocument();
  });

  it('TC-07: 読み込み中はスケルトンで、科目を切り替えても画面全体を置き換えない', async () => {
    const pending: Array<(value: unknown) => void> = [];
    mockGet.mockImplementation((url: string) =>
      url === URL
        ? new Promise((resolve) => { pending.push(resolve); })
        : Promise.resolve({ data: {} })
    );
    renderDashboard();

    expect(screen.getByTestId('dashboard-skeleton')).toBeInTheDocument();
    const heading = screen.getByRole('heading', { level: 1 });
    const startButton = screen.getByTestId('start-quiz-button');
    const reviewCard = screen.getByText('今日の復習のカード');
    expect(screen.queryByText('ダッシュボードを読み込み中...')).not.toBeInTheDocument();

    await act(async () => { pending[0]({ data: overview() }); });
    // React Query は応答を少し遅れて画面に反映するので、出るのを待つ
    expect(await screen.findByTestId('stat-answered-count')).toHaveTextContent('12');
    expect(screen.queryByTestId('dashboard-skeleton')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));
    expect(screen.getByTestId('dashboard-skeleton')).toBeInTheDocument();
    expect(screen.queryByTestId('stat-answered-count')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toBe(heading);
    expect(screen.getByTestId('start-quiz-button')).toBe(startButton);
    expect(screen.getByText('今日の復習のカード')).toBe(reviewCard);
    expect(screen.queryByText('ダッシュボードを読み込み中...')).not.toBeInTheDocument();
  });

  it('TC-08: StrictMode でも初回の取得は 1 回', async () => {
    respond(overview());
    renderDashboard(<React.StrictMode><Dashboard /></React.StrictMode>);

    expect(await screen.findByTestId('stat-answered-count')).toHaveTextContent('12');
    expect(overviewCalls()).toBe(1);
  });

  it('TC-09: 取得に失敗したらエラーと再読み込みを出し、押すと取り直す', async () => {
    let calls = 0;
    mockGet.mockImplementation((url: string) => {
      if (url !== URL) return Promise.resolve({ data: {} });
      calls += 1;
      return calls === 1 ? Promise.reject(new Error('network')) : Promise.resolve({ data: overview() });
    });
    renderDashboard();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('ダッシュボードの数字を読み込めませんでした');
    expect(toast.error).not.toHaveBeenCalled();

    await userEvent.click(within(alert).getByRole('button', { name: '再読み込み' }));
    expect(await screen.findByTestId('stat-answered-count')).toHaveTextContent('12');
    expect(overviewCalls()).toBe(2);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('TC-10a: 目標時間は設定の daily_study_goal_minutes に従う', async () => {
    respond(overview(), { daily_study_goal_minutes: 45 });
    mockGetUserSubjects.mockResolvedValue(SUBJECTS);
    renderDashboard();

    expect(await screen.findByText('目標（全科目）: 45分 (11%)')).toBeInTheDocument();
    expect(screen.getByText('今日の目標（全科目）達成まであと40分です')).toBeInTheDocument();
    expect(screen.queryByText(/目標: 60分/)).not.toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '11');
  });

  it('TC-10b: 目標に届いたら達成の文を出す', async () => {
    respond(
      overview({ today: { study_seconds: 2700, answered_count: 3, correct_count: 2, accuracy_rate: 0.6667 } }),
      { daily_study_goal_minutes: 45 }
    );
    mockGetUserSubjects.mockResolvedValue(SUBJECTS);
    renderDashboard();

    expect(await screen.findByText('今日の目標（全科目・45分）を達成しました！')).toBeInTheDocument();
  });

  it('TC-10c: 設定を読めなければ、目標の表示を出さない', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === URL) return Promise.resolve({ data: overview() });
      if (url === SETTINGS_URL) return Promise.reject(new Error('network'));
      return Promise.resolve({ data: {} });
    });
    mockGetUserSubjects.mockResolvedValue(SUBJECTS);
    renderDashboard();

    expect(await screen.findByText('5分')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('start-quiz-button')).toBeEnabled());
    expect(screen.queryByText(/目標（全科目）/)).not.toBeInTheDocument();
    expect(screen.queryByText(/今日の目標/)).not.toBeInTheDocument();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });

  it('TC-16: お知らせの関数が描くたびに変わっても、取り直さない（F11）', async () => {
    mockFreshNotificationFunctions = true;
    respond(overview());
    const { rerender } = renderDashboard();
    expect(await screen.findByTestId('stat-answered-count')).toHaveTextContent('12');

    rerender(<Dashboard />);
    rerender(<Dashboard />);
    await act(async () => { await Promise.resolve(); });
    expect(overviewCalls()).toBe(1);
  });

  // ---- I513 ----

  it('TC-30: 科目を選んでも、目標の残りと進み具合は全科目の今日の合計で出す', async () => {
    respondBySubject(withToday(600), withToday(300), { daily_study_goal_minutes: 30 });
    mockGetUserSubjects.mockResolvedValue(SUBJECTS);
    renderDashboard();
    await screen.findByText('10分');

    await userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));

    expect(await screen.findByText('5分')).toBeInTheDocument();
    expect(screen.getByText('今日の目標（全科目）達成まであと20分です')).toBeInTheDocument();
    expect(screen.getByText('目標（全科目）: 30分 (33%)')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '33');
    expect(overviewCallsWith({})).toBe(1);
    expect(overviewCallsWith({ subject_id: '5' })).toBe(1);
  });

  it('TC-30b: 選んだ科目に記録が無いと、数字のカードに進み具合を出さず、目標は「学習を開始」の全科目の行で出す', async () => {
    respondBySubject(withToday(600), emptyOverview(), { daily_study_goal_minutes: 30 });
    mockGetUserSubjects.mockResolvedValue(SUBJECTS);
    renderDashboard();
    await screen.findByText('10分');
    expect(screen.getByText('目標（全科目）: 30分 (33%)')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));

    expect(
      await screen.findByText('この科目はまだ解答がありません。まずは問題を解いてみましょう！')
    ).toBeInTheDocument();
    expect(screen.getAllByText('まだ記録がありません').length).toBeGreaterThan(0);
    expect(screen.queryByText(/目標（全科目）:/)).not.toBeInTheDocument();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    expect(screen.getByText('今日の目標（全科目）達成まであと20分です')).toBeInTheDocument();
  });

  it.each([
    ['失敗', () => Promise.reject(new Error('network'))],
    ['読み込み中のまま', () => new Promise(() => {})],
  ])('TC-31: 「すべて」の取得が%sなら、科目を選んでも目標の行と進み具合を出さない', async (_label, allResponse) => {
    mockGet.mockImplementation((url: string, config?: { params: Record<string, string> }) => {
      if (url === URL) {
        return config?.params.subject_id ? Promise.resolve({ data: withToday(300) }) : allResponse();
      }
      if (url === SETTINGS_URL) return Promise.resolve({ data: { daily_study_goal_minutes: 30 } });
      return Promise.resolve({ data: {} });
    });
    mockGetUserSubjects.mockResolvedValue(SUBJECTS);
    renderDashboard();
    await waitFor(() => expect(screen.getByTestId('start-quiz-button')).toBeEnabled());

    await userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));

    expect(await screen.findByText('5分')).toBeInTheDocument();
    expect(screen.queryByText(/今日の目標/)).not.toBeInTheDocument();
    expect(screen.queryByText(/目標（全科目）/)).not.toBeInTheDocument();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });

  it('TC-32: 推移は棒グラフで、値は分の切り捨て・縦軸は 0 から整数・列のどこでも tooltip を出す', async () => {
    respond(overview());
    renderDashboard();

    expect(await screen.findByTestId('bar-chart')).toHaveAttribute('data-points', '0,0,0,0,0,2,5');
    expect(screen.queryByTestId('line-chart')).not.toBeInTheDocument();
    const options = barOptions();
    expect(options.interaction).toEqual({ mode: 'index', intersect: false });
    expect(options.scales.y.beginAtZero).toBe(true);
    expect(options.scales.y.ticks.precision).toBe(0);
  });

  const dayOf = (index: number, seconds: number, answered: number, correct: number) => ({
    date: `2026-11-${String(7 + index).padStart(2, '0')}`,
    study_seconds: seconds,
    answered_count: answered,
    correct_count: correct,
  });

  /** 渡した日の後ろは 0 で埋めて 7 日にする */
  const weekOf = (...rows: Array<[number, number, number]>) =>
    [...rows, ...Array.from({ length: 7 - rows.length }, (): [number, number, number] => [0, 0, 0])]
      .map((row, i) => dayOf(i, ...row));

  it('TC-33: 棒の tooltip に日付・学習時間・解答数・正答率（答えが無い日は「—」）を出す', async () => {
    respond(overview({ last_7_days: weekOf([0, 0, 0], [30, 1, 1], [0, 0, 0], [0, 0, 0], [0, 0, 0], [120, 1, 0], [330, 3, 2]) }));
    renderDashboard();
    const chart = await screen.findByTestId('bar-chart');

    const { title, label } = barOptions().plugins.tooltip.callbacks;
    expect(title([{ dataIndex: 6 }])).toBe('11/13（金）');
    expect(label({ dataIndex: 6 })).toEqual(['学習時間: 5分', '解答数: 3問', '正答率: 67%']);
    expect(label({ dataIndex: 0 })).toEqual(['学習時間: 0分', '解答数: 0問', '正答率: —']);
    expect(label({ dataIndex: 1 })).toEqual(['学習時間: 0分', '解答数: 1問', '正答率: 100%']);
    expect(chart.getAttribute('aria-label')).toContain('11/8（日） 0分・1問');
  });

  it.each([
    [
      '60 分以上も分で出し、分は切り捨て',
      weekOf([125, 3, 2], [0, 0, 0], [2785, 5, 4], [1800, 1, 1]),
      '直近 7 日の合計: 78分・9問・正答率78%',
    ],
    ['正答率は四捨五入（12.5% → 13%）', weekOf([600, 8, 1]), '直近 7 日の合計: 10分・8問・正答率13%'],
    ['7 日の答えが 0 件なら正答率は「—」', weekOf(), '直近 7 日の合計: 0分・0問・正答率—'],
  ])('TC-34: 直近 7 日の合計（%s）', async (_label, lastDays, text) => {
    respond(overview({ last_7_days: lastDays }));
    renderDashboard();

    expect(await screen.findByTestId('weekly-total')).toHaveTextContent(text);
  });

  it('TC-34d: データ無しなら直近 7 日の合計を出さない', async () => {
    respond(emptyOverview());
    renderDashboard();

    expect((await screen.findAllByText('まだ記録がありません')).length).toBeGreaterThan(0);
    expect(screen.queryByTestId('weekly-total')).not.toBeInTheDocument();
  });

  it('TC-35: 合計の行は見出しとグラフの間にあり、グラフには日ごとの値の読み上げがある', async () => {
    respond(overview());
    renderDashboard();
    const chart = await screen.findByTestId('bar-chart');

    const heading = screen.getByRole('heading', { name: '直近 7 日の学習時間' });
    const total = screen.getByTestId('weekly-total');
    expect(isBefore(heading, total)).toBe(true);
    expect(isBefore(total, chart)).toBe(true);
    const ariaLabel = chart.getAttribute('aria-label') ?? '';
    expect(ariaLabel.startsWith('11/7（土） 0分')).toBe(true);
    expect(ariaLabel).toContain('11/13（金） 5分');
  });
});
