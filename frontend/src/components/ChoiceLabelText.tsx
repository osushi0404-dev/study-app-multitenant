import { Box } from '@mui/material';
import { choiceLabel } from '../utils/choiceLabel';

type Props = {
  /** 選択肢の順番（0 から） */
  index: number;
  text: string;
};

/**
 * 選択肢の記号と本文を別の要素で並べる（I645）。区切りの文字なしで記号と本文を見分けられるようにする。
 * 色は親から受け継ぐ（クイズの画面の正解・誤答の色が記号にも付く）
 */
function ChoiceLabelText({ index, text }: Props) {
  return (
    <Box component="span" sx={{ display: 'inline-flex', alignItems: 'baseline', gap: 1.5 }}>
      <Box component="span" sx={{ fontWeight: 700, minWidth: '1.5em', flexShrink: 0 }}>
        {choiceLabel(index)}
      </Box>
      <span>{text}</span>
    </Box>
  );
}

export default ChoiceLabelText;
