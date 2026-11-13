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
  Alert,
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
import { DashboardOverview, Subject } from '../services/types';
import { toast } from 'react-hot-toast';
import { SubjectSelector } from '../components/SubjectSelector';
import TodayReviewCard from '../components/TodayReviewCard';

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
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
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

  // 達成のお知らせは利用者の全体の記録の節目なので、科目が「すべて」の応答だけで判定する（I473 F2）
  const checkForAchievements = useCallback((data: DashboardOverview) => {
    const { streak, totals } = data;

    // Check for streak milestones
    if (streak.current_days > 0 && streak.current_days % 7 === 0) {
      showStreakNotification(streak.current_days);
    }

    // Check for problem count milestones
    const milestones = [10, 50, 100, 250, 500, 1000];
    milestones.forEach(milestone => {
      if (totals.answered_count === milestone) {
        showAchievement(`${milestone}問解答達成！おめでとうございます！🎉`);
      }
    });

    // Check for accuracy achievements（答えが 0 件の null は判定しない）
    if (
      totals.accuracy_rate !== null &&
      totals.accuracy_rate >= 0.95 &&
      totals.answered_count >= 20
    ) {
      const lastCheck = localStorage.getItem('lastHighAccuracyNotification');
      const today = new Date().toDateString();

      if (lastCheck !== today) {
        showAchievement('素晴らしい正答率です！95%以上をキープしています！🎯');
        localStorage.setItem('lastHighAccuracyNotification', today);
      }
    }

    // Check for daily goal achievements
    const dailyGoalMinutes = 60; // This should come from user settings（#487）
    const todayStudyMinutes = Math.floor(data.today.study_seconds / 60);

    if (todayStudyMinutes >= dailyGoalMinutes) {
      const lastCheck = localStorage.getItem('lastDailyGoalNotification');
      const today = new Date().toDateString();

      if (lastCheck !== today) {
        showAchievement('今日の学習目標を達成しました！継続は力なり！💪');
        localStorage.setItem('lastDailyGoalNotification', today);
      }
    }
  }, [showAchievement, showStreakNotification]);

  useEffect(() => {
    // 科目を切り替えた後に届いた古い応答（成功・失敗とも）は捨てる（TodayReviewCard と同じ形・I473 F3）
    let ignore = false;
    const isAll = selectedSubject === 'all';
    const params = isAll ? {} : { subject_id: selectedSubject };

    const load = async () => {
      setLoading(true);
      try {
        // 応答の形が違えば getOverview が投げる（欠けたキーを 0 で埋めない・I473）
        const data = await dashboardService.getOverview(params);
        if (ignore) return;
        if (isAll) checkForAchievements(data);
        setOverview(data);
      } catch (error) {
        if (ignore) return;
        console.error('Error fetching dashboard data:', error);
        toast.error('ダッシュボードデータの取得に失敗しました');
        // 読み込みの後で overview が null なのは失敗のときだけ（下の表示でエラーの文を出す）
        setOverview(null);
      }
      if (!ignore) setLoading(false);
    };

    load();
    return () => {
      ignore = true;
    };
  }, [selectedSubject, checkForAchievements]);

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

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <Typography variant="h6">ダッシュボードを読み込み中...</Typography>
      </Box>
    );
  }

  const todayMinutes = overview ? Math.floor(overview.today.study_seconds / 60) : 0;
  const accuracyRate = overview?.totals.accuracy_rate ?? null;
  const lastDays = overview?.last_7_days ?? [];

  const weeklyChartData = {
    labels: lastDays.map(day =>
      new Date(`${day.date}T00:00:00`).toLocaleDateString('ja-JP', { weekday: 'short' })
    ),
    datasets: [
      {
        label: '学習時間（分）',
        data: lastDays.map(day => Math.round(day.study_seconds / 60)),
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
        data: accuracyRate === null ? [] : [accuracyRate * 100, (1 - accuracyRate) * 100],
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

      {/* 今日の復習（I452）: 科目の選択の下・数字の並びの上 */}
      <Box sx={{ mb: 3 }}>
        <TodayReviewCard subjectId={selectedSubject} />
      </Box>

      {!overview ? (
        // 取得の失敗・形の違いは 0 で埋めずに伝える（再試行などの作り込みは #487）
        <Alert severity="error" sx={{ mb: 4 }}>
          ダッシュボードの数字を読み込めませんでした
        </Alert>
      ) : (
      <>
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
                  <Typography variant="h6">{todayMinutes}分</Typography>
                  <Typography variant="body2" color="text.secondary">
                    今日の学習時間
                  </Typography>
                </Box>
              </Box>
              <LinearProgress
                variant="determinate"
                value={Math.min((todayMinutes / 60) * 100, 100)}
                sx={{ mt: 2 }}
              />
              <Typography variant="caption" color="text.secondary">
                目標: 60分 ({Math.floor((todayMinutes / 60) * 100)}%)
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
                  <Typography variant="h6">{overview.streak.current_days}日</Typography>
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
                  <Typography variant="h6" data-testid="stat-answered-count">
                    {overview.totals.answered_count}
                  </Typography>
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
                    {accuracyRate === null ? '—' : `${Math.round(accuracyRate * 100)}%`}
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
                直近 7 日の学習時間
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
              <Box sx={{ height: 300, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                {overview.has_data ? (
                  <Doughnut data={accuracyChartData} options={chartOptions} />
                ) : (
                  // データ無しで「不正解 100%」の赤い円を出さない（I473）
                  <Typography variant="body2" color="text.secondary">
                    まだ解答の記録がありません
                  </Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      </>
      )}

      {/* Action Buttons */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              学習を開始
            </Typography>
            {overview && (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                今日の目標達成まであと{Math.max(0, 60 - todayMinutes)}分です
              </Typography>
            )}
            <Button
              variant="contained"
              size="large"
              startIcon={<PlayArrow />}
              onClick={handleStartQuiz}
              fullWidth
              disabled={loadingSubjects}
              data-testid="start-quiz-button"
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
      {overview && (
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                間違いやすい分野
              </Typography>
              {/* 一覧は科目の選択に関係なく全科目から出す。出し分けも一覧の有無を先に見る（I473 F1・F4） */}
              {overview.weak_subjects.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {selectedSubject === 'all' && !overview.has_data
                    ? 'データがありません。まずは問題を解いてみましょう！'
                    : '5 問以上解いた科目のうち、正答率が 70% 未満の科目はありません'}
                </Typography>
              ) : (
                overview.weak_subjects.map(subject => (
                  <Box key={subject.subject_id} sx={{ mb: 2 }}>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography variant="body1">{subject.subject_name}</Typography>
                      <Chip
                        label={`${Math.round(subject.accuracy_rate * 100)}%`}
                        size="small"
                        color={subject.accuracy_rate < 0.5 ? 'error' : 'warning'}
                      />
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      解答数: {subject.answered_count}問
                    </Typography>
                  </Box>
                ))
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
              {overview.recommendations.length > 0 ? (
                overview.recommendations.map(rec => (
                  <Box key={`${rec.kind}-${rec.subject_id}`} sx={{ mb: 2 }}>
                    <Typography variant="body1">{rec.subject_name}</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {rec.reason}
                    </Typography>
                    <Button
                      size="small"
                      variant="text"
                      onClick={() => navigate(`/quiz?subject=${rec.subject_id}`)}
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
      )}

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
