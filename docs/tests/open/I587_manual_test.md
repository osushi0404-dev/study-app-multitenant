<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude）
-->

# I587 手動テスト: 問題・解説の画像を DB に保存し、組織の境界を確かめる API から返す

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M1 | （ステップ 1・コードを変える前）`docker compose exec -T backend python manage.py shell -c` で、`MediaAsset` の件数（全体・`is_deleted`・`organization`／`subject` が null）、`is_deleted=False` のうち `MEDIA_ROOT/storage_key` が無い行（ID・キー）、古い `question_image`・`explanation_image` に値のある問題の件数を読むだけで数える。`git ls-files backend/media` で消すファイルを並べる | 2026-11-19 の調べと同じ: 全体 4・論理削除 0・null 0・ファイルの無い行 4（`org/e2e-org-a/subjects/i472-check/...` の 4 つ）・古い列 0。ファイルは PNG 6・`.gitkeep` 12。違えば数を書き直してから承認を求める | Claude |  |  |
| M2 | （ステップ 1）`bash scripts/db_backup.sh` で控えを取り、ファイルの大きさを `wc -c` で読む | `backup_<日時>.sql` ができる（`.gitignore` 済みで `git status` に出ない）。大きさ（バイト）を記録する | Claude |  |  |
| M3 | （ステップ 4・0025 を流す前）`docker compose exec -T backend python manage.py check_media_migration` | 行ごとの判定が「消す（ファイル無し）」4 行・「移す」0・「済み」0、古い列に値のある問題 0 と出る（M1 と同じ）。`showmigrations problems` で `0025`・`0026` が `[ ]` | Claude |  |  |
| M4 | （ステップ 7・承認の後）`DANGER_OK=1 docker compose exec -T backend python manage.py migrate problems` → `showmigrations problems` → M1 の数え方で数え直す | 出力に `I587 media: moved=0 already=0 deleted_assets=4 deleted_links=<紐づけの数>`。`0024`〜`0026` が `[X]`。`MediaAsset` 0 件・`problems_problem` に古い 2 列が無い | Claude |  |  |
| M5 | Playwright MCP で `e2e_user_a`（組織 A・管理者）でログインし、`/quiz-management` で問題を 1 つ作る（問題画像 2 枚・解説画像 1 枚の PNG）。一覧のプレビューで画像を開き、拡大する。編集のダイアログを開く。`browser_network_requests` で通信を見る | プレビューに問題画像 2 枚・解説画像 1 枚が出て、押すと拡大のダイアログに同じ画像が出る。編集のダイアログの保存済みの画像 3 枚にサムネイルが出る。通信は `GET /api/media/<id>/` が 200（`/media/` への通信が無い）。コンソールに新しい `error` が無い。`backend/media` にファイルが増えていない（`git status --short backend` が空） | Claude |  |  |
| M6 | M5 の問題の科目で `e2e_user_c`（組織 A・一般の利用者）がクイズを解く（問題画像を見て、答えて解説画像を見る）。別に、`e2e_user_b`（組織 B）のアクセストークンで M5 の画像の URL を `browser_evaluate` の `fetch`（`Authorization: Bearer`）で取る。未ログインで同じ URL を取る | クイズの問題に画像 2 枚、答えた後の解説に画像 1 枚が出る。組織 B は 404、未ログインは 401。同じ画像を 2 回取ると、2 回目はブラウザのキャッシュか 304 で返る（`browser_network_requests` の状態） | Claude |  |  |
| M7 | （AC14・M5 の後）`bash scripts/db_backup.sh` で控えを取り、大きさを M2 と比べる。`docker run --rm -d --network <app-1 のネットワーク> -e POSTGRES_HOST_AUTH_METHOD=trust --name i587-restore <db のイメージ>` で捨てる DB を起こし、`learning_app` を作って控えを `psql` で戻す。`docker compose stop backend` → `docker compose run -d --rm --use-aliases --service-ports -e DB_HOST=i587-restore backend` で戻した DB に向けた backend を起こす。Playwright MCP で `e2e_user_a` でログインし、M5 の問題をプレビューで開く。終わったら、その backend のコンテナと `i587-restore` を `docker stop` で止め（どちらも `--rm` で消える）、`docker compose start backend` で元の backend を戻す | 戻した DB の画面で M5 の問題に画像 3 枚が出る（`GET /api/media/<id>/` が 200）。控えの大きさの増え方（M2 との差と、画像の合計バイト）を記録する。元の backend に戻した後、`/quiz-management` が今までどおり開く | Claude |  | 戻し先は捨てるコンテナなので、開発の DB を変えない（計画書 9）。`docker run`・`docker stop`・`psql` で見張りの承認画面が出うるので、流す前にユーザーに予告する |

## 画面確認
<!-- frontend/src を変えたイシューでは 1 行以上必要（test-gate 段階の check-frontend-evidence.sh が確かめる）。
     画像の列は .evidence/I587/ 直下のファイル名（カンマ区切り）。書き方: docs/runbooks/frontend-verify.md -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

結論: 未実施
