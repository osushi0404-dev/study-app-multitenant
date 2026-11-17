/**
 * ダッシュボードの「学習を開始」のカード（I487）
 *
 * - クイズの対象は問題のある科目だけ（I539）。科目を選んでいればその科目で、「すべて」なら 1 件はすぐ・
 *   2 件以上はダイアログで科目を選ぶ
 * - 科目 0 件・問題 0 問・科目の取得失敗は、押せないボタンとカードの中の案内で伝える（toast だけにしない）
 * - 科目 0 件の案内は、組織に科目があれば設定画面の「学ぶ科目」のカードへの導線（I494）。無ければ、管理者には
 *   科目を作る案内と行き先、管理者でない人には管理者が用意するのを待つ案内（I539）
 * - 問題 0 問の案内は、管理者には問題を作る行き先、管理者でない人には待つ案内（I539）
 * - 目標の 1 行は、クイズを始められ、設定の目標と全科目の今日の分が読めたときだけ出す（科目を選んでいても
 *   全科目で計算・I513。始められないときは出さない・I539）
 * - 「クイズを始める」の下に「苦手を優先して始める」（I466）。押せる条件・科目の選び方は同じで、行き先に mode=weak を付ける
 */
import React, { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
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
import { PlayArrow, TrackChanges } from '@mui/icons-material';
import { ALL_SUBJECTS } from '../../hooks/useDashboardOverview';
import SubjectsRetryRow from '../SubjectsRetryRow';
import { UserSubjectsState } from '../../hooks/useUserSubjects';
import { AvailableSubjectsState } from '../../hooks/useAvailableSubjects';
import {
  LEARNING_SUBJECTS_PATH,
  QUIZ_MANAGEMENT_PATH,
  QuizStartMode,
  SUBJECT_MANAGEMENT_PATH,
  quizPath,
} from '../../constants/routes';

interface StartQuizCardProps {
  /** 組織の管理者か（組織の科目が 0 件のときの案内を分ける・I539） */
  isOrgAdmin: boolean;
  subjects: UserSubjectsState;
  onRetrySubjects: () => void;
  /** 組織の科目（選んだ科目が 0 件のときだけ読む・I494） */
  availableSubjects: AvailableSubjectsState;
  onRetryAvailable: () => void;
  /** 科目の選択の値（'all' なら全科目） */
  selectedSubject: string;
  /** 全科目の今日の学習の分。目標は 1 日全体のものなので、選んだ科目に関係なく全科目の値（読めていないときは null・I513） */
  todayMinutes: number | null;
  /** 1 日の目標の分（読めていないときは null） */
  goalMinutes: number | null;
}

const goalText = (todayMinutes: number, goalMinutes: number): string =>
  todayMinutes >= goalMinutes
    ? `今日の目標（全科目・${goalMinutes}分）を達成しました！`
    : `今日の目標（全科目）達成まであと${goalMinutes - todayMinutes}分です`;

interface CreateGuideProps {
  message: string;
  actionLabel: string;
  to: string;
}

/** 管理者への作る案内。その時点で次にやること 1 つだけを目立つボタンで出す（I539） */
const CreateGuide = ({ message, actionLabel, to }: CreateGuideProps) => (
  <Box sx={{ mb: 2 }}>
    <Alert severity="info" role="status" sx={{ mb: 1 }}>
      {message}
    </Alert>
    <Button variant="contained" component={RouterLink} to={to}>
      {actionLabel}
    </Button>
  </Box>
);

/** 管理者でない人への待つ案内（I539） */
const WaitGuide = ({ message }: { message: string }) => (
  <Alert severity="info" role="status" sx={{ mb: 2 }}>
    {message}
  </Alert>
);

interface NoSubjectsGuideProps {
  isOrgAdmin: boolean;
  availableSubjects: AvailableSubjectsState;
  onRetry: () => void;
}

/**
 * 選んだ科目が 0 件のときの案内（I494）。組織に科目があれば設定画面の「学ぶ科目」のカードへ。
 * 1 つも無ければ、管理者には科目を作る行き先、管理者でない人には待つ案内（I539）。
 * 組織の科目を読み込み中は何も出さない
 */
const NoSubjectsGuide = ({ isOrgAdmin, availableSubjects, onRetry }: NoSubjectsGuideProps) => {
  if (availableSubjects.status === 'error') {
    return <SubjectsRetryRow onRetry={onRetry} sx={{ mb: 2 }} />;
  }
  if (availableSubjects.status === 'loading') return null;
  if (availableSubjects.data.length === 0 && isOrgAdmin) {
    return (
      <CreateGuide
        message="まず科目と問題を作りましょう。科目管理で科目を作り、問題管理でその科目の問題を作ると、クイズを始められます"
        actionLabel="科目を作る"
        to={SUBJECT_MANAGEMENT_PATH}
      />
    );
  }
  if (availableSubjects.data.length === 0) {
    return <WaitGuide message="科目がまだ用意されていません。管理者が科目を用意するまでお待ちください" />;
  }
  return (
    <Box sx={{ mb: 2 }}>
      <Alert severity="info" role="status" sx={{ mb: 1 }}>
        学ぶ科目がまだ選ばれていません。設定画面で学ぶ科目を選んでください
      </Alert>
      <Button variant="outlined" component={RouterLink} to={LEARNING_SUBJECTS_PATH}>
        学ぶ科目を選ぶ
      </Button>
    </Box>
  );
};

interface NoProblemsGuideProps {
  isOrgAdmin: boolean;
  /** 「すべて」を選んでいるか（文言を「学ぶ科目」と「この科目」で分ける） */
  isAllSubjects: boolean;
}

/**
 * 学ぶ科目はあるが、クイズの対象の科目に問題が 1 問も無いときの案内（I539）。
 * 「クイズを始める」を押してエラーの通知で戻される流れを作らないため、押せないボタンと一緒に出す
 */
const NoProblemsGuide = ({ isOrgAdmin, isAllSubjects }: NoProblemsGuideProps) => {
  if (isOrgAdmin) {
    const target = isAllSubjects ? '学ぶ科目' : 'この科目';
    return (
      <CreateGuide
        message={`問題を作りましょう。問題管理で${target}の問題を作ると、クイズを始められます`}
        actionLabel="問題を作る"
        to={QUIZ_MANAGEMENT_PATH}
      />
    );
  }
  const noProblems = isAllSubjects ? '学ぶ科目にまだ問題がありません' : 'この科目にはまだ問題がありません';
  return <WaitGuide message={`${noProblems}。管理者が問題を用意するまでお待ちください`} />;
};

const StartQuizCard: React.FC<StartQuizCardProps> = ({
  isOrgAdmin,
  subjects,
  onRetrySubjects,
  availableSubjects,
  onRetryAvailable,
  selectedSubject,
  todayMinutes,
  goalMinutes,
}) => {
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);
  // ダイアログで科目を選んだときに使うモード（押したボタンのモード・I466）
  const [startMode, setStartMode] = useState<QuizStartMode>('normal');

  const subjectList = subjects.status === 'success' ? subjects.subjects : [];
  const hasSubjects = subjectList.length > 0;
  const isAllSubjects = selectedSubject === ALL_SUBJECTS;
  // クイズの対象は問題のある科目だけ（問題 0 問の科目で始めてエラーの通知で戻されないように・I539）
  const quizTargets = subjectList.filter(
    (subject) => subject.problem_count > 0 && (isAllSubjects || String(subject.id) === selectedSubject)
  );
  const canStart = quizTargets.length > 0;

  const goToQuiz = (subjectId: number, mode: QuizStartMode) => {
    setDialogOpen(false);
    navigate(quizPath(subjectId, mode));
  };

  // 対象が 1 件ならすぐ始め、2 件以上（「すべて」）ならダイアログで選ぶ
  const handleStart = (mode: QuizStartMode) => {
    if (quizTargets.length === 1) {
      goToQuiz(quizTargets[0].id, mode);
    } else {
      setStartMode(mode);
      setDialogOpen(true);
    }
  };

  return (
    <Paper sx={{ p: 3, height: '100%' }} data-testid="start-quiz-card">
      <Typography variant="h6" component="h2" gutterBottom>
        学習を開始
      </Typography>

      {subjects.status === 'error' && <SubjectsRetryRow onRetry={onRetrySubjects} sx={{ mb: 2 }} />}

      {subjects.status === 'success' && !hasSubjects && (
        <NoSubjectsGuide
          isOrgAdmin={isOrgAdmin}
          availableSubjects={availableSubjects}
          onRetry={onRetryAvailable}
        />
      )}

      {hasSubjects && !canStart && (
        <NoProblemsGuide isOrgAdmin={isOrgAdmin} isAllSubjects={isAllSubjects} />
      )}

      {/* 目標の行は、クイズを始められるときだけ（始められないのに「あと◯分」と促さない・I539） */}
      {canStart && todayMinutes !== null && goalMinutes !== null && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {goalText(todayMinutes, goalMinutes)}
        </Typography>
      )}

      <Button
        variant="contained"
        size="large"
        startIcon={<PlayArrow />}
        onClick={() => handleStart('normal')}
        fullWidth
        disabled={!canStart}
        data-testid="start-quiz-button"
      >
        クイズを始める
      </Button>

      <Button
        variant="outlined"
        size="large"
        startIcon={<TrackChanges />}
        onClick={() => handleStart('weak')}
        fullWidth
        disabled={!canStart}
        data-testid="start-weak-quiz-button"
        aria-describedby="start-weak-quiz-help"
        sx={{ mt: 1.5, minHeight: 44 /* タッチの的は 44px 以上（ux-rules.md 6） */ }}
      >
        苦手を優先して始める
      </Button>
      <Typography
        id="start-weak-quiz-help"
        variant="caption"
        color="text.secondary"
        component="p"
        sx={{ mt: 0.5 }}
      >
        間違えた問題や正答率の低い難易度から出します
      </Typography>

      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        aria-labelledby="start-quiz-dialog-title"
      >
        {/* 見出しは押したボタンの始め方に合わせる（I466 AC12） */}
        <DialogTitle id="start-quiz-dialog-title">
          {startMode === 'weak' ? '📚 苦手を優先して始める科目を選択' : '📚 クイズを始める科目を選択'}
        </DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {quizTargets.map((subject) => (
            <Button
              key={subject.id}
              variant="outlined"
              fullWidth
              size="large"
              onClick={() => goToQuiz(subject.id, startMode)}
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
