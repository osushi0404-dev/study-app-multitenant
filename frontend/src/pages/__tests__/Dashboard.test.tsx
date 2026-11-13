/**
 * ダッシュボード（I473・TC-20〜TC-23・TC-25）
 * 契約どおりのキーを読む・データ無し・形の違い/失敗はエラー（0 で埋めない）・科目の選択・苦手 0 件
 */
import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Dashboard from '../Dashboard';
import apiClient from '../../services/api';
import SubjectService from '../../services/subjectService';
import { DashboardOverview } from '../../types/api';

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
      {/* 読み込み中は画面全体が置き換わるので、科目 5 を選んだ直後に「すべて」へ切り替える動きをまとめて起こす */}
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

  it('TC-25: 一覧が空なら、一覧に入る条件（5 問以上）を含めて伝える（F4）', async () => {
    respond(overview({ weak_subjects: [] }));
    render(<Dashboard />);

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
    render(<Dashboard />);
    await screen.findByText('5分');

    await userEvent.click(screen.getByRole('button', { name: '科目5を選ぶ' }));

    expect(await screen.findByText('まだ解答の記録がありません')).toBeInTheDocument();
    expect(screen.getByText('英語')).toBeInTheDocument();
    expect(
      screen.queryByText('データがありません。まずは問題を解いてみましょう！')
    ).not.toBeInTheDocument();
  });

  it('TC-27: 達成のお知らせは「すべて」の応答だけで判定し、科目で絞った応答では出さない（F2）', async () => {
    const milestone = { totals: { answered_count: 10, correct_count: 5, accuracy_rate: 0.5 } };
    respond(overview(milestone));
    render(<Dashboard />);
    await screen.findByText('5分');
    expect(mockShowAchievement).toHaveBeenCalledTimes(1);
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
    render(<Dashboard />);
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
});
