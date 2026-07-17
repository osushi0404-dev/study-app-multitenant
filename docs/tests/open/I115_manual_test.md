# I115 手動テスト（未認証の登録画面向け科目取得の復旧確認）

- 関連: docs/issues/open/I115.md / docs/plans/open/plan_I115.md / GitHub #213 / Draft PR #228
- 前提: `docker compose up -d backend db frontend`（No.4 はフロント必要）。アカウントは**不要**（未認証状態の確認のため。ブラウザはシークレットウィンドウ等でログアウト状態にする）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docker compose exec backend python -m pytest problems/tests/test_I115_public_unauth.py -q` を実行 | 全件 PASS（TC-AUTO-01/03/05） | Claude | OK（8 passed・2026-07-18） | |
| 2 | `docker compose exec backend python -m pytest problems/tests -q` を実行（全体回帰 = TC-AUTO-04） | 新規含め全件 PASS（既存 68 件に回帰なし） | Claude | OK（76 passed・2026-07-18） | |
| 3 | 未認証 `APIClient` で dev 実 DB に対し `GET /api/subjects/public/?slug=personal` と `GET /api/organizations/subjects/public/?slug=personal` を実行（`manage.py shell -c`・修正前実測 401 と同一コマンド） | 両ルートとも `status 200`・personal 組織の科目の JSON 配列（`id`/`name`/`description`）が返る | Claude | OK（両ルート 200・personal の科目 11 件・フィールドは id/name/description のみ・2026-07-18） | 修正前実測（2026-07-17: 両ルート 401）との比較 |
| 4 | シークレットウィンドウ（未ログイン）で `http://localhost:3000/register` を開き、科目選択欄を確認 | 科目リスト（personal 組織の科目）がセレクトに表示される。エラー表示・空のままにならない | Human | OK（2026-07-18・スクリーンショット確認: 登録ステップ2「科目選択」に AWS認定2科目・Python・テスト科目名1〜5・数学・理科・英語の計11件がチェックボックスで表示・エラーなし） | 401 時代は科目が出ない状態だった。`/register/<組織slug>` でも同様に表示されればなお良（任意） |
