# I103 手動テスト（越境 subject 書き込み防止）

- 関連: docs/issues/open/I103.md / docs/plans/open/plan_I103.md / GitHub #193
- 前提: BE のみの変更（UI なし）。挙動確認は自動テスト（`I103_auto_test.md`）が主。本文書はコード/挙動の目視・確認系。

## 実施結果（2026-07-15）
- **自動テスト**: `problems/tests/` **56 passed**（既存50＋I103 の TC-AUTO-01〜06・回帰なし）。false-green 検証済み（ガード無しで否定TC が RED）。
- **Frontend Jest / E2E**: 本変更（backend のみ）に非該当。CI で全ジョブ green を確認済み。
- **手動テスト（Claude 実施）**: 下表のとおり全項目 OK。3経路のガード（views.py:254/389-390/518-519）・403 の一貫性（upload:634 / delete:751 と一致）を確認。
- **Human 実施項目**: なし。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `backend/problems/views.py` の `perform_create` を確認 | 冒頭に `subject.organization_id != self.request.user.organization_id` の場合 `PermissionDenied('他組織の科目には問題を作成できません')`（403）を raise する分岐がある | Claude | OK | |
| 2 | 同 `generate_ai` を確認 | `Subject.objects.get(id=subject_id)` 取得直後・生成 try の前に org 一致チェックがあり、越境時 `Response({'error': '他組織の科目には問題を作成できません'}, status=403)` を返す | Claude | OK | |
| 3 | 同 `generate_adaptive` を確認 | 同様の org チェック（403）が subject 取得直後に入っている | Claude | OK | |
| 4 | `docker compose exec -T backend python -m pytest problems/tests/test_I103_cross_org_create.py -q` を実行 | 新規 TC 全 PASS | Claude | OK | |
| 5 | `docker compose exec -T backend python -m pytest problems/tests/ -q` を実行 | 既存 50 件＋新規が全 PASS（回帰なし） | Claude | OK | |
| 6 | 越境拒否 status が 403 で、既存 `upload_image`/`delete_image`（403）と一致していることを diff/grep で確認 | create/AI の追加分がいずれも `HTTP_403_FORBIDDEN` / `PermissionDenied`（403）を使用 | Claude | OK | |
