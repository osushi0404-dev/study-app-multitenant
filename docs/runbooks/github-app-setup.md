# GitHub の名義（GitHub App）と鍵の設定

Claude は GitHub App `osushi0404-claude`（GitHub 上の名前は `osushi0404-claude[bot]`）の名義で GitHub を操作する（I223）。この手順書だけで、新しい端末（WSL）に同じ仕組みを入れられる。

---

## 1. 仕組み

- App の鍵は 1 時間で切れる。`gh` の入口（`scripts/claude/gh-app/gh` を `~/.local/bin/gh` として入れる）が、`gh` を呼ぶたびに `gh-app-token` から鍵を受け取り、`GH_TOKEN` で本物の `gh`（`/usr/bin/gh`）に渡す。受け取った鍵は `~/.cache/github-app/` に控え、残り 10 分を切ったら取り直す
- `git push` なども同じ入口を通る（git の credential helper を `!~/.local/bin/gh auth git-credential` にする）
- テスト用のセッション（`claude -p`）には読み取りだけの鍵を渡す（`GH_APP_READONLY=1`）。`gh issue`・`gh pr`・`gh api`・`git push` のどの書き方でも、書き込みは GitHub が拒否する（HTTP 403）。手で起こすときの入口は `scripts/claude/test-session.sh`。`scripts/claude/` のスクリプトが Claude を起こす行（`claude -p`・tmux の中の `claude`）にはすべて `GH_APP_READONLY=1` と `--strict-mcp-config`（MCP は `--mcp-config` で渡したものだけ。手元の設定の MCP が読み取りだけの鍵を迂回しないように・I225）を付ける（レビュー役も同じ）。tmux の中の `claude` には、入口のある `PATH`（`~/.local/bin` が先頭）も渡す（先に立っていた tmux サーバーの `PATH` で入口を通らないことがないように・I225）。付け忘れは `scripts/claude/tests/test_i223_gh_app.sh` の G6・G7 が CI で止める（見るのは `scripts/claude/` 直下の `.sh` の、`claude -p` の呼び出しと、tmux で `claude` を起こす行。それ以外の形の起動は見ない）。決まりの正は `docs/runbooks/plan-writing-rules.md`
- GitHub の MCP は使わない（I223 で外した。`docs/runbooks/mcp-usage.md`）

## 2. App の設定（今の値）

- 組織 `osushi0404-dev` の下に作り、このリポジトリ（`study-app-multitenant`）だけに入れる
- 権限: Contents・Issues・Pull requests・Workflows は読み書き。Actions・Checks・Commit statuses は読み取り。それ以外はなし
- App の番号（Client ID・Installation ID）は `scripts/claude/gh-app/gh-app-token` の既定値（秘密ではない。秘密の鍵ファイルが無ければ使えない）。変えるときは環境変数 `GH_APP_CLIENT_ID`・`GH_APP_INSTALLATION_ID` で上書きできる
- develop・main の push 制限の一覧（`docs/runbooks/branch-protection-setup.md`）に App を入れない。マージは `oshui0404` だけが行う

## 3. 秘密の鍵ファイルを置く

1. App の設定画面（組織の Settings → Developer settings → GitHub Apps → `osushi0404-claude`）の「Private keys」で鍵を作り、ダウンロードする
2. 次のように置く（フォルダは 700・ファイルは 600）:
   ```bash
   mkdir -p ~/.config/github-app
   chmod 700 ~/.config/github-app
   mv <ダウンロードしたファイル> ~/.config/github-app/app.pem
   chmod 600 ~/.config/github-app/app.pem
   ```
3. リポジトリの中に置かない（`.gitignore` の `*.pem`・コミットの前と CI の detect-secrets でも止まる）。鍵の中身をコマンドの引数・画面・記録に出さない

## 4. 入れる

```bash
bash scripts/claude/gh-app/install.sh
bash scripts/claude/gh-app/install.sh --check
```

- `install.sh` は、前提（`openssl`・`curl`・`python3`・`/usr/bin/gh`・鍵ファイルの権限 600・`PATH` で `~/.local/bin` が `/usr/bin` より前）を確かめ、足りなければ何も変えずに止まる
- `~/.local/bin/gh-app-token`・`~/.local/bin/gh` を入れ（前の版は `~/.cache/github-app/backup/` に写す）、git の credential helper（github.com・gist.github.com）と、このリポジトリの git の作者（`osushi0404-claude[bot]`）を設定する。最後に GitHub に読みに行って確かめる
- `--check` は何も変えず、入っているものがリポジトリの版と同じか・設定がそろっているかだけを見る（終了コード 0 = そろっている）。リポジトリの版を変えたら `install.sh` を流し直す

