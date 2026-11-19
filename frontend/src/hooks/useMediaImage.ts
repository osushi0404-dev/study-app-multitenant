/**
 * 画像の中身を取り、表示用の URL（blob:）を返す（I587）
 *
 * 同じ画像の中身は変わらない（画像を替えると新しい ID になる）ので、取れた中身は捨てずに使い回す。
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
