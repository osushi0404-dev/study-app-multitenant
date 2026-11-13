/**
 * ダッシュボードの「学習を開始」のカード（I487）
 *
 * - 科目を選んでいればその科目で、「すべて」なら 1 件はすぐ・2 件以上はダイアログで科目を選ぶ
 * - 科目 0 件・科目の取得失敗は、押せないボタンとカードの中の案内で伝える（toast だけにしない）
 * - 目標の 1 行は、設定の目標が読めたときだけ出す
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  Typography,
} from '@mui/material';
import { PlayArrow, Replay } from '@mui/icons-material';
import { ALL_SUBJECTS } from '../../hooks/useDashboardOverview';
import { UserSubjectsState } from '../../hooks/useUserSubjects';

interface StartQuizCardProps {
  subjects: UserSubjectsState;
  onRetrySubjects: () => void;
  /** 科目の選択の値（'all' なら全科目） */
  selectedSubject: string;
  /** 今日の学習の分（数字を読めていないときは null） */
  todayMinutes: number | null;
  /** 1 日の目標の分（読めていないときは null） */
  goalMinutes: number | null;
}

const goalText = (todayMinutes: number, goalMinutes: number): string =>
  todayMinutes >= goalMinutes
    ? `今日の目標（${goalMinutes}分）を達成しました！`
    : `今日の目標達成まであと${goalMinutes - todayMinutes}分です`;

const StartQuizCard: React.FC<StartQuizCardProps> = ({
  subjects,
  onRetrySubjects,
  selectedSubject,
  todayMinutes,
  goalMinutes,
}) => {
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);

  const subjectList = subjects.status === 'success' ? subjects.subjects : [];
  const hasSubjects = subjectList.length > 0;

  const goToQuiz = (subjectId: number | string) => {
    setDialogOpen(false);
    navigate(`/quiz?subject=${subjectId}`);
  };

  const handleStart = () => {
    if (selectedSubject !== ALL_SUBJECTS) {
      goToQuiz(selectedSubject);
    } else if (subjectList.length === 1) {
      goToQuiz(subjectList[0].id);
    } else {
      setDialogOpen(true);
    }
  };

  return (
    <Paper sx={{ p: 3, height: '100%' }} data-testid="start-quiz-card">
      <Typography variant="h6" component="h2" gutterBottom>
        学習を開始
      </Typography>

      {subjects.status === 'error' && (
        <Box display="flex" alignItems="center" justifyContent="space-between" gap={2} flexWrap="wrap" sx={{ mb: 2 }}>
          <Typography variant="body2">科目を読み込めませんでした</Typography>
          <Button variant="outlined" size="small" startIcon={<Replay />} onClick={onRetrySubjects}>
            再読み込み
          </Button>
        </Box>
      )}

      {subjects.status === 'success' && !hasSubjects && (
        <Alert severity="info" role="status" sx={{ mb: 2 }}>
          科目がまだ登録されていません。組織の管理者に科目の登録を依頼してください
        </Alert>
      )}

      {hasSubjects && todayMinutes !== null && goalMinutes !== null && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {goalText(todayMinutes, goalMinutes)}
        </Typography>
      )}

      <Button
        variant="contained"
        size="large"
        startIcon={<PlayArrow />}
        onClick={handleStart}
        fullWidth
        disabled={!hasSubjects}
        data-testid="start-quiz-button"
      >
        クイズを始める
      </Button>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>📚 クイズを始める科目を選択</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {subjectList.map((subject) => (
            <Button
              key={subject.id}
              variant="outlined"
              fullWidth
              size="large"
              onClick={() => goToQuiz(subject.id)}
              aria-label={`${subject.name}のクイズを開始`}
              sx={{ mb: 1.5, py: 2 }}
            >
              {subject.name}
            </Button>
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>キャンセル</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default StartQuizCard;
