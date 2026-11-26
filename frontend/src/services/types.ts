// API Response Types
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  status: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// User Types
export interface User {
  id: string;
  email: string;
  user_id: string;
  first_name: string;
  last_name: string;
  role: 'user' | 'admin';
  is_verified: boolean;
  is_staff?: boolean;
  is_superuser?: boolean;
  created_at: string;
  last_login: string;
  organization_name?: string;
  organization_is_individual?: boolean;  // 本人ひとりの組織（メンバー管理を出さない・I620）
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface RegisterRequest {
  email: string;
  user_id: string;
  password: string;
  password_confirm: string;
  first_name?: string;
  last_name?: string;
  subject_ids?: number[];
}

export interface TokenRefreshRequest {
  refresh: string;
}

export interface TokenRefreshResponse {
  access: string;
}

// Problem Types
export interface Choice {
  id?: string;
  text: string;
  is_correct: boolean;
}

// MediaAsset型（画像アセット）- イシュー#033対応
export interface MediaAsset {
  id: string;
  url: string;
  usage_kind: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  created_at: string;
}

/**
 * 編集ダイアログの画像アイテム（イシュー#073）
 * 既存画像（サーバ保存済み）と新規画像（未送信File）を1リストで扱う。
 */
export type EditableImage =
  | { kind: 'existing'; assetId: string; url: string; filename: string }
  | { kind: 'new'; file: File };

export interface Problem {
  id: string;
  question_text: string;
  subject: string;
  subject_name?: string;
  difficulty: 'easy' | 'medium' | 'hard';
  problem_type: 'single_choice' | 'multiple_choice' | 'text';
  choices: Choice[];
  explanation?: string;
  /** 出典（無ければ空の文字・I609） */
  source?: string;
  created_at: string;
  updated_at: string;
  // 画像（MediaAsset の配列。古い形の question_image・explanation_image は I587 で外した）
  question_images?: MediaAsset[];
  explanation_images?: MediaAsset[];
}

export interface Subject {
  id: number;
  name: string;
  description?: string;
  problem_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface CreateProblemRequest {
  question_text: string;
  subject: string;
  difficulty: 'easy' | 'medium' | 'hard';
  problem_type: 'single_choice' | 'multiple_choice' | 'text';
  choices: Omit<Choice, 'id'>[];
  explanation?: string;
  source?: string;
}

// Quiz Types
export interface QuizSession {
  id: string;
  problems: Problem[];
  current_problem_index: number;
  total_problems: number;
  start_time: string;
  end_time?: string;
  is_completed: boolean;
  subject?: string;
  difficulty?: string;
}

export interface QuizAnswer {
  problem_id: string;
  selected_choices?: string[];
  text_answer?: string;
  time_taken: number;
}

export interface QuizResult {
  session_id: string;
  total_problems: number;
  correct_answers: number;
  accuracy_percentage: number;
  time_taken: number;
  results: Array<{
    problem: Problem;
    user_answer: QuizAnswer;
    is_correct: boolean;
  }>;
}

// 設定の型は API のスキーマから作ったもの（types/api の UserSettings）を使う（I487）
// 学習統計の型も API のスキーマから作ったもの（types/api の DashboardAnalytics）を使う（I488）
