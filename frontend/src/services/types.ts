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

// Study Types
export interface StudySession {
  id: string;
  start_time: string;
  end_time: string | null;
  total_duration: number;
  problems_attempted: number;
  problems_correct: number;
  subject: string;
}

export interface StudyStats {
  today_study_time: number;
  week_study_time: number;
  total_problems_solved: number;
  accuracy_rate: number;
  current_streak: number;
  longest_streak: number;
}

export interface DashboardData {
  stats: StudyStats;
  recent_sessions: StudySession[];
  weekly_progress: Array<{
    date: string;
    study_time: number;
    problems_solved: number;
    accuracy: number;
  }>;
  subject_progress: Array<{
    subject_name: string;
    problems_solved: number;
    accuracy: number;
    time_spent: number;
  }>;
  recommendations: Array<{
    type: 'weak_subject' | 'unstudied_subject' | 'streak_reminder';
    title: string;
    description: string;
    action_url?: string;
  }>;
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

export interface Problem {
  id: string;
  question_text: string;
  subject: string;
  subject_name?: string;
  difficulty: 'easy' | 'medium' | 'hard';
  problem_type: 'single_choice' | 'multiple_choice' | 'text';
  choices: Choice[];
  explanation?: string;
  created_at: string;
  updated_at: string;
  // 画像フィールド - イシュー#033対応
  question_image?: string;
  explanation_image?: string;
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

// Settings Types
export interface UserSettings {
  id: string;
  theme: 'light' | 'dark';
  daily_study_goal: number;
  study_reminder_enabled: boolean;
  study_reminder_time: string;
  email_notifications: boolean;
  push_notifications: boolean;
  difficulty_preference: 'easy' | 'medium' | 'hard' | 'mixed';
}

// Analytics Types
export interface AnalyticsFilters {
  period: 'daily' | 'weekly' | 'monthly';
  start_date?: string;
  end_date?: string;
  subject?: string;
}

export interface AnalyticsData {
  study_time_trend: Array<{
    date: string;
    study_time: number;
  }>;
  accuracy_trend: Array<{
    date: string;
    accuracy: number;
  }>;
  subject_breakdown: Array<{
    subject_name: string;
    problems_solved: number;
    time_spent: number;
    accuracy: number;
  }>;
  mistake_patterns: Array<{
    subject_name: string;
    problem_type: string;
    difficulty: string;
    mistake_count: number;
    improvement_suggestion: string;
  }>;
}