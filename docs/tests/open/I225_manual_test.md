<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude。Human の行は備考に「試した手段: …」が必須。scripts/claude/check-manual-test-executor.sh が確かめる）
-->

# I225 手動テスト: GitHub の鍵が画面に出る・漏れたときの手順と、テスト用のセッションの抜け道を塞ぐ

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| M-01 | この端末に入れ直す: `bash scripts/claude/gh-app/install.sh` → `bash scripts/claude/gh-app/install.sh --check` → `--json` なしの `auth status` の出力を画面に出さずにスクラッチパッドのファイルに書く: `gh auth status > <スクラッチパッド>/m01.txt 2>&1` → 鍵の形が無いことを確かめる: `! grep -q ghs_ <スクラッチパッド>/m01.txt` → `gh auth status -a` → `rm <スクラッチパッド>/m01.txt`（どれも 1 コマンドずつ流す） | `install.sh`・`--check` が exit 0。`! grep -q ghs_` が exit 0（鍵の形が無い）。`gh auth status -a` が `github.com osushi0404-claude[bot] GH_TOKEN success (active)` の 1 行と、標準エラーの置き換えの案内 1 行を出し exit 0 | Claude | 手元のシェル |  | 受け入れ条件 1。本物の `gh` と App の鍵で、入口の置き換えが効くこと。`-a` なしでは本物の `gh` に保存された停止中の bot のログイン（`error`）も並び exit 1 になる（元の `gh` と同じ） |
| M-02 | 鍵が出たときの手順を本物の GitHub で流す: `bash scripts/claude/gh-app/revoke.sh` → `gh api installation/repositories --jq .total_count` | `revoke.sh` が `token`・`token-readonly` の各行に「失効を確認して控えを消しました」または「控えがありません」を出し exit 0。鍵の値は出ない。続く `gh api` が `1` を出す（控えが消えたので新しい鍵を取り直して読める） | Claude | 手元のシェル |  | 受け入れ条件 3。ほかのセッションが App の鍵で動いていない時に流す（失効した鍵を環境変数で持っているプロセスは、その後の GitHub の操作が 401 になる） |
| M-03 | 対話画面の MCP: `bash scripts/claude/tui-capture.sh --wait 3 '/mcp' '{Enter}'` | 画面の MCP の一覧に `playwright`・`github` が出ない（MCP サーバーが 0 件の表示。実際に出た文言を実結果に写す） | Claude | 対話画面の判定 |  | 受け入れ条件 5（F7）。`--strict-mcp-config` が tmux の中の `claude` に効くこと。`{Enter}` で `/mcp` を開くだけでモデルは呼ばない |
| M-04 | MCP が要る承認の判定が動く: `bash scripts/claude/check-permission-prompt.sh mcp mcp__playwright__browser_tabs '{"action":"list"}'` | 終了コードが 0 または 10（判定できた）。2（判定できない）にならない | Claude | claude -p の判定 |  | 受け入れ条件 5（F7）の副作用の確かめ。`--strict-mcp-config` と `--mcp-config .mcp.json` を併せても、ワークツリーの `.mcp.json` の Playwright を読める。2 が出たらもう 1 回流す |

結論: OK / NG
