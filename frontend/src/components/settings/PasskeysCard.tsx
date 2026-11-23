/**
 * 設定画面の「パスキー」の欄（I619）
 *
 * - 一覧（名前・登録日・最後に使った日）・登録・名前の変更・削除
 * - 登録・削除の前に本人の確認（5 分以内に確かめていれば出ない・usePasskeyReauth）
 * - 削除は確認のダイアログ → 本人の確認 → 削除
 */
import { useState } from 'react';
import toast from 'react-hot-toast';
import { browserSupportsWebAuthn } from '@simplewebauthn/browser';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Skeleton,
  Typography,
} from '@mui/material';
import { Add, Delete, Edit } from '@mui/icons-material';

import { useAuth } from '../../contexts/AuthContext';
import { usePasskeys } from '../../hooks/usePasskeys';
import { ReauthCancelledError, usePasskeyReauth } from '../../hooks/usePasskeyReauth';
import { Passkey } from '../../types/api';
import {
  apiErrorText,
  PASSKEY_DELETE_FAILED,
  PASSKEY_UNSUPPORTED,
  registrationErrorText,
} from '../../utils/passkeyErrors';
import PasskeyReauthDialog from './PasskeyReauthDialog';
import PasskeyRenameDialog from './PasskeyRenameDialog';

const formatDate = (value: string) =>
  new Intl.DateTimeFormat('ja-JP', { timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit' })
    .format(new Date(value));

function PasskeysCard() {
  const { user } = useAuth();
  const { list, register, rename, remove } = usePasskeys(user?.id ?? '');
  const reauth = usePasskeyReauth();
  const supported = browserSupportsWebAuthn();
  const [renaming, setRenaming] = useState<Passkey | null>(null);
  const [deleting, setDeleting] = useState<Passkey | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const passkeys = list.status === 'success' ? list.data : [];

  const handleRegister = async () => {
    setActionError(null);
    try {
      await reauth.withReauth((token) => register.mutateAsync(token));
      toast.success('パスキーを登録しました');
    } catch (error) {
      if (!(error instanceof ReauthCancelledError)) setActionError(registrationErrorText(error));
    }
  };

  const handleDelete = async () => {
    const target = deleting;
    setDeleting(null);
    if (!target) return;
    setActionError(null);
    try {
      await reauth.withReauth((token) => remove.mutateAsync({ reauthToken: token, id: target.id }));
      toast.success('パスキーを削除しました');
    } catch (error) {
      if (!(error instanceof ReauthCancelledError)) setActionError(apiErrorText(error, PASSKEY_DELETE_FAILED));
    }
  };

  const handleRename = async (name: string) => {
    if (!renaming) return;
    await rename.mutateAsync({ id: renaming.id, name });
    setRenaming(null);
    toast.success('名前を変えました');
  };

  const renderList = () => {
    if (list.status === 'loading') {
      return <Skeleton variant="rounded" height={72} aria-label="パスキーを読み込み中" />;
    }
    if (list.status === 'error') {
      return (
        <Alert
          severity="error"
          action={<Button color="inherit" onClick={list.retry}>再読み込み</Button>}
        >
          パスキーを読み込めませんでした
        </Alert>
      );
    }
    if (passkeys.length === 0) {
      return <Typography color="text.secondary">パスキーはまだありません</Typography>;
    }
    return (
      <List disablePadding>
        {passkeys.map((passkey) => (
          <ListItem
            key={passkey.id}
            divider
            secondaryAction={
              <Box sx={{ display: 'flex', gap: 1 }}>
                {/* 押す的は 44px 以上（ux-rules.md §6。IconButton の既定は 40px） */}
                <IconButton
                  aria-label={`『${passkey.name}』の名前を変える`}
                  onClick={() => setRenaming(passkey)}
                  sx={{ width: 44, height: 44 }}
                >
                  <Edit />
                </IconButton>
                <IconButton
                  aria-label={`『${passkey.name}』を削除`}
                  onClick={() => setDeleting(passkey)}
                  sx={{ width: 44, height: 44 }}
                >
                  <Delete />
                </IconButton>
              </Box>
            }
            sx={{ pr: 14 }}
          >
            <ListItemText
              primary={passkey.name}
              primaryTypographyProps={{ sx: { overflowWrap: 'anywhere' } }}
              secondary={
                <>
                  <span>登録 {formatDate(passkey.created_at)}</span>
                  <br />
                  <span>
                    最後に使った日 {passkey.last_used_at ? formatDate(passkey.last_used_at) : 'まだ使っていません'}
                  </span>
                </>
              }
            />
          </ListItem>
        ))}
      </List>
    );
  };

  return (
    <Card data-testid="passkeys-card">
      <CardContent>
        <Typography variant="h6" component="h2" gutterBottom>
          パスキー
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          指紋・顔・PIN でパスワードなしにログインできます
        </Typography>
        {renderList()}
        {actionError && (
          <Alert severity="error" role="alert" sx={{ mt: 2 }}>
            {actionError}
          </Alert>
        )}
        <Button
          variant="outlined"
          startIcon={register.isPending ? undefined : <Add />}
          onClick={handleRegister}
          disabled={!supported || register.isPending || list.status !== 'success'}
          sx={{ mt: 2, minHeight: 44 }}
        >
          {register.isPending ? <CircularProgress size={20} aria-label="登録しています" /> : 'パスキーを登録'}
        </Button>
        {!supported && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {PASSKEY_UNSUPPORTED}
          </Typography>
        )}
      </CardContent>

      <Dialog open={deleting !== null} onClose={() => setDeleting(null)} aria-labelledby="passkey-delete-title">
        <DialogTitle id="passkey-delete-title">パスキーの削除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            『{deleting?.name}』を削除しますか？このパスキーではログインできなくなります
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleting(null)} sx={{ minHeight: 44 }}>キャンセル</Button>
          <Button color="error" variant="contained" onClick={handleDelete} sx={{ minHeight: 44 }}>削除</Button>
        </DialogActions>
      </Dialog>
      <PasskeyRenameDialog
        open={renaming !== null}
        currentName={renaming?.name ?? ''}
        onSave={handleRename}
        onCancel={() => setRenaming(null)}
      />
      <PasskeyReauthDialog
        open={reauth.dialogOpen}
        hasPasskeys={passkeys.length > 0}
        onSuccess={reauth.complete}
        onCancel={reauth.cancel}
      />
    </Card>
  );
}

export default PasskeysCard;
