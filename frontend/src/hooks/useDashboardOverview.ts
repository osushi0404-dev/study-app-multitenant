/**
 * ダッシュボードの数字の取得と状態（I487）
 *
 * - 状態は読み込み中・失敗・成功の 3 つ（データ無しは成功の中の has_data で表す）
 * - 科目を切り替えた後に届いた古い応答は捨てる（I473 F3）
 * - 同じユーザー・同じ科目の取得が進んでいる間は、同じ Promise を使い回す。
 *   開発時の StrictMode が effect を 2 回動かしても、呼び出しは 1 回になる
 */
import { useCallback, useEffect, useState } from 'react';
import dashboardService from '../services/dashboard.service';
import { DashboardOverview } from '../types/api';

export const ALL_SUBJECTS = 'all';

type OverviewState =
  | { status: 'loading'; data: null }
  | { status: 'error'; data: null }
  | { status: 'success'; data: DashboardOverview };

const inFlight = new Map<string, Promise<DashboardOverview>>();

const requestKey = (userId: string, subjectId: string) => `${userId}:${subjectId}`;

const fetchOverview = (userId: string, subjectId: string): Promise<DashboardOverview> => {
  const key = requestKey(userId, subjectId);
  const pending = inFlight.get(key);
  if (pending) return pending;

  const params = subjectId === ALL_SUBJECTS ? {} : { subject_id: subjectId };
  const request = dashboardService.getOverview(params).finally(() => {
    inFlight.delete(key);
  });
  inFlight.set(key, request);
  return request;
};

export const useDashboardOverview = (userId: string, subjectId: string) => {
  // 結果はどの取得のものかを一緒に持つ。科目を切り替えた直後は、前の科目の結果を出さずに読み込み中とする（C7）
  const [result, setResult] = useState<{ key: string; state: OverviewState } | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let ignore = false;
    const key = requestKey(userId, subjectId);
    setResult(null);
    fetchOverview(userId, subjectId)
      .then((data) => {
        if (!ignore) setResult({ key, state: { status: 'success', data } });
      })
      .catch((error) => {
        if (ignore) return;
        // 応答の形が違うときも getOverview が投げる（欠けたキーを 0 で埋めない・I473）
        console.error('Error fetching dashboard data:', error);
        setResult({ key, state: { status: 'error', data: null } });
      });
    return () => {
      ignore = true;
    };
  }, [userId, subjectId, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  const state: OverviewState =
    result && result.key === requestKey(userId, subjectId) ? result.state : { status: 'loading', data: null };
  return { ...state, retry };
};
