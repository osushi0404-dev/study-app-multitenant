import { AxiosResponse } from 'axios';
import apiClient from './api';
import {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  User,
  TokenRefreshRequest,
  TokenRefreshResponse,
} from './types';

class AuthService {
  private readonly AUTH_BASE_URL = '/api/auth';

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response: AxiosResponse<LoginResponse> = await apiClient.post(
      `${this.AUTH_BASE_URL}/login/`,
      credentials
    );
    return response.data;
  }

  async register(userData: RegisterRequest, organizationSlug?: string): Promise<{ message: string }> {
    const endpoint = organizationSlug 
      ? `${this.AUTH_BASE_URL}/register/${organizationSlug}/`
      : `${this.AUTH_BASE_URL}/register/`;
    
    const response: AxiosResponse<{ message: string }> = await apiClient.post(
      endpoint,
      userData
    );
    return response.data;
  }

  async logout(): Promise<void> {
    const refreshToken = localStorage.getItem('refreshToken');
    if (refreshToken) {
      try {
        await apiClient.post(`${this.AUTH_BASE_URL}/logout/`, {
          refresh: refreshToken,
        });
      } catch (error) {
        console.error('Logout API call failed:', error);
        // Continue with local logout even if API call fails
      }
    }

    // Clear local storage
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    apiClient.removeAuthToken();
  }

  async refreshToken(refreshToken: string): Promise<TokenRefreshResponse> {
    const response: AxiosResponse<TokenRefreshResponse> = await apiClient.post(
      `${this.AUTH_BASE_URL}/token/refresh/`,
      { refresh: refreshToken }
    );
    return response.data;
  }

  async verifyEmail(token: string): Promise<{ message: string }> {
    const response: AxiosResponse<{ message: string }> = await apiClient.post(
      `${this.AUTH_BASE_URL}/verify-email/`,
      { token }
    );
    return response.data;
  }

  async resendEmailVerification(email: string): Promise<{ message: string }> {
    const response: AxiosResponse<{ message: string }> = await apiClient.post(
      `${this.AUTH_BASE_URL}/resend-verification/`,
      { email }
    );
    return response.data;
  }

  async requestPasswordReset(email: string): Promise<{ message: string }> {
    const response: AxiosResponse<{ message: string }> = await apiClient.post(
      `${this.AUTH_BASE_URL}/password-reset/`,
      { email }
    );
    return response.data;
  }

  async confirmPasswordReset(
    token: string,
    newPassword: string
  ): Promise<{ message: string }> {
    const response: AxiosResponse<{ message: string }> = await apiClient.post(
      `${this.AUTH_BASE_URL}/password-reset/confirm/`,
      { token, new_password: newPassword }
    );
    return response.data;
  }

  async changePassword(
    currentPassword: string,
    newPassword: string
  ): Promise<{ message: string }> {
    const response: AxiosResponse<{ message: string }> = await apiClient.post(
      `${this.AUTH_BASE_URL}/change-password/`,
      {
        current_password: currentPassword,
        new_password: newPassword,
      }
    );
    return response.data;
  }

  async getCurrentUser(): Promise<User> {
    const response: AxiosResponse<User> = await apiClient.get('/api/auth/me/');
    return response.data;
  }

  async updateProfile(userData: Partial<User>): Promise<User> {
    const response: AxiosResponse<User> = await apiClient.patch('/api/auth/me/', userData);
    return response.data;
  }

  // Helper methods
  isAuthenticated(): boolean {
    const token = localStorage.getItem('accessToken');
    const refreshToken = localStorage.getItem('refreshToken');
    return !!(token && refreshToken);
  }

  getStoredUser(): User | null {
    const userString = localStorage.getItem('user');
    if (userString) {
      try {
        return JSON.parse(userString);
      } catch (error) {
        console.error('Error parsing stored user:', error);
        return null;
      }
    }
    return null;
  }

  getAccessToken(): string | null {
    return localStorage.getItem('accessToken');
  }

  getRefreshToken(): string | null {
    return localStorage.getItem('refreshToken');
  }
}

export const authService = new AuthService();
export default authService;