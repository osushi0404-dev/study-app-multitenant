// frontend/src/components/ImageModal.tsx

import React from 'react';
import { Dialog, IconButton, Box } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import MediaImage from './MediaImage';

interface ImageModalProps {
  /** 画像の API の URL（/api/media/<id>/・I587） */
  imageUrl: string;
  open: boolean;
  onClose: () => void;
}

/**
 * 画像拡大表示モーダルコンポーネント
 * クイズの問題画像・解説画像をクリックした際に拡大表示する
 */
const ImageModal: React.FC<ImageModalProps> = ({ imageUrl, open, onClose }) => {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth={false}
      PaperProps={{
        style: {
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          boxShadow: 'none',
          maxWidth: '90vw',
          maxHeight: '90vh',
        },
      }}
    >
      <Box position="relative">
        <IconButton
          onClick={onClose}
          sx={{
            position: 'absolute',
            top: 8,
            right: 8,
            color: 'white',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            '&:hover': {
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
            },
          }}
        >
          <CloseIcon />
        </IconButton>
        <MediaImage
          src={imageUrl}
          alt="拡大画像"
          sx={{
            width: '100%',
            height: 'auto',
            display: 'block',
          }}
        />
      </Box>
    </Dialog>
  );
};

export default ImageModal;
