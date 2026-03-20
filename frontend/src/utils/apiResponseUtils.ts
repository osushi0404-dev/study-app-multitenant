import { PaginatedResponse } from '../services/types';

/**
 * APIレスポンス処理のユーティリティ関数
 * 型安全で堅牢なAPIレスポンス処理を提供
 */
export class ApiResponseUtils {
  /**
   * ページネーション形式または配列のレスポンスを統一された配列に変換
   * @param data APIから取得したデータ
   * @param validator オプションの検証関数
   * @returns 正規化された配列
   */
  static normalizeToArray<T>(
    data: any,
    validator?: (item: any) => item is T
  ): T[] {
    try {
      // 既に配列の場合
      if (Array.isArray(data)) {
        return validator ? data.filter(validator) : data;
      }

      // ページネーション形式 (Django REST framework標準)
      if (this.isPaginatedResponse(data)) {
        const items = data.results || [];
        return validator ? items.filter(validator) : items;
      }

      // data プロパティがある場合
      if (data && typeof data === 'object' && 'data' in data) {
        if (Array.isArray(data.data)) {
          return validator ? data.data.filter(validator) : data.data;
        }
      }

      // その他の想定外の形式
      console.warn('想定外のAPIレスポンス形式:', {
        type: typeof data,
        constructor: data?.constructor?.name,
        keys: data && typeof data === 'object' ? Object.keys(data) : [],
        data: data
      });

      return [];
    } catch (error) {
      console.error('APIレスポンスの正規化中にエラーが発生:', error);
      return [];
    }
  }

  /**
   * ページネーション形式のレスポンスかどうかを判定
   */
  private static isPaginatedResponse(data: any): data is PaginatedResponse<any> {
    return (
      data &&
      typeof data === 'object' &&
      'results' in data &&
      Array.isArray(data.results) &&
      'count' in data &&
      typeof data.count === 'number'
    );
  }

  /**
   * APIレスポンスのエラーハンドリング
   * @param error エラーオブジェクト
   * @param context エラーが発生したコンテキスト
   * @returns ユーザー向けのエラーメッセージ
   */
  static handleApiError(error: any, context: string = 'API'): string {
    console.error(`${context}エラー:`, error);

    // ネットワークエラー
    if (error.code === 'NETWORK_ERROR' || !error.response) {
      return 'ネットワークエラーが発生しました。インターネット接続を確認してください。';
    }

    // HTTPステータスコード別のメッセージ
    const status = error.response?.status;
    switch (status) {
      case 400:
        return 'リクエストに問題があります。入力内容を確認してください。';
      case 401:
        return '認証が必要です。ログインしてください。';
      case 403:
        return 'この操作を実行する権限がありません。';
      case 404:
        return '要求されたリソースが見つかりません。';
      case 422:
        return '入力データに問題があります。内容を確認してください。';
      case 500:
        return 'サーバーでエラーが発生しました。しばらく待ってから再試行してください。';
      case 503:
        return 'サービスが一時的に利用できません。しばらく待ってから再試行してください。';
      default:
        return 'エラーが発生しました。しばらく待ってから再試行してください。';
    }
  }

  /**
   * 型安全なAPI呼び出しラッパー
   * @param apiCall API呼び出し関数
   * @param context エラーコンテキスト
   * @returns 結果またはnull
   */
  static async safeApiCall<T>(
    apiCall: () => Promise<T>,
    context: string = 'API'
  ): Promise<T | null> {
    try {
      return await apiCall();
    } catch (error) {
      const errorMessage = this.handleApiError(error, context);
      console.error(`${context}呼び出し失敗:`, errorMessage);
      return null;
    }
  }

  /**
   * デバッグ情報を含むログ出力
   * @param label ログのラベル
   * @param data ログに出力するデータ
   */
  static debugLog(label: string, data: any): void {
    if (process.env.NODE_ENV === 'development') {
      console.group(`🔍 ${label}`);
      console.log('Type:', typeof data);
      console.log('Is Array:', Array.isArray(data));
      console.log('Constructor:', data?.constructor?.name);
      if (data && typeof data === 'object') {
        console.log('Keys:', Object.keys(data));
      }
      console.log('Data:', data);
      console.groupEnd();
    }
  }
}

export default ApiResponseUtils;