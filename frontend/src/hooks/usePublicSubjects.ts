/**
 * 招待先の組織の科目（未ログイン・会員登録の画面用・I539）
 * 取得は React Query（規約 6.3）。失敗を「0 件」と取り違えて科目なしで登録させないよう、3 つの状態（toLoadState）で返す
 */
import { useQuery } from '@tanstack/react-query';
import SubjectService from '../services/subjectService';
import { toLoadState } from './queryLoadState';

export const publicSubjectsKey = (slug: string) => ['public-subjects', slug] as const;

export const usePublicSubjects = (slug: string | undefined, { enabled = true }: { enabled?: boolean } = {}) =>
  toLoadState(
    useQuery({
      queryKey: publicSubjectsKey(slug ?? ''),
      queryFn: () => SubjectService.getSubjects(slug),
      enabled: enabled && !!slug,
    })
  );
