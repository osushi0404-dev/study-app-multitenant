import { AxiosResponse } from 'axios';
import apiClient from './api';
import { DashboardData, StudyStats, StudySession, AnalyticsData, AnalyticsFilters, UserSettings } from './types';

class DashboardService {
  private readonly DASHBOARD_BASE_URL = '/api/dashboard';
  private readonly STUDYLOGS_BASE_URL = '/api/studylogs';
  private readonly ACCOUNTS_BASE_URL = '/api/accounts';

  async getDashboardData(params?: { subject_id?: string }): Promise<DashboardData> {
    const response: AxiosResponse<DashboardData> = await apiClient.get(
      `${this.DASHBOARD_BASE_URL}/overview/`,
      { params }
    );
    return response.data;
  }

  async getStudyStats(): Promise<StudyStats> {
    const response: AxiosResponse<StudyStats> = await apiClient.get(`${this.STUDYLOGS_BASE_URL}/stats/`);
    return response.data;
  }

  async getRecentSessions(limit: number = 10): Promise<StudySession[]> {
    const response: AxiosResponse<StudySession[]> = await apiClient.get(
      `${this.STUDYLOGS_BASE_URL}/sessions/`,
      { params: { limit } }
    );
    return response.data;
  }

  async getWeeklyProgress(): Promise<Array<{
    date: string;
    study_time: number;
    problems_solved: number;
    accuracy: number;
  }>> {
    const response: AxiosResponse<Array<{
      date: string;
      study_time: number;
      problems_solved: number;
      accuracy: number;
    }>> = await apiClient.get(`${this.DASHBOARD_BASE_URL}/weekly-progress/`);
    return response.data;
  }

  async getSubjectProgress(): Promise<Array<{
    subject_name: string;
    problems_solved: number;
    accuracy: number;
    time_spent: number;
  }>> {
    const response: AxiosResponse<Array<{
      subject_name: string;
      problems_solved: number;
      accuracy: number;
      time_spent: number;
    }>> = await apiClient.get(`${this.DASHBOARD_BASE_URL}/subject-progress/`);
    return response.data;
  }

  async getRecommendations(): Promise<Array<{
    type: 'weak_subject' | 'unstudied_subject' | 'streak_reminder';
    title: string;
    description: string;
    action_url?: string;
  }>> {
    const response: AxiosResponse<Array<{
      type: 'weak_subject' | 'unstudied_subject' | 'streak_reminder';
      title: string;
      description: string;
      action_url?: string;
    }>> = await apiClient.get(`${this.DASHBOARD_BASE_URL}/recommendations/`);
    return response.data;
  }

  async getAnalytics(filters: AnalyticsFilters): Promise<AnalyticsData> {
    const response: AxiosResponse<AnalyticsData> = await apiClient.get(
      `${this.DASHBOARD_BASE_URL}/analytics/`,
      { params: filters }
    );
    return response.data;
  }

  async getUserSettings(): Promise<UserSettings> {
    const response: AxiosResponse<UserSettings> = await apiClient.get(`/api/settings/`);
    return response.data;
  }

  async updateUserSettings(settings: Partial<UserSettings>): Promise<UserSettings> {
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

  // Study session management
  async startStudySession(subject?: string): Promise<StudySession> {
    const response: AxiosResponse<StudySession> = await apiClient.post(`${this.STUDYLOGS_BASE_URL}/sessions/`, {
      subject,
    });
    return response.data;
  }

  async endStudySession(sessionId: string): Promise<StudySession> {
    const response: AxiosResponse<StudySession> = await apiClient.patch(
      `${this.STUDYLOGS_BASE_URL}/sessions/${sessionId}/`,
      { action: 'end' }
    );
    return response.data;
  }

  async recordProblemAttempt(sessionId: string, problemId: string, isCorrect: boolean, timeTaken: number): Promise<void> {
    await apiClient.post(`${this.STUDYLOGS_BASE_URL}/problem-attempts/`, {
      session: sessionId,
      problem: problemId,
      is_correct: isCorrect,
      time_taken: timeTaken,
    });
  }
}

export const dashboardService = new DashboardService();
export default dashboardService;