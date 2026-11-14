/**
 * ダッシュボードの直近 7 日の値の書式（I513）
 *
 * 応答の last_7_days から、棒の値・tooltip・7 日の合計を作る（裏側は変えない）。
 * 分は切り捨て（数字のカードの「今日の学習時間」と同じ）、正答率は整数の % に四捨五入・答えが 0 件は「—」。
 * 日付は 'YYYY-MM-DD' を分けて読む（new Date('YYYY-MM-DD') は UTC として読まれ、端末によっては日がずれるため）。
 */
import { DashboardOverview } from '../../types/api';
import { formatRate } from '../statistics/format';

export type DashboardDay = DashboardOverview['last_7_days'][number];

/** 秒を分に切り捨て */
export const studyMinutes = (seconds: number): number => Math.floor(seconds / 60);

const rateOf = (correct: number, answered: number): number | null =>
  answered > 0 ? correct / answered : null;

/** 横軸のラベル（曜日だけ。例: 金） */
export const dayAxisLabel = (date: string): string => {
  const [year, month, day] = date.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('ja-JP', { weekday: 'short' });
};

/** tooltip の題（例: 11/13（金）） */
export const dayTitle = (date: string): string => {
  const [, month, day] = date.split('-').map(Number);
  return `${month}/${day}（${dayAxisLabel(date)}）`;
};

/** tooltip の 3 行 */
export const dayLines = (day: DashboardDay): string[] => [
  `学習時間: ${studyMinutes(day.study_seconds)}分`,
  `解答数: ${day.answered_count}問`,
  `正答率: ${formatRate(rateOf(day.correct_count, day.answered_count))}`,
];

/** 画面読み上げ用の日ごとの値（11/13（金） 5分・3問、…） */
export const daysAriaLabel = (days: DashboardDay[]): string =>
  days
    .map((day) => `${dayTitle(day.date)} ${studyMinutes(day.study_seconds)}分・${day.answered_count}問`)
    .join('、');

/** 直近 7 日の合計: 78分・9問・正答率78%（秒・解答・正解をそれぞれ足してから丸める） */
export const weeklyTotalText = (days: DashboardDay[]): string => {
  const seconds = days.reduce((sum, day) => sum + day.study_seconds, 0);
  const answered = days.reduce((sum, day) => sum + day.answered_count, 0);
  const correct = days.reduce((sum, day) => sum + day.correct_count, 0);
  return `直近 7 日の合計: ${studyMinutes(seconds)}分・${answered}問・正答率${formatRate(rateOf(correct, answered))}`;
};
