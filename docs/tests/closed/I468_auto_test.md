# I468 自動テスト: ワークツリーで ESLint のフックをコンテナで流す・Playwright MCP が切れたときの手順

実行コマンド: 下の「決定論ゲート」。pytest・Jest・E2E は対象のコードが無いので対象外（CI の `scripts/claude/tests/run-all.sh` も同じテストを流す）

結果:
- 計画時のベースライン（2026-11-15・変更前）: `docker compose run --rm --no-deps -T --build --entrypoint npm frontend run lint` exit 0（違反 0 件）
- 実行記録（2026-11-15・implement・/simplify の後）: `bash scripts/claude/tests/test_i468_lint_frontend.sh` exit 0（pass=17 fail=0・TC-01〜TC-04 と FG-01〜FG-04）。Red（ラッパーが無い状態）で fail=17 を確かめてから実装した
- 実行記録（2026-11-15・test-gate）: `bash scripts/claude/gate-check.sh I468` exit 0（GATE_CHECK: OK・コードレビュー 20261115_1115・敵対的レビュー 20261115_1122）。決定論ゲートは review-gate が実走済みで、heavy の委譲は無い（pytest・Jest・E2E は CI が合格）。手元で流し直していない

共通の準備（新しいテスト `scripts/claude/tests/test_i468_lint_frontend.sh` の中）: 一時のディレクトリに git リポジトリ（`git init`）と `frontend/` を作り、そこを作業フォルダにして本物の `scripts/claude/lint-frontend.sh` を呼ぶ。偽の `docker`・`npm` を一時のフォルダに置いて `PATH` の先頭に足す。偽物は、受け取った引数（空白区切り 1 行）と作業フォルダを記録のファイルに書き、`version`（デーモンに届くかの確かめ）は `STUB_DAEMON_RC`、`compose ps` は `STUB_PS_OUT` を出して 0、それ以外（lint を流す呼び出し）は `STUB_RC` で終わる。本物の Docker は使わない。失敗の注入は、ラッパーの写しを壊して同じ準備で流す（本物は書き換えない）。最後に「壊した写しがすべて作れた（置き換え前の文字列が本体にある）」を確かめる

| TC | AC | 内容 | 期待（合格=exit 0） | 失敗の注入 |
|---|---|---|---|---|
| TC-01 | AC1 | `STUB_PS_OUT` が `backend` と `frontend` の 2 行。`STUB_RC=0` と `STUB_RC=1` で 1 回ずつ | 記録が `compose exec -T frontend npm run lint` と完全一致。ラッパーの終了コードが 0・1（偽の lint と同じ）。`compose run` の呼び出しが無い | FG-01: `exec docker compose exec -T frontend npm run lint` の行末に ` \|\| true` を足した写し（exec を外す）で、`STUB_RC=1` のときに 0 が返り不合格 |
| TC-02 | AC1 | `STUB_PS_OUT` が (a) `backend` だけ (b) 空 (c) `frontend-old`（`frontend` を含む別の名前）。`STUB_RC=0`・`1` | (a)〜(c) とも記録が `compose run --rm --no-deps -T --build --entrypoint npm frontend run lint` と完全一致し、`compose exec` の呼び出しが無い。終了コードが偽の lint と同じ | FG-02a: `grep -qx` を `grep -q`（部分一致）にした写しで (c) が `compose exec` になり不合格／FG-02b: 使い捨ての行に ` \|\| true` を足した写しで `STUB_RC=1` のときに 0 が返り不合格 |
| TC-03 | AC2 | `STUB_DAEMON_RC=1`（Docker が止まっている）・一時のリポジトリに実行できる `frontend/node_modules/.bin/eslint`（中身は `exit 0`）。`STUB_RC=0`・`1` | 偽の `npm` の記録が `run lint` で、作業フォルダが一時のリポジトリの `frontend`。`docker compose` の呼び出しが無い。終了コードが偽の lint と同じ | FG-03: ホストの行に ` \|\| true` を足した写しで `STUB_RC=1` のときに 0 が返り不合格 |
| TC-04 | AC2 | (a) `STUB_DAEMON_RC=1`・ホストの eslint なし (b) `PATH` に `docker` が無い（`git`・`bash` など要るものだけを入れたフォルダを `PATH` にする）・ホストの eslint なし | (a)(b) とも終了コード 1。標準エラーに `ESLint を流せません` と `Docker` と `frontend/node_modules/.bin/eslint` がある。lint を流す呼び出し（`compose exec`・`compose run`・`npm run lint`）の記録が無い | FG-04: 最後の `exit 1` を `exit 0` にした写しで (a)(b) が 0 になり不合格 |
| TC-05 | AC1 | 本物の pre-commit と git: 一時のリポジトリに、本物の `.pre-commit-config.yaml` から取り出した eslint のフック（PyYAML で取り出す）とラッパーの写しを置き、`pre-commit install`（`PRE_COMMIT_HOME` は一時のフォルダ）。偽の docker（起動中のコンテナなし）を `PATH` に置き、`frontend/src/probe*.ts` を足して `git commit` を `STUB_RC=1`・`0` で 1 回ずつ（敵対的レビュー 1 周目の V3 の未検証を受けて足した） | `STUB_RC=1`: コミットが 0 以外で終わり HEAD が進まない／`STUB_RC=0`: コミットが 0 で HEAD が進む。どちらも使い捨てのコンテナの呼び出しが 1 回（作業フォルダが一時のリポジトリ） | FG-05: フックの `entry` を `true` にした設定では、`STUB_RC=1` でもコミットされ不合格 |

