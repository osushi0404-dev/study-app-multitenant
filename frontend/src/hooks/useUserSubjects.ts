/**
 * 利用者が選んだ科目の一覧（I487）と、その保存（I494）
 * 取得は React Query（規約 6.3）。取得の失敗を「科目 0 件」と取り違えないよう、状態を分けて返す
 */
import axios, { AxiosError } from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import SubjectService from '../services/subjectService';
import { UserSubject } from '../types/api';
import { availableSubjectsKey } from './useAvailableSubjects';
import { DASHBOARD_OVERVIEW_KEY_ROOT } from './useDashboardOverview';

export type UserSubjectsState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'success'; subjects: UserSubject[] };

export const userSubjectsKey = (userId: string) => ['user-subjects', userId] as const;

const fetchSubjects = async (): Promise<UserSubject[]> => {
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

/** 400（入力の誤り）の応答か（組織の科目が変わった場合に一覧を取り直す・画面に理由を出すのに使う） */
export const isBadRequest = (error: unknown): error is AxiosError =>
  axios.isAxiosError(error) && error.response?.status === 400;

/**
 * 学ぶ科目の保存（I494）
 * 保存の応答（裏側が保存した一覧）で、ダッシュボードが使う選んだ科目のキャッシュを書き換える（I487 F7・F10 と同じ手順）
 */
export const useSaveUserSubjects = (userId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (subjectIds: number[]) => SubjectService.updateUserSubjects(subjectIds),
    onSuccess: async (saved) => {
      // 保存の前に始まった取得の古い応答が、書き換えたキャッシュを上書きしないよう先に止める
      await queryClient.cancelQueries({ queryKey: userSubjectsKey(userId) });
      queryClient.setQueryData(userSubjectsKey(userId), saved);
      // ダッシュボードのおすすめは選んだ科目で変わる
      queryClient.invalidateQueries({ queryKey: DASHBOARD_OVERVIEW_KEY_ROOT });
    },
    onError: (error) => {
      if (isBadRequest(error)) {
        queryClient.invalidateQueries({ queryKey: availableSubjectsKey(userId) });
      }
    },
  });
};
