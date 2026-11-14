/**
 * React Query の結果を、画面が出し分ける 3 つの状態（読み込み中・失敗・成功）にする（I487・I488）
 *
 * 失敗の後の取り直しの間も読み込み中にする（失敗の表示のまま古い文言を出し続けない）。
 * 前のキーの数字を出さないため、呼ぶ側は placeholderData を使わない（C7）。
 */
import { UseQueryResult } from '@tanstack/react-query';

export type LoadState<T> =
  | { status: 'loading'; data: null }
  | { status: 'error'; data: null }
  | { status: 'success'; data: T };

export const toLoadState = <T,>(query: UseQueryResult<T>): LoadState<T> & { retry: () => void } => {
  let state: LoadState<T>;
  if (query.isSuccess) {
    state = { status: 'success', data: query.data };
  } else if (query.isError && !query.isFetching) {
    state = { status: 'error', data: null };
  } else {
    state = { status: 'loading', data: null };
  }
  return { ...state, retry: () => { query.refetch(); } };
};
