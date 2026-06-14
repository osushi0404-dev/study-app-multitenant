# I062 手動テスト

- **関連イシュー**: #128
- **計画書**: docs/plans/open/plan_I062.md

> 大半の検証は自動テスト（`docs/tests/open/I062_auto_test.md` / `bash scripts/claude/tests/test_review_verdict.sh`）でカバーする。本文書は `claude -p` 込みの実レビュー経路（非決定的・実行コスト高）と、生成側エージェントが実際に `VERDICT:` 行を出力することの確認に限定する。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 実イシュー1件で `/code-review I###` を実行し、生成された `docs/reviews/I###_code_review_*.md` の最終行を確認する | 最終行に `VERDICT: BLOCKER` / `HIGH` / `OK` のいずれか1行が出力されている | Human | | `claude -p` で実エージェントを動かす必要があるため Human |
| 2 | 同じ実レビュー結果に対するスクリプトの最終案内表示を確認する | レビュー本文の重大度（太字含む）と一致した案内（⛔ / ❌ / ✅）が表示され、誤 `✅` が出ない | Human | | 受け入れ条件「実レビュー1件で誤判定なし」の確認 |
| 3 | 実イシュー1件で `/plan-issue-review I###` を実行し、生成された `docs/reviews/I###_plan_review_*.md` の最終行を確認する | 最終行に `VERDICT: BLOCKER` / `HIGHRISK` / `OK` のいずれか1行が出力されている | Human | | 同上 |
| 4 | `plan_I###_2.md` 等の再作成計画書が存在する実イシューで `/code-review` または `/plan-issue-review` を実行する | スクリプトが連番数値順で最新（最大サフィックス）の計画書を読み込む（レビュー文中の参照計画書が `_2` 等になっている） | Human | | 実運用での `_N` 読み取り確認。なければ TC-01〜TC-04（自動）で代替確認済み |
