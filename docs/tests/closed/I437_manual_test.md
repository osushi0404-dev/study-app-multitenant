# I437 手動テスト: 監視の記録から利用者のメールアドレスを外す（個人情報をログに残さない）

- 関連: docs/plans/open/plan_I437.md / Draft PR #482
- 環境: app-1 ワークツリーのコンテナ（dev）。ログはコンテナの `/app/logs/django.log`・`/app/logs/errors.jsonl`
- アカウント: `e2e_user_c@example.com`（組織 A・一般ユーザー。パスワード欄には名前 `E2E_TEST_PASSWORD` を入れる。`docs/runbooks/frontend-verify.md` の表）
- 呼び方: スクラッチパッドに Python のファイルを書き、`docker compose cp` でコンテナの `/tmp/` に入れ、`docker compose exec -T backend python /tmp/<ファイル>` で流す（コンテナの中から `http://localhost:8000` を呼ぶ）。各手順の前に対象のログの行数を控え、それより後の行だけを見る
- 実施: 2026-11-13 00:38・コミット `b11d8524`（レビュー済みの HEAD・gate-check OK）。スクリプトは `manage.py shell --command "exec(open('/tmp/<ファイル>').read())"` で流した

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `django.log` の行数を控える。`e2e_user_c@example.com` の access トークンで `GET /api/problems/` を呼ぶ（計画は `POST /api/auth/login/` でトークンを受け取る手順だったが、パスワードの値がコンテナに無いので、dev DB の利用者から `RefreshToken.for_user` で作った。確かめるログは同じ）。控えた行より後の `django.log` で、`e2e_user_c@example.com` を含む行の件数と、`User Activity:` の行を出す。dev DB で `e2e_user_c@example.com` の `id` も出す | 応答はどちらも 200。メールアドレスを含む行は 0 件。`User Activity:` の行が 1 件以上あり、その JSON に `user_email` のキーが無く、`user_id` が出した `id` と同じ | Claude | OK | 応答は 403（期待の 200 と違う。`/api/problems/` は組織管理者だけの API〔`backend/problems/views.py:165` の `IsOrgAdmin`・I102〕で、一般ユーザーの `e2e_user_c` は 403 になる既存の動き。I437 は認可を変えない。期待結果の 200 は計画の書き誤り）。403 でも利用者の操作の記録は書かれるので、確かめる点は満たす。控えた後の 133 行でメールアドレスを含む行 0 件。`User Activity:` の行 1 件・`user_email` のキー無し・`user_id` が dev DB の `id`（`a8a774d8-…`）と同じ |
| 2 | `errors.jsonl` の行数を控える。`POST /api/auth/login/` をフォームの形（`application/x-www-form-urlencoded`）で、`email=i437_nobody@example.com`・`password=wrong` で 1 回だけ呼ぶ（いない利用者なので、`e2e_user_c` のログインの制限に当たらない）。控えた行より後の `errors.jsonl` で、その呼び出しの記録の `request.body` を出す | 応答は 4xx。記録の `request.body` の `email` と `password` が `[REDACTED]`。控えた行より後に `i437_nobody@example.com` を含む行が 0 件 | Claude | OK | 応答は 415（ログインの API はフォームの形を受けない設定。4xx なので記録される）。控えた後の 33 行の記録の `request.body` が `{"email": "[REDACTED]", "password": "[REDACTED]"}`。`i437_nobody@example.com` を含む行 0 件・`"wrong"` も 0 件 |

結論: OK
