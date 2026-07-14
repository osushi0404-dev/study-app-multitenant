# I103 手動テスト（越境 subject 書き込み防止）

- 関連: docs/issues/open/I103.md / docs/plans/open/plan_I103.md / GitHub #193
- 前提: BE のみの変更（UI なし）。挙動確認は自動テスト（`I103_auto_test.md`）が主。本文書はコード/挙動の目視・確認系。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `backend/problems/views.py` の `perform_create` を確認 | 冒頭に `subject.organization_id != self.request.user.organization_id` の場合 `PermissionDenied('他組織の科目には問題を作成できません')`（403）を raise する分岐がある | Claude | - | |
| 2 | 同 `generate_ai` を確認 | `Subject.objects.get(id=subject_id)` 取得直後・生成 try の前に org 一致チェックがあり、越境時 `Response({'error': '他組織の科目には問題を作成できません'}, status=403)` を返す | Claude | - | |
| 3 | 同 `generate_adaptive` を確認 | 同様の org チェック（403）が subject 取得直後に入っている | Claude | - | |
| 4 | `docker compose exec -T backend python -m pytest problems/tests/test_I103_cross_org_create.py -q` を実行 | 新規 TC 全 PASS | Claude | - | |
| 5 | `docker compose exec -T backend python -m pytest problems/tests/ -q` を実行 | 既存 50 件＋新規が全 PASS（回帰なし） | Claude | - | |
| 6 | 越境拒否 status が 403 で、既存 `upload_image`/`delete_image`（403）と一致していることを diff/grep で確認 | create/AI の追加分がいずれも `HTTP_403_FORBIDDEN` / `PermissionDenied`（403）を使用 | Claude | - | |
