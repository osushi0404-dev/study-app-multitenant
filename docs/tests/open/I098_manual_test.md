# I098 手動テスト: 全 worktree 横断採番スクリプト

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 実リポジトリで `bash scripts/claude/next-issue-num.sh` を実行 | 全 worktree 横断で算出した 3 桁番号が 1 行だけ stdout に出る（実行時点で妥当な次番号。例: 現状なら `099`）。exit 0 | Claude | | primary の untracked も加味されること |
| 2 | `bash scripts/claude/tests/test_next_issue_num.sh` を実行 | `pass=N fail=0` で終了（exit 0） | Claude | | 決定論ゲート |
| 3 | `git worktree list` の各 worktree の `docs/issues` 最大と手順1の出力を突き合わせ | 手順1の番号 = 全 worktree 横断の最大 + 1 になっている | Claude | | 横断集計の妥当性 |
| 4 | `docs/runbooks/issue-flow.md`・`.claude/skills/issue-bootstrap/SKILL.md`・`docs/runbooks/worktree.md` §8 を目視 | 採番は `next-issue-num.sh` 呼び出しに統一され、旧インライン bash・§8 の人手規律が残っていない | Claude | | 記述整合 |

結論: OK / NG
