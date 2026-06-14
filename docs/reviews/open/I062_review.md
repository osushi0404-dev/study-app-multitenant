# I062 実装レビュー

- **関連イシュー**: #128
- **計画書**: docs/plans/open/plan_I062.md
- **自動テスト**: docs/tests/open/I062_auto_test.md
- **手動テスト**: docs/tests/open/I062_manual_test.md

## レビュー対象（実装後に評価する）
- `scripts/claude/code-review.sh`（`find_plan_file` / `detect_code_verdict` / source ガード / 判定 `case`）
- `scripts/claude/plan-issue-review.sh`（`find_plan_file` / `detect_plan_verdict` / source ガード / 判定 `case`）
- `.claude/review-agents/code-reviewer.md`（`VERDICT` 契約 + P1 gate 観点）
- `.claude/review-agents/plan-reviewer.md`（`VERDICT` 契約 + P1 gate 観点）
- `scripts/claude/tests/test_review_verdict.sh`（回帰テスト資産）

## 観点（実装後にチェック）
- [ ] 受け入れ条件7項目（plan_I062 セクション2）をすべて満たすか
- [ ] 太字 `| **Blocker** |` / `| **High** |` で誤 `✅` を出さないか（TC-05）
- [ ] `VERDICT:` 一次判定 → 無ければ保険、の優先順位が正しいか
- [ ] `find_plan_file` が連番数値順・最大選択・open/closed 横断で正しいか（`_10` > `_9`）
- [ ] 既存 `find_file` の issues/tests/reviews ルックアップに退行がないか
- [ ] 関数前出し・source ガードで本体（CI 待機・claude -p・PLAN_FILE 追記）の挙動が変わっていないか
- [ ] 命名規約ドキュメント（plan-writing-rules.md / review-rules.md / issue-flow.md）を変更していないか（I064 棲み分け維持）
- [ ] P1 gate 観点が両エージェント定義に追加されているか
- [ ] `bash -n` 構文チェック・全自動 TC が PASS か
- [ ] 計画書に記載のないファイル変更がないか

## レビュー結果
（`/plan-issue-review I062` および実装後の `/code-review I062` の結果をここに追記）
