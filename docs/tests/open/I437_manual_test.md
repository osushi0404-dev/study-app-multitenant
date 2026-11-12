# I437 手動テスト: 監視の記録から利用者のメールアドレスを外す（個人情報をログに残さない）

- 関連: docs/plans/open/plan_I437.md / Draft PR #482
- 環境: app-1 ワークツリーのコンテナ（dev）。ログはコンテナの `/app/logs/django.log`・`/app/logs/errors.jsonl`
- アカウント: `e2e_user_c@example.com`（組織 A・一般ユーザー。パスワード欄には名前 `E2E_TEST_PASSWORD` を入れる。`docs/runbooks/frontend-verify.md` の表）
- 呼び方: スクラッチパッドに Python のファイルを書き、`docker compose cp` でコンテナの `/tmp/` に入れ、`docker compose exec -T backend python /tmp/<ファイル>` で流す（コンテナの中から `http://localhost:8000` を呼ぶ）。各手順の前に対象のログの行数を控え、それより後の行だけを見る
- 実施: 未実施

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `django.log` の行数を控える。`POST /api/auth/login/`（JSON）で `e2e_user_c@example.com` でログインし、受け取った access トークンで `GET /api/problems/` を呼ぶ。控えた行より後の `django.log` で、`e2e_user_c@example.com` を含む行の件数と、`User Activity:` の行を出す。dev DB で `e2e_user_c@example.com` の `id` も出す | 応答はどちらも 200。メールアドレスを含む行は 0 件。`User Activity:` の行が 1 件以上あり、その JSON に `user_email` のキーが無く、`user_id` が出した `id` と同じ | Claude | | |
| 2 | `errors.jsonl` の行数を控える。`POST /api/auth/login/` をフォームの形（`application/x-www-form-urlencoded`）で、`email=i437_nobody@example.com`・`password=wrong` で 1 回だけ呼ぶ（いない利用者なので、`e2e_user_c` のログインの制限に当たらない）。控えた行より後の `errors.jsonl` で、その呼び出しの記録の `request.body` を出す | 応答は 4xx。記録の `request.body` の `email` と `password` が `[REDACTED]`。控えた行より後に `i437_nobody@example.com` を含む行が 0 件 | Claude | | |

結論: 未実施
