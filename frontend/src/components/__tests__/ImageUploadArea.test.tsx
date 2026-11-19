/**
 * ImageUploadArea（I587 TC-18）: 保存済みの画像は画像の API の URL から取って出し、新しく選んだ画像は手元の URL で出す
 */
import { render, screen } from '@testing-library/react';
import ImageUploadArea from '../ImageUploadArea';
import { EditableImage } from '../../services/types';

// 画像の取得はしない（フックを差し替え、渡された API の URL を src に出す・I587）
jest.mock('../../hooks/useMediaImage');

describe('ImageUploadArea の画像のプレビュー', () => {
  const createObjectURL = jest.fn();
  const revokeObjectURL = jest.fn();

  beforeAll(() => {
    Object.assign(URL, { createObjectURL, revokeObjectURL });
  });

  beforeEach(() => {
    // CRA の resetMocks で各テストの前に返り値が消えるので、ここで入れ直す
    createObjectURL.mockReturnValue('blob:new');
  });

  it('保存済みは MediaImage（API の URL）、新しい画像は手元の URL で出す', () => {
    const file = new File(['png'], 'new.png', { type: 'image/png' });
    const items: EditableImage[] = [
      { kind: 'existing', assetId: 'a1', url: '/api/media/a1/', filename: 'saved.png' },
      { kind: 'new', file },
    ];
    render(
      <ImageUploadArea
        label="問題用画像"
        items={items}
        onImagesAdd={jest.fn()}
        onRemove={jest.fn()}
        onMoveUp={jest.fn()}
        onMoveDown={jest.fn()}
      />
    );

    expect(screen.getByRole('img', { name: 'saved.png' })).toHaveAttribute('src', '/api/media/a1/');
    expect(screen.getByRole('img', { name: 'new.png' })).toHaveAttribute('src', 'blob:new');
    expect(createObjectURL).toHaveBeenCalledWith(file);
  });
});
