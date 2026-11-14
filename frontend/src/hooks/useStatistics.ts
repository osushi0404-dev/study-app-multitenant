/**
 * 学習統計の取得と状態（I488）
 *
 * 取得は React Query（規約 6.3）。状態はダッシュボードと同じ 3 つ（読み込み中・失敗・成功・toLoadState）
 * で返す（データ無しは成功の中の has_data で表す）。
 */
import { useQuery } from '@tanstack/react-query';
import dashboardService from '../services/dashboard.service';
import { DashboardAnalytics } from '../types/api';
import { toLoadState } from './queryLoadState';
import { ALL_SUBJECTS } from './useDashboardOverview';

/** 画面で選べる期間（API の days はこの 4 つだけを送る） */
export const STATISTICS_PERIODS = [
  { days: 7, label: '直近 7 日' },
  { days: 30, label: '直近 30 日' },
  { days: 90, label: '直近 90 日' },
  { days: 365, label: '直近 1 年' },
] as const;

export const DEFAULT_STATISTICS_DAYS = 30;

const fetchStatistics = async (days: number, subjectId: string): Promise<DashboardAnalytics> => {
  try {
    // 応答の形が違えば getAnalytics が投げる（欠けたキーを空で埋めない）
    return await dashboardService.getAnalytics(
      subjectId === ALL_SUBJECTS ? { days } : { days, subject_id: subjectId }
    );
  } catch (error) {
    console.error('Error fetching analytics data:', error);
    throw error;
  }
};

export const useStatistics = (userId: string, days: number, subjectId: string) =>
  // キーにユーザーを入れる（同じタブで別のユーザーで入り直したときに、前のユーザーのキャッシュを出さない）。
  // 期間・科目を切り替えるとキーが変わり、新しいキーは読み込み中になる（前の数字は出さない・C7）
  toLoadState(useQuery({
    queryKey: ['dashboard', 'analytics', userId, days, subjectId],
    queryFn: () => fetchStatistics(days, subjectId),
  }));
