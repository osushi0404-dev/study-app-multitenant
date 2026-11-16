/**
 * 画面をまたいで使う道筋と、画面の中の目印（I494）
 * 画面どうしが互いの部品を読み込まずに、同じ値を指せるようにする
 */

/** 設定画面の「学ぶ科目」のカードの目印（カードの id・URL のハッシュ） */
export const LEARNING_SUBJECTS_ANCHOR = 'learning-subjects';

/** 設定画面の「学ぶ科目」のカードへの道筋（ダッシュボードの科目 0 件の案内から使う） */
export const LEARNING_SUBJECTS_PATH = `/settings#${LEARNING_SUBJECTS_ANCHOR}`;
