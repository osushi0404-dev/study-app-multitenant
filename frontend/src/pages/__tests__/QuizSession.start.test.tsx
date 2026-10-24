/**
 * QuizSession の開始経路（id なし）のテスト
 * I158: StrictMode でも開始リクエストは 1 回だけ・Idempotency-Key 付きで送る
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import QuizSessionPage from '../QuizSession';
import apiClient from '../../services/api';

jest.mock('../../services/api');

jest.mock('react-hot-toast', () => ({
  toast: {
    error: jest.fn(),
    success: jest.fn(),
  },
}));

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useParams: () => ({}),
  useSearchParams: () => [new URLSearchParams('subject=1')],
}));

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

const renderInStrictMode = () =>
  render(
    <React.StrictMode>
      <BrowserRouter>
        <QuizSessionPage />
      </BrowserRouter>
    </React.StrictMode>
  );

const startCalls = () =>
  (apiClient.post as jest.Mock).mock.calls.filter(([url]) => url === '/api/quiz/');

describe('QuizSession 開始経路', () => {
  const mockSession = {
    id: 's1',
    subject: '1',
    total_problems: 2,
    answered_problems: 0,
    correct_answers: 0,
    is_active: true,
    started_at: new Date().toISOString(),
  };

  const mockProblem = {
    id: 'problem-1',
    question_text: '開始テスト問題文',
    subject_name: 'テスト科目',
    difficulty: 'easy' as const,
    problem_type: 'single_choice' as const,
    total_problems_in_subject: 2,
    choices: [
      { id: 'choice-1', text: '選択肢1' },
      { id: 'choice-2', text: '選択肢2' },
    ],
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('StrictMode でも開始 POST は 1 回だけで Idempotency-Key が付く（TC-30）', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({ data: mockSession });
    (apiClient.get as jest.Mock).mockResolvedValue({ data: mockProblem });

    renderInStrictMode();

    await waitFor(() => {
      expect(screen.getByText('開始テスト問題文')).toBeInTheDocument();
    });
    expect(startCalls()).toHaveLength(1);
    expect(startCalls()[0]).toEqual([
      '/api/quiz/',
      { subject: '1' },
      { headers: { 'Idempotency-Key': expect.stringMatching(UUID_V4) } },
    ]);
  });

  it('開始に失敗したらトーストを出してダッシュボードへ戻る（TC-31）', async () => {
    (apiClient.post as jest.Mock).mockRejectedValue({ response: { status: 409 } });

    renderInStrictMode();

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
    expect(toast.error).toHaveBeenCalledWith('クイズセッションの作成に失敗しました');
    expect(startCalls()).toHaveLength(1);
  });
});
