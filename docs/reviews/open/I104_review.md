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
（実装後に記録）
