/**
 * 発行した直後の登録用リンク（I620）。一度だけ見せ、閉じたら値を捨てる（親の state だけに置く）
 */
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

function RegistrationLinkDialog({ userId, link, onClose }: Props) {
  const handleCopy = async () => {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link.url);
      toast.success('リンクをコピーしました');
    } catch {
      toast.error('コピーできませんでした。リンクを選んでコピーしてください');
    }
  };

  return (
    <Dialog open={link !== null} onClose={onClose} fullWidth maxWidth="sm" aria-labelledby="registration-link-title">
      <DialogTitle id="registration-link-title">『{userId}』の登録用リンク</DialogTitle>
      {link && (
        <DialogContent>
          <Stack spacing={2}>
            <Box sx={{ display: 'flex', justifyContent: 'center' }}>
              <QRCodeSVG value={link.url} size={192} aria-label="登録用リンクの QR コード" role="img" />
            </Box>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <TextField
                label="リンク"
                value={link.url}
                fullWidth
                InputProps={{ readOnly: true }}
                onFocus={(event) => event.target.select()}
                sx={{ flex: '1 1 240px' }}
              />
              <Button variant="outlined" startIcon={<ContentCopy />} onClick={handleCopy} sx={{ minHeight: 56 }}>
                コピー
              </Button>
            </Box>
            <Typography variant="body2">有効期限: {formatDateTime(link.expires_at)}（1 時間・1 回だけ）</Typography>
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
