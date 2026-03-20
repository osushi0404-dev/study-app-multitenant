/**
 * URL関連のユーティリティ関数
 */

/**
 * メディアファイルの完全なURLを生成するユーティリティ
 *
 * @param relativePath - APIから返される相対パス（例: /media/org/...）
 * @returns 完全なURL（例: http://localhost:8000/media/org/...）
 *
 * @example
 * getMediaUrl('/media/org/personal/subjects/aws-saa/problem/image.png')
 * // => 'http://localhost:8000/media/org/personal/subjects/aws-saa/problem/image.png'
 */
export const getMediaUrl = (relativePath: string | null | undefined): string => {
  // null/undefinedまたは空文字の場合は空文字を返す
  if (!relativePath) {
    return '';
  }

  // 既に絶対URLの場合はそのまま返す
  if (relativePath.startsWith('http://') || relativePath.startsWith('https://')) {
    return relativePath;
  }

  const baseUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
  return `${baseUrl}${relativePath}`;
};
