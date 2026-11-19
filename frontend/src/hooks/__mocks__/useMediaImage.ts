/**
 * useMediaImage の差し替え（I587）: 画像を取りにいかず、渡された API の URL を取れた画像の URL として返す
 * 画面のテストは本物の MediaImage を描き、「どの画像の URL を、どの順で、どの属性で出すか」を確かめる。
 * 取得と 4 つの状態は MediaImage.test.tsx（本物のフック）が確かめる。
 * 使い方: テストで jest.mock('<…>/hooks/useMediaImage')
 */
export const mediaImageKey = (url: string) => ['media', url] as const;

export const useMediaImage = (url: string) => ({
  state: 'success' as const,
  objectUrl: url,
  retry: () => {},
});
