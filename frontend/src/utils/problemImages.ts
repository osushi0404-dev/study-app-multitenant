import { MediaAsset } from '../services/types';

/**
 * 表示する画像の URL（新しい形式が 1 枚以上あれば新しい形式だけ、無ければ古い形式の 1 枚）
 * 問題管理のプレビューとクイズの画面で同じ規則を使う（I472）
 */
export const pickImageUrls = (
  assets: MediaAsset[] | null | undefined,
  legacyUrl: string | null | undefined,
): string[] => {
  if (assets && assets.length > 0) {
    return assets.map((asset) => asset.url);
  }
  return legacyUrl ? [legacyUrl] : [];
};
