#!/usr/bin/env bash
# I107: トラック軸ラベル（track:app / track:harness）のルール記述が運用文書から失われていないかを
# 決定論検証する文書回帰ゲート（docker/pytest/gh 非依存・ファイル読み取りのみ）。
# 実行: bash scripts/claude/tests/test_i107_track_label_docs.sh
#
# 検証内容（行数カウントの下限チェック）:
#   - .claude/skills/issue-bootstrap/SKILL.md : 各文言 1 行以上
#   - docs/runbooks/issue-flow.md             : 各文言 2 行以上（「自動実行フロー」「統合ルール」2 箇所更新の代理指標）
#   - docs/runbooks/worktree.md               : 各文言 1 行以上（§10 トラック構成表の対応ラベル）
# 0=全 PASS / 1=FAIL あり（不足箇所を stderr に列挙）。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SKILL="$REPO_ROOT/.claude/skills/issue-bootstrap/SKILL.md"
ISSUE_FLOW="$REPO_ROOT/docs/runbooks/issue-flow.md"
WORKTREE_MD="$REPO_ROOT/docs/runbooks/worktree.md"

fail=0
req() { # $1=file $2=文言 $3=最低行数
  local n
  n="$(grep -cF "$2" "$1" 2>/dev/null)" || n=0
  if [ "$n" -ge "$3" ]; then
    printf 'PASS %s: "%s" %s行（>= %s）\n' "${1#"$REPO_ROOT"/}" "$2" "$n" "$3"
  else
    printf 'FAIL %s: "%s" %s行（>= %s 必要）\n' "${1#"$REPO_ROOT"/}" "$2" "$n" "$3" >&2
    fail=1
  fi
}

req "$SKILL"       "track:app"     1
req "$SKILL"       "track:harness" 1
req "$ISSUE_FLOW"  "track:app"     2
req "$ISSUE_FLOW"  "track:harness" 2
req "$WORKTREE_MD" "track:app"     1
req "$WORKTREE_MD" "track:harness" 1

exit "$fail"
