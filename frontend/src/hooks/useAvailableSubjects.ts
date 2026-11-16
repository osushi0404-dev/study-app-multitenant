/**
 * 利用者が選べる自組織の科目（I494）
 * 取得は React Query（規約 6.3）。失敗を「0 件」と取り違えないよう、3 つの状態（toLoadState）で返す
 */
import { useQuery } from '@tanstack/react-query';
import SubjectService from '../services/subjectService';
import { AvailableSubject } from '../types/api';
import { LoadState, toLoadState } from './queryLoadState';

export type AvailableSubjectsState = LoadState<AvailableSubject[]>;

export const availableSubjectsKey = (userId: string) => ['available-subjects', userId] as const;

export const useAvailableSubjects = (userId: string, { enabled = true }: { enabled?: boolean } = {}) =>
  toLoadState(
    useQuery({
      queryKey: availableSubjectsKey(userId),
      queryFn: () => SubjectService.getAvailableSubjects(),
      enabled,
    })
  );
