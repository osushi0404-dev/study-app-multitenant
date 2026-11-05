# I225 自動テスト: GitHub の鍵が画面に出る・漏れたときの手順と、テスト用のセッションの抜け道を塞ぐ

実行コマンド（例）: 下の「決定論ゲート」（アプリのコード変更なし。pytest・Jest・E2E は CI が流す）

結果:
- backend: 対象外
- frontend: 対象外

## テストケース
| TC | 内容 | 合否の判定 | 結果 |
|---|---|---|---|
| TC-01 | 起動の行を触るファイルを見ている既存のテスト 5 本（`test_tui_capture.sh`・`test_check_permission_prompt.sh`・`test_i197_adversarial_process.sh`・`test_fix_review.sh`・`test_i193_official_flow.sh`）が合格する。`test_tui_capture.sh` の T1 は、起動の行に `-e PATH=$HOME/.local/bin:<呼び出し元の PATH>` と `claude --permission-mode manual --strict-mcp-config` があることを照合する形に直し、FG-T1b（写しから `-e PATH=…` を消すと T1 が不合格）を足す | 各スクリプトが exit 0 | 実装前のベースライン（2026-11-06・develop 由来の feature/I225）: 5 本とも exit 0（37/26/113/66/174 件合格）。T1 の照合の直し・FG-T1b は実装前のため未実行 |
| TC-02 | `test_i223_gh_app.sh` の G1〜G10（`curl`・`openssl`・本物の `gh`・`claude` は一時フォルダの偽物。秘密の鍵ファイルと本物の GitHub は使わない）。既存 G1〜G6 はそのまま。新しく: **G7** `scripts/claude/*.sh` の Claude を起こす論理行（G6 と同じ読み方。`export GH_APP_READONLY=1` のファイルも除外しない）がすべて `--strict-mcp-config` を持つ **G8** 入口 `gh` で `auth status`（引数なし・`-a`・`-h github.com`）が、偽物の本物の `gh` の鍵の行（`Token: SECRET-…`）を出さず、`<host> <login> <tokenSource> <state>`（使用中に ` (active)`）だけを出し、偽物に `--json hosts` と元の引数が渡る。`state` がすべて `success` なら exit 0・1 つでも違えば exit 1。`auth status -t`・`--show-token`・`--json hosts` は置き換えず偽物にそのまま渡る。`pr list` などほかのコマンドもそのまま **G9** `revoke.sh` が、控えの `token`・`token-readonly` の両方の鍵で `api -X DELETE installation/token` を呼び（偽物の本物の `gh` に `GH_TOKEN` で渡る）、無効を確かめて 2 つの控えを消し、exit 0。標準出力・標準エラーに鍵の値が出ない。控えが 1 つも無ければ exit 0。DELETE の後も読める（偽物が失効を受け付けない）鍵があれば、その控えを消さず exit 1。`--stdin` に標準入力で鍵（`leaked-x`）を渡すと、その鍵で DELETE を呼び、控えは触らず exit 0・出力に `leaked-x` が出ない。`--stdin` で空の入力・知らない引数は exit 2 **G10** `CLAUDE.md`・`docs/runbooks/`・`.claude/skills/`・`.claude/agents/`・`scripts/claude/`（`tests/` を除く）・`docs/*/templates/` に、`--json` なし、または `-t`/`--show-token` 付きの `gh auth status` が無い | スクリプトが exit 0。各新しい G に FG（写しを壊すと該当の G が不合格になることをテストの中で確かめる）: G7 `code-review.sh`・`tui-capture.sh` の写しから `--strict-mcp-config` を消す／G8 入口の写しから置き換えの分岐を消す・`state` の判定を消す（exit 0 になる）／G9 写しの控えの名前の一覧から `token-readonly` を消す・失効の確かめを消す（読める鍵でも控えを消す）・`--stdin` で読んだ値を使わず控えの鍵を使う／G10 一時フォルダの `docs/runbooks/x.md` に `` `gh auth status` `` と `` `gh auth status --json hosts -t` `` を書くとそれぞれ不合格・`--json hosts --jq …` の形だけなら合格 | 実装前のため G7〜G10 は未実行（G1〜G6 は 2026-11-06 のベースラインで 18/18） |
| TC-03 | `docs/runbooks/harness-audit.md` の古い鍵の点検コマンド（コードブロックの 2 行目）をそのまま流す | 同じコマンドの後ろに `2>&1 >/dev/null` を付けて流し、exit 0 で、出力（＝標準エラー。jq の構文エラーなど）が空（`[ -z "$(<コマンド> 2>&1 >/dev/null)" ]` が exit 0）。出力の中身はこの端末の保存されたログインで変わるので合否に使わない | 計画の段階で同じコマンドを流して OK（2026-11-06）: `osushi0404-bot /home/tacic/.config/gh/hosts.yml error`・exit 0。手順書への反映は実装前のため未実行 |

新しい決定論テストは G7〜G10 と T1 の照合の直しだけにする（plan_I225.md §9: どれも、壊れても気づきにくく、壊れると鍵が画面に出る・読み取りだけの鍵を迂回する所）。手順書の文言（失効の手順の説明・総点検の一覧の並び）はレビューで見る。

## 決定論ゲート
```bash
bash scripts/claude/tests/test_i223_gh_app.sh
bash scripts/claude/tests/test_tui_capture.sh
bash scripts/claude/tests/test_check_permission_prompt.sh
bash scripts/claude/tests/test_i197_adversarial_process.sh
bash scripts/claude/tests/test_fix_review.sh
bash scripts/claude/tests/test_i193_official_flow.sh
```

## 実行記録
- 2026-11-06・plan（実装前）: TC-01 の 5 本と `test_i223_gh_app.sh`（G1〜G6）すべて exit 0。TC-03 のコマンドは計画の段階で OK
