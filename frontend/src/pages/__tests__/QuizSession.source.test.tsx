/**
 * I609: クイズの画面の出典の表示と、解説が無い問題を解いたときの表示（TC-24〜TC-26）
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import QuizSessionPage from '../QuizSession';
import apiClient from '../../services/api';

jest.mock('../../services/api');

// 画像の取得はしない（フックを差し替え、渡された API の URL を src に出す・I587）
jest.mock('../../hooks/useMediaImage');

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
  useParams: () => ({ id: 'test-session-id' }),
  useSearchParams: () => [new URLSearchParams('')],
}));

const session = {
  id: 'test-session-id',
  subject: '1',
  total_problems: 10,
  answered_problems: 0,
  correct_answers: 0,
  is_active: true,
  started_at: new Date().toISOString(),
};

const problem = {
  id: 'problem-1',
  question_text: 'I609の問題文',
  subject_name: 'テスト科目',
  difficulty: 'easy' as const,
  problem_type: 'single_choice' as const,
  total_problems_in_subject: 10,
  choices: [
    { id: 'choice-1', text: '選択肢1' },
    { id: 'choice-2', text: '選択肢2' },
  ],
};

const questionImage = {
  id: 'q1',
  url: '/api/media/q1/',
  usage_kind: 'problem',
  original_filename: 'q1.png',
  mime_type: 'image/png',
  file_size_bytes: 100,
  created_at: '2026-11-21T00:00:00Z',
};

const precedes = (a: Element, b: Element) =>
  Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);

const renderWith = (current: Record<string, unknown>) => {
  (apiClient.get as jest.Mock).mockResolvedValueOnce({ data: session });
  (apiClient.get as jest.Mock).mockResolvedValueOnce({ data: current });
  render(
    <BrowserRouter>
      <QuizSessionPage />
    </BrowserRouter>
  );
};

describe('QuizSession の出典と解説（I609）', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('TC-24: 答える前から、出典を問題画像の後・選択肢の前に出す', async () => {
    renderWith({ ...problem, source: '出典X', question_images: [questionImage] });

    const source = await screen.findByText('出典：出典X');
    expect(precedes(screen.getByAltText('問題画像 1'), source)).toBe(true);
    expect(precedes(source, screen.getByLabelText('選択肢1'))).toBe(true);
  });

  it('TC-25: 出典が空なら何も出さない', async () => {
    renderWith({ ...problem, source: '' });

    await screen.findByText('I609の問題文');
    expect(screen.queryByText(/出典：/)).not.toBeInTheDocument();
  });

  it('TC-26: 解説が空の問題に答えると、正誤と正解の印は出て「解説:」は出ない', async () => {
    renderWith({ ...problem, source: '' });
    (apiClient.post as jest.Mock).mockResolvedValueOnce({
      data: {
        is_correct: true,
        explanation: '',
        explanation_images: [],
        correct_choices: [{ id: 'choice-1', text: '選択肢1' }],
        session_complete: false,
      },
    });

    await screen.findByText('I609の問題文');
    fireEvent.click(screen.getByLabelText('選択肢1'));

    await waitFor(() => {
      expect(screen.getByText('正解です！')).toBeInTheDocument();
    });
    expect(screen.getByTestId('CheckCircleOutlineIcon')).toBeInTheDocument();
    expect(screen.queryByText('解説:')).not.toBeInTheDocument();
  });
});
