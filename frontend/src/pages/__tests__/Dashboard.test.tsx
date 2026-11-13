/**
 * ダッシュボード（I473・TC-20〜TC-23・TC-25）
 * 契約どおりのキーを読む・データ無し・形の違い/失敗はエラー（0 で埋めない）・科目の選択・苦手 0 件
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Dashboard from '../Dashboard';
import apiClient from '../../services/api';
import SubjectService from '../../services/subjectService';
import { DashboardOverview } from '../../services/types';

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
  useAuth: () => ({ user: { user_id: 'u_i473' } }),
}));

// useCallback の依存に入るので、毎回同じ関数を返す
const mockShowAchievement = jest.fn();
const mockShowStreakNotification = jest.fn();
jest.mock('../../contexts/NotificationContext', () => ({
  useNotifications: () => ({
    showAchievement: mockShowAchievement,
    showStreakNotification: mockShowStreakNotification,
  }),
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
    </>
  ),
}));

jest.mock('../../components/TodayReviewCard', () => ({
  __esModule: true,
  default: () => <div>今日の復習のカード</div>,
}));

jest.mock('react-chartjs-2', () => ({
  Line: ({ data }: { data: { labels: string[]; datasets: Array<{ data: number[] }> } }) => (
    <div data-testid="line-chart" data-points={data.datasets[0].data.join(',')} />
  ),
  Doughnut: () => <div data-testid="doughnut-chart" />,
}));

const URL = '/api/dashboard/overview/';
const mockGet = apiClient.get as jest.Mock;

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

const respond = (data: unknown) => {
  mockGet.mockImplementation((url: string) =>
    url === URL ? Promise.resolve({ data }) : Promise.resolve({ data: {} })
  );
};

describe('Dashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // CRA の Jest は各テストの前にモックの実装を消す（resetMocks）ので、ここで入れ直す
    (SubjectService.getUserSubjects as jest.Mock).mockResolvedValue([]);
  });

  it('TC-20: 契約どおりの応答の数字・推移・苦手・おすすめを出し、「練習する」でその科目へ進む', async () => {
    respond(overview());
    render(<Dashboard />);

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

  it('TC-21: データ無しなら赤い円を出さず、正答率は「—」', async () => {
    respond(overview({
      has_data: false,
      today: { study_seconds: 0, answered_count: 0, correct_count: 0, accuracy_rate: null },
      streak: { current_days: 0 },
      totals: { answered_count: 0, correct_count: 0, accuracy_rate: null },
      last_7_days: days([0, 0, 0, 0, 0, 0, 0]),
      weak_subjects: [],
      recommendations: [],
    }));
    render(<Dashboard />);

    expect(await screen.findByText('まだ解答の記録がありません')).toBeInTheDocument();
    expect(screen.queryByTestId('doughnut-chart')).not.toBeInTheDocument();
    expect(screen.getByText('—')).toBeInTheDocument();
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
    render(<Dashboard />);

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
    render(<Dashboard />);
    await screen.findByText('5分');
    expect(mockGet).toHaveBeenCalledWith(URL, { params: {} });

    await userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));
    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(URL, { params: { subject_id: '5' } });
    });
  });

  it('TC-25: 正答率 70% 未満の科目が無ければ、その旨を出す', async () => {
    respond(overview({ weak_subjects: [] }));
    render(<Dashboard />);

    expect(await screen.findByText('正答率が 70% 未満の科目はありません')).toBeInTheDocument();
  });
});
