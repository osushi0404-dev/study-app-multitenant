# I060 自動テスト（棚卸し整合性の機械検証）

対象: `CLAUDE.md` および `docs/runbooks/*`。すべて grep/ls による read-only 検証で、`/test` 実行時に Claude が自動実行できる。

| TC | 観点 | 検証コマンド | 期待結果 | 結果 |
|----|------|--------------|----------|------|
| TC-01 | D1 参照漏れゼロ | `comm -3 <(grep -oE 'docs/runbooks/[a-z-]+\.md' CLAUDE.md \| sort -u) <(find docs/runbooks -maxdepth 1 -name '*.md' \| sort -u)` | 差分なし（CLAUDE.md 参照先 = 実在14本が一致。legacy 配下は maxdepth 1 で除外） | |
| TC-02 | D2 PostToolUse 記載 | `grep -c "posttooluse_check.py" CLAUDE.md` | `1` 以上（PostToolUse フックが記載されている） | |
| TC-03 | D5 shellcheck 追記 | `grep -c "shellcheck" docs/runbooks/pre-commit.md` | `1` 以上（フック表に shellcheck 行が存在） | |
| TC-04 | D6/D7 不在テンプレ参照除去 | `grep -nE "test_record_template|error_log_template" docs/runbooks/issue-flow.md` | 0件（非実在テンプレ参照が残っていない） | |
| TC-05 | D8 レビューファイル命名統一 | `grep -c "reviewXXX_IXXX" docs/runbooks/issue-flow.md` | `0`（`IXXX_review.md` に統一済み） | |
| TC-06 | D9 retro 必須統一 | `! grep -iE "retro.*(任意\|optional)" docs/runbooks/issue-flow.md`（retro 行に「任意/optional」が無いとき exit 0） | exit 0（issue-flow.md の retro 記述が「必須」で workflow.md と一致） | |
| TC-07 | D10 docker compose 統一 | `grep -c "docker-compose " docs/runbooks/common-commands.md`（ハイフン+スペース形式） | `0`（旧形式が残っていない。`.yml` ファイル名等の正当なハイフンは誤検知しないこと） | |
| TC-08 | D11 非実在スクリプト除去 | `grep -c "test_api_integration" docs/runbooks/backend-check.md` | `0`（非実在スクリプト参照が削除済み） | |
| TC-09 | D13/D14 onboarding 整合 | `grep -c "posttooluse_check.py" docs/runbooks/onboarding.md` と `grep -c "grill-me" docs/runbooks/onboarding.md` | いずれも `1` 以上 | |
| TC-10 | D3 同期手順の存在 | `grep -niE "CLAUDE.md.*参照先\|参照先.*CLAUDE.md" docs/runbooks/template-sync.md` | 1件以上（新規 runbook 追加時の CLAUDE.md 同期手順が記載されている） | |
| TC-11 | リンク健全性（CLAUDE.md→runbooks/rules） | `for f in $(grep -oE '(docs/runbooks\|rules)/[a-z_-]+\.md' CLAUDE.md \| sort -u); do test -f "$f" \|\| echo "MISSING: $f"; done` | 出力なし（全参照先が実在） | |
| TC-12 | runbook 間リンク健全性 | `for f in docs/runbooks/*.md; do grep -oE 'docs/runbooks/[a-z-]+\.md' "$f"; done \| sort -u \| while read p; do test -f "$p" \|\| echo "MISSING: $p"; done` | 出力なし（runbook 間の相互参照が全て実在ファイルに解決） | |

## 補足
- TC-07 は `docker-compose.yml` のようなファイル名内のハイフンを誤検知しないよう、コマンド形式（`docker-compose ` のように後ろにスペース＋サブコマンドが続く箇所）に限定して確認する。残存が正当な箇所のみの場合は備考に記録する。
- TC-06 は実行可能形式（「任意/optional」が残っていなければ pass）。補助として issue-flow.md と workflow.md の retro 記述が「必須」で一致していることを目視確認してもよい。
