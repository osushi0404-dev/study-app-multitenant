/**
 * 達成のお知らせの判定（I487・TC-12〜TC-15）
 * 日付と記録は引数で渡す（時刻の差し替えはしない）
 */
import {
  AchievementRecord,
  achievementStorageKey,
  decideAchievements,
  emptyRecord,
  loadRecord,
  saveRecord,
} from '../dashboardAchievements';
import { DashboardOverview } from '../../types/api';

const overview = (patch: {
  answered?: number;
  accuracy?: number | null;
  streak?: number;
  todaySeconds?: number;
  /** 今日の答えの数（連続の終わりが今日か昨日かを決める・裏側の _current_streak と同じ規則） */
  answeredToday?: number;
} = {}): DashboardOverview => ({
  has_data: true,
  today: {
    study_seconds: patch.todaySeconds ?? 0,
    answered_count: patch.answeredToday ?? 0,
    correct_count: 0,
    accuracy_rate: null,
  },
  streak: { current_days: patch.streak ?? 0 },
  totals: {
    answered_count: patch.answered ?? 0,
    correct_count: 0,
    accuracy_rate: patch.accuracy === undefined ? null : patch.accuracy,
  },
  last_7_days: [{ date: '2026-11-13', study_seconds: 0, answered_count: 0, correct_count: 0 }],
  weak_subjects: [],
  recommendations: [],
});

const decide = (
  data: DashboardOverview,
  record: AchievementRecord = emptyRecord(),
  today = '2026-11-13',
  goalMinutes: number | null = null
) => decideAchievements({ overview: data, goalMinutes, today, record });

const answeredMessage = (n: number) => `${n}問解答達成！おめでとうございます！🎉`;
const HIGH_ACCURACY = '素晴らしい正答率です！95%以上をキープしています！🎯';
const DAILY_GOAL = '今日の学習目標を達成しました！継続は力なり！💪';

describe('dashboardAchievements', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('TC-12: 記録はユーザーごとのキーで、壊れた値は空の記録として読む', () => {
    expect(achievementStorageKey('user-1')).toBe('dashboardAchievements:user-1');

    localStorage.setItem('lastHighAccuracyNotification', 'Fri Nov 13 2026');
    localStorage.setItem('lastDailyGoalNotification', 'Fri Nov 13 2026');
    saveRecord('user-1', { ...emptyRecord(), answeredMilestone: 50 });

    expect(loadRecord('user-1').answeredMilestone).toBe(50);
    expect(loadRecord('user-2')).toEqual(emptyRecord());
    // ユーザーの区別が無い古いキーは消す
    expect(localStorage.getItem('lastHighAccuracyNotification')).toBeNull();
    expect(localStorage.getItem('lastDailyGoalNotification')).toBeNull();

    localStorage.setItem(achievementStorageKey('user-3'), '{');
    expect(() => loadRecord('user-3')).not.toThrow();
    expect(loadRecord('user-3')).toEqual(emptyRecord());
  });

  it('TC-13: 解答数は、越えた中で一番大きい未表示の節目を 1 回だけ出す', () => {
    const first = decide(overview({ answered: 12 }));
    expect(first.messages).toEqual([answeredMessage(10)]);
    expect(first.record.answeredMilestone).toBe(10);

    expect(decide(overview({ answered: 12 }), first.record).messages).toEqual([]);
    expect(decide(overview({ answered: 55 }), first.record).messages).toEqual([answeredMessage(50)]);

    const none = decide(overview({ answered: 9 }));
    expect(none.messages).toEqual([]);
    expect(none.record.answeredMilestone).toBe(0);

    const jump = decide(overview({ answered: 120 }));
    expect(jump.messages).toEqual([answeredMessage(100)]);
    expect(jump.record.answeredMilestone).toBe(100);
    expect(decide(overview({ answered: 130 }), jump.record).messages).toEqual([]);
  });

  it('TC-14: 連続日数の節目は同じ連続の間に 1 回、途切れて再び届けばもう一度', () => {
    const answered = (streak: number) => overview({ streak, answeredToday: 1 });
    const first = decide(answered(7), emptyRecord(), '2026-11-13');
    expect(first.streakDays).toBe(7);
    expect(first.record.streakRuns['7']).toBe('2026-11-07');

    expect(decide(answered(7), first.record, '2026-11-13').streakDays).toBeNull();
    expect(decide(answered(8), first.record, '2026-11-14').streakDays).toBeNull();

    const fourteen = decide(answered(14), first.record, '2026-11-20');
    expect(fourteen.streakDays).toBe(14);
    expect(fourteen.record.streakRuns['14']).toBe('2026-11-07');

    const again = decide(answered(7), first.record, '2026-11-30');
    expect(again.streakDays).toBe(7);
    expect(again.record.streakRuns['7']).toBe('2026-11-24');

    expect(decide(overview({ streak: 0 })).streakDays).toBeNull();
  });

  it('TC-14b: 今日まだ答えていない日は、連続の終わりを昨日として同じ連続と見なす（F1）', () => {
    const first = decide(overview({ streak: 7, answeredToday: 1 }), emptyRecord(), '2026-11-13');
    // 翌日、まだ答えずに開く: 裏側は昨日までの 7 日を返す。同じ連続なので出さない
    const nextDay = decide(overview({ streak: 7, answeredToday: 0 }), first.record, '2026-11-14');
    expect(nextDay.streakDays).toBeNull();
    expect(nextDay.record.streakRuns['7']).toBe('2026-11-07');

    // 初めて開いたのが「昨日まで 7 日・今日はまだ」の日: 始まりは昨日の 6 日前
    const fresh = decide(overview({ streak: 7, answeredToday: 0 }), emptyRecord(), '2026-11-14');
    expect(fresh.streakDays).toBe(7);
    expect(fresh.record.streakRuns['7']).toBe('2026-11-07');
  });

  it('TC-15: 正答率 95% と目標達成は 1 日 1 回', () => {
    const high = decide(overview({ answered: 20, accuracy: 0.95 }), { ...emptyRecord(), answeredMilestone: 10 });
    expect(high.messages).toEqual([HIGH_ACCURACY]);
    expect(high.record.highAccuracyDate).toBe('2026-11-13');
    expect(decide(overview({ answered: 20, accuracy: 0.95 }), high.record).messages).toEqual([]);
    expect(
      decide(overview({ answered: 20, accuracy: 0.95 }), high.record, '2026-11-14').messages
    ).toEqual([HIGH_ACCURACY]);
    expect(decide(overview({ answered: 19, accuracy: 0.95 })).messages).not.toContain(HIGH_ACCURACY);
    expect(decide(overview({ answered: 20, accuracy: null })).messages).not.toContain(HIGH_ACCURACY);

    const goal = decide(overview({ todaySeconds: 1800 }), emptyRecord(), '2026-11-13', 30);
    expect(goal.messages).toEqual([DAILY_GOAL]);
    expect(goal.record.dailyGoalDate).toBe('2026-11-13');
    expect(decide(overview({ todaySeconds: 1800 }), goal.record, '2026-11-13', 30).messages).toEqual([]);
    expect(
      decide(overview({ todaySeconds: 1800 }), goal.record, '2026-11-14', 30).messages
    ).toEqual([DAILY_GOAL]);
    expect(decide(overview({ todaySeconds: 99999 }), emptyRecord(), '2026-11-13', null).messages).toEqual([]);
    expect(decide(overview({ todaySeconds: 1799 }), emptyRecord(), '2026-11-13', 30).messages).toEqual([]);
  });
});
