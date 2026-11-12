import { AxiosResponse } from 'axios';
import apiClient from './api';
import { DashboardData, AnalyticsData, AnalyticsFilters, UserSettings } from './types';

class DashboardService {
  private readonly DASHBOARD_BASE_URL = '/api/dashboard';
  private readonly ACCOUNTS_BASE_URL = '/api/accounts';

  async getDashboardData(params?: { subject_id?: string }): Promise<DashboardData> {
    const response: AxiosResponse<DashboardData> = await apiClient.get(
      `${this.DASHBOARD_BASE_URL}/overview/`,
      { params }
    );
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
}

export const dashboardService = new DashboardService();
export default dashboardService;
