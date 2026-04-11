import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Switch,
  FormControl,
  FormControlLabel,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Divider,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  InputAdornment,
  Chip,
} from '@mui/material';
import { Visibility, VisibilityOff, Save, Security } from '@mui/icons-material';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import toast from 'react-hot-toast';
import axios from 'axios';

import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { useNotifications } from '../contexts/NotificationContext';
import dashboardService from '../services/dashboard.service';
import { UserSettings } from '../services/types';

interface UserSettingsData {
  dailyStudyGoalMinutes: number;
  studyRemindersEnabled: boolean;
  reminderTime: string;
  themePreference: 'light' | 'dark' | 'auto';
  notificationSettings: {
    email: boolean;
    push: boolean;
    achievements: boolean;
    reminders: boolean;
  };
}

interface PasswordChangeData {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

const settingsSchema = yup.object({
  dailyStudyGoalMinutes: yup
    .number()
    .min(5, '最低5分から設定できます')
    .max(480, '最大8時間まで設定できます')
    .required('学習目標時間は必須です'),
  studyRemindersEnabled: yup.boolean().required(),
  reminderTime: yup.string().required(),
  themePreference: yup.string().oneOf(['light', 'dark', 'auto']).required(),
  notificationSettings: yup.object({
    email: yup.boolean().required(),
    push: yup.boolean().required(),
    achievements: yup.boolean().required(),
    reminders: yup.boolean().required(),
  }).required(),
});

const passwordSchema = yup.object({
  currentPassword: yup.string().required('現在のパスワードは必須です'),
  newPassword: yup
    .string()
    .min(8, 'パスワードは8文字以上で入力してください')
    .matches(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      'パスワードは大文字、小文字、数字を含む必要があります'
    )
    .required('新しいパスワードは必須です'),
  confirmPassword: yup
    .string()
    .oneOf([yup.ref('newPassword')], 'パスワードが一致しません')
    .required('パスワード確認は必須です'),
});

const Settings: React.FC = () => {
  const [settings, setSettings] = useState<UserSettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const { user } = useAuth();
  const { darkMode, toggleDarkMode } = useTheme();
  const {
    permission,
    isEnabled,
    requestPermission,
    scheduleReminders,
    testNotification,
    activeRemindersCount
  } = useNotifications();

  const settingsForm = useForm({
    resolver: yupResolver(settingsSchema),
  });
  const { reset: resetSettingsForm } = settingsForm;

  const passwordForm = useForm<PasswordChangeData>({
    resolver: yupResolver(passwordSchema),
  });

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const userSettings = await dashboardService.getUserSettings();

        const settingsData: UserSettingsData = {
          dailyStudyGoalMinutes: userSettings.daily_study_goal,
          studyRemindersEnabled: userSettings.study_reminder_enabled,
          reminderTime: userSettings.study_reminder_time || '09:00',
          themePreference: userSettings.theme,
          notificationSettings: {
            email: userSettings.email_notifications,
            push: userSettings.push_notifications,
            achievements: true,
            reminders: userSettings.study_reminder_enabled,
          },
        };

        setSettings(settingsData);
        resetSettingsForm(settingsData);
      } catch (error) {
        console.error('Error loading settings:', error);
        toast.error('設定の読み込みに失敗しました');
      } finally {
        setLoading(false);
      }
    };
    loadSettings();
  }, [resetSettingsForm]);

  const onSettingsSubmit = async (data: UserSettingsData) => {
    setSaving(true);
    try {
      const submitData: Partial<UserSettings> = {
        daily_study_goal: data.dailyStudyGoalMinutes,
        study_reminder_enabled: data.studyRemindersEnabled,
        study_reminder_time: data.reminderTime, // HH:MM format
        theme: data.themePreference as 'light' | 'dark',
        email_notifications: data.notificationSettings.email,
        push_notifications: data.notificationSettings.push,
      };

      const updatedSettings = await dashboardService.updateUserSettings(submitData);

      // Update notification reminders if enabled
      if (data.studyRemindersEnabled && isEnabled) {
        scheduleReminders(updatedSettings);
      }

      setSettings(data);
      toast.success('設定を保存しました');
    } catch (error) {
      console.error('Error saving settings:', error);
      toast.error('設定の保存に失敗しました');
    } finally {
      setSaving(false);
    }
  };

  const onPasswordSubmit = async (data: PasswordChangeData) => {
    try {
      await axios.post('/api/auth/change-password/', {
        current_password: data.currentPassword,
        new_password: data.newPassword,
        confirm_password: data.confirmPassword,
      });

      setPasswordDialogOpen(false);
      passwordForm.reset();
      toast.success('パスワードを変更しました');
    } catch (error: any) {
      const message = error.response?.data?.message || 'パスワード変更に失敗しました';
      toast.error(message);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        設定
      </Typography>

      <Grid container spacing={3}>
          {/* User Information */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  アカウント情報
                </Typography>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    メールアドレス
                  </Typography>
                  <Typography variant="body1">{user?.email}</Typography>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    役割
                  </Typography>
                  <Typography variant="body1">
                    {user?.role === 'admin' ? '管理者' : 'ユーザー'}
                  </Typography>
                </Box>

                <Button
                  variant="outlined"
                  startIcon={<Security />}
                  onClick={() => setPasswordDialogOpen(true)}
                >
                  パスワード変更
                </Button>
              </CardContent>
            </Card>
          </Grid>

          {/* Study Settings */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  学習設定
                </Typography>

                <Box component="form" onSubmit={settingsForm.handleSubmit(onSettingsSubmit as any)}>
                  <TextField
                    fullWidth
                    label="1日の学習目標時間（分）"
                    type="number"
                    margin="normal"
                    {...settingsForm.register('dailyStudyGoalMinutes')}
                    error={!!settingsForm.formState.errors.dailyStudyGoalMinutes}
                    helperText={settingsForm.formState.errors.dailyStudyGoalMinutes?.message}
                  />

                  <FormControlLabel
                    control={
                      <Switch
                        {...settingsForm.register('studyRemindersEnabled')}
                        checked={settingsForm.watch('studyRemindersEnabled')}
                      />
                    }
                    label="学習リマインダーを有効にする"
                    sx={{ mt: 2, mb: 1 }}
                  />

                  {settingsForm.watch('studyRemindersEnabled') && (
                    <TextField
                      fullWidth
                      label="リマインダー時刻"
                      type="time"
                      {...settingsForm.register('reminderTime')}
                      error={!!settingsForm.formState.errors.reminderTime}
                      helperText={settingsForm.formState.errors.reminderTime?.message}
                      margin="normal"
                      InputLabelProps={{ shrink: true }}
                    />
                  )}

                  <Button
                    type="submit"
                    variant="contained"
                    startIcon={<Save />}
                    disabled={saving}
                    sx={{ mt: 2 }}
                  >
                    {saving ? <CircularProgress size={20} /> : '保存'}
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Appearance Settings */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  表示設定
                </Typography>

                <FormControlLabel
                  control={
                    <Switch
                      checked={darkMode}
                      onChange={toggleDarkMode}
                    />
                  }
                  label="ダークモード"
                  sx={{ mb: 2 }}
                />

                <FormControl fullWidth margin="normal">
                  <InputLabel>テーマ設定</InputLabel>
                  <Select
                    {...settingsForm.register('themePreference')}
                    value={settingsForm.watch('themePreference') || 'light'}
                    label="テーマ設定"
                  >
                    <MenuItem value="light">ライト</MenuItem>
                    <MenuItem value="dark">ダーク</MenuItem>
                    <MenuItem value="auto">自動</MenuItem>
                  </Select>
                </FormControl>
              </CardContent>
            </Card>
          </Grid>

          {/* Notification Settings */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  通知設定
                </Typography>

                {/* Browser Notification Permission */}
                <Box sx={{ mb: 3, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    ブラウザ通知の許可状況
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      現在の状態:
                    </Typography>
                    <Chip
                      label={
                        permission === 'granted' ? '許可済み' :
                        permission === 'denied' ? '拒否' : '未設定'
                      }
                      color={
                        permission === 'granted' ? 'success' :
                        permission === 'denied' ? 'error' : 'default'
                      }
                      size="small"
                    />
                  </Box>

                  {permission !== 'granted' && (
                    <Box sx={{ mb: 2 }}>
                      <Alert severity="info" sx={{ mb: 1 }}>
                        ブラウザ通知を有効にすると、学習リマインダーやお知らせを受け取れます。
                      </Alert>
                      <Button
                        variant="outlined"
                        size="small"
                        onClick={requestPermission}
                      >
                        通知を有効にする
                      </Button>
                    </Box>
                  )}

                  {isEnabled && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" color="text.secondary">
                        アクティブなリマインダー: {activeRemindersCount}件
                      </Typography>
                      <Button
                        variant="text"
                        size="small"
                        onClick={testNotification}
                      >
                        テスト通知
                      </Button>
                    </Box>
                  )}
                </Box>

                <Divider sx={{ mb: 2 }} />

                <FormControlLabel
                  control={
                    <Switch
                      checked={settings?.notificationSettings?.email || false}
                      onChange={(e) => {
                        const current = settingsForm.getValues('notificationSettings');
                        const updated = {
                          ...current,
                          email: e.target.checked,
                        };
                        settingsForm.setValue('notificationSettings', updated);
                      }}
                    />
                  }
                  label="メール通知"
                  sx={{ display: 'block', mb: 1 }}
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={settings?.notificationSettings?.push || false}
                      onChange={(e) => {
                        const current = settingsForm.getValues('notificationSettings');
                        const updated = {
                          ...current,
                          push: e.target.checked,
                        };
                        settingsForm.setValue('notificationSettings', updated);
                      }}
                      disabled={!isEnabled}
                    />
                  }
                  label={
                    <Box>
                      <Typography>ブラウザ通知</Typography>
                      {!isEnabled && (
                        <Typography variant="caption" color="text.secondary">
                          ブラウザ通知の許可が必要です
                        </Typography>
                      )}
                    </Box>
                  }
                  sx={{ display: 'block', mb: 1 }}
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={settings?.notificationSettings?.achievements || false}
                      onChange={(e) => {
                        const current = settingsForm.getValues('notificationSettings');
                        const updated = {
                          ...current,
                          achievements: e.target.checked,
                        };
                        settingsForm.setValue('notificationSettings', updated);
                      }}
                      disabled={!isEnabled}
                    />
                  }
                  label="達成・記録更新通知"
                  sx={{ display: 'block', mb: 1 }}
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={settings?.notificationSettings?.reminders || false}
                      onChange={(e) => {
                        const current = settingsForm.getValues('notificationSettings');
                        const updated = {
                          ...current,
                          reminders: e.target.checked,
                        };
                        settingsForm.setValue('notificationSettings', updated);
                      }}
                      disabled={!isEnabled}
                    />
                  }
                  label="学習リマインダー通知"
                  sx={{ display: 'block' }}
                />
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Password Change Dialog */}
        <Dialog
          open={passwordDialogOpen}
          onClose={() => setPasswordDialogOpen(false)}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>パスワード変更</DialogTitle>
          <DialogContent>
            <Box component="form" onSubmit={passwordForm.handleSubmit(onPasswordSubmit)}>
              <TextField
                fullWidth
                label="現在のパスワード"
                type={showCurrentPassword ? 'text' : 'password'}
                margin="normal"
                {...passwordForm.register('currentPassword')}
                error={!!passwordForm.formState.errors.currentPassword}
                helperText={passwordForm.formState.errors.currentPassword?.message}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                        edge="end"
                      >
                        {showCurrentPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <TextField
                fullWidth
                label="新しいパスワード"
                type={showNewPassword ? 'text' : 'password'}
                margin="normal"
                {...passwordForm.register('newPassword')}
                error={!!passwordForm.formState.errors.newPassword}
                helperText={passwordForm.formState.errors.newPassword?.message}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowNewPassword(!showNewPassword)}
                        edge="end"
                      >
                        {showNewPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <TextField
                fullWidth
                label="パスワード確認"
                type={showConfirmPassword ? 'text' : 'password'}
                margin="normal"
                {...passwordForm.register('confirmPassword')}
                error={!!passwordForm.formState.errors.confirmPassword}
                helperText={passwordForm.formState.errors.confirmPassword?.message}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        edge="end"
                      >
                        {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setPasswordDialogOpen(false)}>
              キャンセル
            </Button>
            <Button
              onClick={passwordForm.handleSubmit(onPasswordSubmit)}
              variant="contained"
            >
              変更
            </Button>
          </DialogActions>
        </Dialog>
    </Box>
  );
};

export default Settings;
