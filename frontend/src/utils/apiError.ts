/**
 * バックエンドのカスタム例外ハンドラー（core/exceptions.py）が返す
 * 統一エラー形式からメッセージを抽出するユーティリティ
 *
 * レスポンス形式:
 * { error: { main_message: string, sub_message: string | null, details: {} } }
 */
export function extractApiErrorMessage(data: unknown, fallback: string): string {
  if (typeof data !== 'object' || data === null) return fallback;
  const d = data as Record<string, any>;
  return (
    (typeof d.error?.sub_message === 'string' && d.error.sub_message) ||
    (typeof d.error?.main_message === 'string' && d.error.main_message) ||
    fallback
  );
}
