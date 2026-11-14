/**
 * 学習統計の数字のカード 4 枚（選んだ期間の合計・I488）
 * 期間に答えが無ければ 0 と「—」を出す（データ無し〔has_data が false〕のときは画面がこの部品を出さない）
 */
import React from 'react';
import { Card, CardContent, Grid, Typography } from '@mui/material';
import { DashboardAnalytics } from '../../types/api';
import { formatPeriod, formatRate, formatStudyTime } from './format';

interface StatisticsSummaryCardsProps {
  analytics: DashboardAnalytics;
}

const StatisticsSummaryCards = ({ analytics }: StatisticsSummaryCardsProps) => {
  const { period, totals } = analytics;
  const cards = [
    { label: '学習時間', value: formatStudyTime(totals.study_seconds) },
    { label: '正答率', value: formatRate(totals.accuracy_rate) },
    { label: '解いた問題数', value: `${totals.answered_count}問` },
    { label: '学習した日数', value: `${totals.studied_days}日` },
  ];

  return (
    <>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        {formatPeriod(period.start_date, period.end_date)}
      </Typography>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {cards.map((card) => (
          <Grid item xs={6} md={3} key={card.label}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>{card.label}</Typography>
                <Typography variant="h5" component="p">{card.value}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </>
  );
};

export default StatisticsSummaryCards;
