<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude）
-->

# I587 手動テスト: 問題・解説の画像を DB に保存し、組織の境界を確かめる API から返す

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M1 | （ステップ 1・コードを変える前）`docker compose exec -T backend python manage.py shell -c` で、`MediaAsset` の件数（全体・`is_deleted`・`organization`／`subject` が null）、`is_deleted=False` のうち `MEDIA_ROOT/storage_key` が無い行（ID・キー）、古い `question_image`・`explanation_image` に値のある問題の件数を読むだけで数える。`git ls-files backend/media` で消すファイルを並べる | 2026-11-19 の調べと同じ: 全体 4・論理削除 0・null 0・ファイルの無い行 4（`org/e2e-org-a/subjects/i472-check/...` の 4 つ）・古い列 0。ファイルは PNG 6・`.gitkeep` 12。違えば数を書き直してから承認を求める | Claude | OK（2026-11-19）: 全体 4・論理削除 0・null 0・ファイルの無い行 4（`382d843e…`・`c0c95afb…`・`ad4263ac…`・`26677f13…`。どれも紐づけ 0 件）・古い列 0／0。ファイルは PNG 6・`.gitkeep` 12 |  |
| M2 | （ステップ 1）`bash scripts/db_backup.sh` で控えを取り、ファイルの大きさを `wc -c` で読む | `backup_<日時>.sql` ができる（`.gitignore` 済みで `git status` に出ない）。大きさ（バイト）を記録する | Claude | OK（2026-11-19）: `backup_I587_before_20261119.sql`（156,338 バイト・`.gitignore` の `backup_*.sql` に当たる） | `scripts/db_backup.sh` はサンドボックスの中で `.env` を読めず止まったので、同じ `pg_dump` を DB のコンテナの中で流して `docker compose cp` で取り出した |
| M3 | （ステップ 4・0025 を流す前）`docker compose exec -T backend python manage.py check_media_migration` | 行ごとの判定が「消す（ファイル無し）」4 行・「移す」0・「済み」0、古い列に値のある問題 0 と出る（M1 と同じ）。`showmigrations problems` で `0025`・`0026` が `[ ]` | Claude | OK（2026-11-19）: 「消す（ファイル無し）」4 行（M1 と同じ ID）・移す 0・済み 0・`deleted_links=0`、古い画像の列に値のある問題 0 件。このとき `0024`〜`0026` は `[ ]` | 中身の表が無い（0024 の前）ときも試しが動くように直した（計画変更記録） |
| M4 | （ステップ 7・承認の後）`DANGER_OK=1 docker compose exec -T backend python manage.py migrate problems` → `showmigrations problems` → M1 の数え方で数え直す | 出力に `I587 media: moved=0 already=0 deleted_assets=4 deleted_links=<紐づけの数>`。`0024`〜`0026` が `[X]`。`MediaAsset` 0 件・`problems_problem` に古い 2 列が無い | Claude | OK（2026-11-19）: `I587 media: moved=0 already=0 deleted_assets=4 deleted_links=0`。`0024`〜`0026` を流した後、`MediaAsset` 0 件・`problems_problem` に `image` を含む列なし・`media_asset_contents.data` の `attstorage` が `e` | `DANGER_OK=1` を前に付けるとサンドボックスの中で動いて `.env` を読めず止まった（DB は変わらず）。前進の `migrate` は見張りの判定の対象外（danger-ops.md）で、承認はステップ 1 で得ていたので前置きなしで流した |
| M5 | Playwright MCP で `e2e_user_a`（組織 A・管理者）でログインし、`/quiz-management` で問題を 1 つ作る（問題画像 2 枚・解説画像 1 枚の PNG）。一覧のプレビューで画像を開き、拡大する。編集のダイアログを開く。`browser_network_requests` で通信を見る | プレビューに問題画像 2 枚・解説画像 1 枚が出て、押すと拡大のダイアログに同じ画像が出る。編集のダイアログの保存済みの画像 3 枚にサムネイルが出る。通信は `GET /api/media/<id>/` が 200（`/media/` への通信が無い）。コンソールに新しい `error` が無い。`backend/media` にファイルが増えていない（`git status --short backend` が空） | Claude | OK（2026-11-19）: 問題「I587確認: 画像のある問題」（科目 I472確認用）を問題画像 2 枚・解説画像 1 枚で作成（201）。プレビューで 3 枚・拡大で解説画像・編集のダイアログで保存済みの 2 枚のサムネイルが出た。通信は `GET /api/media/<id>/` が 3 本とも 200・`/media/` への通信なし。`backend/media` は無いまま。コンソールの `error` は開発サーバーの WebSocket とログイン前の `/api/settings/` 401（どちらも既知）だけ |  |
| M6 | M5 の問題の科目で `e2e_user_c`（組織 A・一般の利用者）がクイズを解く（問題画像を見て、答えて解説画像を見る）。別に、`e2e_user_b`（組織 B）のアクセストークンで M5 の画像の URL を `browser_evaluate` の `fetch`（`Authorization: Bearer`）で取る。未ログインで同じ URL を取る | クイズの問題に画像 2 枚、答えた後の解説に画像 1 枚が出る。組織 B は 404、未ログインは 401。同じ画像を 2 回取ると、2 回目はブラウザのキャッシュか 304 で返る（`browser_network_requests` の状態） | Claude | OK（2026-11-19）: `e2e_user_c` のクイズで問題画像 2 枚・答えた後の解説画像 1 枚が出た。同じ画像を `If-None-Match` 付きで取ると 304。見出しは `image/png`・`private, max-age=3600`・`nosniff`・`default-src 'none'; sandbox`。未ログインは 401。`e2e_user_b`（組織 B）は 404（本文 `{"error": {"main_message": "リソースが見つかりません", ...}}`） |  |
| M7 | （AC14・M5 の後）`bash scripts/db_backup.sh` で控えを取り、大きさを M2 と比べる。`docker run --rm -d --network <app-1 のネットワーク> -e POSTGRES_HOST_AUTH_METHOD=trust --name i587-restore <db のイメージ>` で捨てる DB を起こし、`learning_app` を作って控えを `psql` で戻す。`docker compose stop backend` → `docker compose run -d --rm --use-aliases --service-ports -e DB_HOST=i587-restore backend` で戻した DB に向けた backend を起こす。Playwright MCP で `e2e_user_a` でログインし、M5 の問題をプレビューで開く。終わったら、その backend のコンテナと `i587-restore` を `docker stop` で止め（どちらも `--rm` で消える）、`docker compose start backend` で元の backend を戻す | 戻した DB の画面で M5 の問題に画像 3 枚が出る（`GET /api/media/<id>/` が 200）。控えの大きさの増え方（M2 との差と、画像の合計バイト）を記録する。元の backend に戻した後、`/quiz-management` が今までどおり開く | Claude | OK（2026-11-20）: 控え 156,338 → 160,427 バイト（+4,089。DB の画像は 3 枚・合計 674 バイトで、平文の `pg_dump` では 16 進の文字になる。差には確かめで増えた問題・クイズの記録も入る）。捨てる DB（`i587-restore`）に戻すと `media_asset_contents` が 3 件・674 バイトで元と同じ。戻した DB に向けた backend（`DB_HOST=i587-restore`・開発の backend は止めた）で `e2e_user_a` のプレビューに画像 3 枚が出て、`/api/media/<id>/` が 3 本とも 200。片付けの後、一時のコンテナは無く、開発の backend は元に戻った | 戻し先は捨てるコンテナ。`psql -f` は見張りが止め、`DANGER_OK=1` を付けるとサンドボックスの中で Docker に届かなかったので、ユーザーが `!` で流した（2026-11-20）。確かめに使った「after」の控えは消した |

