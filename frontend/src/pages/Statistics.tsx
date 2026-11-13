/**
 * 学習統計（I488 で作り直し）
 *
 * 上から: 見出し → 絞り込み（期間・科目）→ 期間 → 数字のカード → タブ（学習時間・正答率・科目別（全科目））
 * 取得と状態はフック、表示は components/statistics の部品が受け持つ。
 * 読み込み中・失敗・データ無しは絞り込みの下だけを置き換え、絞り込みは出し続ける。
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  Tab,
  Tabs,
  Typography,
} from '@mui/material';
import { Replay } from '@mui/icons-material';

import { useAuth } from '../contexts/AuthContext';
import { SubjectSelector } from '../components/SubjectSelector';
import { NO_RECORD_TEXT } from '../components/dashboard/DashboardStatCards';
import StatisticsSummaryCards from '../components/statistics/StatisticsSummaryCards';
import StatisticsTrendChart from '../components/statistics/StatisticsTrendCharts';
import SubjectBreakdown from '../components/statistics/SubjectBreakdown';
import { ALL_SUBJECTS } from '../hooks/useDashboardOverview';
import { DEFAULT_STATISTICS_DAYS, STATISTICS_PERIODS, useStatistics } from '../hooks/useStatistics';

const TABS = ['学習時間', '正答率', '科目別（全科目）'] as const;

interface TabPanelProps {
  index: number;
  value: number;
  children: React.ReactNode;
}

/** 描画の中で定義すると描くたびに別の部品になり中身が作り直されるので、外で定義する（MUI の例と同じ形） */
const TabPanel: React.FC<TabPanelProps> = ({ index, value, children }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`statistics-tabpanel-${index}`}
    aria-labelledby={`statistics-tab-${index}`}
  >
    {value === index && <Box sx={{ p: { xs: 2, sm: 3 } }}>{children}</Box>}
  </div>
);

const StatisticsSkeleton: React.FC = () => (
  <Box aria-busy="true">
    {/* 画面には出さず読み上げにだけ伝える（ダッシュボードのスケルトンと同じ・styles/accessibility.css の .sr-only） */}
    <span className="sr-only">学習統計を読み込み中</span>
    <Grid container spacing={2} sx={{ mb: 3 }}>
      {[0, 1, 2, 3].map((key) => (
        <Grid item xs={6} md={3} key={key}>
          <Skeleton variant="rounded" height={96} />
        </Grid>
      ))}
    </Grid>
    <Skeleton variant="rounded" height={360} />
  </Box>
);

const Statistics: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [days, setDays] = useState<number>(DEFAULT_STATISTICS_DAYS);
  const [selectedSubject, setSelectedSubject] = useState(ALL_SUBJECTS);
  const [tab, setTab] = useState(0);
  // 取得のキャッシュのキーに使う（利用者の情報が無い間の扱いは #508）
  const statistics = useStatistics(user?.id ?? '', days, selectedSubject);

  return (
    <Box>
      <Typography variant="h5" component="h1" sx={{ mb: 3 }}>学習統計</Typography>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth>
              <InputLabel id="statistics-period-label">期間</InputLabel>
              <Select
                labelId="statistics-period-label"
                value={days}
                label="期間"
                onChange={(event) => setDays(Number(event.target.value))}
              >
                {STATISTICS_PERIODS.map((period) => (
                  <MenuItem key={period.days} value={period.days}>{period.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <SubjectSelector value={selectedSubject} onChange={setSelectedSubject} label="科目" />
          </Grid>
        </Grid>
      </Paper>

      {statistics.status === 'loading' && <StatisticsSkeleton />}

      {statistics.status === 'error' && (
        // 取得の失敗・形の違いは 0 や空のグラフで埋めずに伝え、その場で取り直せるようにする（C7）
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" startIcon={<Replay />} onClick={statistics.retry}>
              再読み込み
            </Button>
          }
        >
          学習統計を読み込めませんでした
        </Alert>
      )}

      {statistics.status === 'success' && !statistics.data.has_data && (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="h6" component="p" gutterBottom>{NO_RECORD_TEXT}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              クイズを解くと、学習時間と正答率の推移がここに出ます
            </Typography>
            <Button variant="contained" onClick={() => navigate('/quiz')}>クイズを始める</Button>
          </CardContent>
        </Card>
      )}

      {statistics.status === 'success' && statistics.data.has_data && (
        <>
          <StatisticsSummaryCards analytics={statistics.data} />
          <Paper sx={{ width: '100%' }}>
            <Tabs
              value={tab}
              onChange={(_, next: number) => setTab(next)}
              variant="scrollable"
              allowScrollButtonsMobile
            >
              {TABS.map((label, index) => (
                <Tab
                  key={label}
                  label={label}
                  id={`statistics-tab-${index}`}
                  aria-controls={`statistics-tabpanel-${index}`}
                />
              ))}
            </Tabs>
            <TabPanel value={tab} index={0}>
              <StatisticsTrendChart analytics={statistics.data} metric="study_time" />
            </TabPanel>
            <TabPanel value={tab} index={1}>
              <StatisticsTrendChart analytics={statistics.data} metric="accuracy" />
            </TabPanel>
            <TabPanel value={tab} index={2}>
              <SubjectBreakdown subjects={statistics.data.subject_breakdown} />
            </TabPanel>
          </Paper>
        </>
      )}
    </Box>
  );
};

export default Statistics;
