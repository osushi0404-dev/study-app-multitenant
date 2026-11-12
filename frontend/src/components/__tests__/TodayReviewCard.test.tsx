/**
 * 今日の復習のカード（I452・TC-16）
 * 件数・0 問の文言・読み込み中・読み込みの失敗と再読み込み・遷移先・科目の切り替え
 */
import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TodayReviewCard from '../TodayReviewCard';
import apiClient from '../../services/api';

jest.mock('../../services/api');

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const URL = '/api/study/spaced-repetition/review_summary/';
const mockGet = apiClient.get as jest.Mock;

describe('TodayReviewCard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('読み込み中の表示を出す', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<TodayReviewCard subjectId="all" />);
    expect(screen.getByRole('status')).toHaveTextContent('今日の復習を読み込み中…');
  });

  it('件数と「復習を始める」を出し、「すべて」なら科目なしで復習を始める', async () => {
    mockGet.mockResolvedValue({ data: { due_count: 3, next_review_date: null } });
    render(<TodayReviewCard subjectId="all" />);

    expect(await screen.findByRole('heading', { name: '今日の復習 3問' })).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledWith(URL, { params: {} });
    await userEvent.click(screen.getByRole('button', { name: '復習を始める' }));
    expect(mockNavigate).toHaveBeenCalledWith('/quiz?mode=review');
  });

  it('科目を選んでいれば、その科目で数えて、その科目で復習を始める', async () => {
    mockGet.mockResolvedValue({ data: { due_count: 1, next_review_date: null } });
    render(<TodayReviewCard subjectId="5" />);

    await screen.findByRole('heading', { name: '今日の復習 1問' });
    expect(mockGet).toHaveBeenCalledWith(URL, { params: { subject_id: '5' } });
    await userEvent.click(screen.getByRole('button', { name: '復習を始める' }));
    expect(mockNavigate).toHaveBeenCalledWith('/quiz?mode=review&subject=5');
  });

  it('0 問なら次の日付つきで「今日の復習はありません」を出す', async () => {
    mockGet.mockResolvedValue({ data: { due_count: 0, next_review_date: '2026-11-15' } });
    render(<TodayReviewCard subjectId="all" />);

    expect(await screen.findByText('今日の復習はありません（次は 11月15日）')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '復習を始める' })).not.toBeInTheDocument();
  });

  it('0 問で次の日付が無ければ「今日の復習はありません」だけを出す', async () => {
    mockGet.mockResolvedValue({ data: { due_count: 0, next_review_date: null } });
    render(<TodayReviewCard subjectId="all" />);

    expect(await screen.findByText('今日の復習はありません')).toBeInTheDocument();
  });

  it('読み込みに失敗したら文言と「再読み込み」を出し、押すと読み直す', async () => {
    mockGet.mockRejectedValueOnce(new Error('network'));
    mockGet.mockResolvedValueOnce({ data: { due_count: 2, next_review_date: null } });
    render(<TodayReviewCard subjectId="all" />);

    expect(await screen.findByText('今日の復習を読み込めませんでした')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '再読み込み' }));
    expect(await screen.findByRole('heading', { name: '今日の復習 2問' })).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledTimes(2);
  });

  it('科目を切り替えたら読み直し、古い応答で新しい表示を上書きしない', async () => {
    let resolveOld: (value: unknown) => void = () => {};
    mockGet.mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve; }));
    mockGet.mockResolvedValueOnce({ data: { due_count: 4, next_review_date: null } });

    const { rerender } = render(<TodayReviewCard subjectId="1" />);
    rerender(<TodayReviewCard subjectId="2" />);
    expect(await screen.findByRole('heading', { name: '今日の復習 4問' })).toBeInTheDocument();

    await act(async () => {
      resolveOld({ data: { due_count: 9, next_review_date: null } });
    });
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: '今日の復習 4問' })).toBeInTheDocument();
    });
    expect(mockGet).toHaveBeenLastCalledWith(URL, { params: { subject_id: '2' } });
  });
});
