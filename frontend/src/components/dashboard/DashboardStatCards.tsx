/**
 * ダッシュボードの数字のカード 4 枚（I487）
 * データ無し（has_data が false）は 0 を並べず、それぞれに「まだ記録がありません」を出す
 */
import React from 'react';
import { Avatar, Box, Card, CardContent, Grid, LinearProgress, Typography } from '@mui/material';
import { EmojiEvents, Quiz, Timer, TrendingUp } from '@mui/icons-material';
import { DashboardOverview } from '../../types/api';
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

const noRecord = <Typography variant="body1" color="text.secondary">{NO_RECORD_TEXT}</Typography>;

interface DashboardStatCardsProps {
  overview: DashboardOverview;
  goalMinutes: number | null;
}

const DashboardStatCards: React.FC<DashboardStatCardsProps> = ({ overview, goalMinutes }) => {
  const { has_data: hasData, totals } = overview;
  const todayMinutes = todayStudyMinutes(overview);
  const goalPercent = goalMinutes ? Math.min((todayMinutes / goalMinutes) * 100, 100) : 0;

  const cards: StatCardProps[] = [
    {
      icon: <Timer />,
      color: 'primary.main',
      label: '今日の学習時間',
      value: hasData ? <Typography variant="h6">{todayMinutes}分</Typography> : noRecord,
      footer: hasData && goalMinutes !== null && (
        <>
          <LinearProgress variant="determinate" value={goalPercent} sx={{ mt: 2 }} />
          <Typography variant="caption" color="text.secondary">
            目標: {goalMinutes}分 ({Math.floor((todayMinutes / goalMinutes) * 100)}%)
          </Typography>
        </>
      ),
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
