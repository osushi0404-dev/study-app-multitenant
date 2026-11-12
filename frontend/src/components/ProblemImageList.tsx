/**
 * 問題画像・解説画像の並べ方（I472）
 * 問題管理のプレビューとクイズの画面で同じ見え方にする。拡大の画面は親が持つ
 */
import React from 'react';
import { Box, ImageList, ImageListItem } from '@mui/material';
import { getMediaUrl } from '../utils/url';

interface ProblemImageListProps {
  /** 表示する画像の URL（API の相対パス・pickImageUrls の戻り値） */
  images: string[];
  /** 代替テキストの頭（例: '問題画像' → 「問題画像 1」） */
  alt: string;
  /** 画像を押したとき（クリック・Enter・スペース）に、完全な URL を受け取る */
  onImageClick: (fullUrl: string) => void;
}

const ProblemImageList: React.FC<ProblemImageListProps> = ({ images, alt, onImageClick }) => {
  if (images.length === 0) return null;

  return (
    <Box sx={{ mt: 2 }}>
      <ImageList cols={images.length === 1 ? 1 : Math.min(images.length, 3)} gap={8}>
        {images.map((imageUrl, index) => (
          <ImageListItem key={index}>
            <Box
              component="img"
              src={getMediaUrl(imageUrl)}
              alt={`${alt} ${index + 1}`}
              role="button"
              tabIndex={0}
              aria-label={`${alt} ${index + 1}枚目。クリックで拡大表示`}
              loading="lazy"
              sx={{
                width: '100%',
                maxHeight: 300,
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
              onClick={() => onImageClick(getMediaUrl(imageUrl))}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onImageClick(getMediaUrl(imageUrl));
                }
              }}
            />
          </ImageListItem>
        ))}
      </ImageList>
    </Box>
  );
};

export default ProblemImageList;
