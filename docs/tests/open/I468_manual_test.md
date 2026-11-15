<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude。Human の行は備考に「試した手段: …」が必須。scripts/claude/check-manual-test-executor.sh が確かめる）
-->

# I468 手動テスト: ワークツリーで ESLint のフックをコンテナで流す・Playwright MCP が切れたときの手順

共通: harness-1 のワークツリー（ホストの `frontend/node_modules` は空のフォルダ）で行う。違反を入れるファイルは一時の `frontend/src/i468Probe.ts`（中身 `const i468Unused = 1;` の 1 行・`no-unused-vars` の警告で `--max-warnings 0` に当たる）。各行の後でファイルを消し、`git restore --staged` で外し、`git status --porcelain` が空（または No.1 の前と同じ）であることを確かめる。違反の無い確かめには、同じ名前で `export const i468Probe = 1;` の 1 行のファイルを使う（コミットはせず `pre-commit run eslint --files frontend/src/i468Probe.ts` で流す）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | frontend のコンテナを止めた状態（`docker compose ps --status running --services` に `frontend` が無い）で、違反のあるファイルを `git add` して `git commit -m "i468 probe"` | コミットが作られない（`git log -1` が変わらない）。出力に `ESLint` の `Failed`・`使い捨ての frontend コンテナで流します`・`i468Unused` の警告がある。違反の無いファイルの `pre-commit run eslint --files ...` は `Passed` | Claude |  |  |
| 2 | `bash scripts/claude/wt-ports.sh` の後 `docker compose up -d --no-deps frontend` で起動し、No.1 と同じ違反のコミットと、違反の無い確かめを流す。終わったら `docker compose stop frontend` | コミットが作られない。出力に `起動中の frontend コンテナで流します` と `i468Unused` の警告がある。違反の無い確かめは `Passed` | Claude |  |  |
| 3 | `docs/runbooks/frontend-verify.md` の 11 を読み、目印の文言を本物の記録 `~/.cache/claude-cli-nodejs/-mnt-c-app-study-app-multitenant--claude-worktrees-app-1/mcp-logs-playwright/*.jsonl` と `grep -F` で突き合わせる | 11 に確かめ方（`browser_tabs` の `list`）・目印 `excludeStalePluginClients: marking stale`・`/mcp` → playwright → 再接続の依頼の文例があり、目印の文言が記録に 1 件以上当たる | Claude |  |  |
| 4 | `.claude/skills/implement/SKILL.md` と `.claude/skills/test-gate/SKILL.md` を読む | implement は 1) の前の 0) で、コードを書く前に MCP を確かめ、使えなければ 11 の文例で依頼して止まる。test-gate は画面確認の前に同じ確かめがある。どちらも 11 を指し、test-gate へ持ち越す書き方が無い | Claude |  |  |
| 5 | `bash scripts/claude/tui-capture.sh '/mcp{Enter}'` で、新しいセッションの `/mcp` の画面を取る | 画面に `playwright` のサーバーがあり、選ぶと再接続（Reconnect）の項目が出る（文例の操作がそのままできる）。`{Enter}` だけで選べない場合は、取れた画面と、取れなかった部分を実結果に書く | Claude |  | 実施環境: 対話画面の判定 |

結論: OK / NG