## 画面確認
<!-- frontend/src を変えたイシューでは 1 行以上必要（test-gate 段階の check-frontend-evidence.sh が確かめる）。
     画像の列は .evidence/I587/ 直下のファイル名（カンマ区切り）。書き方: docs/runbooks/frontend-verify.md -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
| 2026-11-19 18:14 | bc94cfea | `/quiz-management` で画像付きの問題を作り、プレビューを開く | e2e_user_a | 問題画像 2 枚が出る・`/api/media/<id>/` が 200 | 2 枚が出た・3 本とも 200 | preview-a-1.png |
| 2026-11-19 18:15 | bc94cfea | プレビューで解説画像を押して拡大する | e2e_user_a | 拡大のダイアログに解説画像が出る | 出た（元の画像が 120×80 と小さいので小さく出る） | preview-zoom-a-2.png |
| 2026-11-19 18:15 | bc94cfea | 同じ問題の編集のダイアログを開く | e2e_user_a | 保存済みの問題画像 2 枚のサムネイルが出る | 出た | edit-a-3.png |
| 2026-11-19 18:16 | bc94cfea | `/quiz?subject=20` で問題を解く | e2e_user_c | 問題画像 2 枚・答えた後の解説画像 1 枚 | 出た・新しいコンソールのエラーなし | quiz-c-4.png |
| 2026-11-19 18:16 | bc94cfea | 組織 B のトークンで M5 の画像の URL を取る | e2e_user_b | 404 | 404・共通のエラーの形 | 理由: 画面に出ない API の確かめ（`browser_evaluate` の `fetch`） |