## 再発防止記録（fix-loop・2026-11-15）
- なぜ失敗したか: implement の /simplify で test-gate/SKILL.md の画面確認の行を短くし、I187 の決まりの目印 ``docs/runbooks/frontend-verify.md` の手順（§9 の安全上の注意を含む）`` を崩した。CI の Harness Tests の `test_i193_official_flow.sh` S21 が捕まえた（pass=173 fail=1）。/simplify の前には関係するテストを流していたが、/simplify で文言を変えた後に流し直さなかった
- 何を変えたか: 元の言い回しをそのまま残し、その前に「先に下の手順書の §11 で MCP が使えるかを確かめてから」を置いた（診断メモ `docs/reviews/I468_fix_diagnosis_20261115_1058.md` の案 A）。テストは変えていない
- セキュリティ: 影響なし（§9 の安全上の注意の参照はそのまま）
- 次回どう防ぐか: /simplify で文書の文言を変えたら、/simplify の前と同じ「変えたファイルを読むテスト」を流し直してからコミットする（implement の 1.5) の「書き換えが計画の範囲を外れていないかを差分で確かめ」の確かめに含める）
- 確かめた結果: `test_i193_official_flow.sh`・`test_i205_stop_criteria.sh`・`test_review_commit_lifecycle.sh`・`test_i181_review_slim.sh`・`test_i197_adversarial_process.sh`・`test_i468_lint_frontend.sh` の 6 本が合格（run-all: pass=6 fail=0）

## 再発防止記録（fix-loop 2 回目・close の最終確認から・2026-11-15）
- なぜ失敗したか: retro で作った一覧 `docs/reviews/backlog/I468.md` に、手で説明の行「- F6（…）は…」を書いた。`test_i202_ledger_cleanup.sh` の D3 は「- F」で始まる行を指摘の行と見なして形を確かめるので落ちた。retro の後に、記録のファイルを読むテストを流していなかった
- 何を変えたか: 説明の行の書き出しを「- 台帳の F6（…）」にした（診断メモ `docs/reviews/I468_fix_diagnosis_20261115_1145.md` の案 A）。テストは変えていない
- セキュリティ: 影響なし
- 次回どう防ぐか: 一覧のファイルにはスクリプトの出力の行だけを「- F」で始め、説明は「- F」で始めない（retro 4-0 の「出力の行をそのまま貼る」のとおり）。手で足す行は「- R」など別の頭文字にする
- 確かめた結果: `test_i202_ledger_cleanup.sh` 合格（run-all: pass=1 fail=0）

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i468_lint_frontend.sh
bash scripts/claude/tests/test_pipefail_negated_grep.sh
```
