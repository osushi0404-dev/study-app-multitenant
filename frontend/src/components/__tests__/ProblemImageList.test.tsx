/**
 * ProblemImageList（I472 TC-08）: 問題管理のプレビューと同じ画像の並べ方
 */
import { render, screen, fireEvent } from '@testing-library/react';
import ProblemImageList from '../ProblemImageList';
import { getMediaUrl } from '../../utils/url';

const renderList = (images: string[], onImageClick = jest.fn()) =>
  render(<ProblemImageList images={images} alt="解説画像" onImageClick={onImageClick} />);

describe('ProblemImageList', () => {
  it('1 枚は 1 列で、代替テキスト・操作の属性・URL を持つ', () => {
    renderList(['/media/a.png']);

    expect(screen.getByRole('list')).toHaveStyle({ gridTemplateColumns: 'repeat(1, 1fr)' });
    const image = screen.getByAltText('解説画像 1');
    expect(image).toHaveAttribute('aria-label', '解説画像 1枚目。クリックで拡大表示');
    expect(image).toHaveAttribute('role', 'button');
    expect(image).toHaveAttribute('tabindex', '0');
    expect(image).toHaveAttribute('src', getMediaUrl('/media/a.png'));
  });

  it('2 枚は 2 列', () => {
    renderList(['/media/a.png', '/media/b.png']);

    expect(screen.getByRole('list')).toHaveStyle({ gridTemplateColumns: 'repeat(2, 1fr)' });
  });

  it('4 枚は 3 列', () => {
    renderList(['/media/a.png', '/media/b.png', '/media/c.png', '/media/d.png']);

    expect(screen.getByRole('list')).toHaveStyle({ gridTemplateColumns: 'repeat(3, 1fr)' });
    expect(screen.getAllByAltText(/^解説画像 \d$/)).toHaveLength(4);
  });

  it('クリック・Enter・スペースで完全な URL を渡し、ほかのキーでは渡さない', () => {
    const onImageClick = jest.fn();
    renderList(['/media/a.png'], onImageClick);
    const image = screen.getByAltText('解説画像 1');

    fireEvent.click(image);
    fireEvent.keyDown(image, { key: 'Enter' });
    fireEvent.keyDown(image, { key: ' ' });
    fireEvent.keyDown(image, { key: 'a' });

    expect(onImageClick).toHaveBeenCalledTimes(3);
    expect(onImageClick).toHaveBeenNthCalledWith(1, getMediaUrl('/media/a.png'));
    expect(onImageClick).toHaveBeenNthCalledWith(2, getMediaUrl('/media/a.png'));
    expect(onImageClick).toHaveBeenNthCalledWith(3, getMediaUrl('/media/a.png'));
  });

  it('画像が無ければ何も描かない', () => {
    const { container } = renderList([]);

    expect(container).toBeEmptyDOMElement();
  });

  it('絶対 URL はそのまま使う', () => {
    renderList(['https://cdn.example.com/x.png']);

    expect(screen.getByAltText('解説画像 1')).toHaveAttribute('src', 'https://cdn.example.com/x.png');
  });
});
