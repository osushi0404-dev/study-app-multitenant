# I102 レビュー: 問題管理を組織管理者権限に限定（read+write を admin 限定・FE/BE 二重ガード）

> 実装完了後・`/plan-issue-review` および実装後レビューで記入する。

## 変更概要
- `ProblemViewSet` 全体（参照＋更新系・AI生成・画像）を組織管理者（`role == 'admin'`）限定にし、FE（`OrgAdminRoute`＋`Layout` ナビ）と BE（`permission_classes`）で二重ガード。

## 変更点（レビュー対象）
- `backend/problems/views.py`: `ProblemViewSet.permission_classes = [IsAuthenticated, IsOrgAdmin]`（read+write 一律 admin）
- `backend/problems/tests/test_I102_problem_authz.py`（新設）: role 別 authz 結合テスト
- `backend/problems/tests/test_I073_image_update.py`: fixture を admin 化（既存テスト整合）
- `backend/accounts/management/commands/seed_e2e.py`: 非admin `e2e_user_c` 追加
- `frontend/src/components/OrgAdminRoute.tsx`（新設）: `role === 'admin'` 判定ガード
- `frontend/src/App.tsx`: `quiz-management` ルートを `OrgAdminRoute` で保護
- `frontend/src/components/Layout.tsx`: 「問題管理」ナビを org-admin 限定表示
- `e2e/global-setup.ts` / `e2e/playwright.config.ts`: 非admin storageState
- `e2e/tests/problem-management-authz.spec.ts`（新設）: 非admin 遮断 / admin 到達
- `.claude/settings.json`: allowlist に `Edit/Write(docs/issues/**)` 追加（機能非影響）

## レビュー観点（重点）
- [ ] `permission_classes` が全アクション（custom action 含む）に効いているか（override が無いこと）
- [ ] FE ガードが `role === 'admin'` 判定で、既存 `AdminRoute`（is_staff）を流用していないか（org admin ロックアウト防止）
- [ ] 非admin=全経路403 / admin=200-201 の回帰テストが false-green でないか（200→403 の遷移を確認）
- [ ] `test_I073` fixture admin 化後、越境テスト（`test_other_org_cannot_edit`/`test_cross_org_subject_rejected`）が role ゲートで短絡せず越境拒否を検証しているか
- [ ] I078 との hard 依存（I102 先行マージ）が守られているか
- [ ] 最小権限の原則に沿っているか（read も admin 限定＝確定利用モデルで非admin 参照利用者ゼロ）

## 影響範囲
- Backend / Frontend / E2E: 上記。DB: なし。Config: `.claude/settings.json`（allowlist）。

## テスト結果
- 自動: （/test で記入）
- 手動: （/test で記入）

## 計画との差分
- なし / あり（理由）

## ロールバック
- `git revert` で PR コミットを戻せば認可・ガードは元に戻る。DB 影響なし。
