import { AxiosResponse } from 'axios';
import apiClient from './api';
import {
  Problem,
  Subject,
  CreateProblemRequest,
  QuizSession,
  QuizAnswer,
  QuizResult,
  PaginatedResponse,
} from './types';

class QuizService {
  private readonly PROBLEMS_BASE_URL = '/api/problems';
  private readonly QUIZ_BASE_URL = '/api/quiz';

  // Problem management
  async getProblems(params?: {
    subject?: string;
    difficulty?: string;
    problem_type?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Problem>> {
    const response: AxiosResponse<PaginatedResponse<Problem>> = await apiClient.get(
      `${this.PROBLEMS_BASE_URL}/`,
      { params }
    );
    return response.data;
  }

  async getProblem(id: string): Promise<Problem> {
    const response: AxiosResponse<Problem> = await apiClient.get(`${this.PROBLEMS_BASE_URL}/${id}/`);
    return response.data;
  }

  async createProblem(problemData: CreateProblemRequest): Promise<Problem> {
    const response: AxiosResponse<Problem> = await apiClient.post(`${this.PROBLEMS_BASE_URL}/`, problemData);
    return response.data;
  }

  async updateProblem(id: string, problemData: Partial<CreateProblemRequest>): Promise<Problem> {
    const response: AxiosResponse<Problem> = await apiClient.put(
      `${this.PROBLEMS_BASE_URL}/${id}/`,
      problemData
    );
    return response.data;
  }

  async deleteProblem(id: string): Promise<void> {
    await apiClient.delete(`${this.PROBLEMS_BASE_URL}/${id}/`);
  }

  // Subject management
  async getSubjects(): Promise<Subject[]> {
    // ユーザーが選択した科目を取得
    const response: AxiosResponse<Subject[]> = await apiClient.get('/api/user/subjects/');
    return response.data;
  }

  async createSubject(name: string, description?: string): Promise<Subject> {
    const response: AxiosResponse<Subject> = await apiClient.post(`${this.PROBLEMS_BASE_URL}/subjects/`, {
      name,
      description,
    });
    return response.data;
  }

  async updateSubject(id: string, name: string, description?: string): Promise<Subject> {
    const response: AxiosResponse<Subject> = await apiClient.put(`${this.PROBLEMS_BASE_URL}/subjects/${id}/`, {
      name,
      description,
    });
    return response.data;
  }

  async deleteSubject(id: string): Promise<void> {
    await apiClient.delete(`${this.PROBLEMS_BASE_URL}/subjects/${id}/`);
  }

  // Quiz session management
  async startQuizSession(params?: {
    subject?: string;
    difficulty?: string;
    problem_count?: number;
    problem_types?: string[];
  }): Promise<QuizSession> {
    const response: AxiosResponse<QuizSession> = await apiClient.post(`${this.QUIZ_BASE_URL}/sessions/`, params);
    return response.data;
  }

  async getQuizSession(sessionId: string): Promise<QuizSession> {
    const response: AxiosResponse<QuizSession> = await apiClient.get(`${this.QUIZ_BASE_URL}/sessions/${sessionId}/`);
    return response.data;
  }

  async getCurrentProblem(sessionId: string): Promise<Problem> {
    const response: AxiosResponse<Problem> = await apiClient.get(
      `${this.QUIZ_BASE_URL}/sessions/${sessionId}/current-problem/`
    );
    return response.data;
  }

  async submitAnswer(sessionId: string, answer: QuizAnswer): Promise<{
    is_correct: boolean;
    correct_answer: string | string[];
    explanation?: string;
  }> {
    const response: AxiosResponse<{
      is_correct: boolean;
      correct_answer: string | string[];
      explanation?: string;
    }> = await apiClient.post(`${this.QUIZ_BASE_URL}/sessions/${sessionId}/answer/`, answer);
    return response.data;
  }

  async nextProblem(sessionId: string): Promise<Problem | null> {
    const response: AxiosResponse<Problem | null> = await apiClient.post(
      `${this.QUIZ_BASE_URL}/sessions/${sessionId}/next/`
    );
    return response.data;
  }

  async completeQuizSession(sessionId: string): Promise<QuizResult> {
    const response: AxiosResponse<QuizResult> = await apiClient.post(
      `${this.QUIZ_BASE_URL}/sessions/${sessionId}/complete/`
    );
    return response.data;
  }

  async getQuizResults(sessionId: string): Promise<QuizResult> {
    const response: AxiosResponse<QuizResult> = await apiClient.get(
      `${this.QUIZ_BASE_URL}/sessions/${sessionId}/results/`
    );
    return response.data;
  }

  // Quiz history
  async getQuizHistory(params?: {
    page?: number;
    page_size?: number;
    subject?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<PaginatedResponse<QuizResult>> {
    const response: AxiosResponse<PaginatedResponse<QuizResult>> = await apiClient.get(
      `${this.QUIZ_BASE_URL}/history/`,
      { params }
    );
    return response.data;
  }

  // AI-powered features (placeholder for future implementation)
  async generateProblem(params: {
    subject: string;
    difficulty: string;
    problem_type: string;
    topic?: string;
  }): Promise<Problem> {
    const response: AxiosResponse<Problem> = await apiClient.post(
      `${this.PROBLEMS_BASE_URL}/ai-generate/`,
      params
    );
    return response.data;
  }

  async getPersonalizedProblems(params?: {
    count?: number;
    focus_weak_areas?: boolean;
  }): Promise<Problem[]> {
    const response: AxiosResponse<Problem[]> = await apiClient.get(
      `${this.QUIZ_BASE_URL}/personalized-problems/`,
      { params }
    );
    return response.data;
  }

  // Bulk operations
  async bulkDeleteProblems(problemIds: string[]): Promise<{ deleted_count: number }> {
    const response: AxiosResponse<{ deleted_count: number }> = await apiClient.post(
      `${this.PROBLEMS_BASE_URL}/bulk-delete/`,
      { problem_ids: problemIds }
    );
    return response.data;
  }

  async importProblems(file: File): Promise<{ imported_count: number; errors: string[] }> {
    const formData = new FormData();
    formData.append('file', file);

    const response: AxiosResponse<{ imported_count: number; errors: string[] }> = await apiClient.post(
      `${this.PROBLEMS_BASE_URL}/import/`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  }

  async exportProblems(params?: {
    subject?: string;
    difficulty?: string;
    format?: 'json' | 'csv';
  }): Promise<Blob> {
    const response: AxiosResponse<Blob> = await apiClient.get(
      `${this.PROBLEMS_BASE_URL}/export/`,
      {
        params,
        responseType: 'blob',
      }
    );
    return response.data;
  }
}

export const quizService = new QuizService();
export default quizService;