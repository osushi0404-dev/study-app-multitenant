/**
 * 問題の出典の表示（I609）
 *
 * クイズの画面と問題のプレビューで、問題文（画像があれば画像）のすぐ下に灰色の小さい文字で出す。
 * 保存しているのは本文だけで、頭の「出典：」はここで付ける。空（空白だけを含む）なら何も描かない。
 * URL もただの文字として出し（リンクにしない）、長い URL は画面の幅で折り返す。
 */
import { Typography } from '@mui/material';

interface ProblemSourceProps {
  source?: string;
}

const ProblemSource = ({ source }: ProblemSourceProps) => {
  const text = source?.trim();
  if (!text) return null;
  return (
    <Typography
      variant="caption"
      component="p"
      color="text.secondary"
      sx={{ mt: 1, overflowWrap: 'anywhere' }}
    >
      出典：{text}
    </Typography>
  );
};

export default ProblemSource;
