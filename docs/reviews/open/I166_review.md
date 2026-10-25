# I166 実装レビュー（クイズの組織境界）

- 関連: docs/issues/open/I166.md / docs/plans/open/plan_I166.md / GitHub #284 / Draft PR #330
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
（/code-review・/test で記入）
