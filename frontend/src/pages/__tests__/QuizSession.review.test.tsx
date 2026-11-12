/**
 * 今日の復習のクイズ（I452・TC-17）
 * ?mode=review で開始・最後の問題の後の「結果を見る」・終わりの表示・復習中の印
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
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
let mockSearch = 'mode=review&subject=1';
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useParams: () => ({}),
  useSearchParams: () => [new URLSearchParams(mockSearch)],
}));

const mockGet = apiClient.get as jest.Mock;
const mockPost = apiClient.post as jest.Mock;

const session = (overrides = {}) => ({
  id: 's1',
  subject: '1',
  mode: 'review',
  total_problems: 2,
  answered_problems: 0,
  correct_answers: 0,
  is_active: true,
  started_at: new Date().toISOString(),
  ...overrides,
});

const problem = (id: string) => ({
  id,
  question_text: `復習の問題 ${id}`,
  subject_name: 'テスト科目',
  difficulty: 'easy',
  problem_type: 'multiple_choice',
  total_problems_in_subject: 2,
  is_review_mode: false,
  choices: [
    { id: `${id}-a`, text: '選択肢A' },
    { id: `${id}-b`, text: '選択肢B' },
  ],
});

const complete = (completed: number, correct: number) => ({
  review_complete: true,
  total_problems: 2,
  completed_problems: completed,
  correct_answers: correct,
});

const answerResult = (answered: number) => ({
  is_correct: true,
  explanation: '解説',
  correct_choices: [],
  session: session({ answered_problems: answered, correct_answers: answered }),
});

const renderPage = () =>
  render(
    <BrowserRouter>
      <QuizSessionPage />
    </BrowserRouter>
  );

const answerCurrent = async () => {
  userEvent.click(screen.getByLabelText('選択肢A'));
  userEvent.click(screen.getByRole('button', { name: '回答する' }));
};

describe('今日の復習のクイズ', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSearch = 'mode=review&subject=1';
  });

  it('復習として開始し、印を出し、最後の問題の後は「結果を見る」から終わりの表示へ', async () => {
    mockPost.mockImplementation((url: string) => {
      if (url === '/api/quiz/') return Promise.resolve({ data: session() });
      if (url.endsWith('/end/')) return Promise.resolve({ data: {} });
      const answered = mockPost.mock.calls.filter(([u]) => u.endsWith('/submit_answer/')).length;
      return Promise.resolve({ data: answerResult(answered) });
    });
    mockGet
      .mockResolvedValueOnce({ data: problem('p1') })
      .mockResolvedValueOnce({ data: problem('p2') })
      .mockResolvedValueOnce({ data: complete(2, 1) });

    renderPage();

    expect(await screen.findByText('復習の問題 p1')).toBeInTheDocument();
    expect(mockPost.mock.calls[0][0]).toBe('/api/quiz/');
    expect(mockPost.mock.calls[0][1]).toEqual({ subject: '1', mode: 'review' });
    expect(screen.getByText('今日の復習')).toBeInTheDocument();

    await answerCurrent();
    userEvent.click(await screen.findByRole('button', { name: '次の問題' }));
    expect(await screen.findByText('復習の問題 p2')).toBeInTheDocument();

    await answerCurrent();
    expect(await screen.findByRole('button', { name: '結果を見る' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '次の問題' })).not.toBeInTheDocument();
    userEvent.click(screen.getByRole('button', { name: '結果を見る' }));

    expect(await screen.findByText('今日の復習が終わりました（2問中1問正解）')).toBeInTheDocument();
    expect(mockPost).toHaveBeenCalledWith('/api/quiz/s1/end/');
    expect(screen.queryByRole('button', { name: 'もう一度挑戦' })).not.toBeInTheDocument();
    userEvent.click(screen.getByRole('button', { name: 'ダッシュボードへ戻る' }));
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
  });

  it('開いた時点で対象が無ければ「今日の復習はありません」', async () => {
    mockPost.mockResolvedValue({ data: session({ total_problems: 0 }) });
    mockGet.mockResolvedValueOnce({ data: { ...complete(0, 0), total_problems: 0 } });

    renderPage();

    expect(await screen.findByText('今日の復習はありません')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'ダッシュボードへ戻る' })).toBeInTheDocument();
  });

  it('回を終える要求が失敗しても終わりの表示を出す', async () => {
    mockPost.mockImplementation((url: string) => (
      url.endsWith('/end/')
        ? Promise.reject(new Error('network'))
        : Promise.resolve({ data: session() })
    ));
    mockGet.mockResolvedValueOnce({ data: complete(2, 2) });

    renderPage();

    expect(await screen.findByText('今日の復習が終わりました（2問中2問正解）')).toBeInTheDocument();
    await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/api/quiz/s1/end/'));
  });

  it('いつものクイズでは印を出さず、復習の値も送らない', async () => {
    mockSearch = 'subject=1';
    mockPost.mockResolvedValue({ data: session({ mode: 'normal' }) });
    mockGet.mockResolvedValueOnce({ data: problem('p1') });

    renderPage();

    expect(await screen.findByText('復習の問題 p1')).toBeInTheDocument();
    expect(mockPost.mock.calls[0][1]).toEqual({ subject: '1' });
    expect(screen.queryByText('今日の復習')).not.toBeInTheDocument();
  });
});
