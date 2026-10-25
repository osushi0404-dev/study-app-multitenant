# I166 実装レビュー（クイズの組織境界）

- 関連: docs/issues/closed/I166.md / docs/plans/closed/plan_I166.md / GitHub #284 / Draft PR #330
- レビュー対象コミット: （/code-review で記入）

## レビュー観点（計画に対応）

### 1. 境界の判定が 1 か所にある
- [ ] 「クイズで扱ってよい科目・問題」が `QuizService.available_subjects` / `available_problems` だけで決まり、開始（`QuizSubjectField`）・開始時の問題数（`start_session`）・出題（`get_next_problem`）・回答（`submit_answer`）のすべてがそれを通る
- [ ] クイズの経路に `Subject.objects` / `Problem.objects` を直接使った取得が残っていない（`views.py` の `QuizSessionViewSet`・`quiz_service.py`）
- [ ] 問題の組織を `subject__organization_id` で判定している（`Problem.organization_id` を使っていない）
- [ ] 判定がキャッシュ（`SubjectService` のキャッシュ）を通っていない

### 2. 越境の拒否（AC）
- [ ] 他組織の科目での開始は存在しない ID と同じ 400・セッションを作らない（TC-01）
- [ ] 科目なしの開始は受け付け、問題数・出題が自組織だけ（TC-03・TC-04・手動 No.3）
- [ ] 他組織・セッションの科目外の問題への回答は `404 {"error": "Problem not found"}`・回答を保存しない・正解と解説を返さない（TC-05・TC-06）
- [ ] 「もう一度挑戦」の経路にも同じ検査（TC-08・手動 No.4）
- [ ] 他組織の科目を持つセッションが既にあっても漏れない（TC-09）
- [ ] 組織に属さないユーザー・context の無いシリアライザは何も受け付けない（TC-10・TC-11）

### 3. 無退行
- [ ] 自組織の科目での開始・出題・回答の応答が従来どおり（TC-02・TC-07）
- [ ] `QuizSessionSerializer` の応答（`subject` は科目 ID）が変わらない（TC-11 ②）
- [ ] 全体回帰（Backend 123 件 baseline）・E2E 全件合格（TC-21・TC-23）・lint／bandit 合格（TC-22）

### 4. 設計品質・計画との一致
- [ ] ビューは薄いまま（判定はサービス、入力の検証はシリアライザ）・`start_session` に二重の検査を足していない
- [ ] `permission_classes`・`get_queryset`・`http_method_names` が不変更
- [ ] 変更ファイルが計画「4. 変更点一覧」の範囲内

## 敵対的レビュー観点（独立サブエージェント向け・「合格を反証せよ」）
- 「他組織の問題文・正解・解説はクイズの API から取れない」を反証せよ: `next_problem`・`submit_answer`・`retrieve`（`answers` の `problem`）・`end`・`list` のどれかで、他組織の問題を含む応答が返る入力（科目なし・`subject: null`・文字列の ID・削除済みの問題・全体共有科目・別ユーザーのセッション ID）が無いか。
- 「他組織の科目・問題があるかどうかは推測できない」を反証せよ: 存在しない ID と他組織の ID で、ステータス・本文・応答時間の差（問題の取得の前後で別のクエリが走る等）が出ないか。
- 「自組織の利用者は従来どおり使える」を反証せよ: 科目なし・科目あり・もう一度挑戦・復習モード・削除済みの問題がある科目で、正常な利用が 400／404 になるケースが無いか。
- 「判定は 1 か所」を反証せよ: クイズの経路で `available_subjects` / `available_problems` を通らない科目・問題の取得が残っていないか。

## 結果
（2026-10-26 記入）

### 実装結果評価
- 観点 1〜4 全項目 OK。エビデンス: 基本レビュー `docs/reviews/closed/I166_code_review_20261025_1230.md`（AC 7 件すべて実装済み・Blocker/High 0・Low 2・VERDICT: OK）、敵対的レビュー 3 記録（`I166_adversarial_review_20261025_1249.md`＝第 1 周・3 体とも確認画面で止まり報告なし／`_1450.md`＝第 2 周・Medium 1 を修正・親による再実証つき／`_1820.md`＝ユーザー承認の延長周・読むだけのレビュー役＋親が実験を実行・範囲内 High 1 を TC-12 で修正）。
- 観点 1「クイズの経路に組織で絞らない取得が残っていない」: `QuizSessionViewSet` と `quiz_service.py` の中で `Problem`／`Subject` を取り出すのは `available_problems`／`available_subjects` だけ（親が読んで確認・延長周の観点 1 も静的に確定）。
- 範囲外で見つかったもの: 学習記録 API（間隔反復のカード作成）の他組織データの漏れ（High・以前からの別経路・実測済み）→ ユーザー決定で別イシュー・最優先。適応的な問題選択（Low）・解説画像がある問題への回答で 500（Low）も別イシューの候補。起票コマンドはデスクトップ。
- 計画外の変更: なし（実装コードは計画どおり。テストの追加〔TC-01 の共有科目・TC-12〕はレビュー指摘への対応で、テスト文書に記録）。

### テスト結果
- 自動（/test 2026-10-26）: TC-20 **14 passed**・TC-21 **137 passed**・TC-22 全 Passed・TC-23 E2E **8 passed**・CI 7 ジョブすべて pass。
- TDD RED（実装前 10 failed / 2 passed）・false-green 注入（出題・回答・開始・組織なし・共有科目・復習モードの 2 分岐）を確認済み（`docs/tests/closed/I166_auto_test.md`）。
- 手動: No.1〜4 すべて OK（すべて Claude 実施・Playwright MCP で画面確認・画像は `.evidence/I166/`）。

### 総合判定
OK — 残作業は /retro・/close と PR #330 の Approve & Merge。retro の材料: 敵対的レビューの第 1 周が確認画面で止まり「通過」になった件（検証の仕組みを白紙から作り直すイシューを I166 のクローズ後に起票・ユーザー指示）。
