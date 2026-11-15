/**
 * ダッシュボードの画面と部品が共有する型（I513）
 * API の応答の型は types/api（OpenAPI から作る）にあり、ここは画面の中だけで組み立てる値の型を置く。
 */

/** 1 日の目標の進み具合（全科目の今日の分と目標の分） */
export interface GoalProgress {
  todayMinutes: number;
  goalMinutes: number;
}
