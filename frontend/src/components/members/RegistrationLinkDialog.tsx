/**
 * 発行した直後の登録用リンク（I620）。一度だけ見せ、閉じたら値を捨てる（親の state だけに置く）
 * 親が値を null にして閉じても、閉じるアニメーションの間は最後に見せた見出しと中身を残し、閉じ終わった
 * 時点（onExited）で捨てる（I636 F8）
 */
import { useState } from 'react';
import toast from 'react-hot-toast';
import { QRCodeSVG } from 'qrcode.react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { ContentCopy } from '@mui/icons-material';
import { RegistrationLinkIssued } from '../../types/api';

const formatDateTime = (value: string) =>
  new Intl.DateTimeFormat('ja-JP', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));

type Props = {
  userId: string;
  link: RegistrationLinkIssued | null;
  onClose: () => void;
};

type Shown = { userId: string; link: RegistrationLinkIssued };

function RegistrationLinkDialog({ userId, link, onClose }: Props) {
  // 最後に見せた値（閉じるアニメーションの間の表示用）。新しい値が来たら描くときに置き換える（React の推奨の形）
  const [shown, setShown] = useState<Shown | null>(null);
  if (link !== null && (shown === null || shown.link !== link || shown.userId !== userId)) {
    setShown({ userId, link });
  }

  const handleCopy = async () => {
    if (!shown) return;
    try {
      await navigator.clipboard.writeText(shown.link.url);
      toast.success('リンクをコピーしました');
    } catch {
      toast.error('コピーできませんでした。リンクを選んでコピーしてください');
    }
  };

  return (
    <Dialog
      open={link !== null}
      onClose={onClose}
      TransitionProps={{ onExited: () => setShown(null) }}
      fullWidth
      maxWidth="sm"
      aria-labelledby="registration-link-title"
    >
      <DialogTitle id="registration-link-title">『{shown?.userId ?? userId}』の登録用リンク</DialogTitle>
      {shown && (
        <DialogContent>
          <Stack spacing={2}>
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <QRCodeSVG value={shown.link.url} size={192} aria-label="登録用リンクの QR コード" role="img" />
            </Box>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <TextField
                label="リンク"
                value={shown.link.url}
                fullWidth
                InputProps={{ readOnly: true }}
                onFocus={(event) => event.target.select()}
                sx={{ flex: '1 1 240px' }}
              />
              <Button variant="outlined" startIcon={<ContentCopy />} onClick={handleCopy} sx={{ minHeight: 56 }}>
                コピー
              </Button>
            </Box>
            <Typography variant="body2">有効期限: {formatDateTime(shown.link.expires_at)}（1 時間・1 回だけ）</Typography>
            <Alert severity="warning">この画面を閉じると、リンクは二度と表示できません</Alert>
          </Stack>
        </DialogContent>
      )}
      <DialogActions>
        <Button onClick={onClose} sx={{ minHeight: 44 }}>閉じる</Button>
      </DialogActions>
    </Dialog>
  );
}

export default RegistrationLinkDialog;
