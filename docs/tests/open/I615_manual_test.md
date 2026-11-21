<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude。Human の行は備考に「試した手段: …」が必須。scripts/claude/check-manual-test-executor.sh が確かめる）
-->

# I615 手動テスト: 外で動く入口をレビュー済みの写しで動かし、人に `!` を頼まなくする

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | このブランチ（`scripts/claude/` を変えている）で、Claude の Bash から単体で `bash scripts/claude/issue-source.sh path I615` を流す（見張りが起動役の形に付け替え、外で動く） | 標準出力が `docs/issues/open/I615.md`、終了コード 0。標準エラーに `[unreviewed run]` の行が無い。`~/.cache/claude-reviewed-snapshots/<develop から分かれた時点のコミット>/.complete` がある（`ls` で確かめる） | Claude |  | AC1 の本物の起動役での確かめ（I599 までは exit 3 で止まった） |
| 2 | 同じブランチで、単体で `bash scripts/claude/fix-diagnosis-review.sh I615`（このブランチで書き換えた入口）を流す | 終了コード 75。標準エラーに `[unreviewed run]` と `fix-diagnosis-review.sh` と `! bash scripts/claude/fix-diagnosis-review.sh I615` がある。診断レビュー（`claude -p`）は起きない（`docs/reviews/open/` に新しい記録ができない） | Claude |  | AC2 の本物の起動役での確かめ |
| 3 | 本物のフックの起動役に、見張りが止める入力 `{"tool_name":"Bash","tool_input":{"command":"git push --force origin develop"}}` を標準入力で渡す: `bash .claude/hooks/reviewed-hook.sh scripts/claude/hooks/pretooluse_guard.py`。続けて `posttooluse_check.py` に壊れた JSON の Write の入力、`sessionstart_context.py` に `{"hook_event_name":"SessionStart","source":"startup"}` を渡す | 見張り: 終了コード 2・標準エラーに `[guard] force push requires DANGER_OK=1`。post: 構文の誤りを知らせる出力で終了コード 2。sessionstart: `[sessionstart]` で始まる出力で終了コード 0。どれも `[reviewed-hook]` の行と Traceback が無い | Claude |  | R1: 起動役を変えた後もすべてのフックが写しから動く（I610 manual No.3・No.3b と同じ入力） |
| 4 | `.claude/hooks/reviewed-hook.sh`・`.claude/hooks/unreviewed.py`・`.claude/hooks/reviewed-snapshot.sh` を読み、`git archive` と写しの置き場所（`claude-reviewed-snapshots`）を grep する | `git archive` と置き場所の名前は `reviewed-snapshot.sh` にだけある。`reviewed-hook.sh` は読み込み（`.`）、`unreviewed.py` は `bash …/reviewed-snapshot.sh` で使う | Claude |  | AC4（意図的な変更でしか崩れないので決定論テストにしない・plan 6） |
| 5 | 見張りを直したときの重いテストを流す: `bash scripts/claude/tests/test_guard_bash_oracle.sh`・`bash scripts/claude/tests/test_pretooluse_guard_matrix.sh`・`bash scripts/claude/tests/test_guard_corpus_diff.sh` | 3 本とも終了コード 0。corpus diff の新しい確認・停止は記録の 1% 以下（出力の割合を記録する） | Claude |  | AC6・R6（`docs/runbooks/danger-ops.md`「見張りを直したら、コミットの前に 4 つのテスト」の残り 3 本） |
| 6 | `docs/runbooks/danger-ops.md` の「サンドボックス（第 1 層）」と「外に出すコマンドの書き方」、`docs/runbooks/harness-audit.md` の起動役の行を読む | 起動役は BASE の写しで動く・入口か部品を変えたとき／写しを作れないときだけ 75 で `!` を案内する・その結果をその周の正式な結果にする・写しの置き場所が `claude-reviewed-snapshots`（古い置き場所は消してよい）・git の更新を中で動く形で流すと見張りが止める・途中で止まったときの戻しは `!`、が書いてある。「`scripts/claude/` を変えたブランチでは、マージまで起動役も外で動かない」が残っていない | Claude |  | AC7 |

結論:
