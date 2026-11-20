/**
 * MediaImage（I587 TC-16）: 画像の API の URL から中身を取り、読み込み中・失敗・表示を出し分ける
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MediaImage from '../MediaImage';
import { getMediaBlob } from '../../services/mediaService';

jest.mock('../../services/mediaService');

const mockedGetMediaBlob = jest.mocked(getMediaBlob);

const renderImage = (height?: number) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MediaImage src="/api/media/a/" alt="問題画像 1" height={height} />
    </QueryClientProvider>
  );
};

describe('MediaImage', () => {
  const createObjectURL = jest.fn();
  const revokeObjectURL = jest.fn();

  beforeAll(() => {
    Object.assign(URL, { createObjectURL, revokeObjectURL });
  });

  beforeEach(() => {
    // CRA の resetMocks で各テストの前に返り値が消えるので、ここで入れ直す
    createObjectURL.mockReturnValue('blob:a');
  });

  it('取得中は形だけ（読み込み中）を、渡した高さの枠で出す', () => {
    mockedGetMediaBlob.mockReturnValue(new Promise(() => {}));
    renderImage(300);

    const skeleton = screen.getByLabelText('問題画像 1を読み込み中');
    expect(skeleton).toHaveAttribute('aria-busy', 'true');
    expect(skeleton).toHaveStyle({ height: '300px' });
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(mockedGetMediaBlob).toHaveBeenCalledWith('/api/media/a/');
  });

  it('失敗すると枠に文言と再読み込みのボタンを出し、押すと取り直す', async () => {
    mockedGetMediaBlob.mockRejectedValueOnce(new Error('404'));
    renderImage();

    expect(await screen.findByText('画像を読み込めませんでした')).toBeInTheDocument();
    // 失敗の枠も読み込み中と同じ高さ（既定 150px）・押す的は 44×44px 以上（UX §6）
    expect(screen.getByRole('group', { name: '問題画像 1' })).toHaveStyle({ minHeight: '150px' });
    const retryButton = screen.getByRole('button', { name: '再読み込み' });
    expect(retryButton).toHaveStyle({ minHeight: '44px', minWidth: '44px' });
    mockedGetMediaBlob.mockResolvedValueOnce(new Blob(['png'], { type: 'image/png' }));
    fireEvent.click(retryButton);

    expect(await screen.findByRole('img', { name: '問題画像 1' })).toHaveAttribute('src', 'blob:a');
    expect(mockedGetMediaBlob).toHaveBeenCalledTimes(2);
  });

  it('取れたら blob の URL で表示し、外すと URL を捨てる', async () => {
    mockedGetMediaBlob.mockResolvedValueOnce(new Blob(['png'], { type: 'image/png' }));
    const { unmount } = renderImage();

    expect(await screen.findByRole('img', { name: '問題画像 1' })).toHaveAttribute('src', 'blob:a');
    expect(createObjectURL).toHaveBeenCalledTimes(1);

    unmount();
    await waitFor(() => expect(revokeObjectURL).toHaveBeenCalledWith('blob:a'));
  });
});
