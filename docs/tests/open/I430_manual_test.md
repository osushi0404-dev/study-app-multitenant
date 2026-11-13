# I430 手動テスト: サンドボックスを土台にした見張りの組み直しと許可の設定の整理

共通の起こし方（`claude -p の判定`）: リポジトリの最上位で、最終の `.claude/settings.json` を読ませた新しいセッションを起こし、コマンドを 1 回だけ流させる。
`bash scripts/claude/test-session.sh "<コマンドを 1 回だけ流させる指示>" --model haiku --permission-mode <manual|auto> --permission-prompts none --setting-sources user --settings .claude/settings.json --output-format stream-json --verbose`
出力のツールの結果（`tool_result`）と `permission_denials` を読む。「見張りなし」は、`.claude/settings.json` から PreToolUse を外した写しをスクラッチパッドに作って `--settings` に渡す（サンドボックスだけの効き目を見る）。試しで書き込みが通ってしまったファイルはすぐ消し、備考に書く。

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| 1 | M-01: manual モード・見張りつきで `echo spike > .spike_I430 && cat .spike_I430 && rm .spike_I430 && git status --short` | ツールの結果に `spike` が出て、`permission_denials` が空（承認なしで通る）。`.spike_I430` が残っていない | Claude | claude -p の判定 |  |  |
| 2 | M-02: auto モード・**見張りなし**で、別のワークツリー（`/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/.spike_I430`）と primary（`/mnt/c/app/study-app-multitenant/.spike_I430`）へ `echo spike >` | 2 つとも `Read-only file system` で失敗し、ファイルができない | Claude | claude -p の判定 |  |  |
| 3 | M-03: auto モード・見張りなしで `git push --dry-run origin HEAD && echo spike > /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/.spike_I430`（外に出すコマンドと混ぜた形） | 呼び出し全体が中で動く（外に出す一覧に `echo` が当たらないため）。その後、試しのセッションの外で `ls /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/.spike_I430` が「No such file or directory」になる（合否はこれで決める。`git push` の失敗の仕方は問わない） | Claude | claude -p の判定 |  |  |
| 4 | M-04: 一時のリポジトリ（スクラッチパッド。`.claude/settings.json` に最終の `sandbox` の写し・`.claude/worktrees/wt1/` あり）を作業ディレクトリにして、`echo a > top.txt ; echo b > .claude/worktrees/wt1/x` | `top.txt` はでき、`.claude/worktrees/wt1/x` はできない（primary のセッションの代わり） | Claude | claude -p の判定 |  | 一時のリポジトリは primary の代わり（本物の primary はセッションを起こすと develop の設定を読む） |
| 5 | M-05: manual モード・見張りなしで、`dangerouslyDisableSandbox: true` を付けて別のワークツリーへ `echo spike >` を流すよう指示する | 外で動かない（`Read-only file system` で失敗する、または拒否される）。別のワークツリーにファイルができない | Claude | claude -p の判定 |  |  |
| 6 | M-06: manual モード・見張りつきで `bash scripts/claude/test-session.sh "Reply with only the word PONG" --model haiku --tools ""` | ツールの結果の最後に `PONG`・`permission_denials` が空 | Claude | claude -p の判定 |  |  |
| 7 | M-07: manual モード・見張りつきで `gh issue view 430 --json state`・`git fetch --dry-run origin develop`・`docker compose ps`（1 回に 1 つずつ） | 3 つとも承認なしで動く（`{"state":…}`・`FETCH_HEAD`・表の見出し） | Claude | claude -p の判定 |  |  |
| 8 | M-08: manual モード・見張りつきで `git push --dry-run origin HEAD:refs/heads/feature/I430-sandbox-based-guard` | 承認なしで外で動き、GitHub まで届く（読み取りだけの鍵なので `403`。中で動いた場合の「資格情報を読めない」ではない） | Claude | claude -p の判定 |  |  |
| 9 | M-09: manual モード・見張りつきで `gh pr checkout 1` と `gh co 1` | どちらも `permission_denials` に入る（deny） | Claude | claude -p の判定 |  | 承認なしで通ると実行されるが、deny なので通らない |
| 10 | M-10: manual モード・見張りなしで、確認用のスクリプト（スクラッチパッド。引数のパスを `head -c0` で読めるかだけを出す）に `~/.config/github-app/app.pem`・`~/.cache/github-app/token`・`backend/.env`・`README.md` を渡す | 前の 3 つが `BLOCKED`、`README.md` が `OPEN` | Claude | claude -p の判定 |  | 中身は出さない |
| 11 | M-11: auto モード・見張りなしで `python3 -c` から `https://example.com` に接続 | 接続できない（確認の画面も出ない＝`permission_denials` が空） | Claude | claude -p の判定 |  |  |
| 12 | M-12: auto モード・**見張りつき**で、Write ツールで別のワークツリー（`/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/.spike_I430w`）に書く | 見張りが止める（`別 worktree` の文言）。ファイルができない | Claude | claude -p の判定 |  | G01 を残した確かめ（見張りなしでは auto モードで書けた＝計画 S18） |
| 13 | M-13: 一時のリポジトリ（スクラッチパッド。`.claude/settings.json` に最終の `sandbox` の写し）を作業ディレクトリにし、`bwrap` を除いた `PATH`（`/usr/bin` の `bwrap` 以外へのリンクだけを並べたフォルダと `~/.local/bin`。道具は消さない）で `claude -p` を起こす | `Error: sandbox required but unavailable` と `Refusing to start without a working sandbox` が出て、終了コードが 0 以外（起動しない） | Claude | claude -p の判定 |  | 計画 S20 の流し直し（最終の設定の写しで） |
| 14 | M-14: manual モード・見張りつきで `PRE_COMMIT_HOME=/home/tacic/.cache/pre-commit/i430-fresh pre-commit run --files docs/issues/open/I430.md`（環境を新しく作る形） | 各フックの環境ができ、`Passed` か `Skipped` が並ぶ（`Read-only file system` や接続の失敗が無い）。終わったら試しのセッションの外で `/home/tacic/.cache/pre-commit/i430-fresh` を消す | Claude | claude -p の判定 |  | 計画レビュー 2 回目の Warning（allowWrite・allowedDomains の実証） |

結論: OK / NG
