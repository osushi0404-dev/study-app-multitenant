# I146 レビュー: 外部コード寄稿の受付方針明示と cross-repo PR ゲート

- **関連イシュー**: #260
- **計画書**: docs/plans/open/plan_I146.md
- **Draft PR**: #261
- **ステータス**: /test 完了（2026-10-17）・/close 待ち。手動 No.9 のみマージ後に確認

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

2026-10-17 `/test I146`（HEAD 286ca7d・PR #261 の CI 6 件全緑）。自動テストは auto_test.md の専用テストを正として実行し、決定論ゲート 23 行すべて exit 0・TC-02 注入版は非ゼロ（壊れた実装を不合格にする）・TC-06 件数一致 3・TC-07 `enabled=true`・回帰（push 87 / worktree 27 / checkout 14）fail=0。backend/frontend の変更が無いため pytest / Jest / E2E は非該当（CI では全緑）。

| # | 受け入れ条件 | 判定 | 根拠 |
|---|---|---|---|
| 1 | CONTRIBUTING.md に (a)(b)(c) を英日両方で記載 | ✅ | TC-06 grep 4 件・手動 No.5 |
| 2 | SECURITY.md が PVR へ誘導・メール記載なし | ✅ | TC-06（不在判定＋ダミーでの裏取り）・手動 No.6 |
| 3 | Private vulnerability reporting 有効 | ✅ | TC-07 `enabled=true`・手動 No.8 |
| 4 | PR テンプレート冒頭 1 行追加・既存無改変 | ✅（表示はマージ後 No.9） | TC-06・手動 No.7 |
| 5 | pr-base-sync.sh が cross-repo で exit 1（sync/final） | ✅ | TC-01 T17/T18・TC-02 注入で NG |
| 6 | 照会失敗・空値でも exit 1 | ✅ | TC-01 T19〜T21 |
| 7 | 自前 PR で従来挙動不変 | ✅ | TC-01 T1〜T16 |
| 8 | fork への `gh pr merge` を block | ✅ | TC-03 G1 ほか・手動 No.1 |
| 9 | ready / edit / review --approve を ask（文言に fork・head 名） | ✅（ガード側） | TC-03 G3〜G5。承認画面が出ないのはハーネス側の現象で I174 へ引き継ぎ（手動 No.2） |
| 10 | read-only・close・comment・review --comment は素通し | ✅ | TC-03 G6〜G10・手動 No.3 |
| 11 | 照会失敗時は ask に降格 | ✅ | TC-03 G17 |
| 12 | 自前 PR の挙動不変 | ✅ | TC-03 G2/G18/G19/G104〜G106・手動 No.4 |
| 13 | MCP merge=block・update_branch/APPROVE=ask | ✅ | TC-03 G13〜G16・手動 No.11 |
| 14 | MCP で pull_number 不明なら ask | ✅ | TC-03 G23 |
| 15 | settings.json に MCP matcher 登録・既存 2 エントリ無改変 | ✅ | TC-06 grep・登録数 3 |
| 16 | close SKILL step 0 に isCrossRepository | ✅ | TC-06 grep |
| 17 | 両テスト全 PASS・記録 | ✅ | pr-base-sync 21/21・gh pr guard 245/245（auto_test.md 実行記録） |
| 18 | runbook に外部 PR の扱い | ✅ | TC-06 grep・手動 No.10 |
| 19 | R9: 日常的な書き方でのすり抜けなし | ✅ | TC-03 G28〜G210・敵対的レビュー 8 周で VERDICT OK |
| 20 | R10: checkout=block・update-branch=ask・runbook「手元に checkout しない」 | ✅ | TC-03 G57〜G61/G101・TC-06 grep |

## 指摘一覧

| 重大度 | 観点 | 指摘内容 | 該当箇所 | 対応 |
|--------|------|---------|---------|------|
| - | レビュー | 基本レビュー・敵対的レビュー（8 周）の指摘はすべて対応済み | `docs/reviews/I146_code_review_*.md`・`docs/reviews/I146_adversarial_review_20261016_1600.md` | 対応済み |
| 参考 | ハーネス | フックの ask が承認画面にならない（ガードの不具合ではない） | 手動 No.2 | I174 へ引き継ぎ（2026-10-17・ユーザー判断） |
