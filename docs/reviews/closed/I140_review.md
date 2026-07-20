# I140 実装レビュー（personal 組織自動作成フォールバック廃止）

- 関連: docs/issues/open/I140.md / docs/plans/open/plan_I140.md / GitHub #251 / Draft PR #254
- レビュー対象コミット: 9b223e8（実装）・84f64b3（/test 実施記録）

## レビュー観点（計画に対応）

### 1. 修正の局所性（書き込みパス削除のみ）
- [x] コード差分が `_get_organization` の else 節のみ（フォールバック `Organization.objects.create(...)` の削除・`logger.error` + `return None` 化）である（git diff で確認）
- [x] 呼び出し側（`create()` の None → 400 分岐）・レスポンス契約・例外ハンドリング・権限クラス・モデル/マイグレーションに変更がない
- [x] 追加した error ログに個人情報・認証情報が含まれない（固定文言のみ）

### 2. フォールバック廃止の完全性
- [x] ビュー内に組織作成コードが残存しない（TC-AUTO-05・`! grep -q "Organization.objects.create" backend/accounts/views.py` が exit 0・plan-review Info 指摘反映の強化判定式）
- [x] フォールバック自動作成に依存する箇所（テスト・スクリプト・runbook）が repo 全体に存在しない（grep で確認）

### 3. personal 不在時の挙動（本イシューの根治）
- [x] personal 不在・slug なし登録が 400・body 完全一致（既存分岐流用・TC-AUTO-01）
- [x] 組織が新規作成されない（TC-AUTO-02・false-green 注入検証済み）
- [x] error ログで環境異常が可観測（TC-AUTO-03・caplog）
- [x] personal 非アクティブのみ存在でも同挙動（TC-AUTO-04）

### 4. 通常状態の無退行
- [x] `test_I131_org_id_rename.py`（slug なし 201 = TC-AUTO-06 含む）が引き続き PASS
- [x] 全体回帰（baseline 90 件）PASS（TC-AUTO-06）
- [x] dev 実環境（personal あり）で slug なし登録 201（manual No.3）

### 5. テスト品質・計画との一致
- [x] TDD RED（実装前: TC-AUTO-01/03/04 FAIL）を確認・記録済み
- [x] TC-AUTO-02 の false-green 注入検証（category 付き自動作成の注入で RED）を実施・Edit で復元済み（git diff が実装差分のみ）
- [x] 変更ファイルが `accounts/views.py`・`accounts/tests/test_I140_personal_org_fallback.py` のみ（計画外の変更がない）

## 敵対的レビュー観点（独立サブエージェント向け・「合格を反証せよ」）
- 「フォールバック廃止で壊れる依存箇所はない」を反証せよ: `Organization.objects.create` 由来の personal 組織を前提とする環境・テスト・スクリプト・ドキュメント（seed/初期化手順含む）を repo 全体 grep で洗い出し、廃止後に壊れるものが本当にゼロか。
- 「既存 400 分岐の流用で契約不変」を反証せよ: TC-AUTO-01 の body 完全一致が広域 except 経由 400（「エラーが発生しました」）や serializer 検証 400 と本当に区別できているか。分岐順序（組織決定 → serializer 検証）が変わっていないか。
- 「TC-AUTO-02 は false-green でない」を反証せよ: 注入検証（category 付き create）が「現実に起こり得る回帰」を代表しているか。IntegrityError で失敗する現行フォールバックとの差を含め、注入なしでも合格する経路が残っていないか。
- caplog TC の決定論性を反証せよ: `'django'` ロガーの propagate 設定・他テストとのログ干渉・並列実行時の caplog 捕捉漏れで false-red/false-green にならないか。
- slug 指定ルート（`/api/auth/register/<slug>/`）の挙動が変わっていないことを反証せよ: `_get_organization(slug)` 側の分岐に触れていないか（I131 TC-AUTO-05/07 の PASS を根拠にできるか）。

## 結果
（2026-07-20 記入）

### 実装結果評価
- 観点 1〜5 全項目 OK（チェック済み）。エビデンス: `docs/reviews/I140_code_review_20260720_0242.md`（受け入れ条件 6 件すべて ✅・Blocker/High/Medium 0・VERDICT: OK）＋ `git diff origin/develop...HEAD` の確認（コード変更は views.py の else 節と新規テストのみ。API 契約・権限クラス・例外ハンドリング不変更）。
- 観点 2 の依存箇所 grep（2026-07-20 close 時）: 旧フォールバック文言は repo 内コード/スクリプト/runbook に残存なし。「個人利用」参照は migration（正の作成経路）とテスト fixture（自作）のみで、廃止したビュー内自動作成に依存する箇所はゼロ。
- code-review 指摘は Low 1 件のみ（TC-AUTO-05 の grep が views.py 全体対象 = 将来の正当な組織作成コード追加時に誤検知し得る）→ レビュー自身が「現在は問題なし」と明記・理由記録のうえ見送り。
- 敵対的レビューステージは高リスク判定 No のため非該当（NOT_REQUIRED）。
- 400/500 意味論の是正（personal 不在の 500 化）は I142（#253）本文に引き継ぎ済み（grill-me 時に解決方針・AC を書き換え）。retro 予防処置 P1 は I143（#255）起票済み。

### テスト結果
- 自動（/test 2026-07-20）: Backend 全体 **94 passed**（新規 4 含む・回帰なし）・FE Jest **3 suites / 10 passed**・E2E **7 passed**。停止条件該当なし（初回の Jest/E2E 失敗は I132 依存のコンテナ未同期・webpack キャッシュ失効の環境要因で、コード変更なしに解消。I143 の予防対象）。
- TDD RED（実装前 4 failed・IntegrityError の実発生を実測）・false-green 注入検証（category 付き create 注入で 4 RED・Edit 復元済み）・決定論 grep TC の両方向確認（実装前 exit 1 → 実装後 exit 0）済み（`docs/tests/open/I140_auto_test.md`）。
- 手動: 全 3 項目 OK（すべて Claude 実施・dev 実環境で通常登録 201 と「個人利用」所属を実証・`docs/tests/open/I140_manual_test.md`）。

### 総合判定
OK — 残作業は /close の docs 移動・PR Ready 化と PR #254 の Approve & Merge のみ。
