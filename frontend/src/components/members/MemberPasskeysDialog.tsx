/**
 * 管理者が見る 1 人分のパスキー（I620）。一覧（名前・登録日・最後に使った日）と、確認の後の削除
 */
import { useState } from 'react';
import {
  Alert,
  Button,
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
import { Delete } from '@mui/icons-material';
import { LoadState } from '../../hooks/queryLoadState';
import { Passkey } from '../../types/api';

const formatDate = (value: string) =>
  new Intl.DateTimeFormat('ja-JP', { timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit' })
    .format(new Date(value));

type Props = {
  open: boolean;
  userId: string;
  passkeys: LoadState<Passkey[]> & { retry: () => void };
  error: string | null;
  onDelete: (passkey: Passkey) => void;
  onClose: () => void;
};

function MemberPasskeysDialog({ open, userId, passkeys, error, onDelete, onClose }: Props) {
  const [deleting, setDeleting] = useState<Passkey | null>(null);

  const renderList = () => {
    if (passkeys.status === 'loading') {
      return <Skeleton variant="rounded" height={72} aria-label="パスキーを読み込み中" />;
    }
    if (passkeys.status === 'error') {
      return (
        <Alert severity="error" action={<Button color="inherit" onClick={passkeys.retry}>再読み込み</Button>}>
          パスキーを読み込めませんでした
        </Alert>
      );
    }
    if (passkeys.data.length === 0) {
      return <Typography color="text.secondary">パスキーはまだありません</Typography>;
    }
    return (
      <List disablePadding>
        {passkeys.data.map((passkey) => (
          <ListItem
            key={passkey.id}
            divider
            secondaryAction={
              <IconButton
                aria-label={`『${passkey.name}』を削除`}
                onClick={() => setDeleting(passkey)}
                sx={{ width: 44, height: 44 }}
              >
                <Delete />
              </IconButton>
            }
            sx={{ pr: 8 }}
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

  const confirmDelete = () => {
    const target = deleting;
    setDeleting(null);
    if (target) onDelete(target);
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm" aria-labelledby="member-passkeys-title">
        <DialogTitle id="member-passkeys-title">『{userId}』のパスキー</DialogTitle>
        <DialogContent>
          {renderList()}
          {error && (
            <Alert severity="error" role="alert" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} sx={{ minHeight: 44 }}>閉じる</Button>
        </DialogActions>
      </Dialog>
      <Dialog open={deleting !== null} onClose={() => setDeleting(null)} aria-labelledby="member-passkey-delete-title">
        <DialogTitle id="member-passkey-delete-title">パスキーの削除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            『{deleting?.name}』を削除しますか？このパスキーではログインできなくなります
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleting(null)} sx={{ minHeight: 44 }}>キャンセル</Button>
          <Button color="error" variant="contained" onClick={confirmDelete} sx={{ minHeight: 44 }}>削除</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default MemberPasskeysDialog;
