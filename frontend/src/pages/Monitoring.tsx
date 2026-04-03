import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Typography,
  Paper,
  Grid,
  Box,
  Card,
  CardContent,
  IconButton,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Alert,
  AlertTitle,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Tooltip
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  CheckCircle as CheckCircleIcon,
  Computer as ComputerIcon,
  Storage as StorageIcon,
  Speed as SpeedIcon,
  ClearAll as ClearAllIcon
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import apiService from '../services/api';

interface HealthData {
  overall_status: 'healthy' | 'warning' | 'error';
  timestamp: string;
  database: {
    status: string;
    response_time_ms: number;
    active_connections: number;
  };
  redis: {
    status: string;
    response_time_ms: number;
    used_memory?: string;
    connected_clients?: number;
  };
  system: {
    status: string;
    cpu_percent: number;
    memory_percent: number;
    memory_available_gb: number;
    disk_percent: number;
    disk_free_gb: number;
  };
}

interface ErrorSummary {
  total_errors: number;
  daily_counts: { [date: string]: number };
  error_types: { [type: string]: number };
  period_days: number;
}

interface MonitoringAlert {
  type: string;
  severity: 'warning' | 'critical';
  message: string;
  details: any;
}

const Monitoring: React.FC = () => {
  const [healthData, setHealthData] = useState<HealthData | null>(null);
  const [errorSummary, setErrorSummary] = useState<ErrorSummary | null>(null);
  const [alerts, setAlerts] = useState<MonitoringAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [clearCacheDialogOpen, setClearCacheDialogOpen] = useState(false);
  const [clearingCache, setClearingCache] = useState(false);

  const fetchMonitoringData = useCallback(async () => {
    try {
      setRefreshing(true);

      const [healthResponse, errorsResponse, alertsResponse] = await Promise.all([
        apiService.get('/health/'),
        apiService.get('/monitoring/errors/?days=7'),
        apiService.get('/monitoring/alerts/')
      ]);

      setHealthData(healthResponse.data);
      setErrorSummary(errorsResponse.data);
      setAlerts(alertsResponse.data.alerts || []);

    } catch (error) {
      console.error('Failed to fetch monitoring data:', error);
      toast.error('監視データの取得に失敗しました');
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }, []);

  const handleClearCache = async () => {
    try {
      setClearingCache(true);
      
      await apiService.post('/cache/clear/', {
        types: ['all']
      });
      
      toast.success('キャッシュをクリアしました');
      setClearCacheDialogOpen(false);
      
    } catch (error) {
      console.error('Failed to clear cache:', error);
      toast.error('キャッシュのクリアに失敗しました');
    } finally {
      setClearingCache(false);
    }
  };

  useEffect(() => {
    fetchMonitoringData();

    // 30秒ごとに自動更新
    const interval = setInterval(fetchMonitoringData, 30000);

    return () => clearInterval(interval);
  }, [fetchMonitoringData]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'success';
      case 'warning': return 'warning';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircleIcon color="success" />;
      case 'warning': return <WarningIcon color="warning" />;
      case 'error': return <ErrorIcon color="error" />;
      default: return <ComputerIcon />;
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* ヘッダー */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          システム監視ダッシュボード
        </Typography>
        <Box>
          <Tooltip title="キャッシュクリア">
            <IconButton 
              onClick={() => setClearCacheDialogOpen(true)}
              disabled={refreshing}
            >
              <ClearAllIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="更新">
            <IconButton 
              onClick={fetchMonitoringData}
              disabled={refreshing}
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* 全体ステータス */}
      {healthData && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Box display="flex" alignItems="center" gap={2} mb={2}>
            {getStatusIcon(healthData.overall_status)}
            <Typography variant="h5">
              システム全体: {healthData.overall_status}
            </Typography>
            <Chip 
              label={`最終更新: ${new Date(healthData.timestamp).toLocaleString()}`}
              size="small"
              variant="outlined"
            />
          </Box>
          
          {refreshing && <LinearProgress sx={{ mb: 2 }} />}
        </Paper>
      )}

      {/* アラート */}
      {alerts.length > 0 && (
        <Box mb={3}>
          {alerts.map((alert, index) => (
            <Alert 
              key={index}
              severity={alert.severity === 'critical' ? 'error' : alert.severity as any}
              sx={{ mb: 1 }}
            >
              <AlertTitle>{alert.type}</AlertTitle>
              {alert.message}
            </Alert>
          ))}
        </Box>
      )}

      {/* システムメトリクス */}
      {healthData && (
        <Grid container spacing={3} mb={3}>
          {/* データベース */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <StorageIcon />
                  <Typography variant="h6">データベース</Typography>
                  <Chip 
                    label={healthData.database.status}
                    color={getStatusColor(healthData.database.status) as any}
                    size="small"
                  />
                </Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  レスポンス時間: {healthData.database.response_time_ms}ms
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  アクティブ接続: {healthData.database.active_connections}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Redis */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <SpeedIcon />
                  <Typography variant="h6">Redis</Typography>
                  <Chip 
                    label={healthData.redis.status}
                    color={getStatusColor(healthData.redis.status) as any}
                    size="small"
                  />
                </Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  レスポンス時間: {healthData.redis.response_time_ms}ms
                </Typography>
                {healthData.redis.used_memory && (
                  <Typography variant="body2" color="text.secondary">
                    使用メモリ: {healthData.redis.used_memory}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* システムリソース */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <ComputerIcon />
                  <Typography variant="h6">システム</Typography>
                  <Chip 
                    label={healthData.system.status}
                    color={getStatusColor(healthData.system.status) as any}
                    size="small"
                  />
                </Box>
                <Box mb={1}>
                  <Typography variant="body2" color="text.secondary">
                    CPU: {healthData.system.cpu_percent}%
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={healthData.system.cpu_percent}
                    color={healthData.system.cpu_percent > 80 ? 'error' : 'primary'}
                    sx={{ mt: 0.5 }}
                  />
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    メモリ: {healthData.system.memory_percent}% 
                    (空き: {healthData.system.memory_available_gb}GB)
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={healthData.system.memory_percent}
                    color={healthData.system.memory_percent > 80 ? 'error' : 'primary'}
                    sx={{ mt: 0.5 }}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* エラーサマリー */}
      {errorSummary && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            エラーサマリー (過去{errorSummary.period_days}日)
          </Typography>
          
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Box>
                <Typography variant="h4" color="error.main">
                  {errorSummary.total_errors}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  合計エラー数
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" gutterBottom>
                日別エラー数
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>日付</TableCell>
                      <TableCell align="right">エラー数</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Object.entries(errorSummary.daily_counts)
                      .sort(([a], [b]) => b.localeCompare(a))
                      .slice(0, 7)
                      .map(([date, count]) => (
                      <TableRow key={date}>
                        <TableCell>{date}</TableCell>
                        <TableCell align="right">{count}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* キャッシュクリアダイアログ */}
      <Dialog open={clearCacheDialogOpen} onClose={() => setClearCacheDialogOpen(false)}>
        <DialogTitle>キャッシュクリア</DialogTitle>
        <DialogContent>
          <Typography>
            全てのキャッシュをクリアしますか？
            この操作により、一時的にパフォーマンスが低下する可能性があります。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setClearCacheDialogOpen(false)}>
            キャンセル
          </Button>
          <Button 
            onClick={handleClearCache}
            disabled={clearingCache}
            color="error"
          >
            {clearingCache ? 'クリア中...' : 'クリア'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Monitoring;