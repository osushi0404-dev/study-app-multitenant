# I140 手動テスト（personal 組織自動作成フォールバック廃止の無退行確認）

- 関連: docs/issues/open/I140.md / docs/plans/open/plan_I140.md / GitHub #251 / Draft PR #254
- 前提: `docker compose up -d backend db redis`（FE 不要・UI 変更なしのため全項目 Claude 実施）
- 補足: 「personal 不在」状態はテスト DB（`--no-migrations`）でのみ再現する（No.1 でカバー）。dev 実環境は migration により personal 組織が存在する通常状態であり、No.3 は「通常状態の登録が退行していない」ことの実環境確認。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docker compose exec backend python -m pytest accounts/tests/test_I140_personal_org_fallback.py -q` を実行 | 全件 PASS（TC-AUTO-01/02/03/04） | Claude | OK（4 passed・2026-07-20） | |
| 2 | `docker compose exec backend python -m pytest --tb=short -q` を実行（全体回帰 = TC-AUTO-06） | 新規含め全件 PASS（既存 90 件・`test_I131_org_id_rename.py` 含め回帰なし） | Claude | OK（94 passed・2026-07-20） | |
| 3 | dev 実環境に対し `manage.py shell -c` の未認証 `APIClient`（`HTTP_HOST='localhost'`）で、personal 組織の存在を確認（`Organization.objects.filter(type='personal', is_active=True)`）した上で `POST /api/auth/register/`（slug なし）を実行。入力値: ユーザーID `i140_smoke`／メール `i140_smoke@example.com`／パスワード `I140TestPass123!`（確認も同値）／科目は personal 組織所属の科目から 1 つ | personal 組織（「個人利用」・id=3 想定）が存在し、登録が `status 201`・「登録完了。メール認証を行ってください。」で成功する（通常状態の挙動に退行なし） | Claude | OK（personal org id=3「個人利用」存在・科目 id=21 で status 201・「登録完了。メール認証を行ってください。」・所属 organization_id=3・2026-07-20） | dev DB に新規ユーザー `i140_smoke` が作成される（テスト用・残置可・I131 の `i131_manual` と同運用） |
