import { MediaAsset } from '../services/types';

/**
 * 表示する画像の API の URL（表示順）
 * 問題管理のプレビューとクイズの画面で同じ規則を使う（I472。古い形式の 1 枚は I587 で外した）
 */
export const pickImageUrls = (assets: MediaAsset[] | null | undefined): string[] =>
  (assets ?? []).map((asset) => asset.url);
