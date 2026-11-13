/**
 * ダッシュボードの数字の取得と状態（I487）
 *
 * 取得は React Query（規約 6.3）。同じキーの取得の重ね合わせ（開発時の StrictMode でも 1 回）・
 * 古い応答の破棄・再試行・キャッシュは React Query に任せる。
 * 画面には 3 つの状態（読み込み中・失敗・成功）で返す（データ無しは成功の中の has_data で表す）。
 */
import { useQuery } from '@tanstack/react-query';
import dashboardService from '../services/dashboard.service';
import { DashboardOverview } from '../types/api';

export const ALL_SUBJECTS = 'all';

type OverviewState =
  | { status: 'loading'; data: null }
  | { status: 'error'; data: null }
  | { status: 'success'; data: DashboardOverview };

/** キーにユーザーを入れる（同じタブで別のユーザーで入り直したときに、前のユーザーのキャッシュを出さない） */
export const dashboardOverviewKey = (userId: string, subjectId: string) =>
  ['dashboard', 'overview', userId, subjectId] as const;

const fetchOverview = async (subjectId: string): Promise<DashboardOverview> => {
  try {
    // 応答の形が違えば getOverview が投げる（欠けたキーを 0 で埋めない・I473）
    return await dashboardService.getOverview(subjectId === ALL_SUBJECTS ? {} : { subject_id: subjectId });
  } catch (error) {
    console.error('Error fetching dashboard data:', error);
    throw error;
  }
};

export const useDashboardOverview = (userId: string, subjectId: string) => {
  // 科目を切り替えるとキーが変わり、新しいキーは読み込み中になる。前の科目の数字は出さない（placeholderData を使わない・C7）
  const query = useQuery({
    queryKey: dashboardOverviewKey(userId, subjectId),
    queryFn: () => fetchOverview(subjectId),
  });

  // 失敗の後の取り直しの間も読み込み中（スケルトン）にする
  let state: OverviewState;
  if (query.isSuccess) {
    state = { status: 'success', data: query.data };
  } else if (query.isError && !query.isFetching) {
    state = { status: 'error', data: null };
  } else {
    state = { status: 'loading', data: null };
  }

  return { ...state, retry: () => { query.refetch(); } };
};
