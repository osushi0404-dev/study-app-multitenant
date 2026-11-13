/**
 * 数字のカードとグラフの形のスケルトン（I487）
 */
import React from 'react';
import { Box, Grid, Skeleton } from '@mui/material';

const DashboardSkeleton: React.FC = () => (
  <Box data-testid="dashboard-skeleton" aria-busy="true" sx={{ mb: 4 }}>
    {/* 画面には出さず読み上げにだけ伝える（styles/accessibility.css の .sr-only） */}
    <span className="sr-only">ダッシュボードの数字を読み込み中</span>
    <Grid container spacing={3} sx={{ mb: 4 }}>
      {[0, 1, 2, 3].map((i) => (
        <Grid item xs={12} sm={6} md={3} key={i}>
          <Skeleton variant="rounded" height={96} />
        </Grid>
      ))}
    </Grid>
    <Grid container spacing={3}>
      <Grid item xs={12} md={8}>
        <Skeleton variant="rounded" height={340} />
      </Grid>
      <Grid item xs={12} md={4}>
        <Skeleton variant="rounded" height={340} />
      </Grid>
    </Grid>
  </Box>
);

export default DashboardSkeleton;
