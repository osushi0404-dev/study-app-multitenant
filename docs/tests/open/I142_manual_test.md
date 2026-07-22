# I142 手動テスト計画

- 対象: 登録画面・ログアウト導線・エラー表示（FE コード変更なしの退行確認）
- 前提: `docker compose up -d` で全サービス稼働。backend のコード・settings 変更後は `docker compose restart backend` 済みであること
- 使用アカウント: `e2e_user_a@example.com`（パスワードは `e2e/.env.e2e` の `E2E_TEST_PASSWORD`。`docker-compose.yml:150` が読み込んでいるファイル。E2E で使用中の有効アカウント・組織 `e2e-org-a`）
- 新規登録テスト用の組織 slug: `cute_school`（既存・アクティブ）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docker compose exec backend python manage.py showmigrations token_blacklist` を実行 | `token_blacklist` の全マイグレーションに `[X]`（適用済み）が付いている | Claude | | ステップ1 の migrate 実施確認 |
| 2 | `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/auth/logout/ -H "Content-Type: application/json" -d '{}'` | `400` が出力される（refresh 欠落＝想定内エラー） | Claude | | TC-AUTO-07 の実サーバー版 |
| 3 | `curl -s http://localhost:8000/api/organizations/validate-slug/no-such-org/ -w "\n%{http_code}"` | body が `{"valid":false,"message":"組織 \"no-such-org\" は見つかりません"}`、ステータス `404`（契約不変） | Claude | | |
| 4 | `curl -s http://localhost:8000/api/organizations/validate-slug/cute_school/ -w "\n%{http_code}"` | body に `"valid":true` と `"organization_name"` が含まれ、ステータス `200` | Claude | | |
| 5 | ブラウザで `http://localhost:3000/login` を開き、`e2e_user_a@example.com` + `.env.e2e` のパスワードでログイン | ダッシュボード画面へ遷移する | Human | | |
| 6 | 画面右上のユーザーメニュー → 「ログアウト」をクリック | ログイン画面（`/login`）へ戻る。エラートーストは表示されない | Human | | 変更前は API が 400 を返していたが FE は無視していた。変更後は 200 |
| 7 | 手順 6 の直後、同じアカウントで再ログイン | 正常にログインでき、ダッシュボードが表示される | Human | | 失効させるのは refresh トークンのみで、再ログインは阻害されない |
| 8 | ブラウザで `http://localhost:3000/register/cute_school` を開き、未使用のユーザーID・メールアドレスで登録を完了する | 「かわいいだけじゃだめですか学園への登録が完了しました。メール認証を行ってからログインしてください。」が表示され、3 秒後にログイン画面へ遷移する（slug 指定時は組織名が前置される） | Human | | 正常系の退行確認 |
| 9 | ブラウザで `http://localhost:3000/register/no-such-org` を開く | 「組織が見つかりません」相当のエラー画面が表示される（validate-slug 404 の既存表示・文言は変更なし） | Human | | |
| 10 | 手順 8 の登録画面で、既に使用済みのユーザーID を入力して登録を試みる | 「入力内容にエラーがあります」系のエラーが表示される（500「サーバーエラー」にはならない） | Human | | 想定内 400 の契約維持 |
| 11 | `docker compose logs --tail=50 backend` を実行し、手順 2〜4 の期間のログを確認 | 4xx のリクエストログは出るが、スタックトレース（`Traceback`）は出ていない | Claude | | 想定内エラーで 5xx ログを出さないことの確認 |
| 12 | 手順 5 でログインしたまま 60 分以上放置するか、開発者ツールで `localStorage` の `accessToken` を破棄してから画面操作する | セッションが即座に切れず、既存どおりの挙動（アクセストークン失効時の再ログイン導線）になる。トークン更新の失敗による予期しない強制ログアウトが起きない | Human | | `BLACKLIST_AFTER_ROTATION=False` の実動作確認（TC-AUTO-19 の画面版） |
| 13 | 管理画面 `http://localhost:8000/admin/` にスーパーユーザーでログインし、トップの一覧を確認 | 「Outstanding tokens」「Blacklisted tokens」の項目が表示されない（トークン全文の露出面がない） | Human | | TC-AUTO-20 の画面版 |
