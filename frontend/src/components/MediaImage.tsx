/**
 * 画像の API の URL から中身を取って表示する（I587）
 *
 * 読み込み中は形だけ（Skeleton）、失敗は枠の中に「画像を読み込めませんでした」と再読み込みのボタン
 * （docs/runbooks/ux-rules.md §1・§2）。取れたら img に表示用の URL（blob:）を渡す。
 * 読み込み中・失敗の枠と表示の img を、同じ高さ（height）で出す。読み込み後にまわりが動かない。
 * 表示の img の高さは呼ぶ側の sx で上書きできる（拡大の画面は height: 'auto' で実寸にする）。
 */
import React from 'react';
import { Box, Button, Skeleton, Typography } from '@mui/material';
import type { SxProps, Theme } from '@mui/material';
import { Replay } from '@mui/icons-material';
import { useMediaImage } from '../hooks/useMediaImage';

const DEFAULT_HEIGHT = 150;
/** 押す的の最小の大きさ（docs/runbooks/ux-rules.md §6） */
const MIN_TOUCH_TARGET = 44;

interface MediaImageProps {
  /** 画像の API の URL（MediaAsset の url・/api/media/<id>/） */
  src: string;
  alt: string;
  /** 読み込み中・失敗の枠と表示の img の高さ（px） */
  height?: number;
  sx?: SxProps<Theme>;
  role?: string;
  tabIndex?: number;
  'aria-label'?: string;
  onClick?: () => void;
  onKeyDown?: (event: React.KeyboardEvent<HTMLImageElement>) => void;
}

function MediaImage({ src, alt, height = DEFAULT_HEIGHT, sx, ...imgProps }: MediaImageProps) {
  const { state, objectUrl, retry } = useMediaImage(src);

  if (state === 'error') {
    return (
      <Box
        role="group"
        aria-label={alt}
        sx={{
          minHeight: height,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 1,
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          bgcolor: 'background.paper',
          p: 1,
        }}
      >
        <Typography variant="body2" color="text.secondary">
          画像を読み込めませんでした
        </Typography>
        <Button
          variant="outlined"
          startIcon={<Replay />}
          onClick={retry}
          sx={{ minHeight: MIN_TOUCH_TARGET, minWidth: MIN_TOUCH_TARGET }}
        >
          再読み込み
        </Button>
      </Box>
    );
  }

  if (state !== 'success' || !objectUrl) {
    return (
      <Skeleton
        variant="rectangular"
        aria-busy="true"
        aria-label={`${alt}を読み込み中`}
        sx={{ width: '100%', height, borderRadius: 1 }}
      />
    );
  }

  return (
    <Box
      component="img"
      src={objectUrl}
      alt={alt}
      sx={[{ height }, ...(Array.isArray(sx) ? sx : [sx])]}
      {...imgProps}
    />
  );
}

export default MediaImage;