| 2026-11-20 02:03 | 94ff0e19 | 控えを戻した捨てる DB に backend を向け、`/quiz-management` で I587 の問題のプレビューを開く | e2e_user_a | 問題画像 2 枚が出る・`/api/media/<id>/` が 200 | 2 枚が出た・3 本とも 200 | restore-preview-a-5.png |
| 2026-11-20 09:10 | （追加の直しの実装中） | `/quiz-management` のプレビュー（追加の直しの後） | e2e_user_a | 問題画像が高さ 300px の枠に縦横の比を保って出る | 出た（選択肢「A. 正解A」の上端 536px） | preview-a-6.png |
| 2026-11-20 09:10 | （追加の直しの実装中） | 同じプレビューで `/api/media/` の通信を 404 にする（ページの中だけ） | e2e_user_a | 画像の枠と同じ高さに「画像を読み込めませんでした」と 44px 以上の「再読み込み」・トーストなし | 出た（選択肢の上端は 536px のまま・トーストなし） | preview-error-a-7.png |
| 2026-11-20 09:10 | （追加の直しの実装中） | 通信を戻して「再読み込み」を押す | e2e_user_a | その画像が高さ 300px で出て、まわりが動かない | 出た（押していない 2 枚は失敗の枠のまま） | preview-retry-a-8.png |
| 2026-11-20 09:38 | ce250a2e | 追加の直しの後（レビュー済み）: `/quiz-management` のプレビュー・API の確かめ | e2e_user_a | 画像が高さ 300px の枠・`W/` 付きの `If-None-Match` で 304・`?ordering=id` で 200 | 高さ 300・初回 200・`W/` で 304・`?ordering=id` で 200 | final-preview-a-9.png |
| 2026-11-20 09:40 | ce250a2e | プレビューで解説画像を押して拡大する | e2e_user_a | 拡大のダイアログに解説画像が実寸で出る | 出た | final-zoom-a-10.png |
| 2026-11-20 09:40 | ce250a2e | 同じ問題の編集のダイアログを開く | e2e_user_a | 保存済みの 2 枚が高さ 150px のサムネイルで出る | 出た | final-edit-a-11.png |
| 2026-11-20 09:41 | ce250a2e | `/quiz?subject=20` で問題を解く | e2e_user_c | 問題画像 2 枚・答えた後の解説画像 1 枚・新しいコンソールのエラーなし | 2 枚・1 枚・コンソールのエラー 0 | final-quiz-c-12.png |
| 2026-11-20 09:42 | ce250a2e | 組織 B のトークンと未ログインで、組織 A の画像の URL を取る | e2e_user_b | 404（共通のエラーの形）・未ログインは 401 | 404（`{"error": {"main_message": "リソースが見つかりません", ...}}`）・401 | 理由: 画面に出ない API の確かめ（`browser_run_code_unsafe` の `fetch`） |

結論: M1〜M7 OK（追加の直しの後の M5・M6 も ce250a2e〔レビュー済みのコード a7e24950 の後は記録だけ〕で確かめ直した）
