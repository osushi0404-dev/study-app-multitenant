/**
 * 画像の中身を取り、表示用の URL（blob:）を返す（I587）
 *
 * 同じ画像の中身は変わらない（画像を替えると新しい ID になる）ので、表示している間は取り直さない。
 * 画像は部品が置かれた時点で取る（img の loading="lazy" は blob の URL には効かないので付けない）。
 * 表示用の URL は部品が外れるか中身が変わったときに捨てる（メモリを残さない）。
 */
import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMediaBlob } from '../services/mediaService';
import { LoadState, toLoadState } from './queryLoadState';

export const mediaImageKey = (url: string) => ['media', url] as const;

export const useMediaImage = (url: string): { state: LoadState<Blob>['status']; objectUrl: string | null; retry: () => void } => {
  const load = toLoadState(
    useQuery({
      queryKey: mediaImageKey(url),
      queryFn: () => getMediaBlob(url),
      enabled: !!url,
      staleTime: Infinity,
      // 使わなくなった中身は早めに捨てる（もう一度要るときはブラウザの HTTP キャッシュか 304 で返る）
      gcTime: 60_000,
    })
  );
  const blob = load.status === 'success' ? load.data : null;
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!blob) {
      setObjectUrl(null);
      return undefined;
    }
    const created = URL.createObjectURL(blob);
    setObjectUrl(created);
    return () => URL.revokeObjectURL(created);
  }, [blob]);

  return { state: load.status, objectUrl, retry: load.retry };
};
