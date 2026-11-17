/**
 * 苦手を優先のクイズ（I466・TC-25・TC-28・TC-29）
 * ?mode=weak で開始・「苦手を優先」の印・解答が少ないときの案内・「もう一度挑戦」は同じモード
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
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
let mockSearch = 'subject=1&mode=weak';
let mockParams: Record<string, string> = {};
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useParams: () => mockParams,
  useSearchParams: () => [new URLSearchParams(mockSearch)],
}));

const mockGet = apiClient.get as jest.Mock;
const mockPost = apiClient.post as jest.Mock;

const FALLBACK_TEXT = 'この科目はまだ解答が少ないため、いつもの順で出題しています';

const session = (overrides = {}) => ({
  id: 's9',
  subject: 1,
  mode: 'weak',
  total_problems: 3,
  answered_problems: 0,
  correct_answers: 0,
  is_active: true,
  started_at: new Date().toISOString(),
  ...overrides,
});

const problem = (overrides = {}) => ({
  id: 'p1',
  question_text: '苦手の問題 p1',
  subject_name: 'テスト科目',
  difficulty: 'hard',
  problem_type: 'multiple_choice',
  total_problems_in_subject: 3,
  is_review_mode: false,
  is_weak_fallback: false,
  choices: [
    { id: 'a', text: '選択肢A' },
    { id: 'b', text: '選択肢B' },
  ],
  ...overrides,
});

const renderPage = () =>
  render(
    <BrowserRouter>
      <QuizSessionPage />
    </BrowserRouter>
  );

describe('苦手を優先のクイズ', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSearch = 'subject=1&mode=weak';
    mockParams = {};
  });

  it('TC-25: 苦手を優先として開始し、印を出す。判定できないときだけ案内を出す', async () => {
    mockPost.mockResolvedValue({ data: session() });
    mockGet.mockResolvedValueOnce({ data: problem({ is_weak_fallback: true }) });

    const { unmount } = renderPage();

    expect(await screen.findByText('苦手の問題 p1')).toBeInTheDocument();
    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost.mock.calls[0][0]).toBe('/api/quiz/');
    expect(mockPost.mock.calls[0][1]).toEqual({ subject: '1', mode: 'weak' });
    expect(screen.getByText('苦手を優先')).toBeInTheDocument();
    expect(screen.getByText(FALLBACK_TEXT)).toBeInTheDocument();
    expect(screen.queryByText('今日の復習')).not.toBeInTheDocument();
    expect(screen.getByText('上級')).toBeInTheDocument();
    unmount();

    mockGet.mockResolvedValueOnce({ data: problem() });
    renderPage();
    expect(await screen.findByText('苦手の問題 p1')).toBeInTheDocument();
    expect(screen.queryByText(FALLBACK_TEXT)).not.toBeInTheDocument();
  });

  it('TC-28: 終えた苦手を優先の回の「もう一度挑戦」は、同じモードで始める', async () => {
    mockSearch = '';
    mockParams = { id: 's9' };
    mockGet
      .mockResolvedValueOnce({ data: session({ is_active: false, answered_problems: 3 }) })
      .mockResolvedValueOnce({ data: problem() });
    mockPost.mockResolvedValue({ data: session({ id: 's10' }) });

    renderPage();

    userEvent.click(await screen.findByRole('button', { name: 'もう一度挑戦' }));
    expect(await screen.findByText('苦手を優先')).toBeInTheDocument();
    expect(mockPost.mock.calls[0][0]).toBe('/api/quiz/');
    expect(mockPost.mock.calls[0][1]).toEqual({ subject: 1, mode: 'weak' });
  });

  it('TC-28b: 終えた今日の復習の回の「もう一度挑戦」は、いつものクイズで始める（F2）', async () => {
    mockSearch = '';
    mockParams = { id: 's9' };
    mockGet
      .mockResolvedValueOnce({ data: session({ mode: 'review', is_active: false, answered_problems: 3 }) })
      .mockResolvedValueOnce({ data: problem() });
    mockPost.mockResolvedValue({ data: session({ id: 's10', mode: 'normal' }) });

    renderPage();

    userEvent.click(await screen.findByRole('button', { name: 'もう一度挑戦' }));
    expect(await screen.findByText('苦手の問題 p1')).toBeInTheDocument();
    expect(mockPost.mock.calls[0][0]).toBe('/api/quiz/');
    expect(mockPost.mock.calls[0][1]).toEqual({ subject: 1 });
  });

  it('TC-25b: 全科目の苦手を優先で解答が少ないときは「この科目は」と言わない（AC12）', async () => {
    mockSearch = 'mode=weak';
    mockPost.mockResolvedValue({ data: session({ subject: null }) });
    mockGet.mockResolvedValueOnce({ data: problem({ is_weak_fallback: true }) });

    renderPage();

    expect(await screen.findByText('まだ解答が少ないため、いつもの順で出題しています')).toBeInTheDocument();
    expect(screen.queryByText(FALLBACK_TEXT)).not.toBeInTheDocument();
    expect(mockPost.mock.calls[0][1]).toEqual({ mode: 'weak' });
  });

  it('TC-28c: 再挑戦の始め方は回の種類だけで決まり、URL の mode に頼らない（AC12）', async () => {
    mockSearch = 'mode=review';
    mockParams = { id: 's9' };
    mockGet
      .mockResolvedValueOnce({ data: session({ mode: 'normal', is_active: false, answered_problems: 3 }) })
      .mockResolvedValueOnce({ data: problem() });
    mockPost.mockResolvedValue({ data: session({ id: 's10', mode: 'normal' }) });

    renderPage();

    userEvent.click(await screen.findByRole('button', { name: 'もう一度挑戦' }));
    expect(await screen.findByText('苦手の問題 p1')).toBeInTheDocument();
    expect(mockPost.mock.calls[0][1]).toEqual({ subject: 1 });
  });

  it('TC-29: いつものクイズでは印を出さず、モードも送らない', async () => {
    mockSearch = 'subject=1';
    mockPost.mockResolvedValue({ data: session({ mode: 'normal' }) });
    mockGet.mockResolvedValueOnce({ data: problem() });

    renderPage();

    expect(await screen.findByText('苦手の問題 p1')).toBeInTheDocument();
    expect(mockPost.mock.calls[0][1]).toEqual({ subject: '1' });
    expect(screen.queryByText('苦手を優先')).not.toBeInTheDocument();
  });
});
