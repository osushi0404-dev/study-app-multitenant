# I140 実装レビュー（personal 組織自動作成フォールバック廃止）

- 関連: docs/issues/open/I140.md / docs/plans/open/plan_I140.md / GitHub #251 / Draft PR #254
- レビュー対象コミット: （実装後に記入）

## レビュー観点（計画に対応）

### 1. 修正の局所性（書き込みパス削除のみ）
- [ ] コード差分が `_get_organization` の else 節のみ（フォールバック `Organization.objects.create(...)` の削除・`logger.error` + `return None` 化）である（git diff で確認）
- [ ] 呼び出し側（`create()` の None → 400 分岐）・レスポンス契約・例外ハンドリング・権限クラス・モデル/マイグレーションに変更がない
- [ ] 追加した error ログに個人情報・認証情報が含まれない（固定文言のみ）

### 2. フォールバック廃止の完全性
- [ ] ビュー内に組織作成コードが残存しない（TC-AUTO-05・`! grep -q "Organization.objects.create" backend/accounts/views.py` が exit 0・plan-review Info 指摘反映の強化判定式）
- [ ] フォールバック自動作成に依存する箇所（テスト・スクリプト・runbook）が repo 全体に存在しない（grep で確認）

### 3. personal 不在時の挙動（本イシューの根治）
- [ ] personal 不在・slug なし登録が 400・body 完全一致（既存分岐流用・TC-AUTO-01）
- [ ] 組織が新規作成されない（TC-AUTO-02・false-green 注入検証済み）
- [ ] error ログで環境異常が可観測（TC-AUTO-03・caplog）
- [ ] personal 非アクティブのみ存在でも同挙動（TC-AUTO-04）

### 4. 通常状態の無退行
- [ ] `test_I131_org_id_rename.py`（slug なし 201 = TC-AUTO-06 含む）が引き続き PASS
- [ ] 全体回帰（baseline 90 件）PASS（TC-AUTO-06）
- [ ] dev 実環境（personal あり）で slug なし登録 201（manual No.3）

### 5. テスト品質・計画との一致
- [ ] TDD RED（実装前: TC-AUTO-01/03/04 FAIL）を確認・記録済み
- [ ] TC-AUTO-02 の false-green 注入検証（category 付き自動作成の注入で RED）を実施・Edit で復元済み（git diff が実装差分のみ）
- [ ] 変更ファイルが `accounts/views.py`・`accounts/tests/test_I140_personal_org_fallback.py` のみ（計画外の変更がない）

## 敵対的レビュー観点（独立サブエージェント向け・「合格を反証せよ」）
- 「フォールバック廃止で壊れる依存箇所はない」を反証せよ: `Organization.objects.create` 由来の personal 組織を前提とする環境・テスト・スクリプト・ドキュメント（seed/初期化手順含む）を repo 全体 grep で洗い出し、廃止後に壊れるものが本当にゼロか。
- 「既存 400 分岐の流用で契約不変」を反証せよ: TC-AUTO-01 の body 完全一致が広域 except 経由 400（「エラーが発生しました」）や serializer 検証 400 と本当に区別できているか。分岐順序（組織決定 → serializer 検証）が変わっていないか。
- 「TC-AUTO-02 は false-green でない」を反証せよ: 注入検証（category 付き create）が「現実に起こり得る回帰」を代表しているか。IntegrityError で失敗する現行フォールバックとの差を含め、注入なしでも合格する経路が残っていないか。
- caplog TC の決定論性を反証せよ: `'django'` ロガーの propagate 設定・他テストとのログ干渉・並列実行時の caplog 捕捉漏れで false-red/false-green にならないか。
- slug 指定ルート（`/api/auth/register/<slug>/`）の挙動が変わっていないことを反証せよ: `_get_organization(slug)` 側の分岐に触れていないか（I131 TC-AUTO-05/07 の PASS を根拠にできるか）。

## 結果
（実装後に記入）

### 実装結果評価
（記入待ち）

### テスト結果
（記入待ち）

### 総合判定
（記入待ち）
