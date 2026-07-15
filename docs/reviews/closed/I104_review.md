# I104 実装レビュー記録

- **関連イシュー**: #196
- **計画書**: docs/plans/open/plan_I104.md
- **レビュー対象**:
  - `backend/problems/views.py` `SubjectViewSet.get_permissions()`（更新系を IsOrgAdmin 限定）
  - `frontend/src/App.tsx`（subject-management 系 2 ルートを OrgAdminRoute でラップ）
  - `backend/problems/tests/test_I104_subject_authz.py`（認可回帰テスト新規）

## レビュー観点
- [ ] 更新系（create/update/partial_update/destroy）が `[IsAuthenticated, IsOrgAdmin]` になっているか
- [ ] 参照系（list/retrieve）が `IsAuthenticated` のまま（非admin 200）維持されているか
- [ ] `public`（AllowAny）が不変更・経路保全されているか
- [ ] FE 2 ルートが `OrgAdminRoute` でラップされ、片側ガードになっていないか（BE・FE 二重）
- [ ] 認可回帰テストが 403/200/201/204/401 を具体値で固定し、否定 TC が false-green でないか
- [ ] 計画書外の変更（他 ViewSet・参照範囲の縮小等）が混入していないか

## レビュー結果
- plan-review: `docs/reviews/I104_plan_review_20260715_1335.md` → ✅ 完了（HIGHRISK・Blocker 0）
- security-review: Blocker 0 / High 0 / Medium 0 / Low 2（越境404・public 未認証、いずれも既存防御依存）
- code-review: `docs/reviews/I104_code_review_20260715_1415.md` → ✅ VERDICT OK（Blocker/High 0・Medium=public pre-existing bug スコープ外・Low=許容）
- /test（2026-07-15）: Backend pytest `61 passed`・Frontend Jest `7 passed`・E2E 非該当。自動テスト全 PASS・回帰なし。Claude 実施の手動 TC（STATIC-01/02・INJECT-01・SMOKE-01）は manual_test に記録済み（SMOKE-01 は public 401 の pre-existing bug を検出＝別イシュー候補）。
