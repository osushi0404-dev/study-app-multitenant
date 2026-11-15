/**
 * ダッシュボードの数字のカード 4 枚（I487）
 * データ無し（has_data が false）は 0 を並べず、それぞれに「まだ記録がありません」を出す
 */
import React from 'react';
import { Avatar, Box, Card, CardContent, Grid, LinearProgress, Typography } from '@mui/material';
import { EmojiEvents, Quiz, Timer, TrendingUp } from '@mui/icons-material';
import { DashboardOverview } from '../../types/api';
import { GoalProgress } from '../../types/dashboard';
import { todayStudyMinutes } from '../../utils/dashboardAchievements';

export const NO_RECORD_TEXT = 'まだ記録がありません';

interface StatCardProps {
  icon: React.ReactNode;
  color: string;
  label: string;
  value: React.ReactNode;
  footer?: React.ReactNode;
}

const StatCard: React.FC<StatCardProps> = ({ icon, color, label, value, footer }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Box display="flex" alignItems="center">
        <Avatar sx={{ bgcolor: color, mr: 2 }}>{icon}</Avatar>
        <Box minWidth={0}>
          {value}
          <Typography variant="body2" color="text.secondary">{label}</Typography>
        </Box>
      </Box>
      {footer}
    </CardContent>
  </Card>
);

const GoalFooter = ({ todayMinutes, goalMinutes }: GoalProgress) => {
  const percent = (todayMinutes / goalMinutes) * 100;
  return (
    <>
      <LinearProgress variant="determinate" value={Math.min(percent, 100)} sx={{ mt: 2 }} />
      <Typography variant="caption" color="text.secondary">
        目標（全科目）: {goalMinutes}分 ({Math.floor(percent)}%)
      </Typography>
    </>
  );
};

const noRecord = <Typography variant="body1" color="text.secondary">{NO_RECORD_TEXT}</Typography>;

interface DashboardStatCardsProps {
  overview: DashboardOverview;
  /** 目標は 1 日全体のものなので、全科目の値で渡す（出さないときは null） */
  goalProgress: GoalProgress | null;
}

const DashboardStatCards: React.FC<DashboardStatCardsProps> = ({ overview, goalProgress }) => {
  const { has_data: hasData, totals } = overview;
  const todayMinutes = todayStudyMinutes(overview);

  const cards: StatCardProps[] = [
    {
      icon: <Timer />,
      color: 'primary.main',
      label: '今日の学習時間',
      value: hasData ? <Typography variant="h6">{todayMinutes}分</Typography> : noRecord,
      // 選んだ科目に記録が無いときは出さない（同じカードの「まだ記録がありません」と食い違って読めるため。
      // 目標は「学習を開始」のカードの全科目の行で伝わる）
      footer: hasData && goalProgress && <GoalFooter {...goalProgress} />,
    },
    {
      icon: <EmojiEvents />,
      color: 'success.main',
      label: '連続学習日数',
      value: hasData ? <Typography variant="h6">{overview.streak.current_days}日</Typography> : noRecord,
    },
    {
      icon: <Quiz />,
      color: 'info.main',
      label: '解答問題数',
      value: hasData
        ? <Typography variant="h6" data-testid="stat-answered-count">{totals.answered_count}</Typography>
        : noRecord,
    },
    {
      icon: <TrendingUp />,
      color: 'warning.main',
      label: '正答率',
      value: hasData && totals.accuracy_rate !== null
        ? <Typography variant="h6">{Math.round(totals.accuracy_rate * 100)}%</Typography>
        : noRecord,
    },
  ];

  return (
    <Grid container spacing={3} sx={{ mb: 4 }}>
      {cards.map((card) => (
        <Grid item xs={12} sm={6} md={3} key={card.label}>
          <StatCard {...card} />
        </Grid>
      ))}
    </Grid>
  );
};

export default DashboardStatCards;
