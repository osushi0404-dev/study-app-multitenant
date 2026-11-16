import { apiClient } from './api';
import { Subject, PaginatedResponse } from './types';
import ApiResponseUtils from '../utils/apiResponseUtils';
import { AvailableSubject, UserSubject, UserSubjectSelection } from '../types/api';

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
   * 利用者が選べる自組織の科目の一覧（設定画面の「学ぶ科目」のカード・I494）
   * @returns 自組織の科目（名前の順。組織に属さない利用者は空）
   */
  static async getAvailableSubjects(): Promise<AvailableSubject[]> {
    try {
      const response = await apiClient.get<AvailableSubject[]>('/api/user/subjects/available/');
      return response.data;
    } catch (error) {
      const errorMessage = ApiResponseUtils.handleApiError(error, '選べる科目の取得');
      throw new Error(errorMessage);
    }
  }

  /**
   * 利用者が学ぶ科目を置き換える（I494）
   * 失敗は包まずに投げ直す（画面が 400 の理由〔error.sub_message〕を読むため）
   * @param subjectIds 選んだ科目の番号（自組織の科目・1 件以上）
   * @returns 保存の後の選んだ科目（名前の順）
   */
  static async updateUserSubjects(subjectIds: number[]): Promise<UserSubject[]> {
    const body: UserSubjectSelection = { subject_ids: subjectIds };
    const response = await apiClient.put<UserSubject[]>('/api/user/subjects/', body);
    return response.data;
  }
}

// デフォルトエクスポート
export default SubjectService;
