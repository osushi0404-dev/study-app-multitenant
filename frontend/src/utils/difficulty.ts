/**
 * 難易度の表示名（I466）
 * API は難易度を 'easy'・'medium'・'hard' の文字で返す（裏側の正は backend/problems/difficulty.py）。
 * クイズの画面とダッシュボードの「間違いやすい分野」で同じ表示名を使い、応答の形の確かめもこの表で行う
 */
import { DashboardWeakDifficulty } from '../types/api';

export type Difficulty = DashboardWeakDifficulty['difficulty'];

// API の選択肢が増えても消えても、ここが合わなければ型の検査で落ちる
const LABELS: Record<Difficulty, string> = {
  easy: '初級',
  medium: '中級',
  hard: '上級',
};
const DIFFICULTY_LABELS: ReadonlyMap<string, string> = new Map(Object.entries(LABELS));

/** API の難易度の文字か */
export const isDifficulty = (value: unknown): value is Difficulty =>
  typeof value === 'string' && DIFFICULTY_LABELS.has(value);

/** 表示名。知らない値はそのまま返す */
export const difficultyLabel = (value: string): string => DIFFICULTY_LABELS.get(value) ?? value;
