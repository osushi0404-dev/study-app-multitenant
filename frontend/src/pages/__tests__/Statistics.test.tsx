/**
 * 学習統計（I488・TC-20〜TC-26）
 * 契約どおりのキーを読む・データ無し・期間に記録無し・形の違い/失敗はエラー（空で埋めない）・期間と科目の送り方・区切りのラベル・科目別
 */
import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Statistics from '../Statistics';
import apiClient from '../../services/api';
import { DashboardAnalytics } from '../../types/api';

jest.mock('../../services/api');

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user-1', user_id: 'u_i488' } }),
}));

jest.mock('../../components/SubjectSelector', () => ({
  SubjectSelector: ({ onChange }: { onChange: (value: string) => void }) => (
    <button type="button" onClick={() => onChange('5')}>科目5を選ぶ</button>
  ),
}));

// グラフはデータだけを data 属性に出す軽いものにする（jsdom では SVG の大きさが測れないため）
interface MockPoint { label: string; minutes: number; accuracyPercent: number | null }
jest.mock('recharts', () => {
  const Pass = ({ children }: { children: React.ReactNode }) => <>{children}</>;
  const Nothing = () => null;
  return {
    ResponsiveContainer: Pass,
    BarChart: ({ data }: { data: MockPoint[] }) => (
      <div
        data-testid="bar-chart"
        data-labels={data.map((point) => point.label).join(',')}
        data-points={data.map((point) => point.minutes).join(',')}
      />
    ),
    LineChart: ({ data }: { data: MockPoint[] }) => (
      <div
        data-testid="line-chart"
        data-points={data.map((point) => String(point.accuracyPercent)).join(',')}
      />
    ),
    PieChart: ({ children }: { children: React.ReactNode }) => <div data-testid="pie-chart">{children}</div>,
    Pie: ({ data }: { data: unknown[] }) => <div data-testid="pie" data-count={data.length} />,
    Cell: Nothing,
    Bar: Nothing,
    Line: Nothing,
    XAxis: Nothing,
    YAxis: Nothing,
    CartesianGrid: Nothing,
    Tooltip: Nothing,
  };
});

const URL = '/api/dashboard/analytics/';
const mockGet = apiClient.get as jest.Mock;

const dayBucket = (date: string, seconds = 0, answered = 0, correct = 0) => ({
  start_date: date,
  end_date: date,
  study_seconds: seconds,
  answered_count: answered,
  correct_count: correct,
  accuracy_rate: answered > 0 ? correct / answered : null,
});

// 2026-10-16〜2026-11-14 の 30 日。最後の日だけ答えがある
const thirtyDays = () =>
  Array.from({ length: 30 }, (_, i) => {
    const date = new Date(Date.UTC(2026, 9, 16 + i)).toISOString().slice(0, 10);
    return i === 29 ? dayBucket(date, 7530, 15, 10) : dayBucket(date);
  });

const analytics = (patch: Partial<DashboardAnalytics> = {}): DashboardAnalytics => ({
  has_data: true,
  period: { days: 30, start_date: '2026-10-16', end_date: '2026-11-14', granularity: 'day' },
  totals: {
    study_seconds: 7530, answered_count: 15, correct_count: 10, accuracy_rate: 0.6667, studied_days: 5,
  },
  trend: thirtyDays(),
  subject_breakdown: [
    { subject_id: 3, subject_name: '英語', study_seconds: 600, answered_count: 7, correct_count: 5, accuracy_rate: 0.7143 },
    { subject_id: 4, subject_name: '数学', study_seconds: 300, answered_count: 3, correct_count: 2, accuracy_rate: 0.6667 },
  ],
  ...patch,
});

const emptyPeriod = (): DashboardAnalytics => analytics({
  totals: { study_seconds: 0, answered_count: 0, correct_count: 0, accuracy_rate: null, studied_days: 0 },
  trend: thirtyDays().map((bucket) => dayBucket(bucket.start_date)),
  subject_breakdown: [],
});

const respond = (data: unknown) => {
  mockGet.mockImplementation((url: string) =>
    url === URL ? Promise.resolve({ data }) : Promise.resolve({ data: {} }));
};

const analyticsCalls = () => mockGet.mock.calls.filter(([url]) => url === URL);

const renderStatistics = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Statistics />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

const openTab = (name: string) => fireEvent.click(screen.getByRole('tab', { name }));

