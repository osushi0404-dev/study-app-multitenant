# I158 実装レビュー（クイズ開始時のセッション二重作成の是正）

- 関連: docs/issues/open/I158.md / docs/plans/open/plan_I158.md / GitHub #275 / Draft PR #317
- レビュー対象コミット: 7d9ba67（/code-review 20261024_1738）・b70cc66（敵対的第 1 周の修正）・以降の第 2 周の修正と /test 記録

## レビュー観点（計画に対応）

### 1. 不変条件（1 ユーザー 1 有効セッション）
- [x] 部分ユニーク制約 `uniq_active_quizsession_per_user` がモデルとマイグレーション `0021` にある（TC-09・TC-20）
- [x] 開始処理が `transaction.atomic` 内でユーザー行を `select_for_update` してから、キー照合 → 既存終了 → 新規作成を行う（TC-07・TC-08・false-green 注入済み）
- [x] `IntegrityError` が 409 に変換され、500 にならない（TC-10）
- [x] `submit_answer`・`end` が `update_fields` 指定で保存し、開始処理が終了させた `is_active` を書き戻さない（TC-18・TC-19）

### 2. 冪等性（Idempotency-Key）
- [x] 同じキーは 200 で同じセッション、異なるキーは後勝ちで 201、キー無しも受け付ける（TC-01〜TC-04）
- [x] UUID でないキー（空文字含む）は 400、同じキーで科目が違えば 422、終了済みでもそのまま返す（TC-05・TC-06・TC-15）
- [x] キーの照合が必ず `user` で絞られ、他人のセッションを返さない（TC-16）
- [x] キーの値が応答・ログに出ない

### 3. API の締め
- [x] `http_method_names = ['get', 'post', 'head', 'options']` で PUT/PATCH/DELETE が 405（TC-11）
- [x] `is_active`・`started_at` が読み取り専用（TC-12）
- [x] `permission_classes = [permissions.IsAuthenticated]`・`get_queryset` が不変更（TC-17）
- [x] CORS 許可ヘッダに `idempotency-key` があり、許可オリジンは不変更（TC-13）

### 4. マイグレーション
- [x] 列追加・データ・制約の 3 本に分かれ、`0020` の逆方向が noop（ロールバックは `migrate problems 0018`）
- [x] まっさらな DB で通る（TC-21）・dev DB で通り重複が 0 件（手動 No.1〜3）
- [x] データマイグレーションが「最新以外」だけを終了扱いにし、削除しない・終了済みの行の `ended_at` を変えない（TC-14）

### 5. フロント
- [x] StrictMode でも開始 POST が 1 回・`Idempotency-Key` 付き（TC-30・TC-40・false-green 注入済み）
- [x] `crypto.randomUUID` が無い環境ではヘッダ無しで送る（例外にならない）
- [x] エラー時の挙動が現行どおり（TC-31）・既存の読み込み経路に退行なし（TC-32）
- [x] `react-hooks/exhaustive-deps` 違反なし・型チェック合格（TC-33）

### 6. 設計品質・計画との一致
- [x] 業務ロジックとトランザクション境界が `QuizService.start_session` にあり、ビューは解析と応答の対応付けのみ（Fat View でない）
- [x] `total_problems` の数え方が現行のまま（I166 の範囲に踏み込んでいない）
- [x] 変更ファイルが計画「4. 変更点一覧」の範囲内
- [x] 全体回帰（Backend 103 件・Frontend 10 件 baseline）・E2E 全件合格（TC-22・TC-33・TC-41）

## 敵対的レビュー観点（独立サブエージェント向け・「合格を反証せよ」）
- 「同一ユーザーで有効セッションが 2 件になる経路は無い」を反証せよ: `create` 以外に `is_active=True` の行を作る・戻す経路（admin・`end` 以外のアクション・シリアライザの書き込み・シェル・シード）が残っていないか。制約違反が 500 として漏れる経路が無いか。
- 「同じキーの再送は必ず同じセッションを返す」を反証せよ: 401 後の自動再送・ヘッダの大文字小文字・UUID の別表記（波括弧・ハイフン無し）で別セッションが作られないか。ロック前の照合で取りこぼす時間差が無いか。
- 「他人に影響しない」を反証せよ: 他ユーザーのキーで 200 が返る・他ユーザーの行がロックされ続ける・他ユーザーの有効セッションが終了されるケースが無いか。
- 「マイグレーションは安全」を反証せよ: 同じ `started_at` の重複・`ended_at` が既にある有効行・ユーザー削除済みの行で、`0020` が「最新」を誤選択しないか。`0021` が dev／本番データで失敗し得る条件が残っていないか。
- 「StrictMode でも 1 回」を反証せよ: 科目の切り替え・`id` 付き URL との行き来・アンマウント中の応答で、送信漏れ（開始されない）や二重送信が起きないか。

## 結果
（2026-10-24 記入）

### 実装結果評価
- 観点 1〜6 全項目 OK。エビデンス: `docs/reviews/I158_code_review_20261024_1738.md`（AC 7 件すべて ✅・Blocker/High 0・Medium 1・Low 2・VERDICT: OK）と `docs/reviews/I158_adversarial_review_20261024_1830.md`（2 周・最終 VERDICT: OK）。
- 観点 2「キーの値が応答・ログに出ない」: `QuizSessionSerializer.Meta.fields` に `client_request_id` を含めず（TC-01 で応答に無いことを固定）、開始処理にログ出力を追加していない（diff で確認）。
- 指摘への対応: code-review Medium（もう一度挑戦後の完了画面）・敵対的第 1 周 High（TC-18 が views を通らない）・第 2 周 Medium 2 件（再挑戦の科目引き継ぎ・デプロイ手順の訂正）は修正済み（計画変更記録 5・6）。受け入れ: Medium「TC-14/TC-21 の本物のマイグレーション経路（重複データあり）が CI に無い」（手動 TC-21 と dev DB への実適用で確認済み・CI 化の要否は /retro で判断）、Low「TC-19 の文字列の限界」「end の update_fields に件数列を足す回帰は未検出」「submit_answer の serializer context なし（pre-existing）」。
- 計画外の変更: 「もう一度挑戦」ボタンの呼び出し元追従（変更 2）・科目引き継ぎ（変更 6）・`setSessionComplete(false)`（変更 5）。いずれも計画変更記録に理由付きで記録。

### テスト結果
- 自動（/test 2026-10-24）: Backend **123 passed**・TC-20 exit 0・TC-21 **20 passed**・Frontend **4 suites / 13 passed**・tsc / eslint exit 0・E2E **8 passed**・CI 全ジョブ pass（CI の E2E で `Idempotency-Key` 付きの経路も検証）。
- TDD RED（実装前）・false-green 注入（並行テスト・TC-18/19/20/30/34/40）を確認済み（`docs/tests/open/I158_auto_test.md`）。
- 手動: No.1〜4 すべて OK（すべて Claude 実施・dev DB の重複 5 件を終了扱いにし、重複 0 件・制約 2 つの適用を確認）。

### 総合判定
OK — 残作業は /retro（任意）・/close（docs 移動・PR Ready 化）と PR #317 の Approve & Merge。マージ後、本番に出す際は計画「8. Risk & 回避策」リスク7 の手順に従う。
