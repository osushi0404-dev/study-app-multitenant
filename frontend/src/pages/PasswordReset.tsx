import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  CircularProgress,
  Alert,
  IconButton,
  InputAdornment,
} from '@mui/material';
import { Visibility, VisibilityOff, ArrowBack } from '@mui/icons-material';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import toast from 'react-hot-toast';
import axios from 'axios';

interface PasswordResetRequestData {
  email: string;
}

interface PasswordResetConfirmData {
  newPassword: string;
  confirmPassword: string;
}

const requestSchema = yup.object({
  email: yup
    .string()
    .email('有効なメールアドレスを入力してください')
    .required('メールアドレスは必須です'),
});

const confirmSchema = yup.object({
  newPassword: yup
    .string()
    .min(8, 'パスワードは8文字以上で入力してください')
    .matches(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      'パスワードは大文字、小文字、数字を含む必要があります'
    )
    .required('パスワードは必須です'),
  confirmPassword: yup
    .string()
    .oneOf([yup.ref('newPassword')], 'パスワードが一致しません')
    .required('パスワード確認は必須です'),
});

const PasswordReset: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const isConfirmMode = !!token;

  const requestForm = useForm<PasswordResetRequestData>({
    resolver: yupResolver(requestSchema),
  });

  const confirmForm = useForm<PasswordResetConfirmData>({
    resolver: yupResolver(confirmSchema),
  });

  const onRequestSubmit = async (data: PasswordResetRequestData) => {
    setLoading(true);
    try {
      await axios.post('/api/auth/password-reset/', data);
      setEmailSent(true);
      toast.success('パスワードリセット用のメールを送信しました');
    } catch (error: any) {
      const message = error.response?.data?.message || 'メール送信に失敗しました';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const onConfirmSubmit = async (data: PasswordResetConfirmData) => {
    setLoading(true);
    try {
      await axios.post('/api/auth/password-reset-confirm/', {
        token,
        new_password: data.newPassword,
      });
      toast.success('パスワードがリセットされました');
      navigate('/login');
    } catch (error: any) {
      const message = error.response?.data?.message || 'パスワードリセットに失敗しました';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  if (emailSent && !isConfirmMode) {
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
            <Alert severity="success" sx={{ mb: 2, width: '100%' }}>
              パスワードリセット用のメールを送信しました。
              メール内のリンクをクリックして、新しいパスワードを設定してください。
            </Alert>

            <Button
              onClick={() => navigate('/login')}
              startIcon={<ArrowBack />}
              sx={{ mt: 2 }}
            >
              ログインページに戻る
            </Button>
          </Paper>
        </Box>
      </Container>
    );
  }

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
            {isConfirmMode ? '新しいパスワード設定' : 'パスワードリセット'}
          </Typography>

          {!isConfirmMode && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3, textAlign: 'center' }}>
              登録したメールアドレスを入力してください。
              パスワードリセット用のリンクをお送りします。
            </Typography>
          )}

          {isConfirmMode ? (
            <Box
              component="form"
              onSubmit={confirmForm.handleSubmit(onConfirmSubmit)}
              sx={{ mt: 1, width: '100%' }}
            >
              <TextField
                margin="normal"
                fullWidth
                label="新しいパスワード"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                error={!!confirmForm.formState.errors.newPassword}
                helperText={confirmForm.formState.errors.newPassword?.message}
                {...confirmForm.register('newPassword')}
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

              <TextField
                margin="normal"
                fullWidth
                label="パスワード確認"
                type={showConfirmPassword ? 'text' : 'password'}
                autoComplete="new-password"
                error={!!confirmForm.formState.errors.confirmPassword}
                helperText={confirmForm.formState.errors.confirmPassword?.message}
                {...confirmForm.register('confirmPassword')}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle confirm password visibility"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        edge="end"
                      >
                        {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
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
              >
                {loading ? <CircularProgress size={24} /> : 'パスワードを変更'}
              </Button>
            </Box>
          ) : (
            <Box
              component="form"
              onSubmit={requestForm.handleSubmit(onRequestSubmit)}
              sx={{ mt: 1, width: '100%' }}
            >
              <TextField
                margin="normal"
                fullWidth
                label="メールアドレス"
                type="email"
                autoComplete="email"
                autoFocus
                error={!!requestForm.formState.errors.email}
                helperText={requestForm.formState.errors.email?.message}
                {...requestForm.register('email')}
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={loading}
              >
                {loading ? <CircularProgress size={24} /> : 'リセットメールを送信'}
              </Button>
            </Box>
          )}

          <Button
            onClick={() => navigate('/login')}
            startIcon={<ArrowBack />}
            sx={{ mt: 1 }}
          >
            ログインページに戻る
          </Button>
        </Paper>
      </Box>
    </Container>
  );
};

export default PasswordReset;
