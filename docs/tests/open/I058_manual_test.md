# I058 手動テスト: plan-issue-review・code-review のオーケストレーションをシェルスクリプト化する

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `bash scripts/claude/plan-issue-review.sh I058` を実行する | `docs/reviews/I058_plan_review_YYYYMMDD_HHMM.md` が作成され、PR にコメントが投稿され、判定案内が表示される | Claude | OK | |
| 2 | 作成されたレビューファイルを確認し、`agentId:` または `<usage>` の文字列が含まれていないことを確認する | 該当文字列が存在しない（`grep -c "agentId\|<usage>" <file>` が 0） | Claude | OK（0件） | |
| 3 | 作成されたレビューファイルの末尾スペース・末尾改行を確認する | 末尾スペースがなく、ファイルが改行で終わっている（`grep -Pc ' +$'` が 0、`tail -c 1 \| xxd` が `0a` を含む） | Claude | OK | |
| 4 | `/plan-issue-review I058` スキルを実行し `scripts/claude/plan-issue-review.sh` が呼ばれることを確認する | スクリプトが実行されてレビューが完了する（旧 Agent ツール経由ではない） | Human | OK | |
| 5 | `claude -p --allowedTools "Read" "Grep" "Glob"` で Edit ツールを試みるプロンプトを実行し、テストファイルが変更されないことを確認する: `BEFORE=$(md5sum docs/tests/open/I058_auto_test.md); claude -p --allowedTools "Read" "Grep" "Glob" "docs/tests/open/I058_auto_test.md に 'test' という行を追加してください"; AFTER=$(md5sum docs/tests/open/I058_auto_test.md); [ "$BEFORE" = "$AFTER" ] && echo "PASS" \|\| echo "FAIL"` | PASS（ファイルのハッシュ値が変わらない） | Claude | | ステップ5実装後に実施 |
