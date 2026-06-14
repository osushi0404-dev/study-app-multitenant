# I064 自動テスト（Claude 機械実行）

対象: `docs/runbooks/review-rules.md` / `docs/runbooks/plan-writing-rules.md` / `docs/runbooks/issue-flow.md` の新系統一本化。
検証方式: grep / git diff による静的検証（ドキュメント整合のため）。legacy（`docs/runbooks/legacy/`）と `review001〜003` 履歴注記は除外。

| TC | 目的 | 検証コマンド | 期待結果 |
|----|------|------------|----------|
| TC-01 | review-rules.md に旧系統トークンが残らない | `grep -nE "reviewXXX\|_post\|reviews/in_progress" docs/runbooks/review-rules.md \| grep -v "review00[1-3]"` | マッチ0件（`review001〜003` 履歴注記を除き、旧トークン残存ゼロ。exit 1 相当） |
| TC-02 | review-rules.md が新系統命名を採用 | `grep -nE "IXXX_review\|_code_review_\|_plan_review_\|_issue_review_" docs/runbooks/review-rules.md` | 新系統命名が1件以上存在 |
| TC-02b | review-rules.md の状態が open/closed の2系統 | `grep -nE "in_progress\|In Progress" docs/runbooks/review-rules.md` | マッチ0件（3状態記述の撤去確認） |
| TC-03 | plan-writing-rules.md ヘッダが実体一致 | `sed -n '/^## 基本情報/,/作成日/p' docs/runbooks/plan-writing-rules.md` を目視＋ `grep -nE "reviewXXX\|_post" docs/runbooks/plan-writing-rules.md` | ヘッダに `作成根拠資料: docs/issues/...IXXX.md` / `実装後評価: ...IXXX_review.md（または未作成）` / `Draft PR` 行あり。`reviewXXX`/`_post` マッチ0件 |
| TC-04 | issue-flow.md の計画書命名・close グロブが新系統 | `grep -nE "plan_I\{イシュー番号\}_\{概要\}\|plan_IXXX_\*\.md" docs/runbooks/issue-flow.md` | マッチ0件（旧命名・旧グロブ撤去）。併せて `grep -nE "plan_I###\.md\|plan_IXXX\*\.md" docs/runbooks/issue-flow.md` が1件以上 |
| TC-05 | 全域（scope）で旧形式残存ゼロ（回帰兼） | `grep -rnE "reviewXXX\|review[0-9]{3}_\|reviews/in_progress" .claude/ docs/runbooks/ scripts/ \| grep -v "docs/runbooks/legacy/" \| grep -v "review00[1-3]_I00"` | マッチ0件（legacy・`review001〜003` 履歴注記を除く）。※除外フィルタ `review00[1-3]_I00` は履歴注記の `review001_I004` 等が `review001_I00` を部分一致で含むため正しく除外される（Info指摘・保守メモ） |
| TC-06 | 対象3ファイル以外が無変更 | `git diff --name-only origin/develop...HEAD` | 変更は `docs/issues/open/I064.md`・`docs/plans/open/plan_I064.md`・`docs/tests/open/I064_*`・`docs/reviews/open/I064_review.md`・対象runbook3ファイルのみ。`scripts/claude/*`・`.claude/skills/*`・`review_template.md`・hooks を含まない |
| TC-07 | 命名無関係部分の保持 | `grep -nE "対応品質評価\|プロセス評価\|技術的評価\|改善提案" docs/runbooks/review-rules.md` ＋ `grep -n "ベストプラクティス準拠" docs/runbooks/review-rules.md` | A/B/C/D 必須要素の見出しが残存。スキル変更時の準拠チェックリスト節が残存 |
| TC-07b | レビュー必須性コンテンツの保持（簡素化で趣旨を失わない） | `grep -nE "必須\|実装後評価" docs/runbooks/review-rules.md` | 「レビュー作成は必須」「実装後評価は `IXXX_review.md` に記録」相当の記述が残存（L25-184 簡素化後も必須性・相互参照の趣旨が残ること＝Warning指摘の補強） |
| TC-08 | review001〜003 の履歴注記 | `grep -n "旧形式" docs/runbooks/review-rules.md` | 「旧形式」を含む履歴注記が1件以上存在（全角/半角括弧・句読点の表記差異を問わない＝偽陰性回避。Warning指摘で緩和） |

## 実行記録
（/test または /implement 内で実行し、各 TC の結果を記録する）

実行日: 2026-06-15（/implement 内で実行）

| TC | 結果 | 備考 |
|----|------|------|
| TC-01 | ✅ PASS | review-rules.md 旧トークン残存0件（review001-3履歴注記を除く） |
| TC-02 | ✅ PASS | `I###_review` / `_code_review_` / `_plan_review_` / `_issue_review_` を9件以上検出 |
| TC-02b | ✅ PASS | `in_progress`/`In Progress` 0件（3状態管理を撤去） |
| TC-03 | ✅ PASS | plan-writing-rules ヘッダに `Draft PR`/issueパス/`IXXX_review.md` あり、`reviewXXX`/`_post` 0件 |
| TC-04 | ✅ PASS | issue-flow 旧命名・旧グロブ0件。L241=`plan_I###.md`、L347/L365=`plan_IXXX*.md` |
| TC-05 | ✅ PASS | 全域 旧形式残存0件（legacy・review001-3履歴注記を除く） |
| TC-06 | ✅ PASS | 変更は対象3 runbook + I064 計画系のみ。scripts/skills/template/hooks 無変更 |
| TC-07 | ✅ PASS | A/B/C/D 見出し（対応品質評価/プロセス評価/技術的評価/改善提案）+ ベストプラクティス準拠 節 残存 |
| TC-07b | ✅ PASS | `必須`/`実装後評価` を11件検出（簡素化後も必須性・実装後評価記録の趣旨を保持） |
| TC-08 | ✅ PASS | 「旧形式 `review001〜003`（旧通し番号方式）は廃止・履歴」注記あり |

補足（参照健全性）: `review-rules.md` 末尾の `docs/reviews/README.md` 参照は **I064 以前から実在しない壊れたリンク**（本イシュー前から存在）。命名規約と無関係のため I064 では原文どおり保持（別途フォローアップ候補）。
