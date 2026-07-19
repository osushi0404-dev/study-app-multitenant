# I131 実装レビュー（organization_id 改名漏れ修正・validate-slug 500／登録 API 400）

- 関連: docs/issues/open/I131.md / docs/plans/open/plan_I131.md / GitHub #239 / Draft PR #248
- レビュー対象コミット: 4832b22（実装）・f70e960（手動テスト記録）

## レビュー観点（計画に対応）

### 1. 修正の最小性（改名追随のみ）
- [x] コード差分が計画の 3 行のみ（`accounts/views.py:88`・`:230` の `organization.id` 化、`accounts/serializers.py:91` の `filter(id=value, ...)` 化）である（git diff で確認）
- [x] レスポンスキー名 `organization_id`・serializer 入力フィールド名 `organization_id` が不変更（API 契約維持）
- [x] 権限クラス・例外ハンドリング・ログ出力・モデル/マイグレーションに変更がない

### 2. 改名スイープの完全性
- [x] `.organization_id` の backend 全体 grep で、改名漏れ（Organization インスタンス/クエリセットへの旧名参照）が 3 箇所以外に残存しない（計画の分類表と一致）
- [x] 全体回帰（baseline 84 件）が PASS（FK attname の正当利用に触れていない）

### 3. 両エンドポイントの復旧
- [x] validate-slug: 有効 slug 200（body 完全一致）・存在しない slug 404・非アクティブ組織 404（TC-AUTO-01/03/04）
- [x] 登録 API: slug ルート・slug なしルートとも 201、ユーザーの所属組織・科目アクセス権が正しい（TC-AUTO-05/06）。無効 slug 400 の既存分岐が不変（TC-AUTO-07）
- [x] dev 実環境でも validate-slug 200/404 を確認（manual No.3・修正前実測 500 との比較）

### 4. テスト
- [x] TDD RED（実装前: TC-01→500・TC-05/06→400 で FAIL）を確認・記録済み（AC「false-green でない」に対応）
- [x] false-green 注入検証（404 body 改変・所属組織固定値化の 2 注入で RED）を実施・Edit で復元済み（git diff が実装差分のみ）
- [x] 登録 TC が `RATELIMIT_ENABLE=False`（ファイルローカル autouse）で決定論化されている
- [x] 登録画面の組織名表示・実登録完了の目視確認（manual No.4/5・Human）OK

### 5. 計画との一致
- [x] 変更ファイルが `accounts/views.py`・`accounts/serializers.py`・`accounts/tests/`（新規）のみ（計画外の変更がない）
- [x] イシュー本文がスコープ拡張後の確定値に更新され、GitHub #239 と同期済み（ステップ0）

## 敵対的レビュー観点（独立サブエージェント向け・「合格を反証せよ」）
- `organization_id` の旧名参照（属性・クエリフィルタ・`values()`/`only()`/`order_by` 等あらゆる形）が backend 全体に 3 箇所以外残っていないことを、grep の再実行と分類で反証せよ（migrations/.venv 除外の妥当性も含む）。
- 修正 3 行が外部契約（validate-slug のレスポンスキー・登録 API の入出力形式・エラーレスポンス形式）を 1 つも変えていないことを、実レスポンスの before/after 比較で反証せよ。
- 登録 TC の 201 が「serializer 検証を素通りした」結果でないこと（パスワード validators・user_id regex・科目所属チェックが依然有効なこと）を、無効ペイロードの実リクエストで反証せよ。
- テストの決定論性を反証せよ: redis 共有カウンタ（django-ratelimit）・テスト DB の personal 組織不在（`--no-migrations`）・fixture の slug 衝突（`personal` を他テストが作成していないか）で false-green/false-red にならないか。
- validate-slug の 404 TC が「ルート不在の 404」でも合格しないこと（body 完全一致 assert の実効性）を反証せよ。

## 結果
（2026-07-19 記入）

### 実装結果評価
- 観点 1〜5 全項目 OK（チェック済み）。エビデンス: `docs/reviews/I131_code_review_20260719_2226.md`（受け入れ条件 7 件すべて ✅・Blocker/High/Medium 0・VERDICT: OK）＋ `git diff origin/develop...HEAD` の確認（コード変更は views.py 2 行・serializers.py 1 行・新規テストのみ。API 契約・権限クラス・例外ハンドリング不変更）。
- code-review 指摘は Low 1 件のみ（`_get_organization` の personal 自動作成が `category` 未指定 = スコープ外の既存潜在バグ）→ **I140（#251）として起票済み**（2026-07-19・裏取り済み: `Organization.category` は NOT NULL FK）。
- 敵対的レビューステージは高リスク判定 No のため非該当（NOT_REQUIRED）。受け入れ条件照合・品質/セキュリティ観点は独立レビューエージェント（code-review スクリプト）が実施し VERDICT OK。

### テスト結果
- 自動（/test 2026-07-19）: Backend 全体 **90 passed**（新規 6 含む・回帰なし）・FE Jest **3 suites / 10 passed**・E2E **7 passed**（認証・認可 I102・テナント分離・クイズセッション）。停止条件該当なし。
- TDD RED（実装前 3 failed = TC-01 が 500・TC-05/06 が 400）・false-green 注入検証（2 注入とも RED・Edit 復元済み）確認済み（`docs/tests/open/I131_auto_test.md`）。
- 手動: 全 5 項目 OK（Claude 3・Human 2 = 登録画面スクリーンショット＋実登録の DB 実証・2026-07-19。`docs/tests/open/I131_manual_test.md`）。

### 総合判定
OK — 残作業は /retro（推奨）→ /close → PR #248 の Approve & Merge のみ。
