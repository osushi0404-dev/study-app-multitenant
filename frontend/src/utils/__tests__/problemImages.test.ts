/**
 * pickImageUrls（I472 TC-07・I587 TC-19）: 画像の API の URL を表示順に並べる（古い形式の 1 枚は I587 で外した）
 */
import { pickImageUrls } from '../problemImages';
import { MediaAsset } from '../../services/types';

const asset = (url: string): MediaAsset => ({
  id: url,
  url,
  usage_kind: 'explanation',
  original_filename: 'x.png',
  mime_type: 'image/png',
  file_size_bytes: 100,
  created_at: '2026-11-12T00:00:00Z',
});

describe('pickImageUrls', () => {
  it('画像の URL を表示順に並べる', () => {
    expect(pickImageUrls([asset('/api/media/a/'), asset('/api/media/b/')]))
      .toEqual(['/api/media/a/', '/api/media/b/']);
  });

  it('空配列・無いときは空', () => {
    expect(pickImageUrls([])).toEqual([]);
    expect(pickImageUrls(undefined)).toEqual([]);
    expect(pickImageUrls(null)).toEqual([]);
  });
});
