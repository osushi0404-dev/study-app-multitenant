<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude。Human の行は備考に「試した手段: …」が必須。scripts/claude/check-manual-test-executor.sh が確かめる）
-->

# I226 手動テスト: I225 のレビューの残り: 失効の確かめの取り違え・鍵を出す書き方の検査の狭さ

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M-01 | 本物の GitHub に、ありえない形の鍵を渡す: `printf 'ghs_I226invalid\n' \| bash scripts/claude/gh-app/revoke.sh --stdin` | 標準エラーに `渡された鍵: この鍵は最初から無効でした。貼り間違い（末尾の欠け）がないか確かめてください。すでに失効済みなら対応は不要です` が出て exit 1。`失効を確認しました` は出ない。画面に `ghs_I226invalid` は出ない | Claude | | 最初の読みが 401 なので DELETE は送られない（本物の鍵には触らない） |
| M-02 | このセッションで `docs/tests/open/I999_auto_test.md` を Write で作る（見出しを `## 決定論ゲート（自動実行）` と 1 語違え、その下の bash ブロックに `bash scripts/claude/tests/test_i223_gh_app.sh`）。続けて見出しを `## 決定論ゲート（自動実走）` に Edit で直す。最後にファイルを消す | Write の直後に、フックの知らせ `[posttooluse] auto_test の宣言漏れ in …I999_auto_test.md` と「ひな形 … の見出しに合わせてください」が届く。Edit で直した後は知らせが届かない | Claude | | フックは `$CLAUDE_PROJECT_DIR` のスクリプトを動かすので、このワークツリーの版が効く |
| M-03 | ログインなしで、リポジトリの版の入口を流す: `env -u GH_TOKEN GH_APP_DISABLE=1 GH_CONFIG_DIR=<空の一時フォルダ> bash scripts/claude/gh-app/gh auth status` | 標準エラーに `You are not logged into any GitHub hosts. To log in, run: gh auth login`、標準出力は空、exit 1 | Claude | | 手元の `~/.local/bin/gh` は写しなので、リポジトリの版を直接流す（入れ直しはマージの後） |

結論: OK / NG
