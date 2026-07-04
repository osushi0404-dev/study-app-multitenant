#!/usr/bin/env bash
set -euo pipefail
# I098: イシュー採番の単一権威（forward cross-scan）。
# 全 worktree（git worktree list）の docs/issues FS 最大（untracked 含む）＋ git 履歴最大から
# max+1 を算出し 3 桁ゼロ詰めで stdout に出力する。read-only（I095 は横断読み取りを許可）・CWD 非依存。
# 呼び出し元: docs/runbooks/issue-flow.md ・ .claude/skills/issue-bootstrap/SKILL.md
# 詳細: docs/plans/closed/plan_I098.md ・ docs/runbooks/worktree.md §8

# パターン（I094 decoy 対策・アンカー）: パス末尾が /I###.md または /###.md のときの数字のみ抽出。
#   例: /.../open/I098.md→098 ・ /.../closed/098.md→098 ・ draft-I200.md/error_I016.md→不一致
ISSUE_NUM_RE='/I?\K\d+(?=\.md$)'

worktrees() { git worktree list --porcelain | sed -n 's/^worktree //p'; }

max=0
update_max() {  # $1=数字文字列（空可）。8 進誤解釈を防ぐ 10# で比較。末尾 return 0 で set -e 下でも非 0 を返さない。
  local n="${1:-}"; [ -n "$n" ] || return 0
  n=$((10#$n)); [ "$n" -gt "$max" ] && max="$n"; return 0
}

# 全 worktree の FS 最大（untracked 含む・docs/issues 配下のみ・絶対パス＝CWD 非依存）
while IFS= read -r wt; do
  [ -d "$wt/docs/issues" ] || continue
  update_max "$(find "$wt/docs/issues" -name '*.md' 2>/dev/null \
                 | grep -oP "$ISSUE_NUM_RE" | sort -n | tail -1 || true)"
done < <(worktrees)

# git 履歴最大（削除済み含む・全 ref）。':/docs/issues' で pathspec を repo root に固定＝CWD 非依存。
update_max "$(git log --all --name-only --pretty=format: -- ':/docs/issues' 2>/dev/null \
               | grep -oP "$ISSUE_NUM_RE" | sort -n | tail -1 || true)"

printf '%03d\n' "$((max + 1))"
