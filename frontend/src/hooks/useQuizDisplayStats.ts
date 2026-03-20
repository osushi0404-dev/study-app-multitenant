import { useMemo } from 'react';
import { QuizSession, QuizResult } from '../types/quiz';

/**
 * クイズ画面の表示用統計値を計算するカスタムフック
 *
 * 結果表示中（showResult === true）の場合は、バックエンドから返される値から-1して
 * 現在解いている問題の番号を表示する。これにより、「次の問題」ボタンを押すまでは
 * 画面表示が現在の問題のままになり、UXが向上する。
 *
 * @param session - クイズセッション情報（nullの場合はデフォルト値を返す）
 * @param showResult - 結果表示中かどうか
 * @param result - 現在の問題の回答結果
 * @param totalProblemsInSubject - 科目の総問題数
 * @returns 表示用の統計値
 */
export const useQuizDisplayStats = (
  session: QuizSession | null,
  showResult: boolean,
  result: QuizResult | null,
  totalProblemsInSubject: number
) => {
  return useMemo(() => {
    // sessionがnullの場合はデフォルト値を返す
    if (!session) {
      return {
        displayAnsweredProblems: 0,
        displayCorrectAnswers: 0,
        currentRound: 1,
        problemInRound: 1,
        progressPercentage: 0,
      };
    }

    // 結果表示中は、まだ現在の問題を解いている状態なので-1する
    const hasAnsweredCurrent = showResult;
    const displayAnsweredProblems = hasAnsweredCurrent
      ? session.answered_problems - 1
      : session.answered_problems;

    // 正解数も同様に補正（ただし、実際に正解した場合のみ）
    const displayCorrectAnswers = hasAnsweredCurrent && result?.is_correct
      ? session.correct_answers - 1
      : session.correct_answers;

    // 周回カウンターの計算
    const currentRound = Math.floor(displayAnsweredProblems / totalProblemsInSubject) + 1;
    const problemInRound = (displayAnsweredProblems % totalProblemsInSubject) + 1;

    // プログレスバーの進捗率計算
    const progressPercentage = totalProblemsInSubject > 0
      ? (problemInRound / totalProblemsInSubject) * 100
      : (displayAnsweredProblems / session.total_problems) * 100;

    return {
      displayAnsweredProblems,
      displayCorrectAnswers,
      currentRound,
      problemInRound,
      progressPercentage,
    };
  }, [
    session,
    showResult,
    result?.is_correct,
    totalProblemsInSubject,
  ]);
};
