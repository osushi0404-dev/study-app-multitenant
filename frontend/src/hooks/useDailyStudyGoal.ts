/**
 * 1 日の学習目標（分）を設定から読む（I487）
 * 取得は React Query（規約 6.3）。読めない・値が無いときは null（仮の値で埋めず、目標の表示を隠す・C7）
 * 設定画面は保存のときに USER_SETTINGS_KEY_ROOT のキャッシュを古いことにする（Settings.tsx）
 */
import { useQuery } from '@tanstack/react-query';
import dashboardService from '../services/dashboard.service';
import { UserSettings } from '../types/api';

export type DailyGoalState =
  | { status: 'loading' }
  | { status: 'done'; minutes: number | null };

export const USER_SETTINGS_KEY_ROOT = 'user-settings';
export const userSettingsKey = (userId: string) => [USER_SETTINGS_KEY_ROOT, userId] as const;

const toGoalMinutes = (value: unknown): number | null =>
  typeof value === 'number' && Number.isInteger(value) && value > 0 ? value : null;

const fetchSettings = async (): Promise<UserSettings> => {
  try {
    return await dashboardService.getUserSettings();
  } catch (error) {
    console.error('Error loading study goal:', error);
    throw error;
  }
};

export const useDailyStudyGoal = (userId: string): DailyGoalState => {
  const query = useQuery({ queryKey: userSettingsKey(userId), queryFn: fetchSettings });

  if (query.isSuccess) return { status: 'done', minutes: toGoalMinutes(query.data.daily_study_goal_minutes) };
  if (query.isError) return { status: 'done', minutes: null };
  return { status: 'loading' };
};
