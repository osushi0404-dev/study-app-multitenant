/**
 * 1 日の学習目標（分）を設定から読む（I487）
 * 読めない・値が無いときは null（仮の値で埋めず、目標の表示を隠す・C7）
 */
import { useEffect, useState } from 'react';
import dashboardService from '../services/dashboard.service';

export type DailyGoalState =
  | { status: 'loading' }
  | { status: 'done'; minutes: number | null };

const toGoalMinutes = (value: unknown): number | null =>
  typeof value === 'number' && Number.isInteger(value) && value > 0 ? value : null;

export const useDailyStudyGoal = (): DailyGoalState => {
  const [state, setState] = useState<DailyGoalState>({ status: 'loading' });

  useEffect(() => {
    let ignore = false;
    dashboardService
      .getUserSettings()
      .then((settings) => {
        if (!ignore) setState({ status: 'done', minutes: toGoalMinutes(settings.daily_study_goal_minutes) });
      })
      .catch((error) => {
        if (ignore) return;
        console.error('Error loading study goal:', error);
        setState({ status: 'done', minutes: null });
      });
    return () => {
      ignore = true;
    };
  }, []);

  return state;
};
