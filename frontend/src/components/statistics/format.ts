/**
 * 学習統計の表示の書式（I488）
 *
 * 日付は API の 'YYYY-MM-DD' の文字列を分けて使う（new Date('YYYY-MM-DD') は UTC として読まれ、
 * ブラウザのタイムゾーンによっては日がずれるため）。
 */
import { DashboardAnalyticsGranularity } from '../../types/api';

export const NO_RECORD_IN_PERIOD_TEXT = 'この期間の記録はありません';

interface DateParts {
  year: number;
  month: number;
  day: number;
}

const partsOf = (text: string): DateParts => {
  const [year, month, day] = text.split('-').map(Number);
  return { year, month, day };
};

const fullDate = ({ year, month, day }: DateParts) => `${year}/${month}/${day}`;

/** 学習時間（秒）を分に切り捨て、60 分以上は「◯時間◯分」 */
export const formatStudyTime = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}分`;
  }
  return `${Math.floor(minutes / 60)}時間${minutes % 60}分`;
};

/** 正答率（0〜1）を整数の %。答えが 0 件（null）は「—」 */
export const formatRate = (rate: number | null): string =>
  rate === null ? '—' : `${Math.round(rate * 100)}%`;

/** 期間の表示（例 2026/10/16〜2026/11/14） */
export const formatPeriod = (start: string, end: string): string =>
  `${fullDate(partsOf(start))}〜${fullDate(partsOf(end))}`;

/** グラフの横軸のラベル: 日ごと M/D・週ごと M/D〜・月ごと YYYY/M */
export const formatBucketLabel = (start: string, granularity: DashboardAnalyticsGranularity): string => {
  const { year, month, day } = partsOf(start);
  if (granularity === 'month') {
    return `${year}/${month}`;
  }
  return granularity === 'week' ? `${month}/${day}〜` : `${month}/${day}`;
};

/** ツールチップの範囲: 1 日なら YYYY/M/D、複数日なら YYYY/M/D〜M/D（年をまたぐときは終わりにも年） */
export const formatBucketRange = (start: string, end: string): string => {
  const from = partsOf(start);
  if (start === end) {
    return fullDate(from);
  }
  const to = partsOf(end);
  const toText = to.year === from.year ? `${to.month}/${to.day}` : fullDate(to);
  return `${fullDate(from)}〜${toText}`;
};
