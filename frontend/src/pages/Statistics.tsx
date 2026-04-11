import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tabs,
  Tab,
  Button,
  Paper,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import { Download } from '@mui/icons-material';
import dashboardService from '../services/dashboard.service';
import { AnalyticsData, AnalyticsFilters } from '../services/types';
import { toast } from 'react-hot-toast';
import { SubjectSelector } from '../components/SubjectSelector';

// ネイティブJavaScriptのDateヘルパー関数
const formatDate = (date: Date, formatStr: string) => {
  const month = date.getMonth() + 1;
  const day = date.getDate();

  if (formatStr === 'M/d') {
    return `${month}/${day}`;
  } else if (formatStr === 'M月d日') {
    return `${month}月${day}日`;
  }
  return date.toLocaleDateString();
};

const Statistics: React.FC = () => {
  const [period, setPeriod] = useState<'daily' | 'weekly' | 'monthly'>('weekly');
  const [selectedSubject, setSelectedSubject] = useState('all');
  const [tabValue, setTabValue] = useState(0);
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [mountKey, setMountKey] = useState(Date.now());

  useEffect(() => {
    // 画面表示時にSubjectSelectorを再マウントさせるためkeyを更新
    setMountKey(Date.now());
  }, []);

  useEffect(() => {
    const loadStatistics = async () => {
      try {
        setLoading(true);
        const filters: AnalyticsFilters = {
          period,
          subject: selectedSubject === 'all' ? undefined : selectedSubject || undefined,
        };

        const analyticsData = await dashboardService.getAnalytics(filters);
        setData(analyticsData);
      } catch (error) {
        console.error('Error fetching analytics data:', error);
        toast.error('統計データの取得に失敗しました');
      } finally {
        setLoading(false);
      }
    };
    loadStatistics();
  }, [period, selectedSubject]);

  const handleExportData = () => {
    // Implement data export functionality
    console.log('Exporting data...');
  };

  if (loading || !data) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <Typography variant="h6">統計データを読み込み中...</Typography>
      </Box>
    );
  }

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  // データの存在チェックとデフォルト値の設定
  const studyTimeTrend = data?.study_time_trend || [];
  const accuracyTrend = data?.accuracy_trend || [];
  const subjectBreakdown = data?.subject_breakdown || [];
  const mistakePatterns = data?.mistake_patterns || [];

  const totalStudyTime = studyTimeTrend.length > 0
    ? studyTimeTrend.reduce((sum: number, item: any) => sum + (item.study_time || 0), 0)
    : 0;

  const averageAccuracy = accuracyTrend.length > 0
    ? accuracyTrend.reduce((sum: number, item: any) => sum + (item.accuracy || 0), 0) / accuracyTrend.length
    : 0;

  const totalProblems = subjectBreakdown.length > 0
    ? subjectBreakdown.reduce((sum: number, item: any) => sum + (item.problems_solved || 0), 0)
    : 0;

  const TabPanel = ({ children, value, index }: any) => (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4">学習統計</Typography>
        <Button
          variant="outlined"
          startIcon={<Download />}
          onClick={handleExportData}
        >
          データをエクスポート
        </Button>
      </Box>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth>
              <InputLabel>期間</InputLabel>
              <Select
                value={period}
                label="期間"
                onChange={(e) => setPeriod(e.target.value as 'daily' | 'weekly' | 'monthly')}
              >
                <MenuItem value="daily">日別</MenuItem>
                <MenuItem value="weekly">週別</MenuItem>
                <MenuItem value="monthly">月別</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <SubjectSelector
              key={`statistics-subject-${mountKey}`}
              value={selectedSubject}
              onChange={(value) => setSelectedSubject(value)}
              label="科目"
            />
          </Grid>
        </Grid>
      </Paper>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                総学習時間
              </Typography>
              <Typography variant="h4">
                {Math.floor(totalStudyTime / 60)}h {totalStudyTime % 60}m
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                平均正答率
              </Typography>
              <Typography variant="h4">
                {Math.round(averageAccuracy * 100)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                解いた問題数
              </Typography>
              <Typography variant="h4">
                {totalProblems}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                学習日数
              </Typography>
              <Typography variant="h4">
                {studyTimeTrend.filter((item: any) => item.study_time > 0).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ width: '100%' }}>
        <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab label="学習時間" />
          <Tab label="正答率推移" />
          <Tab label="科目別分析" />
          <Tab label="間違いパターン" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <Typography variant="h6" gutterBottom>
            学習時間の推移
          </Typography>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={studyTimeTrend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={(value) => formatDate(new Date(value), 'M/d')}
              />
              <YAxis />
              <Tooltip
                labelFormatter={(value) => formatDate(new Date(value), 'M月d日')}
                formatter={(value) => [`${value}分`, '学習時間']}
              />
              <Bar dataKey="study_time" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Typography variant="h6" gutterBottom>
            正答率の推移
          </Typography>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={accuracyTrend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={(value) => formatDate(new Date(value), 'M/d')}
              />
              <YAxis
                domain={[0, 1]}
                tickFormatter={(value) => `${Math.round(value * 100)}%`}
              />
              <Tooltip
                labelFormatter={(value) => formatDate(new Date(value), 'M月d日')}
                formatter={(value: number) => [`${Math.round(value * 100)}%`, '正答率']}
              />
              <Line
                type="monotone"
                dataKey="accuracy"
                stroke="#82ca9d"
                strokeWidth={3}
                dot={{ fill: '#82ca9d', strokeWidth: 2, r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                科目別学習時間
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={subjectBreakdown}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ subject_name, percent }) => `${subject_name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="time_spent"
                  >
                    {subjectBreakdown.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${value}分`, '学習時間']} />
                </PieChart>
              </ResponsiveContainer>
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                科目別詳細
              </Typography>
              {subjectBreakdown.map((subject: any, index: number) => (
                <Card key={subject.subject_name} sx={{ mb: 2 }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {subject.subject_name}
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={4}>
                        <Typography variant="body2" color="text.secondary">
                          学習時間
                        </Typography>
                        <Typography variant="body1">
                          {Math.floor(subject.time_spent / 60)}h {subject.time_spent % 60}m
                        </Typography>
                      </Grid>
                      <Grid item xs={4}>
                        <Typography variant="body2" color="text.secondary">
                          正答率
                        </Typography>
                        <Typography variant="body1">
                          {Math.round(subject.accuracy * 100)}%
                        </Typography>
                      </Grid>
                      <Grid item xs={4}>
                        <Typography variant="body2" color="text.secondary">
                          問題数
                        </Typography>
                        <Typography variant="body1">
                          {subject.problems_solved}問
                        </Typography>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              ))}
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <Typography variant="h6" gutterBottom>
            間違いパターン分析
          </Typography>
          <Grid container spacing={2}>
            {mistakePatterns.map((pattern: any, index: number) => (
              <Grid item xs={12} sm={6} md={3} key={`${pattern.subject_name}-${pattern.problem_type}`}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {pattern.subject_name} - {pattern.problem_type}
                    </Typography>
                    <Typography variant="h4" color="error.main" gutterBottom>
                      {pattern.mistake_count}回
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      難易度: {pattern.difficulty}
                    </Typography>
                    <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                      {pattern.improvement_suggestion}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default Statistics;
