import React, { useState, useEffect, useCallback } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
  Button,
  Chip,
  Paper,
  Avatar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  TrendingUp,
  Timer,
  EmojiEvents,
  PlayArrow,
  BarChart,
  Quiz,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { Line, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';

import { useAuth } from '../contexts/AuthContext';
import { useNotifications } from '../contexts/NotificationContext';
import dashboardService from '../services/dashboard.service';
import SubjectService from '../services/subjectService';
import { DashboardData, Subject } from '../services/types';
import { toast } from 'react-hot-toast';
import { SubjectSelector } from '../components/SubjectSelector';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

const Dashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSubject, setSelectedSubject] = useState('all');
  const [mountKey, setMountKey] = useState(Date.now());
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loadingSubjects, setLoadingSubjects] = useState(true);
  const [subjectDialogOpen, setSubjectDialogOpen] = useState(false);
  const { user } = useAuth();
  const { showAchievement, showStreakNotification } = useNotifications();
  const navigate = useNavigate();

  useEffect(() => {
    // 画面表示時にSubjectSelectorを再マウントさせるためkeyを更新
    setMountKey(Date.now());
  }, []);

  const fetchDashboardData = useCallback(async () => {
    // checkForAchievements は fetchDashboardData からのみ使用するためローカル関数として定義
    const checkForAchievements = (data: DashboardData) => {
      const { stats } = data;

      // statsが存在しない場合は処理をスキップ
      if (!stats) return;

      // Check for streak milestones
      if (stats.current_streak > 0 && stats.current_streak % 7 === 0) {
        showStreakNotification(stats.current_streak);
      }

      // Check for problem count milestones
      const milestones = [10, 50, 100, 250, 500, 1000];
      milestones.forEach(milestone => {
        if (stats.total_problems_solved === milestone) {
          showAchievement(`${milestone}問解答達成！おめでとうございます！🎉`);
        }
      });

      // Check for accuracy achievements
      if (stats.accuracy_rate >= 0.95 && stats.total_problems_solved >= 20) {
        const lastCheck = localStorage.getItem('lastHighAccuracyNotification');
        const today = new Date().toDateString();

        if (lastCheck !== today) {
          showAchievement('素晴らしい正答率です！95%以上をキープしています！🎯');
          localStorage.setItem('lastHighAccuracyNotification', today);
        }
      }

      // Check for daily goal achievements
      const dailyGoalMinutes = 60; // This should come from user settings
      const todayStudyMinutes = Math.floor(stats.today_study_time / 60);

      if (todayStudyMinutes >= dailyGoalMinutes) {
        const lastCheck = localStorage.getItem('lastDailyGoalNotification');
        const today = new Date().toDateString();

        if (lastCheck !== today) {
          showAchievement('今日の学習目標を達成しました！継続は力なり！💪');
          localStorage.setItem('lastDailyGoalNotification', today);
        }
      }
    };

    try {
      setLoading(true);
      const params = selectedSubject && selectedSubject !== 'all'
        ? { subject_id: selectedSubject }
        : {};
      const data = await dashboardService.getDashboardData(params);

      // プロパティが存在しない場合はデフォルト値を設定
      const dashboardDataWithDefaults = {
        ...data,
        stats: data?.stats || {
          today_study_time: 0,
          week_study_time: 0,
          total_problems_solved: 0,
          accuracy_rate: 0,
          current_streak: 0,
          longest_streak: 0
        },
        weekly_progress: Array.isArray(data?.weekly_progress) ? data.weekly_progress : [],
        subject_progress: Array.isArray(data?.subject_progress) ? data.subject_progress : [],
        recommendations: Array.isArray(data?.recommendations) ? data.recommendations : [],
        recent_sessions: Array.isArray(data?.recent_sessions) ? data.recent_sessions : []
      };

      // Check for achievements and show notifications
      checkForAchievements(dashboardDataWithDefaults);

      setDashboardData(dashboardDataWithDefaults);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast.error('ダッシュボードデータの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  }, [selectedSubject, showAchievement, showStreakNotification]);

  useEffect(() => {
    fetchDashboardData();
  }, [selectedSubject, fetchDashboardData]);

  // 科目取得処理（データ取得のみに専念）
  useEffect(() => {
    const loadSubjects = async () => {
      try {
        setLoadingSubjects(true);
        const data = await SubjectService.getUserSubjects();
        setSubjects(data);
      } catch (error) {
        console.error('Error loading subjects:', error);
        toast.error('科目の読み込みに失敗しました');
      } finally {
        setLoadingSubjects(false);
      }
    };

    loadSubjects();
  }, []);

  // 「クイズを始める」ボタン押下時の処理
  const handleStartQuiz = useCallback(() => {
    if (subjects.length === 0) {
      toast.error('科目が登録されていません。設定画面から科目を追加してください。');
      return;
    }

    if (subjects.length === 1) {
      // 科目が1件のみの場合は即座に遷移
      navigate(`/quiz?subject=${subjects[0].id}`);
      return;
    }

    // 科目が2件以上の場合はDialogを開く
    setSubjectDialogOpen(true);
  }, [subjects, navigate]);

  // Dialog内の科目選択処理
  const handleSubjectSelect = useCallback((subjectId: number | string) => {
    setSubjectDialogOpen(false);
    navigate(`/quiz?subject=${subjectId}`);
  }, [navigate]);

  if (loading || !dashboardData) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <Typography variant="h6">ダッシュボードを読み込み中...</Typography>
      </Box>
    );
  }

  // 安全なデフォルト値でデータを展開
  const {
    stats = {
      today_study_time: 0,
      week_study_time: 0,
      total_problems_solved: 0,
      accuracy_rate: 0,
      current_streak: 0,
      longest_streak: 0
    },
    weekly_progress = [],
    subject_progress = [],
    recommendations = []
  } = dashboardData || {};

  const weeklyChartData = {
    labels: (weekly_progress || []).map(item => new Date(item.date).toLocaleDateString('ja-JP', { weekday: 'short' })),
    datasets: [
      {
        label: '学習時間（分）',
        data: (weekly_progress || []).map(item => item.study_time),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.4,
      },
    ],
  };

  const accuracyChartData = {
    labels: ['正解', '不正解'],
    datasets: [
      {
        data: [stats.accuracy_rate * 100, (1 - stats.accuracy_rate) * 100],
        backgroundColor: ['#4caf50', '#f44336'],
        borderWidth: 0,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
    },
  };

  return (
    <Box>
      {/* Welcome Section */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          おかえりなさい、{user?.user_id || user?.email}さん！
        </Typography>
        <Typography variant="body1" color="text.secondary">
          今日も学習を頑張りましょう 🚀
        </Typography>
      </Box>

      {/* Subject Selector */}
      <Box sx={{ mb: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <SubjectSelector
              key={`dashboard-subject-${mountKey}`}
              value={selectedSubject}
              onChange={(value) => setSelectedSubject(value)}
              label="科目を選択"
            />
          </Grid>
        </Grid>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
                  <Timer />
                </Avatar>
                <Box>
                  <Typography variant="h6">{Math.floor(stats.today_study_time / 60)}分</Typography>
                  <Typography variant="body2" color="text.secondary">
                    今日の学習時間
                  </Typography>
                </Box>
              </Box>
              <LinearProgress
                variant="determinate"
                value={Math.min((stats.today_study_time / 3600) * 100, 100)}
                sx={{ mt: 2 }}
              />
              <Typography variant="caption" color="text.secondary">
                目標: 60分 ({Math.floor((stats.today_study_time / 3600) * 100)}%)
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Avatar sx={{ bgcolor: 'success.main', mr: 2 }}>
                  <EmojiEvents />
                </Avatar>
                <Box>
                  <Typography variant="h6">{stats.current_streak}日</Typography>
                  <Typography variant="body2" color="text.secondary">
                    連続学習日数
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Avatar sx={{ bgcolor: 'info.main', mr: 2 }}>
                  <Quiz />
                </Avatar>
                <Box>
                  <Typography variant="h6">{stats.total_problems_solved}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    解答問題数
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <Avatar sx={{ bgcolor: 'warning.main', mr: 2 }}>
                  <TrendingUp />
                </Avatar>
                <Box>
                  <Typography variant="h6">
                    {Math.round(stats.accuracy_rate * 100)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    正答率
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts and Data */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                今週の学習時間
              </Typography>
              <Box sx={{ height: 300 }}>
                <Line data={weeklyChartData} options={chartOptions} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                正答率
              </Typography>
              <Box sx={{ height: 300, display: 'flex', justifyContent: 'center' }}>
                <Doughnut data={accuracyChartData} options={chartOptions} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Action Buttons */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              学習を開始
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              今日の目標達成まであと{Math.max(0, 60 - Math.floor(stats.today_study_time / 60))}分です
            </Typography>
            <Button
              variant="contained"
              size="large"
              startIcon={<PlayArrow />}
              onClick={handleStartQuiz}
              fullWidth
              disabled={loadingSubjects}
            >
              クイズを始める
            </Button>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              詳細統計
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              学習進捗の詳細を確認できます
            </Typography>
            <Button
              variant="outlined"
              size="large"
              startIcon={<BarChart />}
              onClick={() => navigate('/statistics')}
              fullWidth
            >
              統計を見る
            </Button>
          </Paper>
        </Grid>
      </Grid>

      {/* Mistake Summary and Recommendations */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                間違いやすい分野
              </Typography>
              {(subject_progress || []).length > 0 ? (
                (subject_progress || [])
                  .filter(subject => subject.accuracy < 0.7)
                  .slice(0, 3)
                  .map((subject, index) => (
                    <Box key={index} sx={{ mb: 2 }}>
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="body1">{subject.subject_name}</Typography>
                        <Chip
                          label={`${Math.round(subject.accuracy * 100)}%`}
                          size="small"
                          color={subject.accuracy < 0.5 ? 'error' : 'warning'}
                        />
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        解答数: {subject.problems_solved}問
                      </Typography>
                    </Box>
                  ))
              ) : (
                <Typography variant="body2" color="text.secondary">
                  データがありません。まずは問題を解いてみましょう！
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                おすすめ練習問題
              </Typography>
              {(recommendations || []).length > 0 ? (
                (recommendations || []).slice(0, 3).map((rec, index) => (
                  <Box key={index} sx={{ mb: 2 }}>
                    <Typography variant="body1">{rec.title}</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {rec.description}
                    </Typography>
                    <Button
                      size="small"
                      variant="text"
                      onClick={() => navigate('/quiz')}
                    >
                      練習する
                    </Button>
                  </Box>
                ))
              ) : (
                <Typography variant="body2" color="text.secondary">
                  現在、おすすめの練習問題はありません
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 科目選択Dialog */}
      <Dialog
        open={subjectDialogOpen}
        onClose={() => setSubjectDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>📚 クイズを始める科目を選択</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {subjects.map((subject) => (
            <Button
              key={subject.id}
              variant="outlined"
              fullWidth
              size="large"
              onClick={() => handleSubjectSelect(subject.id)}
              aria-label={`${subject.name}のクイズを開始`}
              sx={{ mb: 1.5, py: 2 }}
            >
              {subject.name}
            </Button>
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSubjectDialogOpen(false)}>
            キャンセル
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Dashboard;