/**
 * ダッシュボードのグラフ 2 つ（直近 7 日の学習時間・正答率）（I487・I513）
 * データ無しはグラフを描かず「まだ記録がありません」（空の枠・赤い円を出さない）
 * 直近 7 日は日ごとの区切られた値なので棒グラフにし、tooltip に日ごとの解答数・正答率、見出しの下に 7 日の合計を出す（I513）
 */
import React, { useMemo } from 'react';
import { Box, Card, CardContent, Grid, Typography } from '@mui/material';
import { Bar, Doughnut } from 'react-chartjs-2';
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Title,
  Tooltip,
  TooltipItem,
} from 'chart.js';
import { DashboardOverview } from '../../types/api';
import { NO_RECORD_TEXT } from './DashboardStatCards';
import {
  dayAxisLabel,
  dayLines,
  daysAriaLabel,
  dayTitle,
  studyMinutes,
  weeklyTotalText,
} from './weeklySummary';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement);

const CHART_HEIGHT = 300;
const EMPTY_HEIGHT = 120;

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
};

interface ChartCardProps {
  title: string;
  hasData: boolean;
  /** 見出しの下の 1 行（データがあるときだけ出す） */
  subtitle?: React.ReactNode;
  children: React.ReactNode;
}

/** Chart.js の推奨どおり、グラフの入れ物は position: relative でグラフ専用にする */
const ChartCard: React.FC<ChartCardProps> = ({ title, hasData, subtitle, children }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Typography variant="h6" component="h2" gutterBottom>{title}</Typography>
      {hasData ? (
        <>
          {subtitle}
          <Box sx={{ position: 'relative', height: CHART_HEIGHT, minWidth: 0 }}>{children}</Box>
        </>
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
    labels: lastDays.map((day) => dayAxisLabel(day.date)),
    datasets: [
      {
        label: '学習時間（分）',
        data: lastDays.map((day) => studyMinutes(day.study_seconds)),
        backgroundColor: 'rgba(75, 192, 192, 0.6)',
        borderColor: 'rgb(75, 192, 192)',
        borderWidth: 1,
      },
    ],
  }), [lastDays]);

  // tooltip は日ごとの値を読むので、last_7_days から作る
  const weeklyOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    // 高さ 0 の棒の日（答えが無い・1 分未満）も、その日の列を押せば tooltip を出す
    interaction: { mode: 'index' as const, intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          title: (items: Array<Pick<TooltipItem<'bar'>, 'dataIndex'>>) => dayTitle(lastDays[items[0].dataIndex].date),
          label: (item: Pick<TooltipItem<'bar'>, 'dataIndex'>) => dayLines(lastDays[item.dataIndex]),
        },
      },
    },
    // 答えが 0 件の日ばかりでも目盛りがマイナスにならないように（I473 の画面確認）
    scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
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

  const weeklyTotal = (
    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }} data-testid="weekly-total">
      {weeklyTotalText(lastDays)}
    </Typography>
  );

  return (
    <Grid container spacing={3} sx={{ mb: 4 }}>
      <Grid item xs={12} md={8}>
        <ChartCard title="直近 7 日の学習時間" hasData={hasData} subtitle={weeklyTotal}>
          <Bar data={weeklyData} options={weeklyOptions} aria-label={daysAriaLabel(lastDays)} />
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
