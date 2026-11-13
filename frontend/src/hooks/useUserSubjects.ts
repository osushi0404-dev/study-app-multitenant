/**
 * 利用者が選んだ科目の一覧（I487）
 * 取得の失敗を「科目 0 件」と取り違えないよう、状態を分けて返す
 */
import { useCallback, useEffect, useState } from 'react';
import SubjectService from '../services/subjectService';
import { Subject } from '../services/types';

export type UserSubjectsState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'success'; subjects: Subject[] };

export const useUserSubjects = () => {
  const [state, setState] = useState<UserSubjectsState>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let ignore = false;
    setState({ status: 'loading' });
    SubjectService.getUserSubjects()
      .then((subjects) => {
        if (!ignore) setState({ status: 'success', subjects });
      })
      .catch((error) => {
        if (ignore) return;
        console.error('Error loading subjects:', error);
        setState({ status: 'error' });
      });
    return () => {
      ignore = true;
    };
  }, [attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  return { state, retry };
};
