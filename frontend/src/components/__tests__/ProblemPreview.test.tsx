/**
 * ProblemPreview の画像の見え方の守り（I472 TC-10）
 * 画像の選び方・並べ方をクイズの画面と共有するために切り出しても、プレビューの見え方を変えない
 */
import { render, screen, fireEvent, within } from '@testing-library/react';
import ProblemPreview from '../ProblemPreview';
import { MediaAsset, Problem } from '../../services/types';
import { getMediaUrl } from '../../utils/url';

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
  it('新しい形式の解説画像があれば新しい形式だけを出す', () => {
    render(
      <ProblemPreview
        problem={{
          ...baseProblem,
          explanation_image: '/media/legacy.png',
          explanation_images: [
            asset('e1', '/media/e1.png', 'explanation'),
            asset('e2', '/media/e2.png', 'explanation'),
          ],
        }}
      />
    );

    expect(screen.getByAltText('解説画像 1')).toHaveAttribute('src', getMediaUrl('/media/e1.png'));
    expect(screen.getByAltText('解説画像 2')).toHaveAttribute('src', getMediaUrl('/media/e2.png'));
    expect(screen.queryByAltText('解説画像 3')).not.toBeInTheDocument();
  });

  it('新しい形式が無ければ古い形式の解説画像を 1 枚出す', () => {
    render(<ProblemPreview problem={{ ...baseProblem, explanation_image: '/media/legacy.png' }} />);

    expect(screen.getByAltText('解説画像 1')).toHaveAttribute('src', getMediaUrl('/media/legacy.png'));
    expect(screen.queryByAltText('解説画像 2')).not.toBeInTheDocument();
  });

  it('解説文が空なら解説画像を出さない', () => {
    render(
      <ProblemPreview
        problem={{
          ...baseProblem,
          explanation: '',
          explanation_images: [asset('e1', '/media/e1.png', 'explanation')],
        }}
      />
    );

    expect(screen.queryByAltText(/^解説画像/)).not.toBeInTheDocument();
  });

  it('問題画像を押すと拡大の画面が開く', () => {
    render(
      <ProblemPreview
        problem={{ ...baseProblem, question_images: [asset('q1', '/media/q1.png', 'problem')] }}
      />
    );

    fireEvent.click(screen.getByAltText('問題画像 1'));

    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByRole('img')).toHaveAttribute('src', getMediaUrl('/media/q1.png'));
  });
});
