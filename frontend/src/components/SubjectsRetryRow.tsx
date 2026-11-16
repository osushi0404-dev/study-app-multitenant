/**
 * 科目の読み込みに失敗したときの「科目を読み込めませんでした」と「再読み込み」の行（I487・I494）
 * ダッシュボードの「学習を開始」のカードと、設定画面の「学ぶ科目」のカードが使う
 */
import React from 'react';
import { Box, Button, SxProps, Theme, Typography } from '@mui/material';
import { Replay } from '@mui/icons-material';

interface SubjectsRetryRowProps {
  onRetry: () => void;
  sx?: SxProps<Theme>;
}

const SubjectsRetryRow = ({ onRetry, sx }: SubjectsRetryRowProps) => (
  <Box display="flex" alignItems="center" justifyContent="space-between" gap={2} flexWrap="wrap" sx={sx}>
    <Typography variant="body2">科目を読み込めませんでした</Typography>
    <Button variant="outlined" size="small" startIcon={<Replay />} onClick={onRetry}>
      再読み込み
    </Button>
  </Box>
);

export default SubjectsRetryRow;
