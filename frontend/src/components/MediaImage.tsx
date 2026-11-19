/**
 * 画像の API の URL から中身を取って表示する（I587）
 *
 * 読み込み中は形だけ（Skeleton）、失敗は枠の中に「画像を読み込めませんでした」と再読み込みのボタン
 * （docs/runbooks/ux-rules.md §1・§2）。取れたら img に表示用の URL（blob:）を渡す。
 */
import React from 'react';
import { Box, Button, Skeleton, Typography } from '@mui/material';
import type { SxProps, Theme } from '@mui/material';
import { useMediaImage } from '../hooks/useMediaImage';

const PLACEHOLDER_HEIGHT = 150;

interface MediaImageProps {
  /** 画像の API の URL（MediaAsset の url・/api/media/<id>/） */
  src: string;
  alt: string;
  sx?: SxProps<Theme>;
  role?: string;
  tabIndex?: number;
  'aria-label'?: string;
  loading?: 'lazy' | 'eager';
  onClick?: () => void;
  onKeyDown?: (event: React.KeyboardEvent<HTMLImageElement>) => void;
}

function MediaImage({ src, alt, sx, ...imgProps }: MediaImageProps) {
  const { state, objectUrl, retry } = useMediaImage(src);

  if (state === 'error') {
    return (
      <Box
        role="group"
        aria-label={alt}
        sx={{
          minHeight: PLACEHOLDER_HEIGHT,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 1,
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          p: 1,
        }}
      >
        <Typography variant="body2" color="text.secondary">
          画像を読み込めませんでした
        </Typography>
        <Button size="small" variant="outlined" onClick={retry}>
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
        sx={{ width: '100%', height: PLACEHOLDER_HEIGHT, borderRadius: 1 }}
      />
    );
  }

  return <Box component="img" src={objectUrl} alt={alt} sx={sx} {...imgProps} />;
}

export default MediaImage;
