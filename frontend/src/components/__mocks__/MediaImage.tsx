/**
 * MediaImage の差し替え（I587）: 画像の取得をせず、渡された API の URL をそのまま img の src に出す
 * 画面のテストは「どの画像の URL を、どの順で、どの属性で出すか」を確かめる。取得と 4 つの状態は MediaImage.test.tsx
 * 使い方: テストで jest.mock('<…>/components/MediaImage')
 */
import React from 'react';

interface MockMediaImageProps {
  src: string;
  alt: string;
  role?: string;
  tabIndex?: number;
  'aria-label'?: string;
  onClick?: () => void;
  onKeyDown?: (event: React.KeyboardEvent<HTMLImageElement>) => void;
}

function MediaImage({ src, alt, role, tabIndex, 'aria-label': ariaLabel, onClick, onKeyDown }: MockMediaImageProps) {
  return (
    <img
      src={src}
      alt={alt}
      role={role}
      tabIndex={tabIndex}
      aria-label={ariaLabel}
      onClick={onClick}
      onKeyDown={onKeyDown}
    />
  );
}

export default MediaImage;
