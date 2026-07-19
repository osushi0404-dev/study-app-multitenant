# I131 実装レビュー（organization_id 改名漏れ修正・validate-slug 500／登録 API 400）

- 関連: docs/issues/open/I131.md / docs/plans/open/plan_I131.md / GitHub #239 / Draft PR #248
- レビュー対象コミット: （実装後に記入）

## レビュー観点（計画に対応）

### 1. 修正の最小性（改名追随のみ）
- [ ] コード差分が計画の 3 行のみ（`accounts/views.py:88`・`:230` の `organization.id` 化、`accounts/serializers.py:91` の `filter(id=value, ...)` 化）である（git diff で確認）
- [ ] レスポンスキー名 `organization_id`・serializer 入力フィールド名 `organization_id` が不変更（API 契約維持）
- [ ] 権限クラス・例外ハンドリング・ログ出力・モデル/マイグレーションに変更がない

### 2. 改名スイープの完全性
- [ ] `.organization_id` の backend 全体 grep で、改名漏れ（Organization インスタンス/クエリセットへの旧名参照）が 3 箇所以外に残存しない（計画の分類表と一致）
- [ ] 全体回帰（baseline 84 件）が PASS（FK attname の正当利用に触れていない）

### 3. 両エンドポイントの復旧
- [ ] validate-slug: 有効 slug 200（body 完全一致）・存在しない slug 404・非アクティブ組織 404（TC-AUTO-01/03/04）
- [ ] 登録 API: slug ルート・slug なしルートとも 201、ユーザーの所属組織・科目アクセス権が正しい（TC-AUTO-05/06）。無効 slug 400 の既存分岐が不変（TC-AUTO-07）
- [ ] dev 実環境でも validate-slug 200/404 を確認（manual No.3・修正前実測 500 との比較）

### 4. テスト
- [ ] TDD RED（実装前: TC-01→500・TC-05/06→400 で FAIL）を確認・記録済み（AC「false-green でない」に対応）
- [ ] false-green 注入検証（404 body 改変・所属組織固定値化の 2 注入で RED）を実施・Edit で復元済み（git diff が実装差分のみ）
- [ ] 登録 TC が `RATELIMIT_ENABLE=False`（ファイルローカル autouse）で決定論化されている
- [ ] 登録画面の組織名表示・実登録完了の目視確認（manual No.4/5・Human）OK

### 5. 計画との一致
- [ ] 変更ファイルが `accounts/views.py`・`accounts/serializers.py`・`accounts/tests/`（新規）のみ（計画外の変更がない）
- [ ] イシュー本文がスコープ拡張後の確定値に更新され、GitHub #239 と同期済み（ステップ0）

## 敵対的レビュー観点（独立サブエージェント向け・「合格を反証せよ」）
- `organization_id` の旧名参照（属性・クエリフィルタ・`values()`/`only()`/`order_by` 等あらゆる形）が backend 全体に 3 箇所以外残っていないことを、grep の再実行と分類で反証せよ（migrations/.venv 除外の妥当性も含む）。
- 修正 3 行が外部契約（validate-slug のレスポンスキー・登録 API の入出力形式・エラーレスポンス形式）を 1 つも変えていないことを、実レスポンスの before/after 比較で反証せよ。
- 登録 TC の 201 が「serializer 検証を素通りした」結果でないこと（パスワード validators・user_id regex・科目所属チェックが依然有効なこと）を、無効ペイロードの実リクエストで反証せよ。
- テストの決定論性を反証せよ: redis 共有カウンタ（django-ratelimit）・テスト DB の personal 組織不在（`--no-migrations`）・fixture の slug 衝突（`personal` を他テストが作成していないか）で false-green/false-red にならないか。
- validate-slug の 404 TC が「ルート不在の 404」でも合格しないこと（body 完全一致 assert の実効性）を反証せよ。

## 結果
（実装後に記入）

### 実装結果評価
- （未記入）

### テスト結果
- （未記入）

### 総合判定
- （未記入）
