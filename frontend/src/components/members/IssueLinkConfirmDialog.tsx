/**
 * 登録用リンクの発行・取り消しの確認（I620）。発行は今のパスキーとログイン中の状態が消えることを書く
 */
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material';

export type LinkConfirmKind = 'issue' | 'revoke';

type Props = {
  userId: string;
  kind: LinkConfirmKind | null;
  onConfirm: () => void;
  onCancel: () => void;
};

const ISSUE_TEXT = {
  title: '登録用リンクの発行',
  body: '今のパスキーはすべて使えなくなり、ログイン中の端末もログアウトされます。',
  action: '発行する',
};
const REVOKE_TEXT = {
  title: '登録用リンクの取り消し',
  body: '取り消したリンクでは登録できなくなります。',
  action: '取り消す',
};

function IssueLinkConfirmDialog({ userId, kind, onConfirm, onCancel }: Props) {
  const text = kind === 'revoke' ? REVOKE_TEXT : ISSUE_TEXT;
  const question = kind === 'revoke'
    ? `『${userId}』の登録用リンクを取り消しますか？`
    : `『${userId}』の登録用リンクを発行しますか？`;
  return (
    <Dialog open={kind !== null} onClose={onCancel} aria-labelledby="link-confirm-title">
      <DialogTitle id="link-confirm-title">{text.title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{question}</DialogContentText>
        <DialogContentText>{text.body}</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel} sx={{ minHeight: 44 }}>キャンセル</Button>
        <Button
          color={kind === 'revoke' ? 'error' : 'primary'}
          variant="contained"
          onClick={onConfirm}
          sx={{ minHeight: 44 }}
        >
          {text.action}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default IssueLinkConfirmDialog;
