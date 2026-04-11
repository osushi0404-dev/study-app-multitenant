import React, { useState } from 'react';
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
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import apiClient from '../services/api';

interface UserFormData {
  email: string;
  user_id: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
  is_admin: boolean;
  is_superuser: boolean;
  is_active: boolean;
}

const UserCreate: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<UserFormData>({
    email: '',
    user_id: '',
    password: '',
    password_confirm: '',
    first_name: '',
    last_name: '',
    is_admin: false,
    is_superuser: false,
    is_active: true,
  });
  const [errors, setErrors] = useState<Partial<UserFormData>>({});
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error'
  });

  const handleChange = (field: keyof UserFormData) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = event.target.type === 'checkbox'
      ? event.target.checked
      : event.target.value;

    setFormData({
      ...formData,
      // eslint-disable-next-line security/detect-object-injection
      [field]: value,
    });

    // Clear error for this field
    // eslint-disable-next-line security/detect-object-injection
    if (errors[field]) {
      setErrors({
        ...errors,
        // eslint-disable-next-line security/detect-object-injection
        [field]: '',
      });
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Partial<UserFormData> = {};

    if (!formData.user_id) {
      newErrors.user_id = 'ユーザーIDは必須です';
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.user_id)) {
      newErrors.user_id = 'ユーザーIDは半角英数字とアンダースコアのみ使用できます';
    } else if (formData.user_id.length < 3 || formData.user_id.length > 30) {
      newErrors.user_id = 'ユーザーIDは3〜30文字で入力してください';
    }

    if (!formData.email) {
      newErrors.email = 'メールアドレスは必須です';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = '有効なメールアドレスを入力してください';
    }

    if (!formData.password) {
      newErrors.password = 'パスワードは必須です';
    } else if (formData.password.length < 8) {
      newErrors.password = 'パスワードは8文字以上で入力してください';
    }

    if (formData.password !== formData.password_confirm) {
      newErrors.password_confirm = 'パスワードが一致しません';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      await apiClient.post(
        '/api/admin/users/',
        formData
      );

      setSnackbar({
        open: true,
        message: 'ユーザーを作成しました',
        severity: 'success',
      });

      // Redirect to user list after a short delay
      setTimeout(() => {
        navigate('/admin/users');
      }, 1500);
    } catch (error: any) {
      console.error('Failed to create user:', error);

      if (error.response?.data?.error) {
        setSnackbar({
          open: true,
          message: error.response.data.error.main_message || 'ユーザー作成に失敗しました',
          severity: 'error',
        });

        // Set field-specific errors if available
        if (error.response.data.error.details) {
          const fieldErrors: Partial<UserFormData> = {};
          Object.keys(error.response.data.error.details).forEach(key => {
            // eslint-disable-next-line security/detect-object-injection
            const errorMessages = error.response.data.error.details[key];
            if (Array.isArray(errorMessages) && errorMessages.length > 0) {
              fieldErrors[key as keyof UserFormData] = errorMessages[0];
            }
          });
          setErrors(fieldErrors);
        }
      } else {
        setSnackbar({
          open: true,
          message: 'ユーザー作成に失敗しました',
          severity: 'error',
        });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          新規ユーザー作成
        </Typography>

        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="ユーザーID *"
                value={formData.user_id}
                onChange={handleChange('user_id')}
                error={!!errors.user_id}
                helperText={errors.user_id}
                disabled={loading}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="メールアドレス *"
                type="email"
                value={formData.email}
                onChange={handleChange('email')}
                error={!!errors.email}
                helperText={errors.email}
                disabled={loading}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="姓"
                value={formData.last_name}
                onChange={handleChange('last_name')}
                disabled={loading}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="名"
                value={formData.first_name}
                onChange={handleChange('first_name')}
                disabled={loading}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="パスワード *"
                type="password"
                value={formData.password}
                onChange={handleChange('password')}
                error={!!errors.password}
                helperText={errors.password}
                disabled={loading}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="パスワード（確認） *"
                type="password"
                value={formData.password_confirm}
                onChange={handleChange('password_confirm')}
                error={!!errors.password_confirm}
                helperText={errors.password_confirm}
                disabled={loading}
              />
            </Grid>

            <Grid item xs={12}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formData.is_active}
                      onChange={handleChange('is_active')}
                      disabled={loading}
                    />
                  }
                  label="アカウントを有効にする"
                />

                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formData.is_admin}
                      onChange={handleChange('is_admin')}
                      disabled={loading}
                    />
                  }
                  label="管理者権限を付与"
                />

                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formData.is_superuser}
                      onChange={handleChange('is_superuser')}
                      disabled={loading || !formData.is_admin}
                    />
                  }
                  label="スーパーユーザー権限を付与"
                />
              </Box>
            </Grid>
          </Grid>

          <Box sx={{ mt: 4, display: 'flex', gap: 2 }}>
            <Button
              variant="outlined"
              onClick={() => navigate('/admin/users')}
              disabled={loading}
            >
              キャンセル
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={loading}
            >
              {loading ? '作成中...' : '作成'}
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

export default UserCreate;
