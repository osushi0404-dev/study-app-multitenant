/**
 * 画像の中身の取得（I587）
 * 画像はログインと組織の境界を確かめる API（GET /api/media/<id>/）から返る。
 * <img src> は認証の見出しを付けられないので、通信の土台（apiClient）で中身を取る
 */
import apiClient from './api';

/** 画像の API の URL から中身を取る。失敗は共通の通知を出さず、呼ぶ側が画像の枠に出す */
export const getMediaBlob = async (url: string): Promise<Blob> => {
  const response = await apiClient.get<Blob>(url, { responseType: 'blob', skipErrorToast: true });
  return response.data;
};
