/**
 * 登録用リンクで開く、パスキーの登録画面（ログイン不要・I620）
 *
 * - リンクの値は URL の # の後ろ（サーバーのログ・Referer に載らない）。読んだらすぐアドレスバーから消す
 * - 値は画面のメモリにだけ置く（保存領域・console に置かない）
 * - 開いたときに options でリンクが使えるかを確かめ、［パスキーを登録］のたびに challenge を取り直す
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useQuery } from '@tanstack/react-query';
import { browserSupportsWebAuthn } from '@simplewebauthn/browser';
import { Alert, Box, Button, Card, CardContent, CircularProgress, Stack, Typography } from '@mui/material';
import { Key } from '@mui/icons-material';

import { useAuth } from '../contexts/AuthContext';
import { createPasskeyCredential } from '../services/passkey.service';
import { registrationLinkService } from '../services/member.service';
import { MULTI_DEVICE_GUIDE, PASSKEY_UNSUPPORTED, registrationErrorText } from '../utils/passkeyErrors';

export const LINK_UNUSABLE = 'このリンクは使えません。管理者に新しいリンクを発行してもらってください';

const tokenFromHash = (hash: string): string | null => {
  const value = new URLSearchParams(hash.replace(/^#/, '')).get('token');
  return value && value.length > 0 ? value : null;
};

function PasskeySetup() {
  const navigate = useNavigate();
  const { completeRegistrationLink } = useAuth();
  const [token] = useState(() => tokenFromHash(window.location.hash));
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const initialUsed = useRef(false);
  const supported = browserSupportsWebAuthn();

  useEffect(() => {
    if (window.location.hash) {
      window.history.replaceState(window.history.state, '', window.location.pathname);
    }
  }, []);

  const options = useQuery({
    queryKey: ['registration-link-options', token],
    queryFn: () => registrationLinkService.options(token as string),
    enabled: token !== null,
    retry: false,
    staleTime: Infinity,
    gcTime: 0,
    refetchOnWindowFocus: false,
  });

  const handleRegister = async () => {
    if (!token) return;
    setRegistering(true);
    setError(null);
    try {
      // 最初は開いたときの options（challenge）を使い、失敗の後のやり直しだけ取り直す
      const fresh = !initialUsed.current && options.data ? options.data : await registrationLinkService.options(token);
      initialUsed.current = true;
      const credential = await createPasskeyCredential(fresh);
      await completeRegistrationLink({ token, challengeId: fresh.challenge_id, credential });
      toast.success('パスキーを登録しました');
      navigate('/dashboard', { replace: true });
    } catch (caught) {
      setError(registrationErrorText(caught));
    } finally {
      setRegistering(false);
    }
  };

  const renderBody = () => {
    if (token === null || options.isError) {
      return <Alert severity="error">{LINK_UNUSABLE}</Alert>;
    }
    if (options.isPending) {
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CircularProgress size={20} />
          <Typography>リンクを確かめています</Typography>
        </Box>
      );
    }
    return (
      <Stack spacing={2}>
        <Typography>ユーザーID『{options.data.user_id}』のパスキーを登録します</Typography>
        <Alert severity="info">{MULTI_DEVICE_GUIDE}</Alert>
        {error && <Alert severity="error" role="alert">{error}</Alert>}
        <Button
          variant="contained"
          startIcon={registering ? undefined : <Key />}
          onClick={handleRegister}
          disabled={!supported || registering}
          sx={{ minHeight: 44 }}
        >
          {registering ? <CircularProgress size={20} aria-label="登録しています" /> : 'パスキーを登録'}
        </Button>
        {!supported && (
          <Typography variant="body2" color="text.secondary">{PASSKEY_UNSUPPORTED}</Typography>
        )}
      </Stack>
    );
  };

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', p: { xs: 1, sm: 4 } }}>
      <Card sx={{ width: { xs: '100%', sm: 480 } }}>
        <CardContent>
          <Typography variant="h5" component="h1" gutterBottom>
            パスキーの登録
          </Typography>
          {renderBody()}
        </CardContent>
      </Card>
    </Box>
  );
}

export default PasskeySetup;
