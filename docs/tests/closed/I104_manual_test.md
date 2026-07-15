# I104 手動テスト（FE ルートガード）

対象: `frontend/src/App.tsx`（`subject-management`・`subject-management/:id` を `<OrgAdminRoute>` でラップ）

使用アカウント（同一組織・データあり前提。実アカウントは /test 時に確定）:
- admin: `role='admin'` のユーザー
- 非admin: `role='user'` のユーザー

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| TC-MANUAL-01 | 非admin でログインし、URL に `/subject-management` を直接入力して遷移 | MUI Alert（severity=error）「このページにアクセスする権限がありません。管理者権限が必要です。」が表示され、科目管理 UI（一覧・編集・削除ボタン）は描画されない | Human | | `OrgAdminRoute` 委譲 |
| TC-MANUAL-02 | 非admin で `/subject-management/1`（既存科目 id）を直接入力して遷移 | 同上（Alert 表示・科目詳細/編集 UI 非表示） | Human | | |
| TC-MANUAL-03 | admin でログインし `/subject-management` および `/subject-management/:id` に遷移 | 従来どおり科目管理 UI（一覧・詳細・編集・削除）が表示され操作できる | Human | | 回帰確認 |
| TC-MANUAL-04 | 非admin で Layout ナビに科目管理リンクが表示されないこと（既存挙動の回帰） | ナビに「科目管理」項目が出ない（`isOrgAdmin` で非表示） | Human | | 既存挙動の維持確認 |
| TC-MANUAL-05 | 未ログイン状態で `/subject-management` に直接遷移 | `/login` にリダイレクトされる（`OrgAdminRoute` の未ログイン分岐） | Human | | |

## Claude 実施可の静的確認（コード確認で代替可能な項目）
| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| TC-STATIC-01 | `App.tsx` の subject-management 系 2 ルートが `<OrgAdminRoute>` でラップされていることを grep 確認 | 2 ルートとも `OrgAdminRoute` を含む | Claude | OK | 実装で 2 ルートとも `<OrgAdminRoute>` 化済み（App.tsx L84-85） |
| TC-STATIC-02 | `get_permissions()` に `update`/`partial_update`/`destroy` が admin 分岐に含まれることを確認 | admin 分岐に 4 アクション（create 含む）が列挙 | Claude | OK | `if self.action in ('create','update','partial_update','destroy')` |
| TC-INJECT-01 | 否定 TC の false-green 注入検証（auto_test「否定・回帰テストの false-green 自己検証」節の記録先）。`get_permissions()` の update/destroy を一時的に else へ戻し `pytest test_I104_subject_authz.py::test_non_admin_cannot_mutate` を実行 → 元に戻して再実行 | 改変時 **FAIL**（200/204 を返す）、復元後 **PASS**。両結果を本行に記録 | Claude | OK | Red（修正前）: `test_non_admin_cannot_mutate` FAIL（PUT が assert 200==403）。Green（修正後）: PASS。false-green でないことを確認 |
| TC-SMOKE-01 | `public` 経路の未認証到達性の回帰確認（Info 対応）。未認証で `GET /api/subjects/public/?slug=<org_slug>` を叩く | **200**（未認証で科目リスト取得可）。もし 401 なら I104 の経路不変により本 PR とは無関係の pre-existing 挙動として別イシュー起票を検討 | Claude | ⚠️ 401 | **pre-existing bug 検出**（I104 と無関係）。実測: 未認証 `GET /api/subjects/public/?slug=personal` → **401**。原因: override 済み `get_permissions()` が `@action(permission_classes=[AllowAny])` を無視し else 分岐で `[IsAuthenticated()]` を返すため。I104 は else 分岐不変更＝経路保全（本 PR で退行なし）。→ **別イシュー起票候補**（登録画面の未認証科目取得への影響を要調査） |
