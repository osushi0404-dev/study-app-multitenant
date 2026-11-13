# I486 手動テスト: 敵対的レビューの実験の環境（コンテナ）と空振りの見分けを決定論にする

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | このワークツリーで `bash scripts/claude/wt-ports.sh` を流してポートを割り当て（割当済みなら何もしない）、`REVIEW_LIB_SOURCE_ONLY=1` で `adversarial-review.sh` を読み込み、`RUN` に `M\tbackend/x.py` の 1 行の `files.txt` を置き、`REPO_ROOT=$(git rev-parse --show-toplevel)` で `ensure_backend_container` を実際の docker で流す。続けて `docker compose exec -T backend python -c 'print(1)'` を流す。終わったら `docker compose stop` | 関数が 0 で戻り、`CONTAINER_NOTE` が `backend を起こして確かめた（N 秒・締め切りの外）`。`exec` が `1` を出す。`docker ps` の `harness-1-backend-1` が `(healthy)`・ラベルの元の場所がこのワークツリー | Claude | OK | 2026-11-13 実施（HEAD はレビュー済み）。wt-ports.sh → offset=30（backend 8030）。関数は 0・`backend を起こして確かめた（19 秒・締め切りの外）`。db・redis・backend が Healthy。`exec` の出力 `1`。`harness-1-backend-1 Up (healthy)`・元の場所 `/mnt/c/app/study-app-multitenant/.claude/worktrees/harness-1`。終了後 `docker compose stop`・`git status` は空（起こしても作業ツリーは変わらない）。compose v5.6.0 の `--wait`・ラベルの表記・ポートの割当を実機で確かめる。`down -v` はしない。`wt-ports.sh` が作る直下 `.env` は `.gitignore` の `*.env` で無視される（`git check-ignore -v .env` で確認済み）ので、作業ツリーの変更にならず残してよい |
| 2 | `.claude/skills/review-gate/SKILL.md` の §3-1・§3-2 を読む | §3-1 に `docker compose up` のコードブロックと「backend を変えたか」を Claude が決める文が無い。§3-2 の exit 2 に `ADVERSARIAL_ERROR: CONTAINER` は「実行し直さずに止める（止める条件 3）・出力の理由を伝える」とだけある | Claude | OK | §3-1 は 68 行の 1 文（スクリプトが起こす・手で起こさない）だけ。§3-2 は 78 行の CONTAINER の箇条だけ |

結論: OK
