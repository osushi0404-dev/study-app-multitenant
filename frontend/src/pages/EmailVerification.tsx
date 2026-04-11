import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Box,
  Button,
  CircularProgress,
  Alert,
  TextField,
} from '@mui/material';
import { CheckCircle, Error, Email, Refresh } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-hot-toast';

const EmailVerification: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { verifyEmail, resendEmailVerification } = useAuth();

  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'expired' | 'resend'>('loading');
  const [email, setEmail] = useState('');
  const [resending, setResending] = useState(false);

  const token = searchParams.get('token');

  useEffect(() => {
    const handleVerification = async (verificationToken: string) => {
      try {
        setStatus('loading');
        await verifyEmail(verificationToken);
        setStatus('success');

        // Redirect to login page after successful verification
        setTimeout(() => {
          navigate('/login', {
            state: { message: 'メール認証が完了しました。ログインしてください。' }
          });
        }, 3000);
      } catch (error: any) {
        console.error('Email verification error:', error);

        // Check if token is expired or invalid
        if (error?.response?.status === 400) {
          setStatus('expired');
        } else {
          setStatus('error');
        }
      }
    };
    if (token) {
      handleVerification(token);
    } else {
      setStatus('resend');
    }
  }, [token, verifyEmail, navigate]);

  const handleResendVerification = async () => {
    if (!email.trim()) {
      toast.error('メールアドレスを入力してください');
      return;
    }

    try {
      setResending(true);
      await resendEmailVerification(email);
      toast.success('確認メールを再送信しました');
    } catch (error) {
      // Error is handled in AuthContext
      console.error('Resend verification error:', error);
    } finally {
      setResending(false);
    }
  };

  const renderContent = () => {
    switch (status) {
      case 'loading':
        return (
          <Box textAlign="center">
            <CircularProgress size={60} sx={{ mb: 3 }} />
            <Typography variant="h5" gutterBottom>
              メール認証を確認中...
            </Typography>
            <Typography variant="body2" color="text.secondary">
              しばらくお待ちください
            </Typography>
          </Box>
        );

      case 'success':
        return (
          <Box textAlign="center">
            <CheckCircle sx={{ fontSize: 80, color: 'success.main', mb: 2 }} />
            <Typography variant="h5" gutterBottom color="success.main">
              メール認証が完了しました！
            </Typography>
            <Typography variant="body1" sx={{ mb: 3 }}>
              アカウントが正常に認証されました。<br />
              まもなくログインページに移動します。
            </Typography>
            <Button
              variant="contained"
              onClick={() => navigate('/login')}
            >
              ログインページに移動
            </Button>
          </Box>
        );

      case 'error':
        return (
          <Box textAlign="center">
            <Error sx={{ fontSize: 80, color: 'error.main', mb: 2 }} />
            <Typography variant="h5" gutterBottom color="error.main">
              認証に失敗しました
            </Typography>
            <Typography variant="body1" sx={{ mb: 3 }}>
              メール認証の処理中にエラーが発生しました。<br />
              時間をおいて再度お試しください。
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
              <Button
                variant="outlined"
                onClick={() => setStatus('resend')}
              >
                確認メールを再送信
              </Button>
              <Button
                variant="contained"
                component={Link}
                to="/login"
              >
                ログインページに戻る
              </Button>
            </Box>
          </Box>
        );

      case 'expired':
        return (
          <Box textAlign="center">
            <Error sx={{ fontSize: 80, color: 'warning.main', mb: 2 }} />
            <Typography variant="h5" gutterBottom color="warning.main">
              認証リンクが無効です
            </Typography>
            <Typography variant="body1" sx={{ mb: 3 }}>
              認証リンクの有効期限が切れているか、<br />
              既に使用済みの可能性があります。
            </Typography>
            <Alert severity="info" sx={{ mb: 3 }}>
              新しい確認メールを送信することができます。
            </Alert>
            <Button
              variant="contained"
              startIcon={<Refresh />}
              onClick={() => setStatus('resend')}
            >
              確認メールを再送信
            </Button>
          </Box>
        );

      case 'resend':
        return (
          <Box textAlign="center">
            <Email sx={{ fontSize: 80, color: 'primary.main', mb: 2 }} />
            <Typography variant="h5" gutterBottom>
              メール認証確認
            </Typography>
            <Typography variant="body1" sx={{ mb: 3 }}>
              確認メールを再送信いたします。<br />
              登録時に使用したメールアドレスを入力してください。
            </Typography>

            <Box sx={{ mb: 3 }}>
              <TextField
                fullWidth
                label="メールアドレス"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="example@email.com"
                variant="outlined"
                sx={{ mb: 2 }}
              />
              <Button
                variant="contained"
                startIcon={<Email />}
                onClick={handleResendVerification}
                disabled={resending || !email.trim()}
                fullWidth
              >
                {resending ? (
                  <>
                    <CircularProgress size={20} sx={{ mr: 1 }} />
                    送信中...
                  </>
                ) : (
                  '確認メールを送信'
                )}
              </Button>
            </Box>

            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              メールが届かない場合は、迷惑メールフォルダもご確認ください。
            </Typography>

            <Button
              variant="text"
              component={Link}
              to="/login"
            >
              ログインページに戻る
            </Button>
          </Box>
        );

      default:
        return null;
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
          <Typography component="h1" variant="h4" gutterBottom textAlign="center">
            学習アプリ
          </Typography>

          {renderContent()}
        </Paper>
      </Box>
    </Container>
  );
};

export default EmailVerification;
