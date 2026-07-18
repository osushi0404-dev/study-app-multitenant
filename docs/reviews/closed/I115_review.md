# I115 実装レビュー（SubjectViewSet.public 未認証 401 修正）

- 関連: docs/issues/open/I115.md / docs/plans/open/plan_I115.md / GitHub #213 / Draft PR #228
- レビュー対象コミット: f372e1b（実装）・81d0236（code-review Low 対応）

## レビュー観点（計画に対応）

### 1. 認可の変更範囲（最重要・最小権限）
- [x] `views.py` の差分が `get_permissions()` への `if self.action == 'public': return [permissions.AllowAny()]` 追加（2行）**のみ**である（git diff で確認）
- [x] 分岐は `self.action == 'public'` の**完全一致**（in 判定・部分一致でない）
- [x] 更新系（create/update/partial_update/destroy = `IsAuthenticated + IsOrgAdmin`）・参照系（else = `IsAuthenticated`）の分岐が不変更
- [x] I104 回帰テスト（更新系 403・admin CRUD・未認証 list 401）が引き続き PASS

### 2. 情報露出（テナントスコープ・フィールド）
- [x] `public` の返却コード（`views.py:48-82`）に変更がない（slug 指定組織の `id`/`name`/`description` のみ・`values()` 固定）
- [x] TC-AUTO-01 のテナントスコープ assert（他組織科目の非混入）と露出フィールド assert（キー集合完全一致）が PASS
- [x] false-green 注入検証（クエリ全件化・フィールド追加の2注入で RED）を実施・復元済み（git diff が実装差分のみ）

### 3. 両ルートの復旧
- [x] `/api/subjects/public/` と `/api/organizations/subjects/public/` の**両ルート**で未認証 200（TC-AUTO-01・parametrize）
- [x] 存在しない slug → 空リスト 200 が両ルートで不変（TC-AUTO-03）
- [x] レガシー slug 変換（未指定/`register`→`personal`）が両ルートで不変（TC-AUTO-05）
- [x] dev 実環境でも両ルート 200 を確認（manual No.3・修正前実測 401 との比較）

### 4. テスト
- [x] TDD RED（実装前 401 で FAIL）を確認・記録済み（AC「false-green でない」に対応)
- [x] 全体回帰: problems/tests 全件 PASS（既存 68 件 + 新規 8・回帰なし）
- [x] 登録画面の目視確認（manual No.4・Human）OK

### 5. 計画との一致
- [x] 変更ファイルが `backend/problems/views.py`・`backend/problems/tests/test_I115_public_unauth.py` のみ（計画外の変更がない）
- [x] 実装コードが計画書のコード例と一致

## 敵対的レビュー観点（独立サブエージェント向け・「合格を反証せよ」）
- `get_permissions()` の分岐追加で、`public` **以外**の action（list/retrieve/カスタム action すべて）の適用権限が1つも変わっていないことを、全 action の列挙と実レスポンス（未認証/非admin/admin）で反証せよ。
- `AllowAny` 化した `public` から、返却仕様（slug 指定組織の id/name/description）を超える情報が取れる入力が本当に無いか（slug の別名 `register`・`slug` 未指定・非アクティブ組織・クエリパラメータ注入）を実リクエストで反証せよ。
- 両ルート以外に `SubjectViewSet` が配線されている URL が無いか（`router.register` の全走査）を反証せよ。
- 回帰テストの fixture（2組織）が他テストのグローバル状態（キャッシュ・personal 組織）と干渉し false-green/false-red にならないか反証せよ。

## 結果
（2026-07-18 記入）

### 実装結果評価
- 観点 1〜5 全項目 OK（チェック済み）。エビデンス: `docs/reviews/I115_code_review_20260718_0109.md`（受け入れ条件 5 件すべて ✅・Blocker/High 0・VERDICT: OK）＋ `git diff origin/develop...HEAD` の確認（コード変更は `views.py` の 2 行追加と新規テストファイルのみ。他 action の権限・`public` の返却コード・FE は不変更）。
- code-review 指摘は Low 2 件のみ（TC-AUTO-05 の未使用 fixture・組織 fixture の `is_active` 暗黙依存）: いずれもコミット 81d0236 で対応済み（対応後 8 passed 再確認）。Low のみのため再レビュー不要（CI で担保）。
- 敵対的レビュー観点は独立レビューエージェント（code-review スクリプト）が受け入れ条件照合・品質/セキュリティ観点で実施し VERDICT OK。個別の反証記録は code-review 記録を参照。

### テスト結果
- 自動（/test 2026-07-18）: Backend 全体 **76 passed**（新規 8 含む・回帰なし）・FE Jest **2 suites / 7 passed**・E2E **7 passed**（認証・認可 I102・テナント分離・クイズセッション）。停止条件該当なし。
- TDD RED（実装前 8 failed=401）・false-green 注入検証（2 注入とも RED）確認済み（`docs/tests/open/I115_auto_test.md`）。
- 手動: 全 4 項目 OK（Claude 3・Human 1＝登録画面スクリーンショット確認・2026-07-18。`docs/tests/open/I115_manual_test.md`）。

### 総合判定
OK — 残作業は /retro（推奨）→ /close → PR #228 の Approve & Merge のみ。
