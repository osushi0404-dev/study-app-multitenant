/**
 * ダッシュボードの「今日の復習」のカード（I452）
 *
 * 復習する日が来た問題の数を出し、「復習を始める」で復習のクイズへ進む。
 * 件数と出題は、ダッシュボード上部の科目の選択（'all' なら全科目）に合わせる。
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, Card, CardContent, CircularProgress, Typography } from '@mui/material';
import { Replay } from '@mui/icons-material';
import { getReviewSummary, ReviewSummary } from '../services/review.service';

interface TodayReviewCardProps {
  /** ダッシュボードの科目の選択の値（'all' なら全科目） */
  subjectId: string;
}

const ALL_SUBJECTS = 'all';

/** 'YYYY-MM-DD' を「M月D日」に（端末の時刻の設定でずれないよう Date に通さない） */
const formatMonthDay = (isoDate: string): string => {
  const [, month, day] = isoDate.split('-').map(Number);
  return `${month}月${day}日`;
};

const noReviewText = (nextReviewDate: string | null): string => (
  nextReviewDate
    ? `今日の復習はありません（次は ${formatMonthDay(nextReviewDate)}）`
    : '今日の復習はありません'
);

type LoadState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'loaded'; summary: ReviewSummary };

const TodayReviewCard: React.FC<TodayReviewCardProps> = ({ subjectId }) => {
  const navigate = useNavigate();
  const [state, setState] = useState<LoadState>({ status: 'loading' });
  const [reloadKey, setReloadKey] = useState(0);
  const subject = subjectId === ALL_SUBJECTS ? undefined : subjectId;

  useEffect(() => {
    // 科目を切り替えた後に古い応答が届いても、新しい表示を上書きしない
    let ignore = false;
    setState({ status: 'loading' });
    getReviewSummary(subject)
      .then((summary) => {
        if (!ignore) setState({ status: 'loaded', summary });
      })
      .catch(() => {
        if (!ignore) setState({ status: 'error' });
      });
    return () => {
      ignore = true;
    };
  }, [subject, reloadKey]);

  const handleStart = useCallback(() => {
    navigate(subject ? `/quiz?mode=review&subject=${subject}` : '/quiz?mode=review');
  }, [navigate, subject]);

  return (
    <Card>
      <CardContent>
        {state.status === 'loading' && (
          <Box display="flex" alignItems="center" gap={1} role="status">
            <CircularProgress size={20} />
            <Typography variant="body2" color="text.secondary">今日の復習を読み込み中…</Typography>
          </Box>
        )}

        {state.status === 'error' && (
          <Box display="flex" alignItems="center" justifyContent="space-between" gap={2} flexWrap="wrap">
            <Typography variant="body1">今日の復習を読み込めませんでした</Typography>
            <Button variant="outlined" startIcon={<Replay />} onClick={() => setReloadKey((key) => key + 1)}>
              再読み込み
            </Button>
          </Box>
        )}

        {state.status === 'loaded' && state.summary.due_count > 0 && (
          <Box display="flex" alignItems="center" justifyContent="space-between" gap={2} flexWrap="wrap">
            <Typography variant="h6" component="h2">
              今日の復習 {state.summary.due_count}問
            </Typography>
            <Button variant="contained" onClick={handleStart}>
              復習を始める
            </Button>
          </Box>
        )}

        {state.status === 'loaded' && state.summary.due_count === 0 && (
          <Typography variant="body1">{noReviewText(state.summary.next_review_date)}</Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default TodayReviewCard;
