# I115 実装レビュー（SubjectViewSet.public 未認証 401 修正）

- 関連: docs/issues/open/I115.md / docs/plans/open/plan_I115.md / GitHub #213 / Draft PR #228
- レビュー対象コミット: （実装後に記入）

## レビュー観点（計画に対応）

### 1. 認可の変更範囲（最重要・最小権限）
- [ ] `views.py` の差分が `get_permissions()` への `if self.action == 'public': return [permissions.AllowAny()]` 追加（2行）**のみ**である（git diff で確認）
- [ ] 分岐は `self.action == 'public'` の**完全一致**（in 判定・部分一致でない）
- [ ] 更新系（create/update/partial_update/destroy = `IsAuthenticated + IsOrgAdmin`）・参照系（else = `IsAuthenticated`）の分岐が不変更
- [ ] I104 回帰テスト（更新系 403・admin CRUD・未認証 list 401）が引き続き PASS

### 2. 情報露出（テナントスコープ・フィールド）
- [ ] `public` の返却コード（`views.py:48-82`）に変更がない（slug 指定組織の `id`/`name`/`description` のみ・`values()` 固定）
- [ ] TC-AUTO-01 のテナントスコープ assert（他組織科目の非混入）と露出フィールド assert（キー集合完全一致）が PASS
- [ ] false-green 注入検証（クエリ全件化・フィールド追加の2注入で RED）を実施・復元済み（git diff が実装差分のみ）

### 3. 両ルートの復旧
- [ ] `/api/subjects/public/` と `/api/organizations/subjects/public/` の**両ルート**で未認証 200（TC-AUTO-01・parametrize）
- [ ] 存在しない slug → 空リスト 200 が両ルートで不変（TC-AUTO-03）
- [ ] レガシー slug 変換（未指定/`register`→`personal`）が両ルートで不変（TC-AUTO-05）
- [ ] dev 実環境でも両ルート 200 を確認（manual No.3・修正前実測 401 との比較）

### 4. テスト
- [ ] TDD RED（実装前 401 で FAIL）を確認・記録済み（AC「false-green でない」に対応)
- [ ] 全体回帰: problems/tests 全件 PASS（既存 68 件 + 新規・回帰なし）
- [ ] 登録画面の目視確認（manual No.4・Human）OK

### 5. 計画との一致
- [ ] 変更ファイルが `backend/problems/views.py`・`backend/problems/tests/test_I115_public_unauth.py` のみ（計画外の変更がない）
- [ ] 実装コードが計画書のコード例と一致

## 敵対的レビュー観点（独立サブエージェント向け・「合格を反証せよ」）
- `get_permissions()` の分岐追加で、`public` **以外**の action（list/retrieve/カスタム action すべて）の適用権限が1つも変わっていないことを、全 action の列挙と実レスポンス（未認証/非admin/admin）で反証せよ。
- `AllowAny` 化した `public` から、返却仕様（slug 指定組織の id/name/description）を超える情報が取れる入力が本当に無いか（slug の別名 `register`・`slug` 未指定・非アクティブ組織・クエリパラメータ注入）を実リクエストで反証せよ。
- 両ルート以外に `SubjectViewSet` が配線されている URL が無いか（`router.register` の全走査）を反証せよ。
- 回帰テストの fixture（2組織）が他テストのグローバル状態（キャッシュ・personal 組織）と干渉し false-green/false-red にならないか反証せよ。

## 結果
（実装後に記入）

### 実装結果評価
-

### テスト結果
-

### 総合判定
-
