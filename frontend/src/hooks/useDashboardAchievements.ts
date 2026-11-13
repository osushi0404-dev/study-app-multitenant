/**
 * ダッシュボードの達成のお知らせを出す（I487）
 *
 * 「すべて」の応答が来て、ユーザーと目標の読み込みが済んだら判定する。
 * 判定は utils/dashboardAchievements の純粋な関数で、記録はユーザーごとに localStorage に置く。
 * お知らせの関数は ref で持ち、取得の effect の依存に入れない（I473 F11）。
 */
import { useEffect, useRef } from 'react';
import { useNotifications } from '../contexts/NotificationContext';
import { DashboardOverview } from '../types/api';
import {
  decideAchievements,
  loadRecord,
  localDateString,
  saveRecord,
} from '../utils/dashboardAchievements';
import { DailyGoalState } from './useDailyStudyGoal';

export const useDashboardAchievements = (
  userId: string | undefined,
  allSubjectsOverview: DashboardOverview | null,
  goal: DailyGoalState
) => {
  const { showAchievement, showStreakNotification } = useNotifications();
  const notify = useRef({ showAchievement, showStreakNotification });
  notify.current = { showAchievement, showStreakNotification };

  const goalMinutes = goal.status === 'done' ? goal.minutes : undefined;

  useEffect(() => {
    if (!userId || !allSubjectsOverview || goalMinutes === undefined) return;

    const decision = decideAchievements({
      overview: allSubjectsOverview,
      goalMinutes,
      today: localDateString(),
      record: loadRecord(userId),
    });
    if (decision.streakDays !== null) {
      notify.current.showStreakNotification(decision.streakDays);
    }
    decision.messages.forEach((message) => notify.current.showAchievement(message));
    saveRecord(userId, decision.record);
  }, [userId, allSubjectsOverview, goalMinutes]);
};
