# I066 手動テスト

対象: `scripts/claude/plan-issue-review.sh`（#1 判定・#3 追記）/ `scripts/claude/tests/test_review_verdict.sh`（#4）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `bash scripts/claude/tests/test_review_verdict.sh` を実行 | 末尾が `PASS=55 FAIL=0`。TC-05/TC-12 が PASS、TC-24〜TC-27b・TC-28〜TC-31b が PASS | Claude | | 自動テスト本体 |
| 2 | `bash -n scripts/claude/plan-issue-review.sh` を実行 | 構文エラー無し（exit 0・出力なし） | Claude | | |
| 3 | `detect_plan_verdict` に多行高リスク fixture（`## 高リスク判定`\n`判定: Yes`、VERDICT 行なし）を渡す | `HIGHRISK` を返す（保険経路が多行で機能） | Claude | | source 方式で関数を直接実行 |
| 4 | サンプル plan に `append_review_link` を 2 回実行 | `## レビュー結果` 見出しは 1 個のまま、リンク行が 2 行（履歴保持・重複見出しなし） | Claude | | source 方式で関数を直接実行 |
| 5 | `git diff --name-only origin/develop...HEAD` で変更ファイルを確認 | `plan-issue-review.sh` と `test_review_verdict.sh`（＋ docs）のみ。`code-review.sh`・`close/SKILL.md`・`docs/reviews/` の移動が**含まれない**（再スコープ遵守） | Claude | | 計画書一致性検証 |
| 6 | 実際の高リスク計画に対し `/plan-issue-review I###` をライブ実走し、VERDICT 行を持たない旧形式出力で `/security-review` 案内が表示されるか確認（任意） | `✅ プランレビュー完了。/security-review ...` が表示される | Human | | LLM 実行コストを伴うため任意。No.1/3 の自動テストで論理は担保済み |
