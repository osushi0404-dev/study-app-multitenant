/**
 * パスキーの登録・削除の前の「本人の確認」のダイアログ（I619）
 * パスキーがあるときは「パスキーで確かめる」、どちらのときもパスワードで確かめられる
 */
import { useState } from 'react';
import {
  Alert,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  TextField,
} from '@mui/material';
import { Key } from '@mui/icons-material';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';

import passkeyService, { getPasskeyAssertion } from '../../services/passkey.service';
import { ReauthToken } from '../../types/api';
import { apiErrorText, PASSKEY_VERIFY_FAILED } from '../../utils/passkeyErrors';

const REAUTH_FAILED = '本人の確認ができませんでした。時間をおいてもう一度お試しください';
const schema = yup.object({ password: yup.string().required('パスワードを入力してください') });
type FormValues = yup.InferType<typeof schema>;

type Props = {
  open: boolean;
  hasPasskeys: boolean;
  onSuccess: (result: ReauthToken) => void;
  onCancel: () => void;
};

function PasskeyReauthDialog({ open, hasPasskeys, onSuccess, onCancel }: Props) {
  const [passkeyBusy, setPasskeyBusy] = useState(false);
  const [passkeyError, setPasskeyError] = useState<string | null>(null);
  const { register, handleSubmit, setError, reset, formState } = useForm<FormValues>({
    resolver: yupResolver(schema),
    mode: 'onTouched',
  });

  const clear = () => {
    reset();
    setPasskeyError(null);
  };

  const finish = (result: ReauthToken) => {
    clear();
    onSuccess(result);
  };

  const close = () => {
    clear();
    onCancel();
  };

  const submitPassword = async ({ password }: FormValues) => {
    try {
      finish(await passkeyService.reauthWithPassword(password));
    } catch (error) {
      // 400（誤り・ロック）はサーバーの文。それ以外（回数の制限・通信の失敗）は決まった文
      setError('password', { message: apiErrorText(error, REAUTH_FAILED) });
    }
  };

  const confirmWithPasskey = async () => {
    setPasskeyBusy(true);
    setPasskeyError(null);
    try {
      const options = await passkeyService.reauthOptions();
      const credential = await getPasskeyAssertion(options);
      finish(await passkeyService.reauthWithPasskey(options.challenge_id, credential));
    } catch (error) {
      setPasskeyError(apiErrorText(error, PASSKEY_VERIFY_FAILED));
    } finally {
      setPasskeyBusy(false);
    }
  };

  const busy = passkeyBusy || formState.isSubmitting;

  return (
    <Dialog open={open} onClose={close} fullWidth maxWidth="xs" aria-labelledby="passkey-reauth-title">
      <DialogTitle id="passkey-reauth-title">本人の確認</DialogTitle>
      <form onSubmit={handleSubmit(submitPassword)} noValidate>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>続けるには、本人であることを確かめます</DialogContentText>
          {hasPasskeys && (
            <>
              <Button
                fullWidth
                variant="contained"
                startIcon={passkeyBusy ? undefined : <Key />}
                onClick={confirmWithPasskey}
                disabled={busy}
                sx={{ minHeight: 44 }}
              >
                {passkeyBusy ? <CircularProgress size={24} aria-label="確かめています" /> : 'パスキーで確かめる'}
              </Button>
              {passkeyError && (
                <Alert severity="error" role="alert" sx={{ mt: 1 }}>
                  {passkeyError}
                </Alert>
              )}
              <Divider sx={{ my: 2 }}>または</Divider>
            </>
          )}
          <TextField
            fullWidth
            type="password"
            label="パスワード"
            autoComplete="current-password"
            error={!!formState.errors.password}
            helperText={formState.errors.password?.message}
            {...register('password')}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={close} sx={{ minHeight: 44 }}>
            キャンセル
          </Button>
          <Button type="submit" variant={hasPasskeys ? 'outlined' : 'contained'} disabled={busy} sx={{ minHeight: 44 }}>
            確かめる
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}

export default PasskeyReauthDialog;
