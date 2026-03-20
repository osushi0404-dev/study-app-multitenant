import { apiClient } from './api';
import { Subject, PaginatedResponse } from './types';
import ApiResponseUtils from '../utils/apiResponseUtils';

/**
 * 科目API関連のサービス層
 * APIレスポンスの形式を統一し、型安全性を確保する
 */
export class SubjectService {
  /**
   * 組織または個人の科目一覧を取得
   * @param organizationSlug 組織スラッグ（個人の場合は'personal'）
   * @returns 科目配列（常に配列を保証）
   */
  static async getSubjects(organizationSlug?: string): Promise<Subject[]> {
    try {
      const slug = organizationSlug || 'personal';
      const response = await apiClient.get<PaginatedResponse<Subject> | Subject[]>(
        `/api/organizations/subjects/public/?slug=${slug}`
      );

      // レスポンス形式の正規化
      return this.normalizeSubjectsResponse(response.data);
    } catch (error) {
      const errorMessage = ApiResponseUtils.handleApiError(error, '科目一覧取得');
      throw new Error(errorMessage);
    }
  }

  /**
   * APIレスポンスを統一された配列形式に正規化
   * @param data APIから取得したデータ
   * @returns 正規化された科目配列
   */
  private static normalizeSubjectsResponse(
    data: PaginatedResponse<Subject> | Subject[] | any
  ): Subject[] {
    ApiResponseUtils.debugLog('科目APIレスポンス', data);
    return ApiResponseUtils.normalizeToArray(data, this.isValidSubject);
  }

  /**
   * オブジェクトが有効なSubject型かどうかを検証
   * @param item 検証対象のオブジェクト
   * @returns 有効なSubject型かどうか
   */
  private static isValidSubject(item: any): item is Subject {
    return (
      item &&
      typeof item === 'object' &&
      (typeof item.id === 'number' || typeof item.id === 'string') &&
      typeof item.name === 'string'
    );
  }

  /**
   * ユーザーが登録した科目の一覧を取得（ダッシュボード・統計画面用）
   * @returns ユーザー登録科目配列
   */
  static async getUserSubjects(): Promise<Subject[]> {
    try {
      const response = await apiClient.get<Subject[]>('/api/user/subjects/');
      return ApiResponseUtils.normalizeToArray(response.data, this.isValidSubject);
    } catch (error) {
      const errorMessage = ApiResponseUtils.handleApiError(error, 'ユーザー科目取得');
      throw new Error(errorMessage);
    }
  }

  /**
   * 科目取得時のローディング状態とエラーハンドリングを含む便利メソッド
   * @param organizationSlug 組織スラッグ
   * @param onLoading ローディング状態変更コールバック
   * @param onError エラーハンドリングコールバック
   * @returns 科目配列
   */
  static async getSubjectsWithLoading(
    organizationSlug?: string,
    onLoading?: (loading: boolean) => void,
    onError?: (error: string) => void
  ): Promise<Subject[]> {
    try {
      onLoading?.(true);
      const subjects = await this.getSubjects(organizationSlug);
      return subjects;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '科目の取得に失敗しました';
      onError?.(errorMessage);
      return [];
    } finally {
      onLoading?.(false);
    }
  }
}

// デフォルトエクスポート
export default SubjectService;