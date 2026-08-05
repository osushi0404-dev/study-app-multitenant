# I146 レビュー: 外部コード寄稿の受付方針明示と cross-repo PR ゲート

- **関連イシュー**: #260
- **計画書**: docs/plans/open/plan_I146.md
- **Draft PR**: #261
- **ステータス**: 実装前（計画承認待ち）

---

## レビュー対象

| # | 対象 | 種別 |
|---|---|---|
| 1 | `scripts/claude/hooks/pretooluse_guard.py` | 変更（cross-repo PR ガードの追加） |
| 2 | `.claude/settings.json` | 変更（MCP GitHub ツール用 PreToolUse matcher の追加） |
| 3 | `scripts/claude/tests/test_pretooluse_gh_pr_guard.sh` | 新規（決定論テスト） |
| 4 | `scripts/claude/pr-base-sync.sh` | 変更（cross-repo チェック） |
| 5 | `scripts/claude/tests/test_pr_base_sync.sh` | 変更（スタブ拡張＋T17〜T21） |
| 6 | `.claude/skills/close/SKILL.md` | 変更（step 0） |
| 7 | `CONTRIBUTING.md` | 新規 |
| 8 | `SECURITY.md` | 新規 |
| 9 | `.github/pull_request_template.md` | 変更（1 行追加） |
| 10 | `docs/runbooks/workflow.md` | 変更（新規セクション） |
| 11 | GitHub リポジトリ設定（Private vulnerability reporting） | 有効化 |

## 重点レビュー観点

1. **fail-closed / fail-safe の使い分けが妥当か**: `pr-base-sync.sh` は取得失敗も STOP（fail-closed）、hook は取得失敗を ask に降格（fail-safe）。使い分けの根拠（作業不能を招かないこと vs 追従・push を絶対にさせないこと）が実装に反映されているか。
2. **過剰ブロックがないか**: 外部 PR を断るのに必要な操作（`close` / `comment` / `review --comment` / read-only）が素通しになっているか。塞いでしまうと運用が回らない。
3. **判定の一貫性**: cross-repo 判定が全層で `isCrossRepository` 単一ソースになっているか。文字列判定が完全一致（アンカー）で書かれ、部分一致になっていないか。
4. **既存挙動の無改変**: 自前 PR に対する挙動、既存 hard-block の順序、既存 hook 登録（2 エントリ）が変わっていないか。
5. **false-green でないこと**: 素通し系・不在判定系の TC が、失敗条件の注入で実際に NG になることを確認しているか。
6. **hook のコスト**: 対象外コマンドでネットワーク照会が走らないか。タイムアウトが設定されているか。
7. **残存ギャップの明示**: GitHub UI 経路・読み取り調査での思い込み・`curl` 直叩きが対象外であることが、計画書と runbook に明記されているか（no silent caps）。

## 結果

（実装・テスト完了後に記入する）

| # | 受け入れ条件 | 判定 | 根拠 |
|---|---|---|---|
| | | | |

## 指摘一覧

| 重大度 | 観点 | 指摘内容 | 該当箇所 | 対応 |
|--------|------|---------|---------|------|
| | | | | |
