# I069 手動テスト

- **関連計画書**: docs/plans/open/plan_I069.md
- 本イシューは bash スクリプト／スキル指示文の編集のみ（UI・ブラウザ操作なし）。多くは Claude が `/test` 時に自動実行できる。
- `/close` 全体フロー（GitHub PR を要する End-to-End）は実運用での最終サインオフのみ Human とする。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `commit_review_artifact` が両スクリプトに同一実装で定義されているか確認: `grep -n "commit_review_artifact()" scripts/claude/plan-issue-review.sh scripts/claude/code-review.sh` | 両ファイルに関数定義が1つずつ存在する | Claude | | 案A の共通実装 |
| 2 | 両スクリプト本体で REVIEW_FILE 保存直後に `commit_review_artifact "$REVIEW_FILE" "$ISSUE" ...` が配線されているか確認: `grep -n 'commit_review_artifact "\$REVIEW_FILE"' scripts/claude/plan-issue-review.sh scripts/claude/code-review.sh` | plan-issue-review は `"plan-review"`、code-review は `"code-review"` 引数で配線されている | Claude | | 案A 配線 |
| 3 | issue-review.sh に commit 配線が無く、commit しない旨のコメントがあるか確認: 配線=`grep -vE '^[[:space:]]*#' scripts/claude/issue-review.sh \| grep -E 'commit_review_artifact\|git commit'`（コメント除外）／意図=`grep -nE 'commit しない\|コミットしない\|案A' scripts/claude/issue-review.sh` | 配線 grep はマッチ無し（実コードに commit 無し）・意図 grep はヒット（コメントで明記） | Claude | | 案A'（TC-A6/A6b と整合） |
| 4 | close/SKILL.md の timestamped 回収ループに `git add -- "$f"` が `git mv` の前にあるか目視確認 | step 1 の `for f in docs/reviews/I${ISSUE_NUM}_*_review_*.md` ループ内で add→mv の順になっている | Claude | | 案B |
| 5 | I067 のゲート（step 3）が close/SKILL.md に残っているか目視確認 | `git add -u` と決定論ゲート（`grep -vE "I${ISSUE_NUM}`）が step 3 に残存している | Claude | | AC4 回帰 |
| 6 | 自動テスト一式を実行: `bash scripts/claude/tests/test_review_commit_lifecycle.sh` | PASS のみ・FAIL=0 で終了コード 0 | Claude | | 案A/案B/静的解析 |
| 7 | 実運用の `/close` を feature ブランチ（未追跡 issue-review 記録あり）で実行し、`git mv` が `fatal: not under version control` を起こさず完走することを確認 | close が中断せず完走し、レビュー記録が `docs/reviews/closed/` に移動・commit/push される | Human | | E2E 最終サインオフ（実 PR が必要なため Human） |
