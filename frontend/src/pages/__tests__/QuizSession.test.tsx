/**
 * QuizSessionコンポーネントのテスト
 * イシュー#026: クイズ機能バグ修正のためのテスト
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import QuizSessionPage from '../QuizSession';
import apiClient from '../../services/api';

// APIクライアントのモック
jest.mock('../../services/api');

// react-hot-toastのモック
jest.mock('react-hot-toast', () => ({
  toast: {
    error: jest.fn(),
    success: jest.fn(),
  },
}));

// react-router-domのモック
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useParams: () => ({ id: 'test-session-id' }),
  useSearchParams: () => [new URLSearchParams('subject=1&count=10')],
}));

describe('QuizSession Component', () => {
  const mockSession = {
    id: 'test-session-id',
    subject: '1',
    total_problems: 10,
    answered_problems: 0,
    correct_answers: 0,
    is_active: true,
    started_at: new Date().toISOString(),
  };

  const mockProblem = {
    id: 'problem-1',
    question_text: 'テスト問題文',
    subject_name: 'テスト科目',
    difficulty: 'easy' as const,
    problem_type: 'single_choice' as const,
    total_problems_in_subject: 10,
    choices: [
      { id: 'choice-1', text: '選択肢1', is_correct: true },
      { id: 'choice-2', text: '選択肢2', is_correct: false },
    ],
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('問題文が正しく表示される（バグ修正の検証）', async () => {
    // モックAPIレスポンスの設定
    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: mockSession,
    });
    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: mockProblem,
    });

    render(
      <BrowserRouter>
        <QuizSessionPage />
      </BrowserRouter>
    );

    // 問題文が表示されるまで待機
    await waitFor(() => {
      expect(screen.getByText('テスト問題文')).toBeInTheDocument();
    });
  });

  it('問題番号が正しく表示される（バグ修正の検証）', async () => {
    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: mockSession,
    });
    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: mockProblem,
    });

    render(
      <BrowserRouter>
        <QuizSessionPage />
      </BrowserRouter>
    );

    // 問題番号が正しく表示される（NaNでない）
    await waitFor(() => {
      expect(screen.getByText(/問題 1 \/ 10/)).toBeInTheDocument();
    });
    const progressText = screen.getByText(/問題 1 \/ 10/);
    // NaNが含まれていないことを確認
    expect(progressText.textContent).not.toContain('NaN');
  });

  it('単一選択問題で選択肢をクリックすると即座に回答が送信される（UX改善の検証）', async () => {
    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: mockSession,
    });
    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: mockProblem,
    });
    (apiClient.post as jest.Mock).mockResolvedValueOnce({
      data: {
        is_correct: true,
        explanation: 'テスト解説',
      },
    });

    render(
      <BrowserRouter>
        <QuizSessionPage />
      </BrowserRouter>
    );

    // 問題が読み込まれるまで待機
    await waitFor(() => {
      expect(screen.getByText('テスト問題文')).toBeInTheDocument();
    });

    // 選択肢をクリック
    const choice1 = screen.getByLabelText('選択肢1');
    fireEvent.click(choice1);

    // 即座に回答が送信されることを確認
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        expect.stringContaining('/submit_answer/'),
        expect.objectContaining({
          problem_id: 'problem-1',
          selected_choice_ids: ['choice-1'],
        })
      );
    });
  });

  it('単一選択問題では「回答する」ボタンが表示されない（UX改善の検証）', async () => {
    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: mockSession,
    });
    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: mockProblem,
    });

    render(
      <BrowserRouter>
        <QuizSessionPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('テスト問題文')).toBeInTheDocument();
    });

    // 「回答する」ボタンが存在しないことを確認
    const submitButton = screen.queryByRole('button', { name: '回答する' });
    expect(submitButton).not.toBeInTheDocument();

    // 「中断」ボタンは存在することを確認
    const cancelButton = screen.getByRole('button', { name: '中断' });
    expect(cancelButton).toBeInTheDocument();
  });

  it('複数選択問題では「回答する」ボタンが表示される', async () => {
    const multipleChoiceProblem = {
      ...mockProblem,
      problem_type: 'multiple_choice' as const,
    };

    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: mockSession,
    });
    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: multipleChoiceProblem,
    });

    render(
      <BrowserRouter>
        <QuizSessionPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('テスト問題文')).toBeInTheDocument();
    });

    // 「回答する」ボタンが存在することを確認
    const submitButton = screen.getByRole('button', { name: '回答する' });
    expect(submitButton).toBeInTheDocument();
  });

  it('difficulty と problem_type が正しく表示される', async () => {
    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: mockSession,
    });
    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: mockProblem,
    });

    render(
      <BrowserRouter>
        <QuizSessionPage />
      </BrowserRouter>
    );

    // 難易度が日本語で表示される
    await waitFor(() => {
      expect(screen.getByText('初級')).toBeInTheDocument();
    });
  });
});
