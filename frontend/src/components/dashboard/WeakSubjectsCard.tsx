/**
 * 間違いやすい分野（全科目）（I487）
 * 一覧は科目の選択に関係なく全科目から出る（I473 F1）。
 * 選んだ科目の解答が 0 件なら、一番上に案内を出し、その下に全科目の一覧を出す（F9）
 * 科目別の一覧の下に、難易度別の苦手と、急いで答えた間違いの 1 行を出す（I466。当てはまらなければ出さない）
 */
import React from 'react';
import { Alert, Box, Card, CardContent, Chip, Typography } from '@mui/material';
import { DashboardOverview } from '../../types/api';
import { ALL_SUBJECTS } from '../../hooks/useDashboardOverview';
import { difficultyLabel } from '../../utils/difficulty';
import { formatRate } from '../statistics/format';

const NO_ANSWER_IN_SUBJECT = 'この科目はまだ解答がありません。まずは問題を解いてみましょう！';
const NO_DATA_AT_ALL = 'データがありません。まずは問題を解いてみましょう！';
const NO_WEAK_SUBJECT = '5 問以上解いた科目のうち、正答率が 70% 未満の科目はありません';

interface WeakRowProps {
  label: string;
  accuracyRate: number;
  answeredCount: number;
}

/** 苦手の 1 行（名前・正答率・解答数）。科目別と難易度別で同じ形にする */
const WeakRow = ({ label, accuracyRate, answeredCount }: WeakRowProps) => (
  <Box sx={{ mb: 2 }}>
    <Box display="flex" justifyContent="space-between" alignItems="center">
      <Typography variant="body1">{label}</Typography>
      <Chip
        label={formatRate(accuracyRate)}
        size="small"
        color={accuracyRate < 0.5 ? 'error' : 'warning'}
      />
    </Box>
    <Typography variant="caption" color="text.secondary">
      解答数: {answeredCount}問
    </Typography>
  </Box>
);

interface WeakSubjectsCardProps {
  overview: DashboardOverview;
  selectedSubject: string;
}

const WeakSubjectsCard: React.FC<WeakSubjectsCardProps> = ({ overview, selectedSubject }) => {
  const isAll = selectedSubject === ALL_SUBJECTS;
  const showSubjectNotice = !isAll && !overview.has_data;
  const weak = overview.weak_subjects;

  let emptyText: string | null = null;
  if (weak.length === 0 && !showSubjectNotice) {
    emptyText = isAll && !overview.has_data ? NO_DATA_AT_ALL : NO_WEAK_SUBJECT;
  }

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="h6" component="h2" gutterBottom>
          間違いやすい分野（全科目）
        </Typography>
        {showSubjectNotice && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: weak.length > 0 ? 2 : 0 }}>
            {NO_ANSWER_IN_SUBJECT}
          </Typography>
        )}
        {emptyText && (
          <Typography variant="body2" color="text.secondary">{emptyText}</Typography>
        )}
        {weak.map((subject) => (
          <WeakRow
            key={subject.subject_id}
            label={subject.subject_name}
            accuracyRate={subject.accuracy_rate}
            answeredCount={subject.answered_count}
          />
        ))}
        {overview.weak_difficulties.length > 0 && (
          <>
            <Typography variant="subtitle2" component="h3" sx={{ mt: 1, mb: 1 }}>
              難易度別
            </Typography>
            {overview.weak_difficulties.map((difficulty) => (
              <WeakRow
                key={difficulty.difficulty}
                label={difficultyLabel(difficulty.difficulty)}
                accuracyRate={difficulty.accuracy_rate}
                answeredCount={difficulty.answered_count}
              />
            ))}
          </>
        )}
        {overview.rushed_mistakes && (
          <Alert severity="info" role="status">
            {`急いで答えた問題の間違いが多めです（間違いの ${formatRate(overview.rushed_mistakes.rushed_rate)}）。落ち着いて解きましょう`}
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default WeakSubjectsCard;
