/**
 * 問題画像・解説画像の並べ方（I472）
 * 問題管理のプレビューとクイズの画面で同じ見え方にする。拡大の画面は親が持つ
 */
import React from 'react';
import { Box, ImageList, ImageListItem } from '@mui/material';
import MediaImage from './MediaImage';

/** 問題・解説の画像の枠の高さ（今までの表示の上限 maxHeight: 300 と同じ）。MediaImage が 3 つの状態に同じ高さを使う */
const IMAGE_HEIGHT = 300;

interface ProblemImageListProps {
  /** 表示する画像の API の URL（pickImageUrls の戻り値・/api/media/<id>/） */
  images: string[];
  /** 代替テキストの頭（例: '問題画像' → 「問題画像 1」） */
  alt: string;
  /** 画像を押したとき（クリック・Enter・スペース）に、その画像の API の URL を受け取る */
  onImageClick: (fullUrl: string) => void;
}

const ProblemImageList: React.FC<ProblemImageListProps> = ({ images, alt, onImageClick }) => {
  if (images.length === 0) return null;

  return (
    <Box sx={{ mt: 2 }}>
      <ImageList cols={Math.min(images.length, 3)} gap={8}>
        {images.map((imageUrl, index) => {
          return (
            <ImageListItem key={imageUrl}>
              <MediaImage
                src={imageUrl}
                height={IMAGE_HEIGHT}
                alt={`${alt} ${index + 1}`}
                role="button"
                tabIndex={0}
                aria-label={`${alt} ${index + 1}枚目。クリックで拡大表示`}
                sx={{
                  width: '100%',
                  objectFit: 'contain',
                  borderRadius: 1,
                  cursor: 'pointer',
                  border: '1px solid',
                  borderColor: 'divider',
                  '&:hover': {
                    opacity: 0.9,
                  },
                  '&:focus': {
                    outline: '2px solid',
                    outlineColor: 'primary.main',
                    outlineOffset: 2,
                  },
                }}
                onClick={() => onImageClick(imageUrl)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onImageClick(imageUrl);
                  }
                }}
              />
            </ImageListItem>
          );
        })}
      </ImageList>
    </Box>
  );
};

export default ProblemImageList;
