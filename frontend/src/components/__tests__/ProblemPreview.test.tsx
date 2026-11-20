/**
 * ProblemPreview の画像の見え方の守り（I472 TC-10）
 * 画像の選び方・並べ方をクイズの画面と共有するために切り出しても、プレビューの見え方を変えない
 */
import { render, screen, fireEvent, within } from '@testing-library/react';
import ProblemPreview from '../ProblemPreview';
import { MediaAsset, Problem } from '../../services/types';

// 画像の取得はしない（フックを差し替え、渡された API の URL を src に出す・I587）
jest.mock('../../hooks/useMediaImage');

const asset = (id: string, url: string, usageKind: string): MediaAsset => ({
  id,
  url,
  usage_kind: usageKind,
  original_filename: `${id}.png`,
  mime_type: 'image/png',
  file_size_bytes: 100,
  created_at: '2026-11-12T00:00:00Z',
});

const baseProblem: Problem = {
  id: 'p1',
  question_text: 'プレビューの問題文',
  subject: '1',
  subject_name: '科目',
  difficulty: 'easy',
  problem_type: 'single_choice',
  choices: [
    { id: 'c1', text: '正解', is_correct: true },
    { id: 'c2', text: '不正解', is_correct: false },
  ],
  explanation: 'プレビューの解説',
  created_at: '2026-11-12T00:00:00Z',
  updated_at: '2026-11-12T00:00:00Z',
};

describe('ProblemPreview の画像（I472）', () => {
  it('解説画像を表示順に出す', () => {
    render(
      <ProblemPreview
        problem={{
          ...baseProblem,
          explanation_images: [
            asset('e1', '/api/media/e1/', 'explanation'),
            asset('e2', '/api/media/e2/', 'explanation'),
          ],
        }}
      />
    );

    expect(screen.getByAltText('解説画像 1')).toHaveAttribute('src', '/api/media/e1/');
    expect(screen.getByAltText('解説画像 2')).toHaveAttribute('src', '/api/media/e2/');
    expect(screen.queryByAltText('解説画像 3')).not.toBeInTheDocument();
  });

  it('画像が無ければ画像を出さない', () => {
    render(<ProblemPreview problem={baseProblem} />);

    expect(screen.queryByAltText(/^(解説|問題)画像/)).not.toBeInTheDocument();
  });

  it('解説文が空なら解説画像を出さない', () => {
    render(
      <ProblemPreview
        problem={{
          ...baseProblem,
          explanation: '',
          explanation_images: [asset('e1', '/api/media/e1/', 'explanation')],
        }}
      />
    );

    expect(screen.queryByAltText(/^解説画像/)).not.toBeInTheDocument();
  });

  it('問題画像を押すと拡大の画面が開く', () => {
    render(
      <ProblemPreview
        problem={{ ...baseProblem, question_images: [asset('q1', '/api/media/q1/', 'problem')] }}
      />
    );

    fireEvent.click(screen.getByAltText('問題画像 1'));

    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByRole('img')).toHaveAttribute('src', '/api/media/q1/');
  });
});
