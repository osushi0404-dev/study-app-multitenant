/**
 * 選択肢の記号（I645 TC-01）
 * 順番（0 から）から ア・イ・ウ・エ… を出し、表を超えたら 1 から数えた数字を出す
 */
import { CHOICE_LABELS, choiceLabel } from '../choiceLabel';

describe('choiceLabel（I645 TC-01）', () => {
  it('順番から五十音の記号を出す', () => {
    expect(choiceLabel(0)).toBe('ア');
    expect(choiceLabel(1)).toBe('イ');
    expect(choiceLabel(3)).toBe('エ');
    expect(choiceLabel(4)).toBe('オ');
    expect(choiceLabel(45)).toBe('ン');
  });

  it('表を超えたら数字を出す', () => {
    expect(CHOICE_LABELS).toHaveLength(46);
    expect(choiceLabel(46)).toBe('47');
  });
});
