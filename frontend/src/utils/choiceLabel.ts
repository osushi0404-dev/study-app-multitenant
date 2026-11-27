/**
 * 選択肢の記号（I645）
 * IPA の過去問にそろえ、選択肢の順番（0 から）から五十音の順に ア・イ・ウ・エ… を付ける。
 * クイズの画面・問題管理のプレビュー・AI の問題作成の画面で同じ記号を使う
 */
export const CHOICE_LABELS = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';

/** 順番（0 から）の記号。表を超えたら 1 から数えた数字を返す（選択肢の数に上限は無い） */
export const choiceLabel = (index: number): string => CHOICE_LABELS.charAt(index) || String(index + 1);
