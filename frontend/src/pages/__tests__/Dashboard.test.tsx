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

jest.mock('../../services/api');

jest.mock('react-hot-toast', () => ({
  toast: { error: jest.fn(), success: jest.fn() },
}));

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user-1', user_id: 'u_i473' } }),
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
  default: { getUserSubjects: jest.fn() },
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

let mockLineOptions: unknown = null;
jest.mock('react-chartjs-2', () => ({
  Line: ({ data, options }: { data: { datasets: Array<{ data: number[] }> }; options: unknown }) => {
    mockLineOptions = options;
    return <div data-testid="line-chart" data-points={data.datasets[0].data.join(',')} />;
  },
  Doughnut: () => <div data-testid="doughnut-chart" />,
}));

const URL = '/api/dashboard/overview/';
const SETTINGS_URL = '/api/settings/';
const mockGet = apiClient.get as jest.Mock;
const mockGetUserSubjects = SubjectService.getUserSubjects as jest.Mock;

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

const overviewCalls = () => mockGet.mock.calls.filter(([url]) => url === URL).length;

const isBefore = (a: Element, b: Element) =>
  Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);

// 「統計を見る」のリンクのため Router の中で描く（rerender でも同じ包みを使う）
const renderDashboard = (ui: React.ReactElement = <Dashboard />) =>
  render(ui, { wrapper: MemoryRouter });

const SUBJECTS = [{ id: 5, name: '英語' }, { id: 6, name: '数学' }];

describe('Dashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    mockFreshNotificationFunctions = false;
    mockLineOptions = null;
    // CRA の Jest は各テストの前にモックの実装を消す（resetMocks）ので、ここで入れ直す
    mockGetUserSubjects.mockResolvedValue([]);
  });

  it('TC-20: 契約どおりの応答の数字・推移・苦手・おすすめを出し、「練習する」でその科目へ進む', async () => {
    respond(overview());
    renderDashboard();

    expect(await screen.findByText('5分')).toBeInTheDocument();
    expect(screen.getByText('2日')).toBeInTheDocument();
    expect(screen.getByTestId('stat-answered-count')).toHaveTextContent('12');
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('直近 7 日の学習時間')).toBeInTheDocument();
    expect(screen.getByTestId('line-chart')).toHaveAttribute('data-points', '0,0,0,0,0,2,6');
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
    expect(screen.queryByTestId('line-chart')).not.toBeInTheDocument();
    expect(screen.queryByTestId('doughnut-chart')).not.toBeInTheDocument();
    expect(screen.queryByText(/目標:/)).not.toBeInTheDocument();
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
    mockGetUserSubjects.mockResolvedValue([{ id: 7, name: '数学' }]);
    renderDashboard();
    await waitFor(() => expect(screen.getByTestId('start-quiz-button')).toBeEnabled());

    await userEvent.click(screen.getByTestId('start-quiz-button'));
    expect(mockNavigate).toHaveBeenCalledWith('/quiz?subject=7');
  });

  it('TC-05: 科目 0 件なら、画面の中で管理者への依頼を案内し、クイズを始められない', async () => {
    respond(overview(), { daily_study_goal_minutes: 30 });
    renderDashboard();
    await screen.findByText('5分');

    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent(
      '科目がまだ登録されていません。組織の管理者に科目の登録を依頼してください'
    );
    expect(screen.getByTestId('start-quiz-button')).toBeDisabled();
    expect(toast.error).not.toHaveBeenCalled();
    expect(screen.queryByText(/設定画面から科目を追加/)).not.toBeInTheDocument();
    expect(screen.queryByText(/今日の目標達成まで/)).not.toBeInTheDocument();
  });

  it('TC-06: 科目の一覧の取得に失敗したら、0 件と取り違えずに再読み込みを出す', async () => {
    respond(overview());
    mockGetUserSubjects
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce([{ id: 7, name: '数学' }]);
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
    expect(screen.getByTestId('stat-answered-count')).toHaveTextContent('12');
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

    expect(await screen.findByText('目標: 45分 (11%)')).toBeInTheDocument();
    expect(screen.getByText('今日の目標達成まであと40分です')).toBeInTheDocument();
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

    expect(await screen.findByText('今日の目標（45分）を達成しました！')).toBeInTheDocument();
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
    expect(screen.queryByText(/目標:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/今日の目標達成まで/)).not.toBeInTheDocument();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });

  it('TC-11: 推移のグラフの縦軸は 0 から、目盛りは整数', async () => {
    respond(overview());
    renderDashboard();
    await screen.findByTestId('line-chart');

    const options = mockLineOptions as { scales: { y: { beginAtZero: boolean; ticks: { precision: number } } } };
    expect(options.scales.y.beginAtZero).toBe(true);
    expect(options.scales.y.ticks.precision).toBe(0);
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
});
