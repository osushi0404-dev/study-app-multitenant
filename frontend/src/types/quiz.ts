// frontend/src/types/quiz.ts

/**
 * クイズセッション
 */
export interface QuizSession {
  id: string;
  subject?: string;
  subject_name?: string;
  total_problems: number;
  answered_problems: number;  // completed_problemsのエイリアス
  correct_answers: number;
  is_active: boolean;
  started_at: string;
  ended_at?: string;
  duration?: number;
  accuracy?: number;
}

/**
 * 問題の選択肢
 */
export interface Choice {
  id: string;
  text: string;
  is_correct?: boolean;  // 回答後のみ含まれる
  order?: number;
}

/**
 * 問題（表示用）
 */
export interface Problem {
  id: string;
  question_text: string;
  question_image?: string;
  subject_name?: string;
  difficulty: 'easy' | 'medium' | 'hard';
  problem_type: 'single_choice' | 'multiple_choice' | 'text';
  choices: Choice[];
  explanation?: string;
  explanation_image?: string;
  // 修正で追加されるフィールド
  total_problems_in_subject?: number;
  is_review_mode?: boolean;
}

/**
 * クイズ回答結果
 */
export interface QuizResult {
  is_correct: boolean;
  explanation?: string;
  explanation_image?: string;
  correct_choices?: Choice[];
  session_complete: boolean;
  session?: QuizSession;  // 修正で追加
  session_stats?: {
    completed: number;
    total: number;
    correct: number;
  };
}

/**
 * 回答送信データ
 */
export interface SubmitAnswerData {
  problem_id: string;
  selected_choice_ids?: string[];
  text_answer?: string;
  time_taken: number;
}

/**
 * クイズ進捗情報（カスタムフック用）
 */
export interface QuizProgress {
  currentRound: number;
  problemInRound: number;
  progressPercentage: number;
  isMultiRound: boolean;
}

/**
 * 問題作成用の選択肢（フォームデータ用）
 */
export interface CreateChoiceData {
  text: string;
  is_correct: boolean;
  order: number;
}

/**
 * 問題作成リクエストの型定義（DTO）
 */
export interface CreateProblemRequest {
  question_text: string;
  subject: string;
  difficulty: 'easy' | 'medium' | 'hard';
  problem_type: 'single_choice' | 'multiple_choice' | 'text';
  explanation: string;
  choices: CreateChoiceData[];
}
