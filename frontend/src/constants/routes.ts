/**
 * 画面をまたいで使う道筋と、画面の中の目印（I494）
 * 画面どうしが互いの部品を読み込まずに、同じ値を指せるようにする
 */
import { QuizMode } from '../types/quiz';

/** 設定画面の「学ぶ科目」のカードの目印（カードの id・URL のハッシュ） */
export const LEARNING_SUBJECTS_ANCHOR = 'learning-subjects';

/** 設定画面の「学ぶ科目」のカードへの道筋（ダッシュボードの科目 0 件の案内から使う） */
export const LEARNING_SUBJECTS_PATH = `/settings#${LEARNING_SUBJECTS_ANCHOR}`;

/** 科目管理・問題管理の画面への道筋（組織の科目 0 件のときの管理者への案内から使う・I539） */
export const SUBJECT_MANAGEMENT_PATH = '/subject-management';
export const QUIZ_MANAGEMENT_PATH = '/quiz-management';

/** ダッシュボードから選べるクイズの始め方（いつものクイズ・苦手を優先〔I466〕。今日の復習は専用のカード） */
export type QuizStartMode = Exclude<QuizMode, 'review'>;

/** クイズの画面への道筋（ダッシュボードの「学習を開始」・おすすめから使う。苦手を優先は mode=weak・I466） */
export const quizPath = (subjectId: number, mode: QuizStartMode = 'normal'): string =>
  mode === 'weak' ? `/quiz?subject=${subjectId}&mode=weak` : `/quiz?subject=${subjectId}`;