describe('Statistics', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, 'error').mockImplementation(() => undefined);
  });

  afterEach(() => {
    (console.error as jest.Mock).mockRestore();
  });

  it('TC-20: 契約どおりの応答の数字・期間・推移を出し、書き出しと間違いパターンは無い', async () => {
    respond(analytics());
    renderStatistics();

    expect(await screen.findByText('2時間5分')).toBeInTheDocument();
    expect(screen.getByText('67%')).toBeInTheDocument();
    expect(screen.getByText('15問')).toBeInTheDocument();
    expect(screen.getByText('5日')).toBeInTheDocument();
    expect(screen.getByText('2026/10/16〜2026/11/14')).toBeInTheDocument();
    const bars = screen.getByTestId('bar-chart');
    const points = bars.getAttribute('data-points')?.split(',');
    expect(points).toHaveLength(30);
    // 棒は分の小数第 1 位まで（7530 秒 = 125.5 分。1 分未満の区切りも 0 の棒にしない）
    expect(points?.[29]).toBe('125.5');
    expect(screen.queryByRole('button', { name: /エクスポート/ })).toBeNull();
    expect(screen.queryByRole('tab', { name: /間違い/ })).toBeNull();
  });

  it('TC-21: データ無しは「まだ記録がありません」と「クイズを始める」だけを出す', async () => {
    respond(analytics({ ...emptyPeriod(), has_data: false }));
    renderStatistics();

    expect(await screen.findByText('まだ記録がありません')).toBeInTheDocument();
    expect(screen.getByText('クイズを解くと、学習時間と正答率の推移がここに出ます')).toBeInTheDocument();
    expect(screen.queryByRole('tab')).toBeNull();
    expect(screen.queryByText('解いた問題数')).toBeNull();
    expect(screen.queryByTestId('bar-chart')).toBeNull();

    userEvent.click(screen.getByRole('button', { name: 'クイズを始める' }));
    expect(mockNavigate).toHaveBeenCalledWith('/quiz');
  });

  it.each([
    ['trend を欠く', (() => { const { trend, ...rest } = analytics(); return rest; })()],
    ['totals を欠く', (() => { const { totals, ...rest } = analytics(); return rest; })()],
    ['区切りが知らない値', analytics({ period: { ...analytics().period, granularity: 'year' as never } })],
  ])('TC-22: 形の違う応答（%s）はエラーの表示にし、0 や空のグラフを出さない', async (_, data) => {
    respond(data);
    renderStatistics();

    expect(await screen.findByRole('alert')).toHaveTextContent('学習統計を読み込めませんでした');
    expect(screen.queryByText('0分')).toBeNull();
    expect(screen.queryByText('0問')).toBeNull();
    expect(screen.queryByTestId('bar-chart')).toBeNull();
  });

  it('TC-22: 取得の失敗はエラーの表示にし、「再読み込み」で取り直す', async () => {
    mockGet.mockRejectedValue(new Error('network'));
    renderStatistics();

    expect(await screen.findByRole('alert')).toHaveTextContent('学習統計を読み込めませんでした');
    expect(screen.queryByTestId('bar-chart')).toBeNull();
    const before = analyticsCalls().length;

    respond(analytics());
    userEvent.click(screen.getByRole('button', { name: '再読み込み' }));
    await waitFor(() => expect(analyticsCalls().length).toBe(before + 1));
    expect(await screen.findByText('15問')).toBeInTheDocument();
  });

  it('TC-23: 開いた直後は 30 日、期間と科目を選ぶとその値で取り直す', async () => {
    respond(analytics());
    renderStatistics();
    await screen.findByText('15問');
    expect(mockGet).toHaveBeenLastCalledWith(URL, { params: { days: 30 } });

    userEvent.click(screen.getByRole('combobox', { name: /期間/ }));
    userEvent.click(await screen.findByRole('option', { name: '直近 90 日' }));
    await waitFor(() => expect(mockGet).toHaveBeenLastCalledWith(URL, { params: { days: 90 } }));

    userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));
    await waitFor(() =>
      expect(mockGet).toHaveBeenLastCalledWith(URL, { params: { days: 90, subject_id: '5' } }));
  });

  it('TC-24: 期間に答えが無いときはカードに 0 と「—」、グラフの代わりに「この期間の記録はありません」', async () => {
    respond(emptyPeriod());
    renderStatistics();

    expect(await screen.findByText('0分')).toBeInTheDocument();
    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.getByText('0問')).toBeInTheDocument();
    expect(screen.getByText('0日')).toBeInTheDocument();
    expect(screen.queryByText('まだ記録がありません')).toBeNull();
    expect(screen.getByText('この期間の記録はありません')).toBeInTheDocument();
    expect(screen.queryByTestId('bar-chart')).toBeNull();

    openTab('科目別（全科目）');
    expect(screen.getByText('この期間の記録はありません')).toBeInTheDocument();
  });

  it.each([
    ['week', '2026-11-09', '2026-11-14', '11/9〜'],
    ['month', '2026-11-01', '2026-11-14', '2026/11'],
    ['day', '2026-11-14', '2026-11-14', '11/14'],
  ] as const)('TC-25: 区切り %s のラベル', async (granularity, start, end, label) => {
    respond(analytics({
      period: { days: 90, start_date: '2026-08-17', end_date: '2026-11-14', granularity },
      trend: [
        { ...dayBucket(start, 600, 2, 1), end_date: end },
        { ...dayBucket('2026-11-15'), start_date: '2026-11-15' },
      ],
    }));
    renderStatistics();

    const bars = await screen.findByTestId('bar-chart');
    expect(bars.getAttribute('data-labels')?.split(',')[0]).toBe(label);

    openTab('正答率');
    // 答えの無い区切りは 0% にせず null のまま（線を切る）
    expect(screen.getByTestId('line-chart')).toHaveAttribute('data-points', '50,null');
  });

  it('TC-26: 科目別は科目ごとの学習時間・正答率・問題数と円グラフ。学習時間が 0 なら円グラフの代わりに文言', async () => {
    respond(analytics());
    const { unmount } = renderStatistics();
    await screen.findByText('15問');
    openTab('科目別（全科目）');

    const english = screen.getByRole('region', { name: '英語' });
    expect(within(english).getByText('10分')).toBeInTheDocument();
    expect(within(english).getByText('71%')).toBeInTheDocument();
    expect(within(english).getByText('7問')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '数学' })).toBeInTheDocument();
    expect(screen.getByTestId('pie')).toHaveAttribute('data-count', '2');
    unmount();

    respond(analytics({
      subject_breakdown: analytics().subject_breakdown.map((s) => ({ ...s, study_seconds: 0 })),
    }));
    renderStatistics();
    await screen.findByText('15問');
    openTab('科目別（全科目）');

    expect(screen.queryByTestId('pie')).toBeNull();
    expect(screen.getByText('学習時間の記録がありません')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '英語' })).toBeInTheDocument();
  });
});
