/**
 * ダッシュボード（I487 で作り直し）
 *
 * 上から: 挨拶 → 科目の選択 → 学習を開始・今日の復習 → 数字 → グラフ → 間違いやすい分野・おすすめ → 統計を見る
 * 取得と状態はフック、表示は components/dashboard の部品が受け持つ。
 * 読み込み中・失敗は数字とグラフの場所だけを置き換え、ほかは出し続ける（科目の選択を外して付け直さない）
 */
import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Alert, Box, Button, Grid, Link, Typography } from '@mui/material';
import { Replay } from '@mui/icons-material';

import { useAuth } from '../contexts/AuthContext';
import { SubjectSelector } from '../components/SubjectSelector';
import TodayReviewCard from '../components/TodayReviewCard';
import StartQuizCard from '../components/dashboard/StartQuizCard';
import DashboardStatCards from '../components/dashboard/DashboardStatCards';
import DashboardCharts from '../components/dashboard/DashboardCharts';
import DashboardSkeleton from '../components/dashboard/DashboardSkeleton';
import WeakSubjectsCard from '../components/dashboard/WeakSubjectsCard';
import RecommendationsCard from '../components/dashboard/RecommendationsCard';
import { ALL_SUBJECTS, useDashboardOverview } from '../hooks/useDashboardOverview';
import { useUserSubjects } from '../hooks/useUserSubjects';
import { useDailyStudyGoal } from '../hooks/useDailyStudyGoal';
import { useDashboardAchievements } from '../hooks/useDashboardAchievements';
import { todayStudyMinutes } from '../utils/dashboardAchievements';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [selectedSubject, setSelectedSubject] = useState(ALL_SUBJECTS);
  // 取得のキャッシュのキーに使う（利用者の情報が無い間の扱いは #508）
  const userId = user?.id ?? '';
  const overview = useDashboardOverview(userId, selectedSubject);
  const { state: subjects, retry: retrySubjects } = useUserSubjects(userId);
  const goal = useDailyStudyGoal(userId);
  const goalMinutes = goal.status === 'done' ? goal.minutes : null;

  // 達成のお知らせは利用者の全体の記録の節目なので、「すべて」の応答だけで判定する（I473 F2）
  const allSubjectsOverview = selectedSubject === ALL_SUBJECTS ? overview.data : null;
  useDashboardAchievements(user?.id, allSubjectsOverview, goal);

  const todayMinutes = overview.data ? todayStudyMinutes(overview.data) : null;

  return (
    <Box>
      <Typography variant="h5" component="h1" sx={{ mb: 3, overflowWrap: 'anywhere' }}>
        おかえりなさい、{user?.user_id || user?.email}さん！
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <SubjectSelector value={selectedSubject} onChange={setSelectedSubject} label="科目を選択" />
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}>
          <StartQuizCard
            subjects={subjects}
            onRetrySubjects={retrySubjects}
            selectedSubject={selectedSubject}
            todayMinutes={todayMinutes}
            goalMinutes={goalMinutes}
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <TodayReviewCard subjectId={selectedSubject} />
        </Grid>
      </Grid>

      {overview.status === 'loading' && <DashboardSkeleton />}

      {overview.status === 'error' && (
        // 取得の失敗・形の違いは 0 で埋めずに伝え、その場で取り直せるようにする（I473・C7）
        <Alert
          severity="error"
          sx={{ mb: 4 }}
          action={
            <Button color="inherit" size="small" startIcon={<Replay />} onClick={overview.retry}>
              再読み込み
            </Button>
          }
        >
          ダッシュボードの数字を読み込めませんでした
        </Alert>
      )}

      {overview.status === 'success' && (
        <>
          <DashboardStatCards overview={overview.data} goalMinutes={goalMinutes} />
          <DashboardCharts overview={overview.data} />
          <Grid container spacing={3} sx={{ mb: 2 }}>
            <Grid item xs={12} md={6}>
              <WeakSubjectsCard overview={overview.data} selectedSubject={selectedSubject} />
            </Grid>
            <Grid item xs={12} md={6}>
              <RecommendationsCard recommendations={overview.data.recommendations} />
            </Grid>
          </Grid>
        </>
      )}

      <Box display="flex" justifyContent="flex-end">
        <Link component={RouterLink} to="/statistics" variant="body2">
          統計を見る
        </Link>
      </Box>
    </Box>
  );
};

export default Dashboard;
