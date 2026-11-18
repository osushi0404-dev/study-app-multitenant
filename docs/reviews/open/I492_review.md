# I492 レビュー: 古い学習記録の表（StudyLog など）の片付け

## 変更概要
- 使われなくなった古い学習記録の表（`StudyLog`・`DailyStudySummary`・`StudyGoal`・`ProblemAttempt`）と、それを読む・書くコード（学習記録の API・管理画面・学習リマインダーのメール・呼ばれていない 2 つのタスク）を消し、`SpacedRepetitionReview.study_session` の列と 4 つのテーブルを消すマイグレーションを足す（Danger Ops）。夜 2 時の学習分析の更新の対象を、クイズの答えか復習で判定する形にする

## 変更点
- `backend/studylogs/tasks.py`: `update_daily_analytics_task` の対象を、直近 7 日に `QuizAnswer` か `SpacedRepetitionReview` がある利用者（2 つの `id__in` の副問い合わせ）にした。`send_study_reminders_task`・`export_user_data_task` を消した
- `backend/core/tasks.py`: `generate_system_report_task` を消した。`backend/core/celery.py`: `send-study-reminders` の登録を消した
- `backend/studylogs/views.py`・`urls.py`・`serializers.py`: 学習記録・統計・目標の 3 つの API と 7 つのシリアライザを消した。`submit_review`・`services.review_card` から `study_session` を外した
- `backend/studylogs/admin.py`: 4 モデルの登録しか無かったのでファイルごと消した
- `backend/studylogs/models.py`: `StudyLog`・`DailyStudySummary`・`StudyGoal`・`ProblemAttempt` と 2 つの QuerySet、`SpacedRepetitionReview.study_session` を消した
- `backend/studylogs/migrations/0002_remove_legacy_study_logs.py`（新規・Danger Ops）: 列の削除と 4 モデルの削除の 5 つの操作。開発の DB にはまだ流していない
- テスト: `test_I492_remove_legacy_study_logs.py`（新規・TC-05〜TC-08）。I446・I431・I455・I466・I473 のテストを、消したモデル・経路に合わせて直した

## 影響範囲
- Backend/Frontend/DB/Config: Backend（`studylogs`・`core/tasks.py`・`core/celery.py` とテスト）・DB（列 1 つとテーブル 4 つ〔と多対多の表〕の削除）・Config（Celery の定期処理の登録から `send-study-reminders` を外す）。Frontend なし

## テスト結果
- 自動: 手元で backend 全件 passed（768 件・/simplify の前）。決定論ゲート 4 行とも exit 0。CI は review-gate で記入
- 手動: （test-gate で記入）

## 計画との差分
- あり（計画書の計画変更記録のとおり。方式・範囲・受け入れ条件は変えていない）: I431・I455 のテストの直し方の具体化と訂正、`update_daily_analytics_task` のクエリの書き方（副問い合わせ）、`admin.py` をファイルごと削除、新しいテストで共有の `answer` を使用

## ロールバック
- 計画書 `docs/plans/open/plan_I492.md` の 7

## 自律判断の記録
- [plan-review] 計画レビューは HIGHRISK（DB スキーマの重要な変更・API 経路の削除）。Warning 2 件（TC-04 の記録・R1 の確かめの追加）は計画書とテスト文書に追記し、方式・範囲を変えないので再レビューしない — 計画変更記録のとおり
- [design-security-review] Blocker・High・Medium は無し、Low 4 件（バックアップの置き場所・既存の `str(e)`・利用者の選び方・管理画面の削除）は計画のままで守れるので計画を変えない — 計画書「## セキュリティレビュー結果」
- [implement] ステップ 1: 実装の前の開発の DB の件数は StudyLog 0・DailyStudySummary 0・StudyGoal 0・ProblemAttempt 0・SpacedRepetitionReview 6（study_session あり 0）。バックアップは `.evidence/I492/legacy_backup.json`（0 件・gitignore 済み）— Danger Ops の消す前の記録（AC7）
- [implement] `makemigrations` が出した 12 個の細かい操作を、同じ結果になる 5 つ（列の削除→4 モデルの削除）に書き直した — 計画の 4 の表のとおり。`makemigrations --check` が「No changes detected」で、状態が同じことを確かめた
- [implement] I431 の TC-22 の材料を `StudyLog` から `QuizSession` に、I446 の失敗の注入を目標の経路から復習の記録の経路に、I455 の例文のモデル名を残るモデルに替えた — 消したモデル以外の確かめ（境界の関数・絞り込みを外すと落ちること・コメントの検査）を失わないため（計画変更記録）
- [implement] /simplify の結果: 共有のテスト用データ `problems.tests.i466_data.answer` を使う・利用者の選び方を副問い合わせにする・空の `admin.py` を消す・定期処理のコメントを決まりだけにする、を直した。直さなかったもの: TC-07 の操作の比べを `describe()` の文字列にする案と、`LEGACY_TABLES` をモデルから導く案 — 手で書いた一覧のほうが、マイグレーションと独立した確かめになるため
- [implement] 開発の DB には `0002` を流していない（M3 で `[ ] 0002` を確認）。コンテナも起こし直していない — 計画書 8 の R1・9 の Danger Ops
- [review-gate] 1 回目: CI の E2E Tests (Playwright) が失敗（run 44207144182）。ほかの CI のジョブは通過。`CI_WAIT: FAIL` なので fix-loop へ回す — 手順どおり
- [fix-loop] E2E の失敗の原因は I492 の変更ではない: 2026-11-17 午後から `ubuntu-latest` が Ubuntu 26.04 になり、`@playwright/test` 1.59.1（26.04 に非対応。1.65.1 は対応）がブラウザを入れる段で止まる。I492 の中では直さず、既存の #432（Dependabot #377 の Playwright の版上げを取り込む）を最優先に前倒しして直す。I492 はここで止め（STAGE_DONE を書かない）、#432 のマージの後に develop を取り込んで `/proceed I492` で再開する — ユーザーの方針「ハーネス・ループの BP の観点でベストなやり方で」（2026-11-18）。実行環境を古い版に固定する案はユーザーの指摘（古い版でテストし続けるのは BP ではない）で採らない。#432 に経緯をコメント済み

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
