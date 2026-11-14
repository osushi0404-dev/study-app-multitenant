import { AxiosResponse } from 'axios';
import apiClient from './api';
import {
  DashboardAnalytics,
  DashboardAnalyticsGranularity,
  DashboardOverview,
  DashboardRecommendationKind,
  PatchedUserSettings,
  UserSettings,
} from '../types/api';

// おすすめの種類。API の選択肢が増えても消えても、ここが合わなければ型の検査で落ちる
const RECOMMENDATION_KINDS: Record<DashboardRecommendationKind, true> = {
  weak_subject: true,
  unstudied_subject: true,
};

const isRecommendationKind = (value: unknown): value is DashboardRecommendationKind =>
  typeof value === 'string' && Object.prototype.hasOwnProperty.call(RECOMMENDATION_KINDS, value);

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const isNumber = (value: unknown): value is number => typeof value === 'number';

const isListOf = (value: unknown, isItem: (item: Record<string, unknown>) => boolean): boolean =>
  Array.isArray(value) && value.every((item) => isRecord(item) && isItem(item));

const hasCounts = (value: unknown): value is Record<string, unknown> =>
  isRecord(value) &&
  isNumber(value.answered_count) &&
  isNumber(value.correct_count) &&
  (value.accuracy_rate === null || isNumber(value.accuracy_rate));

/**
 * ダッシュボードの応答が契約（DashboardOverview）の形かを、一覧の中身まで確かめる（I473）
 * 欠けたキーを 0 で埋めず、形が違えばエラーとして扱うため
 * （形の正は backend/openapi.yaml〔OverviewSerializer から作る〕。型は実行時に消えるので、受けるところで形を確かめる・I493）
 */
const isDashboardOverview = (data: unknown): data is DashboardOverview =>
  isRecord(data) &&
  typeof data.has_data === 'boolean' &&
  hasCounts(data.today) &&
  isNumber(data.today.study_seconds) &&
  isRecord(data.streak) &&
  isNumber(data.streak.current_days) &&
  hasCounts(data.totals) &&
  Array.isArray(data.last_7_days) &&
  data.last_7_days.length > 0 &&
  isListOf(data.last_7_days, (day) =>
    typeof day.date === 'string' &&
    isNumber(day.study_seconds) &&
    isNumber(day.answered_count) &&
    isNumber(day.correct_count)
  ) &&
  isListOf(data.weak_subjects, (subject) =>
    isNumber(subject.subject_id) &&
    typeof subject.subject_name === 'string' &&
    isNumber(subject.answered_count) &&
    isNumber(subject.accuracy_rate)
  ) &&
  isListOf(data.recommendations, (rec) =>
    isRecommendationKind(rec.kind) &&
    isNumber(rec.subject_id) &&
    typeof rec.subject_name === 'string' &&
    typeof rec.reason === 'string'
  );

// 推移の区切り。API の選択肢が増えても消えても、ここが合わなければ型の検査で落ちる（I488）
const GRANULARITIES: Record<DashboardAnalyticsGranularity, true> = {
  day: true,
  week: true,
  month: true,
};

const isGranularity = (value: unknown): value is DashboardAnalyticsGranularity =>
  typeof value === 'string' && Object.prototype.hasOwnProperty.call(GRANULARITIES, value);

const hasAnalyticsCounts = (value: unknown): value is Record<string, unknown> =>
  hasCounts(value) && isNumber(value.study_seconds);

/**
 * 学習統計の応答が契約（DashboardAnalytics）の形かを、一覧の中身まで確かめる（I488）
 * 欠けたキーを空の配列や 0 で埋めず、形が違えばエラーとして扱うため（I473 と同じ考え方）
 */
const isDashboardAnalytics = (data: unknown): data is DashboardAnalytics =>
  isRecord(data) &&
  typeof data.has_data === 'boolean' &&
  isRecord(data.period) &&
  isNumber(data.period.days) &&
  typeof data.period.start_date === 'string' &&
  typeof data.period.end_date === 'string' &&
  isGranularity(data.period.granularity) &&
  hasAnalyticsCounts(data.totals) &&
  isNumber(data.totals.studied_days) &&
  isListOf(data.trend, (bucket) =>
    typeof bucket.start_date === 'string' &&
    typeof bucket.end_date === 'string' &&
    hasAnalyticsCounts(bucket)
  ) &&
  (data.trend as unknown[]).length > 0 &&
  isListOf(data.subject_breakdown, (subject) =>
    isNumber(subject.subject_id) &&
    typeof subject.subject_name === 'string' &&
    hasAnalyticsCounts(subject)
  );

class DashboardService {
  private readonly DASHBOARD_BASE_URL = '/api/dashboard';
  private readonly ACCOUNTS_BASE_URL = '/api/accounts';

  async getOverview(params: { subject_id?: string } = {}): Promise<DashboardOverview> {
    const response: AxiosResponse<unknown> = await apiClient.get(
      `${this.DASHBOARD_BASE_URL}/overview/`,
      { params }
    );
    if (!isDashboardOverview(response.data)) {
      throw new Error('ダッシュボードの応答の形が違います');
    }
    return response.data;
  }

  async getAnalytics(params: { days: number; subject_id?: string }): Promise<DashboardAnalytics> {
    const response: AxiosResponse<unknown> = await apiClient.get(
      `${this.DASHBOARD_BASE_URL}/analytics/`,
      { params }
    );
    if (!isDashboardAnalytics(response.data)) {
      throw new Error('学習統計の応答の形が違います');
    }
    return response.data;
  }

  async getUserSettings(): Promise<UserSettings> {
    const response: AxiosResponse<UserSettings> = await apiClient.get(`/api/settings/`);
    return response.data;
  }

  async updateUserSettings(settings: PatchedUserSettings): Promise<UserSettings> {
    const response: AxiosResponse<UserSettings> = await apiClient.patch(
      `/api/settings/`,
      settings
    );
    return response.data;
  }

  async getStudyStreak(): Promise<{
    current_streak: number;
    longest_streak: number;
    last_study_date: string | null;
  }> {
    const response: AxiosResponse<{
      current_streak: number;
      longest_streak: number;
      last_study_date: string | null;
    }> = await apiClient.get(`/api/streak/`);
    return response.data;
  }
}

export const dashboardService = new DashboardService();
export default dashboardService;
