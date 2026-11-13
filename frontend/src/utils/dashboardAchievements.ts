/**
 * ダッシュボードの達成のお知らせの判定と記録（I487）
 *
 * 判定は純粋な関数（日付と記録を引数で受ける）。記録は localStorage にユーザーごとのキー 1 つで置く。
 * - 連続日数: 7 の倍数の節目を、同じ連続の間に 1 回（途切れて新しい連続で届けばもう一度）
 * - 解答数: 越えた節目のうち一番大きい未表示のものを 1 回（小さい未表示の節目はまとめて出したことにする）
 * - 正答率 95%・今日の目標達成: 1 日 1 回
 * 「今日」は端末の日付。アプリの「今日」の日付のずれは #481 の範囲。
 */
import { DashboardOverview } from '../types/api';

export interface AchievementRecord {
  /** 出した解答数の節目の最大（0 = まだ） */
  answeredMilestone: number;
  /** 連続日数の節目 → その連続の始まりの日（YYYY-MM-DD） */
  streakRuns: Record<string, string>;
  /** 正答率 95% を出した日 */
  highAccuracyDate: string | null;
  /** 今日の目標達成を出した日 */
  dailyGoalDate: string | null;
}

const ANSWER_MILESTONES = [10, 50, 100, 250, 500, 1000] as const;
const STREAK_STEP_DAYS = 7;
const HIGH_ACCURACY_RATE = 0.95;
const HIGH_ACCURACY_MIN_ANSWERED = 20;

const HIGH_ACCURACY_MESSAGE = '素晴らしい正答率です！95%以上をキープしています！🎯';
const DAILY_GOAL_MESSAGE = '今日の学習目標を達成しました！継続は力なり！💪';
const answeredMessage = (milestone: number) => `${milestone}問解答達成！おめでとうございます！🎉`;

/** ユーザーの区別が無かった I487 より前のキー（見つけたら消す） */
const LEGACY_KEYS = ['lastHighAccuracyNotification', 'lastDailyGoalNotification'];

/** 今日の学習の分（秒を分に切り捨て） */
export const todayStudyMinutes = (overview: DashboardOverview): number =>
  Math.floor(overview.today.study_seconds / 60);

export const emptyRecord = (): AchievementRecord => ({
  answeredMilestone: 0,
  streakRuns: {},
  highAccuracyDate: null,
  dailyGoalDate: null,
});

export const achievementStorageKey = (userId: string) => `dashboardAchievements:${userId}`;

/** 端末の日付を YYYY-MM-DD で */
export const localDateString = (date: Date = new Date()): string => {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
};

/** YYYY-MM-DD の days 日前（時刻・夏時間に左右されないよう UTC の暦で数える） */
const daysBefore = (isoDate: string, days: number): string => {
  const [year, month, day] = isoDate.split('-').map(Number);
  return new Date(Date.UTC(year, month - 1, day - days)).toISOString().slice(0, 10);
};

const isStringOrNull = (value: unknown): value is string | null =>
  value === null || typeof value === 'string';

const toRecord = (value: unknown): AchievementRecord => {
  if (typeof value !== 'object' || value === null) return emptyRecord();
  const v = value as Record<string, unknown>;
  const runs = v.streakRuns;
  const validRuns =
    typeof runs === 'object' && runs !== null && !Array.isArray(runs) &&
    Object.values(runs).every((start) => typeof start === 'string');
  if (
    typeof v.answeredMilestone !== 'number' ||
    !validRuns ||
    !isStringOrNull(v.highAccuracyDate) ||
    !isStringOrNull(v.dailyGoalDate)
  ) {
    return emptyRecord();
  }
  return {
    answeredMilestone: v.answeredMilestone,
    streakRuns: { ...(runs as Record<string, string>) },
    highAccuracyDate: v.highAccuracyDate,
    dailyGoalDate: v.dailyGoalDate,
  };
};

/** 読めない・壊れた値は空の記録として扱う（お知らせのために画面を落とさない） */
export const loadRecord = (userId: string): AchievementRecord => {
  try {
    const raw = localStorage.getItem(achievementStorageKey(userId));
    return raw ? toRecord(JSON.parse(raw)) : emptyRecord();
  } catch {
    return emptyRecord();
  }
};

export const saveRecord = (userId: string, record: AchievementRecord): void => {
  try {
    localStorage.setItem(achievementStorageKey(userId), JSON.stringify(record));
    LEGACY_KEYS.forEach((key) => localStorage.removeItem(key));
  } catch {
    // 保存できなくても画面は続ける（次に開いたときにもう一度出ることがあるだけ）
  }
};

interface AchievementDecision {
  /** 出す連続日数の節目（無ければ null） */
  streakDays: number | null;
  /** 出すお知らせの文 */
  messages: string[];
  /** 出した後の記録 */
  record: AchievementRecord;
}

export const decideAchievements = ({
  overview,
  goalMinutes,
  today,
  record,
}: {
  overview: DashboardOverview;
  goalMinutes: number | null;
  today: string;
  record: AchievementRecord;
}): AchievementDecision => {
  const next: AchievementRecord = { ...record };
  const messages: string[] = [];
  let streakDays: number | null = null;

  const days = overview.streak.current_days;
  if (days > 0 && days % STREAK_STEP_DAYS === 0) {
    // 裏側（dashboard/selectors.py の _current_streak）は、今日に答えがあれば今日まで、無ければ昨日までを数える。
    // 同じ規則で連続の終わりの日を決め、そこから始まりの日を出す（I487 F1）
    const endsToday = overview.today.answered_count > 0;
    const runStart = daysBefore(today, days - 1 + (endsToday ? 0 : 1));
    const runs = new Map(Object.entries(next.streakRuns));
    if (runs.get(String(days)) !== runStart) {
      streakDays = days;
      runs.set(String(days), runStart);
      next.streakRuns = Object.fromEntries(runs);
    }
  }

  const { answered_count: answered, accuracy_rate: accuracy } = overview.totals;
  const reached = ANSWER_MILESTONES.filter((milestone) => milestone <= answered);
  const largest = reached.length > 0 ? reached[reached.length - 1] : 0;
  if (largest > next.answeredMilestone) {
    messages.push(answeredMessage(largest));
    next.answeredMilestone = largest;
  }

  if (
    accuracy !== null &&
    accuracy >= HIGH_ACCURACY_RATE &&
    answered >= HIGH_ACCURACY_MIN_ANSWERED &&
    next.highAccuracyDate !== today
  ) {
    messages.push(HIGH_ACCURACY_MESSAGE);
    next.highAccuracyDate = today;
  }

  if (goalMinutes !== null && todayStudyMinutes(overview) >= goalMinutes && next.dailyGoalDate !== today) {
    messages.push(DAILY_GOAL_MESSAGE);
    next.dailyGoalDate = today;
  }

  return { streakDays, messages, record: next };
};
