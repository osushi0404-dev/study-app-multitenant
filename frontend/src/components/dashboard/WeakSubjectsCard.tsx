/**
 * 間違いやすい分野（全科目）（I487）
 * 一覧は科目の選択に関係なく全科目から出る（I473 F1）。
 * 選んだ科目の解答が 0 件なら、一番上に案内を出し、その下に全科目の一覧を出す（F9）
 */
import React from 'react';
import { Box, Card, CardContent, Chip, Typography } from '@mui/material';
import { DashboardOverview } from '../../types/api';
import { ALL_SUBJECTS } from '../../hooks/useDashboardOverview';

const NO_ANSWER_IN_SUBJECT = 'この科目はまだ解答がありません。まずは問題を解いてみましょう！';
const NO_DATA_AT_ALL = 'データがありません。まずは問題を解いてみましょう！';
const NO_WEAK_SUBJECT = '5 問以上解いた科目のうち、正答率が 70% 未満の科目はありません';

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
          <Box key={subject.subject_id} sx={{ mb: 2 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Typography variant="body1">{subject.subject_name}</Typography>
              <Chip
                label={`${Math.round(subject.accuracy_rate * 100)}%`}
                size="small"
                color={subject.accuracy_rate < 0.5 ? 'error' : 'warning'}
              />
            </Box>
            <Typography variant="caption" color="text.secondary">
              解答数: {subject.answered_count}問
            </Typography>
          </Box>
        ))}
      </CardContent>
    </Card>
  );
};

export default WeakSubjectsCard;
