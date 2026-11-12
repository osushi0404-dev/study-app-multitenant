/**
 * pickImageUrls（I472 TC-07）: 新しい形式が 1 枚以上あれば新しい形式だけ、無ければ古い形式の 1 枚
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
  it('新しい形式があれば古い形式を使わない', () => {
    expect(pickImageUrls([asset('/media/a.png'), asset('/media/b.png')], '/media/legacy.png'))
      .toEqual(['/media/a.png', '/media/b.png']);
  });

  it('新しい形式が空配列なら古い形式の 1 枚', () => {
    expect(pickImageUrls([], '/media/legacy.png')).toEqual(['/media/legacy.png']);
  });

  it('どちらも無ければ空', () => {
    expect(pickImageUrls(undefined, null)).toEqual([]);
  });

  it('新しい形式だけ', () => {
    expect(pickImageUrls([asset('/media/a.png')], undefined)).toEqual(['/media/a.png']);
  });
});
