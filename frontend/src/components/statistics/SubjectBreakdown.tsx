/**
 * 学習統計の「科目別（全科目）」（I488）
 * 科目の選択に関係なく、期間の全科目を出す（科目を選んだときに 1 科目だけの円グラフにしない）
 */
import React from 'react';
import { Box, Card, CardContent, Grid, Typography } from '@mui/material';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { DashboardAnalytics } from '../../types/api';
import { formatRate, formatStudyTime, NO_RECORD_IN_PERIOD_TEXT } from './format';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

interface SubjectBreakdownProps {
  subjects: DashboardAnalytics['subject_breakdown'];
}

const SubjectBreakdown = ({ subjects }: SubjectBreakdownProps) => {
  if (subjects.length === 0) {
    return <Typography variant="body2" color="text.secondary">{NO_RECORD_IN_PERIOD_TEXT}</Typography>;
  }

  const totalSeconds = subjects.reduce((sum, subject) => sum + subject.study_seconds, 0);

  return (
    <>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        科目の選択に関係なく、期間の全科目を出します
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Typography variant="h6" component="h2" gutterBottom>科目別の学習時間</Typography>
          {totalSeconds > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                {/* 分に丸めると 1 分未満の科目が 0 になって描かれないので、秒のまま描く */}
                <Pie
                  data={subjects}
                  dataKey="study_seconds"
                  nameKey="subject_name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, percent }) => `${name} ${Math.round(percent * 100)}%`}
                >
                  {subjects.map((subject, index) => (
                    <Cell key={subject.subject_id} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => [formatStudyTime(Number(value)), '学習時間']} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <Box display="flex" alignItems="center" sx={{ height: 120 }}>
              <Typography variant="body2" color="text.secondary">学習時間の記録がありません</Typography>
            </Box>
          )}
        </Grid>
        <Grid item xs={12} md={6}>
          <Typography variant="h6" component="h2" gutterBottom>科目ごとの成績</Typography>
          {subjects.map((subject) => (
            <Card
              key={subject.subject_id}
              component="section"
              aria-labelledby={`statistics-subject-${subject.subject_id}`}
              sx={{ mb: 2 }}
            >
              <CardContent>
                <Typography
                  id={`statistics-subject-${subject.subject_id}`}
                  variant="subtitle1"
                  component="h3"
                  gutterBottom
                  sx={{ overflowWrap: 'anywhere' }}
                >
                  {subject.subject_name}
                </Typography>
                <Grid container spacing={2}>
                  {[
                    ['学習時間', formatStudyTime(subject.study_seconds)],
                    ['正答率', formatRate(subject.accuracy_rate)],
                    ['問題数', `${subject.answered_count}問`],
                  ].map(([label, value]) => (
                    <Grid item xs={4} key={label}>
                      <Typography variant="body2" color="text.secondary">{label}</Typography>
                      <Typography variant="body1">{value}</Typography>
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          ))}
        </Grid>
      </Grid>
    </>
  );
};

export default SubjectBreakdown;
