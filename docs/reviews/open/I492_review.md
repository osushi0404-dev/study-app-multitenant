# I492 レビュー: 古い学習記録の表（StudyLog など）の片付け

## 変更概要
- 使われなくなった古い学習記録の表（`StudyLog`・`DailyStudySummary`・`StudyGoal`・`ProblemAttempt`）と、それを読む・書くコード（学習記録の API・管理画面・学習リマインダーのメール・呼ばれていない 2 つのタスク）を消し、`SpacedRepetitionReview.study_session` の列と 4 つのテーブルを消すマイグレーションを足す（Danger Ops）。夜 2 時の学習分析の更新の対象を、クイズの答えか復習で判定する形にする

## 変更点
- （実装の後に記入）

## 影響範囲
- Backend/Frontend/DB/Config: Backend（`studylogs`・`core/tasks.py`・`core/celery.py` とテスト）・DB（列 1 つとテーブル 4 つ〔と多対多の表〕の削除）・Config（Celery の定期処理の登録から `send-study-reminders` を外す）。Frontend なし

## テスト結果
- 自動: （実装の後に記入）
- 手動: （test-gate で記入）

## 計画との差分
- なし

## ロールバック
- 計画書 `docs/plans/open/plan_I492.md` の 7

## 自律判断の記録

STAGE_DONE: plan NEXT: plan-review
