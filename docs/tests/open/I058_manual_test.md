# I058 手動テスト: plan-issue-review・code-review のオーケストレーションをシェルスクリプト化する

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `bash scripts/claude/plan-issue-review.sh I058` を実行する | `docs/reviews/I058_plan_review_YYYYMMDD_HHMM.md` が作成され、PR にコメントが投稿され、判定案内が表示される | Claude | OK | |
| 2 | 作成されたレビューファイルを確認し、`agentId:` または `<usage>` の文字列が含まれていないことを確認する | 該当文字列が存在しない（`grep -c "agentId\|<usage>" <file>` が 0） | Claude | OK（0件） | |
| 3 | 作成されたレビューファイルの末尾スペース・末尾改行を確認する | 末尾スペースがなく、ファイルが改行で終わっている（`grep -Pc ' +$'` が 0、`tail -c 1 \| xxd` が `0a` を含む） | Claude | OK | |
| 4 | `/plan-issue-review I058` スキルを実行し `scripts/claude/plan-issue-review.sh` が呼ばれることを確認する | スクリプトが実行されてレビューが完了する（旧 Agent ツール経由ではない） | Human | OK | |
| 5 | `claude -p --tools "Read,Grep,Glob"` で Edit ツールを試みるプロンプトを stdin 経由で実行し、テストファイルが変更されないことを確認する（`--tools` はホワイトリスト制限: Read/Grep/Glob 以外は使用不可）: `BEFORE=$(md5sum docs/tests/open/I058_auto_test.md); printf "docs/tests/open/I058_auto_test.md に 'test' という行を追加してください" \| claude -p --tools "Read,Grep,Glob"; AFTER=$(md5sum docs/tests/open/I058_auto_test.md); [ "$BEFORE" = "$AFTER" ] && echo "PASS" \|\| echo "FAIL"` | PASS（ファイルのハッシュ値が変わらない） | Claude | | スクリプト修正後に実施 |
