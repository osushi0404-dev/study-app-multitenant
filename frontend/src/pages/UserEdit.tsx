import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Box,
  FormControlLabel,
  Checkbox,
  Alert,
  Snackbar,
  Grid,
  Divider,
  Chip,
} from '@mui/material';
import { useNavigate, useParams } from 'react-router-dom';
import apiClient from '../services/api';

interface UserData {
  id: string;
  email: string;
  user_id: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_admin: boolean;
  is_superuser: boolean;
  is_email_verified: boolean;
  last_login?: string;
  created_at: string;
  updated_at: string;
  failed_login_attempts: number;
  account_locked_until?: string;
}

interface UserEditFormData {
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_admin: boolean;
  is_superuser: boolean;
  password?: string;
  password_confirm?: string;
}

const UserEdit: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [userData, setUserData] = useState<UserData | null>(null);
  const [formData, setFormData] = useState<UserEditFormData>({
    email: '',
    first_name: '',
    last_name: '',
    is_active: true,
    is_admin: false,
    is_superuser: false,
  });
  const [changePassword, setChangePassword] = useState(false);
  const [errors, setErrors] = useState<Partial<UserEditFormData>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [snackbar, setSnackbar] = useState({ 
    open: false, 
    message: '', 
    severity: 'success' as 'success' | 'error' 
  });

  useEffect(() => {
    fetchUser();
  }, [id]);

  const fetchUser = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/api/admin/users/${id}/`);
      
      const user = response.data;
      setUserData(user);
      setFormData({
        email: user.email || '',
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        is_active: user.is_active,
        is_admin: user.is_admin,
        is_superuser: user.is_superuser,
      });
    } catch (error) {
      console.error('Failed to fetch user:', error);
      setSnackbar({ 
        open: true, 
        message: 'ユーザー情報の取得に失敗しました', 
        severity: 'error' 
      });
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field: keyof UserEditFormData) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = event.target.type === 'checkbox' 
      ? event.target.checked 
      : event.target.value;
    
    setFormData({
      ...formData,
      [field]: value,
    });
    
    // Clear error for this field
    if (errors[field]) {
      setErrors({
        ...errors,
        [field]: '',
      });
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Partial<UserEditFormData> = {};
    
    if (!formData.email) {
      newErrors.email = 'メールアドレスは必須です';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = '有効なメールアドレスを入力してください';
    }
    
    if (changePassword) {
      if (!formData.password) {
        newErrors.password = 'パスワードは必須です';
      } else if (formData.password.length < 8) {
        newErrors.password = 'パスワードは8文字以上で入力してください';
      }
      
      if (formData.password !== formData.password_confirm) {
        newErrors.password_confirm = 'パスワードが一致しません';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setSaving(true);
    
    try {
      const dataToSend = { ...formData };
      
      // Remove password fields if not changing password
      if (!changePassword) {
        delete dataToSend.password;
        delete dataToSend.password_confirm;
      }
      
      await apiClient.patch(
        `/api/admin/users/${id}/`,
        dataToSend
      );
      
      setSnackbar({
        open: true,
        message: 'ユーザー情報を更新しました',
        severity: 'success',
      });
      
      // Refresh user data
      fetchUser();
      setChangePassword(false);
    } catch (error: any) {
      console.error('Failed to update user:', error);
      
      if (error.response?.data?.error) {
        setSnackbar({
          open: true,
          message: error.response.data.error.main_message || 'ユーザー更新に失敗しました',
          severity: 'error',
        });
      } else {
        setSnackbar({
          open: true,
          message: 'ユーザー更新に失敗しました',
          severity: 'error',
        });
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        <Typography>読み込み中...</Typography>
      </Container>
    );
  }

  if (!userData) {
    return (
      <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="error">ユーザーが見つかりません</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          ユーザー編集
        </Typography>
        
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" color="text.secondary" gutterBottom>
            ユーザーID: {userData.user_id}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            {userData.is_email_verified && (
              <Chip label="メール認証済み" size="small" color="success" />
            )}
            {userData.failed_login_attempts >= 5 && (
              <Chip label="アカウントロック中" size="small" color="error" />
            )}
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">
                作成日時: {new Date(userData.created_at).toLocaleString('ja-JP')}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">
                最終ログイン: {userData.last_login 
                  ? new Date(userData.last_login).toLocaleString('ja-JP')
                  : '未ログイン'}
              </Typography>
            </Grid>
            {userData.account_locked_until && (
              <Grid item xs={12}>
                <Alert severity="warning">
                  アカウントは {new Date(userData.account_locked_until).toLocaleString('ja-JP')} までロックされています
                </Alert>
              </Grid>
            )}
          </Grid>
        </Box>
        
        <Divider sx={{ mb: 3 }} />
        
        <Box component="form" onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="メールアドレス *"
                type="email"
                value={formData.email}
                onChange={handleChange('email')}
                error={!!errors.email}
                helperText={errors.email}
                disabled={saving}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="姓"
                value={formData.last_name}
                onChange={handleChange('last_name')}
                disabled={saving}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="名"
                value={formData.first_name}
                onChange={handleChange('first_name')}
                disabled={saving}
              />
            </Grid>
            
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formData.is_active}
                      onChange={handleChange('is_active')}
                      disabled={saving}
                    />
                  }
                  label="アカウントを有効にする"
                />
                
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formData.is_admin}
                      onChange={handleChange('is_admin')}
                      disabled={saving}
                    />
                  }
                  label="管理者権限"
                />
                
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formData.is_superuser}
                      onChange={handleChange('is_superuser')}
                      disabled={saving || !formData.is_admin}
                    />
                  }
                  label="スーパーユーザー権限"
                />
              </Box>
            </Grid>
            
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={changePassword}
                    onChange={(e) => setChangePassword(e.target.checked)}
                    disabled={saving}
                  />
                }
                label="パスワードを変更する"
              />
            </Grid>
            
            {changePassword && (
              <>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="新しいパスワード *"
                    type="password"
                    value={formData.password || ''}
                    onChange={handleChange('password')}
                    error={!!errors.password}
                    helperText={errors.password}
                    disabled={saving}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="新しいパスワード（確認） *"
                    type="password"
                    value={formData.password_confirm || ''}
                    onChange={handleChange('password_confirm')}
                    error={!!errors.password_confirm}
                    helperText={errors.password_confirm}
                    disabled={saving}
                  />
                </Grid>
              </>
            )}
          </Grid>
          
          <Box sx={{ mt: 4, display: 'flex', gap: 2 }}>
            <Button
              variant="outlined"
              onClick={() => navigate('/admin/users')}
              disabled={saving}
            >
              戻る
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={saving}
            >
              {saving ? '保存中...' : '保存'}
            </Button>
          </Box>
        </Box>
      </Paper>
      
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert 
          onClose={() => setSnackbar({ ...snackbar, open: false })} 
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default UserEdit;