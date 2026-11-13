/**
 * ダッシュボードのグラフ 2 つ（直近 7 日の学習時間・正答率）（I487）
 * データ無しはグラフを描かず「まだ記録がありません」（空の枠・赤い円を出さない）
 */
import React, { useMemo } from 'react';
import { Box, Card, CardContent, Grid, Typography } from '@mui/material';
import { Doughnut, Line } from 'react-chartjs-2';
import {
  ArcElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js';
import { DashboardOverview } from '../../types/api';
import { NO_RECORD_TEXT } from './DashboardStatCards';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, ArcElement);

const CHART_HEIGHT = 300;
const EMPTY_HEIGHT = 120;

const lineOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  // 答えが 0 件の日ばかりでも目盛りがマイナスにならないように（I473 の画面確認）
  scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
};

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
};

interface ChartCardProps {
  title: string;
  hasData: boolean;
  children: React.ReactNode;
}

/** Chart.js の推奨どおり、グラフの入れ物は position: relative でグラフ専用にする */
const ChartCard: React.FC<ChartCardProps> = ({ title, hasData, children }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Typography variant="h6" component="h2" gutterBottom>{title}</Typography>
      {hasData ? (
        <Box sx={{ position: 'relative', height: CHART_HEIGHT, minWidth: 0 }}>{children}</Box>
      ) : (
        <Box display="flex" justifyContent="center" alignItems="center" sx={{ height: EMPTY_HEIGHT }}>
          <Typography variant="body2" color="text.secondary">{NO_RECORD_TEXT}</Typography>
        </Box>
      )}
    </CardContent>
  </Card>
);

interface DashboardChartsProps {
  overview: DashboardOverview;
}

const DashboardCharts: React.FC<DashboardChartsProps> = ({ overview }) => {
  const { has_data: hasData, last_7_days: lastDays } = overview;
  const accuracyRate = overview.totals.accuracy_rate;

  const weeklyData = useMemo(() => ({
    labels: lastDays.map((day) =>
      new Date(`${day.date}T00:00:00`).toLocaleDateString('ja-JP', { weekday: 'short' })
    ),
    datasets: [
      {
        label: '学習時間（分）',
        data: lastDays.map((day) => Math.round(day.study_seconds / 60)),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.4,
      },
    ],
  }), [lastDays]);

  const accuracyData = useMemo(() => ({
    labels: ['正解', '不正解'],
    datasets: [
      {
        data: accuracyRate === null ? [] : [accuracyRate * 100, (1 - accuracyRate) * 100],
        backgroundColor: ['#4caf50', '#f44336'],
        borderWidth: 0,
      },
    ],
  }), [accuracyRate]);

  return (
    <Grid container spacing={3} sx={{ mb: 4 }}>
      <Grid item xs={12} md={8}>
        <ChartCard title="直近 7 日の学習時間" hasData={hasData}>
          <Line data={weeklyData} options={lineOptions} />
        </ChartCard>
      </Grid>
      <Grid item xs={12} md={4}>
        <ChartCard title="正答率" hasData={hasData && accuracyRate !== null}>
          <Doughnut data={accuracyData} options={doughnutOptions} />
        </ChartCard>
      </Grid>
    </Grid>
  );
};

export default DashboardCharts;
