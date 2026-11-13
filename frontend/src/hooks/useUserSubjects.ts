/**
 * 利用者が選んだ科目の一覧（I487）
 * 取得は React Query（規約 6.3）。取得の失敗を「科目 0 件」と取り違えないよう、状態を分けて返す
 */
import { useQuery } from '@tanstack/react-query';
import SubjectService from '../services/subjectService';
import { Subject } from '../services/types';

export type UserSubjectsState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'success'; subjects: Subject[] };

export const userSubjectsKey = (userId: string) => ['user-subjects', userId] as const;

const fetchSubjects = async (): Promise<Subject[]> => {
  try {
    return await SubjectService.getUserSubjects();
  } catch (error) {
    console.error('Error loading subjects:', error);
    throw error;
  }
};

export const useUserSubjects = (userId: string) => {
  const query = useQuery({ queryKey: userSubjectsKey(userId), queryFn: fetchSubjects });

  let state: UserSubjectsState;
  if (query.isSuccess) {
    state = { status: 'success', subjects: query.data };
  } else if (query.isError && !query.isFetching) {
    state = { status: 'error' };
  } else {
    state = { status: 'loading' };
  }

  return { state, retry: () => { query.refetch(); } };
};