## 5. 確かめる

- 名義: `gh auth status --json hosts --jq '.hosts["github.com"][] | select(.active) | .login + " " + .tokenSource + " " + .state'` が `osushi0404-claude[bot] GH_TOKEN success` を出す
  - 名義の確かめの `auth status` は、上のように `--json` で要る欄だけを取り出す。`--json` を付けないと、App の長い鍵の大部分が画面に出る（`gh` は最後の部分しか伏せない・I223 の手動テストで発生）。入口（`~/.local/bin/gh`）は、`--json` も `-t`/`--show-token` も無い `auth status` を、鍵の欄の無い表示（`<host> <login> <鍵の出どころ> <状態>`）に置き換える（I225）。本物の `gh`（`/usr/bin/gh`）を直接呼ぶと置き換わらない。手順書・スキル・スクリプトに `--json` なし（または `-t`/`--show-token` 付き）の書き方があると、`test_i223_gh_app.sh` の G10 が CI で止める
- `git push` が通る

### 鍵が画面・記録に出てしまったら
1. 控えの 2 つの鍵（`~/.cache/github-app/` の `token`・`token-readonly`）を失効させる:
   ```bash
   bash scripts/claude/gh-app/revoke.sh
   ```
   各控えについて「失効を確認して控えを消しました」か「控えがありません」が出て exit 0 になれば終わり。次の `gh` で新しい鍵を取り直す（そのとき App の鍵を環境変数で持っている別のセッションは、GitHub の操作が 401 になる）
2. 出た鍵が控えの鍵と違うとき（控えが取り直された後に気づいた・別のセッションで出た）は、その鍵を標準入力で渡して失効させる（引数には書かない。画面にも出ない）:
   ```bash
   bash scripts/claude/gh-app/revoke.sh --stdin
   ```
   出た鍵を貼って Enter を押す。「渡された鍵: 失効を確認しました」で終わり
3. 「無効を確かめられませんでした」（exit 1）のときは、GitHub に届くかを確かめて流し直す（失効が確かめられるまで控えは消さない）
4. 秘密の鍵ファイル（`app.pem`）が漏れたときは「8.」で鍵を作り直す

## 6. テスト用のセッション

- 手で起こすときは `bash scripts/claude/test-session.sh <claude -p に渡す引数…>`。GitHub は読めるが、書き込みは GitHub が拒否する
- 手元のシェルで読み取りだけの鍵を使うときは、コマンドの前に `GH_APP_READONLY=1` を付ける

## 7. 困ったとき

- `gh-app-token: 鍵を受け取れませんでした`: 鍵ファイルの場所と権限、App がこのリポジトリに入っているか（組織の Settings → GitHub Apps → Installed）、GitHub に届くか（20 秒で打ち切る）を確かめる
- `GH_APP_DISABLE=1` を付けると、鍵を渡さずに本物の `gh` を動かす（App が使えないときの退避）。今は本物の `gh` に保存されたログインが停止中の bot アカウントのもので無効なので、退避には使えない。読み取りだけの指定（`GH_APP_READONLY=1`）があるときは無視される

## 8. 守ること

- 秘密の鍵ファイル・控え（`~/.cache/github-app/`）をリポジトリに入れない・人と共有しない
- 鍵が漏れたかもしれないときは、App の設定画面で鍵を消して作り直し、「3.」から置き直す
- 書き込みの鍵の控え（`~/.cache/github-app/token`）は、同じ端末のプログラムからは読める。テスト用のセッションがわざと読んだり、`GH_APP_READONLY` を外したり、本物の `gh` を直接呼んだりする書き方は、守りの対象外（ふつうの書き方の事故を止めるためのもの。最後の守りは GitHub の権限）

## 9. 前の仕組み（I223 より前）

- I223 より前は、人の bot アカウント（2026-10-30 に停止）で操作し、GitHub の MCP は別の個人の鍵（Fine-grained PAT・環境変数 `GITHUB_PERSONAL_ACCESS_TOKEN`）で動かしていた。どちらも使わない
- 手元に残っている場合: `~/.bashrc` などの `export GITHUB_PERSONAL_ACCESS_TOKEN=` の行を消す。PAT は、作ったアカウントの GitHub の Settings → Developer settings → Personal access tokens で失効させる
