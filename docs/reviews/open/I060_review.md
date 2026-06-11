# I060 レビュー: CLAUDE.md と runbooks の棚卸し・最新化

## 変更概要
- `CLAUDE.md` と `docs/runbooks/*`（全14本）を横断点検し、参照整合性・実体整合性・相互整合性の3観点で乖離（D1〜D15）を解消。新規 runbook 追加時の CLAUDE.md 同期手順を template-sync.md に追記。

## 変更点
- CLAUDE.md: 参照先を全14本網羅（D1）/ PostToolUse 追記（D2）
- template-sync.md: CLAUDE.md 同期手順追記（D3）/ tasks/templates 整理（D4）
- pre-commit.md: shellcheck 追記（D5）
- issue-flow.md: テンプレ参照修正（D6/D7）/ レビューファイル命名統一（D8）/ retro 必須統一（D9）
- workflow.md: retro 必須統一（D9）
- common-commands.md: docker compose 統一（D10）
- backend-check.md: 非実在スクリプト削除（D11）/ curl 注記（D12）
- onboarding.md: posttooluse 追記（D13）/ grill-me 追記（D14）
- danger-ops / plan-writing-rules / review-rules / ux-rules / mcp-github-setup / mcp-usage / branch-protection-setup: 文体リライト（D15）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/settings.json` / hooks / `.pre-commit-config.yaml` は読み取り点検のみ。実体修正が必要な場合は別イシュー切り出し。

## レビュー観点（本イシュー固有）
- [ ] §3 乖離一覧の各修正がセマンティクスを変えていないか（D9 を除く）
- [ ] D9（retro 必須統一）が承認済み方針どおりか
- [ ] スコープ外除外項目（danger-ops 拡充・ナビ目次・ux スキル連携）に手を出していないか
- [ ] CLAUDE.md が「短く保つ」方針を維持しているか（新規ルール増設なし）
- [ ] 全 TC（TC-01〜TC-12）が pass しているか

## テスト結果
- 自動: （未実施）docs/tests/open/I060_auto_test.md
- 手動: （未実施）docs/tests/open/I060_manual_test.md

## 計画との差分
- なし / あり（理由）

## ロールバック
- 単一 PR(#125) 内のドキュメント変更。`git revert` で原状復帰可能。
