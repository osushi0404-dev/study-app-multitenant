/**
 * 学習統計の推移のグラフ（「学習時間」の棒・「正答率」の折れ線・I488）
 * 期間（と選んだ科目）に答えが無ければ、グラフの代わりに「この期間の記録はありません」
 */
import React, { useMemo } from 'react';
import { Box, Paper, Typography } from '@mui/material';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  TooltipProps,
  XAxis,
  YAxis,
} from 'recharts';
import { DashboardAnalytics } from '../../types/api';
import {
  formatBucketLabel,
  formatBucketRange,
  formatRate,
  formatStudyTime,
  NO_RECORD_IN_PERIOD_TEXT,
} from './format';

const CHART_HEIGHT = 360;

type TrendMetric = 'study_time' | 'accuracy';

interface ChartPoint {
  label: string;
  range: string;
  minutes: number;
  seconds: number;
  answered: number;
  accuracyRate: number | null;
  // 答えが無い区切りは null（0% として描かず、線を切る）
  accuracyPercent: number | null;
}

const PointTooltip: React.FC<TooltipProps<number, string> & { metric: TrendMetric }> = ({
  active,
  payload,
  metric,
}) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }
  const point = payload[0].payload as ChartPoint;
  const value = metric === 'study_time'
    ? `${formatStudyTime(point.seconds)}・${point.answered}問`
    : formatRate(point.accuracyRate);
  return (
    <Paper sx={{ p: 1 }}>
      <Typography variant="body2">{point.range}</Typography>
      <Typography variant="body2">{value}</Typography>
    </Paper>
  );
};

interface StatisticsTrendChartProps {
  analytics: DashboardAnalytics;
  metric: TrendMetric;
}

const StatisticsTrendChart: React.FC<StatisticsTrendChartProps> = ({ analytics, metric }) => {
  const { trend, period, totals } = analytics;

  const points = useMemo<ChartPoint[]>(() => trend.map((bucket) => ({
    label: formatBucketLabel(bucket.start_date, period.granularity),
    range: formatBucketRange(bucket.start_date, bucket.end_date),
    // 整数の分に丸めると、1 分未満しか解いていない区切りの棒が 0 になり「解いたのに空」に見えるので小数第 1 位まで
    minutes: Math.round(bucket.study_seconds / 6) / 10,
    seconds: bucket.study_seconds,
    answered: bucket.answered_count,
    accuracyRate: bucket.accuracy_rate,
    accuracyPercent: bucket.accuracy_rate === null ? null : Math.round(bucket.accuracy_rate * 100),
  })), [trend, period.granularity]);

  if (totals.answered_count === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" sx={{ height: 120 }}>
        <Typography variant="body2" color="text.secondary">{NO_RECORD_IN_PERIOD_TEXT}</Typography>
      </Box>
    );
  }

  const tooltip = <Tooltip content={<PointTooltip metric={metric} />} />;

  return (
    <>
      <Typography variant="h6" component="h2" gutterBottom>
        {metric === 'study_time' ? '学習時間の推移（分）' : '正答率の推移（%）'}
      </Typography>
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        {metric === 'study_time' ? (
          <BarChart data={points}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" />
            <YAxis allowDecimals={false} domain={[0, 'auto']} />
            {tooltip}
            <Bar dataKey="minutes" fill="#8884d8" />
          </BarChart>
        ) : (
          <LineChart data={points}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" />
            <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} />
            {tooltip}
            <Line type="linear" dataKey="accuracyPercent" stroke="#82ca9d" strokeWidth={3} dot={{ r: 4 }} />
          </LineChart>
        )}
      </ResponsiveContainer>
    </>
  );
};

export default StatisticsTrendChart;
