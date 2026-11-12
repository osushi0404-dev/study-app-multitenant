import apiClient from './api';

/** 今日の復習の件数と、次の復習日（YYYY-MM-DD・無ければ null） */
export interface ReviewSummary {
  due_count: number;
  next_review_date: string | null;
}

const REVIEW_SUMMARY_URL = '/api/study/spaced-repetition/review_summary/';

/** 今日の復習の件数を取る。subjectId が無ければ全科目 */
export const getReviewSummary = async (subjectId?: string): Promise<ReviewSummary> => {
  const response = await apiClient.get<ReviewSummary>(REVIEW_SUMMARY_URL, {
    params: subjectId ? { subject_id: subjectId } : {},
  });
  return response.data;
};
