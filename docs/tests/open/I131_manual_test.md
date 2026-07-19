# I131 手動テスト（validate-slug／新規登録の復旧確認）

- 関連: docs/issues/open/I131.md / docs/plans/open/plan_I131.md / GitHub #239 / Draft PR #248
- 前提: `docker compose up -d backend db frontend`（No.4/5 はフロント必要）。No.4/5 はシークレットウィンドウ等の**未ログイン状態**で実施（既存アカウント不要・No.5 で新規アカウントを作成する）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docker compose exec backend python -m pytest accounts/tests/test_I131_org_id_rename.py -q` を実行 | 全件 PASS（TC-AUTO-01/03/04/05/06/07） | Claude | OK（6 passed・2026-07-19） | |
| 2 | `docker compose exec backend python -m pytest --tb=short -q` を実行（全体回帰 = TC-AUTO-08） | 新規含め全件 PASS（既存 84 件に回帰なし） | Claude | OK（90 passed・2026-07-19） | |
| 3 | dev 実環境に対し `manage.py shell -c` の未認証 `APIClient`（`HTTP_HOST='localhost'`）で `GET /api/organizations/validate-slug/personal/` と `GET /api/organizations/validate-slug/no-such-org/` を実行（修正前実測と同一コマンド） | 前者: `status 200`・`valid: true`・`organization_name: "個人利用"`・`organization_id` が整数。後者: `status 404`・`valid: false` | Claude | OK（personal: 200・`{"valid":true,"organization_name":"個人利用","organization_id":3}`／no-such-org: 404・`valid:false`・2026-07-19） | 修正前実測（2026-07-19: personal で 500・AttributeError）との比較 |
| 4 | シークレットウィンドウ（未ログイン）で `http://localhost:3000/register/personal` を開く | 組織名「個人利用」が表示され、「組織の確認中にエラーが発生しました」が**表示されない** | Human | | 修正前は常にこのエラー文言が表示されていた（Register.tsx:117-122） |
| 5 | 同画面のまま新規登録を完了する。入力値: ユーザーID `i131_manual`／メール `i131_manual@example.com`／パスワード `I131TestPass123!`（確認も同値）／科目は表示された中から任意の 1 つを選択 | 登録が完了し「登録完了。メール認証を行ってください。」の案内が表示される（400 エラーにならない） | Human | | 修正前は登録送信が必ず 400 で失敗（views.py:88）。dev DB に新規ユーザー `i131_manual` が作成される（テスト用・残置可） |
