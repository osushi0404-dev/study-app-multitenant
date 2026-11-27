/**
 * クイズの選択肢の記号と、答えた後の印（I645 TC-02〜TC-06）
 * 色が disabled の灰色に勝つかは jsdom では正しく測れないので、ここでは印の有無だけを見る（色は E2E の TC-08）
 */
import { fireEvent, render, screen, within } from '@testing-library/react';
import QuizChoices from '../QuizChoices';
import { Choice } from '../../types/quiz';

const choices: Choice[] = [
  { id: 'c1', text: '本文1' },
  { id: 'c2', text: '本文2' },
  { id: 'c3', text: '本文3' },
];

// 選択肢の行を上から順に返す。各行の入力の名前（記号＋本文）が上から ア・イ・ウ の順であることも確かめる
const rowsOf = (role: 'radio' | 'checkbox'): HTMLElement[] => {
  const rows = screen.getAllByTestId('choice-option');
  expect(rows.map((row) => within(row).getByRole(role).getAttribute('aria-label'))).toEqual([
    'ア 本文1',
    'イ 本文2',
    'ウ 本文3',
  ]);
  return rows;
};

const renderChoices = (props: Partial<React.ComponentProps<typeof QuizChoices>> = {}) =>
  render(
    <QuizChoices
      problemType="single_choice"
      choices={choices}
      selectedChoices={[]}
      onSelect={jest.fn()}
      showResult={false}
      correctChoiceIds={[]}
      {...props}
    />
  );

describe('QuizChoices の記号（I645）', () => {
  it('TC-02: 単一選択で、記号と本文が別の要素で出て、入力の名前に記号が付く', () => {
    renderChoices();

    expect(screen.getByText('ア').textContent).toBe('ア');
    expect(screen.getByText('イ')).toBeInTheDocument();
    expect(screen.getByText('ウ')).toBeInTheDocument();
    expect(screen.getByText('本文1')).not.toBe(screen.getByText('ア'));
    expect(screen.getByRole('radio', { name: 'ア 本文1' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'ウ 本文3' })).toBeInTheDocument();
    expect(screen.queryByText(/^A\./)).not.toBeInTheDocument();
  });

  it('TC-03: 複数選択でも同じ記号と名前', () => {
    renderChoices({ problemType: 'multiple_choice' });

    expect(screen.getByRole('checkbox', { name: 'イ 本文2' })).toBeInTheDocument();
  });
});

describe('QuizChoices の答えた後の印（I645）', () => {
  it('TC-04: 単一選択で誤答を選ぶと、選んだ誤答に×、正解にチェック', () => {
    renderChoices({ showResult: true, selectedChoices: ['c2'], correctChoiceIds: ['c1'] });

    const [correct, wrong, other] = rowsOf('radio');
    expect(within(wrong).getByTestId('CancelIcon')).toBeInTheDocument();
    expect(within(wrong).queryByTestId('CheckCircleOutlineIcon')).not.toBeInTheDocument();
    expect(within(correct).getByTestId('CheckCircleOutlineIcon')).toBeInTheDocument();
    expect(within(correct).queryByTestId('CancelIcon')).not.toBeInTheDocument();
    expect(within(other).queryByTestId('CancelIcon')).not.toBeInTheDocument();
    expect(within(other).queryByTestId('CheckCircleOutlineIcon')).not.toBeInTheDocument();
  });

  it('TC-04b: API と同じく id が数字でも、ラジオを押すと元の数字の id で選ぶ', () => {
    // API は選択肢の id を数字で返すが、ラジオの値は文字になる。文字のまま選ぶと
    // 「選んだ選択肢か」の比べ方が外れ、誤答の印が出なかった（I645 の E2E で判明）
    const numericChoices = [
      { id: 11, text: '本文1' },
      { id: 12, text: '本文2' },
    ] as unknown as Choice[];
    const onSelect = jest.fn();
    renderChoices({ choices: numericChoices, onSelect });

    fireEvent.click(screen.getByRole('radio', { name: 'イ 本文2' }));

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(12);
  });

  it('TC-05: 正解を選ぶと、×はどこにも出ない', () => {
    renderChoices({ showResult: true, selectedChoices: ['c1'], correctChoiceIds: ['c1'] });

    expect(screen.queryAllByTestId('CancelIcon')).toHaveLength(0);
    expect(screen.getAllByTestId('CheckCircleOutlineIcon')).toHaveLength(1);
  });

  it('TC-06: 複数選択で、選んだ誤答だけに×、選び漏れた正解にもチェック', () => {
    renderChoices({
      problemType: 'multiple_choice',
      showResult: true,
      selectedChoices: ['c1', 'c3'],
      correctChoiceIds: ['c1', 'c2'],
    });

    const [first, second, third] = rowsOf('checkbox');
    expect(within(third).getByTestId('CancelIcon')).toBeInTheDocument();
    expect(within(first).getByTestId('CheckCircleOutlineIcon')).toBeInTheDocument();
    expect(within(second).getByTestId('CheckCircleOutlineIcon')).toBeInTheDocument();
    expect(screen.getAllByTestId('CancelIcon')).toHaveLength(1);
  });

  it('答える前は印を出さない', () => {
    renderChoices({ selectedChoices: ['c2'], correctChoiceIds: ['c1'] });

    expect(screen.queryAllByTestId('CancelIcon')).toHaveLength(0);
    expect(screen.queryAllByTestId('CheckCircleOutlineIcon')).toHaveLength(0);
  });
});
