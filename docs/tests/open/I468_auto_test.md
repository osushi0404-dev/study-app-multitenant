# I468 自動テスト: ワークツリーで ESLint のフックをコンテナで流す・Playwright MCP が切れたときの手順

実行コマンド: 下の「決定論ゲート」。pytest・Jest・E2E は対象のコードが無いので対象外（CI の `scripts/claude/tests/run-all.sh` も同じテストを流す）

結果:
- 計画時のベースライン（2026-11-15・変更前）: `docker compose run --rm --no-deps -T --build --entrypoint npm frontend run lint` exit 0（違反 0 件）
- 実装前のため TC-01〜TC-04 は未実行（テストのスクリプトは implement で作る）

共通の準備（新しいテスト `scripts/claude/tests/test_i468_lint_frontend.sh` の中）: 一時のディレクトリに git リポジトリ（`git init`）と `frontend/` を作り、そこを作業フォルダにして本物の `scripts/claude/lint-frontend.sh` を呼ぶ。偽の `docker`・`npm` を一時のフォルダに置いて `PATH` の先頭に足す。偽物は、受け取った引数（空白区切り 1 行）と作業フォルダを記録のファイルに書き、`info` は `STUB_DOCKER_INFO_RC`、`compose ps` は `STUB_PS_OUT` を出して 0、それ以外（lint を流す呼び出し）は `STUB_RC` で終わる。本物の Docker は使わない。失敗の注入は、ラッパーの写しを壊して同じ準備で流す（本物は書き換えない）。最後に「壊した写しがすべて作れた（置き換え前の文字列が本体にある）」を確かめる

| TC | AC | 内容 | 期待（合格=exit 0） | 失敗の注入 |
|---|---|---|---|---|
| TC-01 | AC1 | `STUB_DOCKER_INFO_RC=0`・`STUB_PS_OUT` が `backend` と `frontend` の 2 行。`STUB_RC=0` と `STUB_RC=1` で 1 回ずつ | 記録が `compose exec -T frontend npm run lint` と完全一致。ラッパーの終了コードが 0・1（偽の lint と同じ）。`compose run` の呼び出しが無い | FG-01: `exec docker compose exec -T frontend npm run lint` の行末に ` \|\| true` を足した写し（exec を外す）で、`STUB_RC=1` のときに 0 が返り不合格 |
| TC-02 | AC1 | `STUB_DOCKER_INFO_RC=0`・`STUB_PS_OUT` が (a) `backend` だけ (b) 空 (c) `frontend-old`（`frontend` を含む別の名前）。`STUB_RC=0`・`1` | (a)〜(c) とも記録が `compose run --rm --no-deps -T --build --entrypoint npm frontend run lint` と完全一致し、`compose exec` の呼び出しが無い。終了コードが偽の lint と同じ | FG-02a: `grep -qx` を `grep -q`（部分一致）にした写しで (c) が `compose exec` になり不合格／FG-02b: 使い捨ての行に ` \|\| true` を足した写しで `STUB_RC=1` のときに 0 が返り不合格 |
| TC-03 | AC2 | `STUB_DOCKER_INFO_RC=1`（Docker が止まっている）・一時のリポジトリに実行できる `frontend/node_modules/.bin/eslint`（中身は `exit 0`）。`STUB_RC=0`・`1` | 偽の `npm` の記録が `run lint` で、作業フォルダが一時のリポジトリの `frontend`。`docker compose` の呼び出しが無い。終了コードが偽の lint と同じ | FG-03: ホストの行に ` \|\| true` を足した写しで `STUB_RC=1` のときに 0 が返り不合格 |
| TC-04 | AC2 | (a) `STUB_DOCKER_INFO_RC=1`・ホストの eslint なし (b) `PATH` に `docker` が無い（`git`・`bash` など要るものだけを入れたフォルダを `PATH` にする）・ホストの eslint なし | (a)(b) とも終了コード 1。標準エラーに `ESLint を流せません` と `Docker` と `frontend/node_modules/.bin/eslint` がある。lint を流す呼び出し（`compose exec`・`compose run`・`npm run lint`）の記録が無い | FG-04: 最後の `exit 1` を `exit 0` にした写しで (a)(b) が 0 になり不合格 |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i468_lint_frontend.sh
bash scripts/claude/tests/test_pipefail_negated_grep.sh
```
