# I098 手動テスト: 全 worktree 横断採番スクリプト

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 実リポジトリで `bash scripts/claude/next-issue-num.sh` を実行 | 全 worktree 横断で算出した 3 桁番号が 1 行だけ stdout に出る（実行時点で妥当な次番号。例: 現状なら `099`）。exit 0 | Claude | OK | 出力 `099`・exit 0。primary の untracked（091）も加味 |
| 2 | `bash scripts/claude/tests/test_next_issue_num.sh` を実行 | `pass=N fail=0` で終了（exit 0） | Claude | OK | pass=21 fail=0・exit 0 |
| 3 | `git worktree list` の各 worktree の `docs/issues` 最大と手順1の出力を突き合わせ | 手順1の番号 = 全 worktree 横断の最大 + 1 になっている | Claude | OK | primary=091 / wt-harness=098 / git=098 → max 098 +1 = 099 = 手順1出力 |
| 4 | `docs/runbooks/issue-flow.md`・`.claude/skills/issue-bootstrap/SKILL.md`・`docs/runbooks/worktree.md` §8 を目視 | 採番は `next-issue-num.sh` 呼び出しに統一され、旧インライン bash・§8 の人手規律が残っていない | Claude | OK | next-issue-num.sh: issue-flow×8/SKILL×3/§8×1・旧FS_MAX=0・§8 権威×4・旧規律 0 |

結論: OK（全 4 項目 Claude 実施・Human 実施項目なし）
