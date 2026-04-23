import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  CircularProgress,
  IconButton,
  InputAdornment,
} from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';

import { useAuth } from '../contexts/AuthContext';

interface LoginFormData {
  emailOrUserId: string;
  password: string;
}

const schema = yup.object({
  emailOrUserId: yup
    .string()
    .required('ユーザーIDまたはメールアドレスを入力してください'),
  password: yup
    .string()
    .min(8, 'パスワードは8文字以上で入力してください')
    .required('パスワードは必須です'),
});

const Login: React.FC = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const from = location.state?.from?.pathname || '/dashboard';

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: yupResolver(schema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setLoading(true);
    try {
      await login(data.emailOrUserId, data.password);
      navigate(from, { replace: true });
    } catch (error: any) {
      // Error handling is now done in AuthContext
      console.error('Login error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container component="main" maxWidth="sm">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            padding: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            width: '100%',
          }}
        >
          <Typography component="h1" variant="h4" gutterBottom>
            学習アプリ
          </Typography>

          <Typography component="h2" variant="h5" gutterBottom>
            ログイン
          </Typography>

          <Box component="form" onSubmit={handleSubmit(onSubmit)} sx={{ mt: 1, width: '100%' }}>
            <TextField
              margin="normal"
              fullWidth
              label="ユーザーIDまたはメールアドレス"
              autoComplete="username"
              autoFocus
              error={!!errors.emailOrUserId}
              helperText={errors.emailOrUserId?.message || '登録時のユーザーIDまたはメールアドレスを入力'}
              inputProps={{ 'data-testid': 'email-input' }}
              {...register('emailOrUserId')}
            />

            <TextField
              margin="normal"
              fullWidth
              label="パスワード"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              error={!!errors.password}
              helperText={errors.password?.message}
              inputProps={{ 'data-testid': 'password-input' }}
              {...register('password')}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
              data-testid="login-button"
            >
              {loading ? <CircularProgress size={24} /> : 'ログイン'}
            </Button>

            <Box sx={{ textAlign: 'center' }}>
              <Link to="/password-reset" style={{ textDecoration: 'none' }}>
                <Typography variant="body2" color="primary" sx={{ mb: 1 }}>
                  パスワードを忘れた方はこちら
                </Typography>
              </Link>

              <Link to="/register" style={{ textDecoration: 'none' }}>
                <Typography variant="body2" color="primary">
                  アカウントをお持ちでない方はこちら
                </Typography>
              </Link>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default Login;
