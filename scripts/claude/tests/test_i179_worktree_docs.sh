#!/usr/bin/env bash
# I179: ワークツリー運用（公式 claude --worktree 方式）の文書・設定を決定論検証する（docker/gh 非依存・読み取りのみ）。
# 実行: bash scripts/claude/tests/test_i179_worktree_docs.sh
#
# 検査は check_all <root> にまとめ、実物（repo root）で全 PASS を確認したうえで、
# 対象ファイルを一時ディレクトリへ複製して 1 つずつ失敗を注入し、狙った TC が FAIL になること（FG-D1）を確認する。
# 0=全 PASS / 1=FAIL あり。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
# 廃止したスクリプト名（このファイル自身が D2 の検索に掛からないよう分割して組み立てる）
OLD="wt-""new"

FAILED=""   # check_all が FAIL にした TC の ID（空白区切り）
VERBOSE=1
pass=0; fail=0
res() { # $1=TC $2=説明 $3=0(成立)/非0
  if [ "$3" -eq 0 ]; then
    [ "$VERBOSE" -eq 1 ] && printf 'PASS %s %s\n' "$1" "$2"
  else
    [ "$VERBOSE" -eq 1 ] && printf 'FAIL %s %s\n' "$1" "$2"
    FAILED="$FAILED $1"
  fi
}
has()   { grep -qF -- "$2" "$1" 2>/dev/null; }          # ファイル $1 に固定文字列 $2 がある
hasx()  { grep -qxF -- "$2" "$1" 2>/dev/null; }         # ファイル $1 に行全体一致 $2 がある
step5() { awk '/^\*\*ステップ5/{f=1} /^\*\*ステップ6/{f=0} f' "$1"; }   # issue-flow.md のステップ5〜6 の範囲

check_all() {
  local R="$1" W C S F rc t hits
  FAILED=""
  W="$R/docs/runbooks/worktree.md"
  C="$R/docs/runbooks/common-commands.md"
  S="$R/.claude/skills/plan-issue/SKILL.md"
  F="$R/docs/runbooks/issue-flow.md"

  # D1: 廃止したスクリプトが無い
  rc=0; [ ! -e "$R/scripts/claude/$OLD.sh" ] || rc=1
  res D1 "scripts/claude/$OLD.sh が無い" "$rc"

  # D2: 実行手順としての参照が無い（closed の記録類・I179 自身の記録は除く）
  hits="$(git -C "$R" grep -n -F -e "$OLD" 2>/dev/null \
          | grep -Ev '^docs/(issues|plans|tests|reviews)/closed/' \
          | grep -Ev '^(docs/issues/open/I179\.md|docs/plans/open/plan_I179\.md|docs/tests/open/I179_[^:]*|docs/reviews/open/I179_review\.md|docs/reviews/I179_[^:]*):' )"
  rc=0; [ -z "$hits" ] || { rc=1; [ "$VERBOSE" -eq 1 ] && printf '  %s\n' "$hits"; }
  res D2 "$OLD の参照が記録類以外に 0 件" "$rc"

  # D3: worktree.md に必要な記述がすべてある
  rc=0
  for t in 'claude --worktree' '.worktreeinclude' 'wt-ports.sh' 'wt-remove.sh' 'git stash push -u -m' \
           'git config' 'docker compose ls -a' 'git worktree list' 'track:harness' 'track:app' \
           '/plan-issue' '旧方式からの移行' 'grep -r'; do
    has "$W" "$t" || { rc=1; [ "$VERBOSE" -eq 1 ] && printf '  missing: %s\n' "$t"; }
  done
  res D3 "worktree.md に必要な記述がある" "$rc"

  # D4: worktree.md に旧記述が無い
  rc=0
  for t in '2026-07 時点' 'トラック = 1 作業ツリー' '採番権威でもある' '新設しない'; do
    has "$W" "$t" && { rc=1; [ "$VERBOSE" -eq 1 ] && printf '  unexpected: %s\n' "$t"; }
  done
  res D4 "worktree.md に旧記述が無い" "$rc"

  # D5: /plan-issue が develop をチェックアウトせず origin/develop 基点で作る
  rc=0
  has "$S" 'git checkout develop' && rc=1
  has "$S" 'checkout --no-track -b' || rc=1
  has "$S" 'origin/develop' || rc=1
  res D5 "plan-issue/SKILL.md が origin/develop 基点" "$rc"

  # D6: issue-flow.md ステップ5 も同じ（範囲外のステップ25 は対象外）
  rc=0
  step5 "$F" | grep -qF 'git checkout develop' && rc=1
  step5 "$F" | grep -qF 'git pull origin develop' && rc=1
  step5 "$F" | grep -qF 'checkout --no-track -b' || rc=1
  res D6 "issue-flow.md ステップ5 が origin/develop 基点" "$rc"

  # D7: 公式の作成・片付けを置き換えるフックが無い
  rc=0
  has "$R/.claude/settings.json" 'WorktreeCreate' && rc=1
  has "$R/.claude/settings.json" 'WorktreeRemove' && rc=1
  res D7 "settings.json に WorktreeCreate/WorktreeRemove が無い" "$rc"

  # D8: .worktreeinclude が設定ファイルをコピー対象にしている
  rc=0
  hasx "$R/.worktreeinclude" 'backend/.env' || rc=1
  hasx "$R/.worktreeinclude" 'e2e/.env.e2e' || rc=1
  res D8 ".worktreeinclude に backend/.env と e2e/.env.e2e" "$rc"

  # D9: 公式ワークツリー置き場が gitignore 済み
  rc=0; hasx "$R/.gitignore" '.claude/worktrees/' || rc=1
  res D9 ".gitignore に .claude/worktrees/" "$rc"

  # D10: common-commands.md が wt-ports.sh を案内し、廃止スクリプトを案内しない
  rc=0
  has "$C" 'wt-ports.sh' || rc=1
  has "$C" "$OLD" && rc=1
  res D10 "common-commands.md が wt-ports.sh を案内" "$rc"

  # D11: トラックとワークツリーの固定対応が無い
  rc=0
  has "$R/.claude/skills/issue-bootstrap/SKILL.md" '対応 worktree: wt-harness' && rc=1
  has "$F" '対応 worktree: wt-harness' && rc=1
  res D11 "issue-bootstrap/SKILL.md・issue-flow.md に wt-harness 固定が無い" "$rc"

  # DOC1（I097 から移設）: ポート分離の記述が残る
  rc=0
  has "$W" '同時' || rc=1
  has "$W" 'BACKEND_PORT' || rc=1
  has "$W" 'port-offset' || rc=1
  has "$W" '1 スタックずつ' && rc=1
  has "$C" 'BACKEND_PORT' || rc=1
  res DOC1 "worktree.md・common-commands.md にポート分離の記述" "$rc"

  [ -z "$FAILED" ]
}

# ===================== 実物 =====================
if check_all "$REPO_ROOT"; then pass=$((pass+1)); echo "PASS 実物 check_all"
else fail=$((fail+1)); echo "FAIL 実物 check_all:$FAILED"; fi

# ===================== FG-D1 失敗注入 =====================
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
FILES=(docs/runbooks/worktree.md docs/runbooks/common-commands.md docs/runbooks/issue-flow.md
       docs/runbooks/onboarding.md .claude/skills/plan-issue/SKILL.md .claude/skills/issue-bootstrap/SKILL.md
       .claude/settings.json .worktreeinclude .gitignore)
make_copy() { # 対象ファイルを複製し、D2 の git grep が使えるよう git 管理下に置く。stdout=複製先
  local d="$TMP/$1" f
  mkdir -p "$d"
  for f in "${FILES[@]}"; do mkdir -p "$d/$(dirname "$f")"; cp "$REPO_ROOT/$f" "$d/$f"; done
  git -C "$d" init -q
  git -C "$d" add -A
  printf '%s' "$d"
}
fg() { # $1=TC $2=注入内容（eval する文字列。$D が複製先）
  local D; D="$(make_copy "$1")"
  eval "$2"
  git -C "$D" add -A
  VERBOSE=0
  if check_all "$D"; then
    fail=$((fail+1)); echo "FAIL FG-D1 $1 注入しても PASS（false-green）"
  elif printf ' %s ' "$FAILED" | grep -qF " $1 "; then
    pass=$((pass+1)); echo "PASS FG-D1 $1 注入で $1 が FAIL"
  else
    fail=$((fail+1)); echo "FAIL FG-D1 $1 注入したが FAIL は別の TC:$FAILED"
  fi
  VERBOSE=1
}

# 注入なしの複製は PASS（複製の作り方で FAIL していないことの確認）
D0="$(make_copy base)"
VERBOSE=0
if check_all "$D0"; then pass=$((pass+1)); echo "PASS FG-D0 注入なしの複製は PASS"
else fail=$((fail+1)); echo "FAIL FG-D0 注入なしの複製が FAIL:$FAILED"; fi
VERBOSE=1

# shellcheck disable=SC2016  # 注入内容は fg 内で eval する（$D・$OLD はその時点で展開）
{
fg D1  'mkdir -p "$D/scripts/claude"; : > "$D/scripts/claude/$OLD.sh"'
fg D2  'printf "%s\n" "$OLD" >> "$D/docs/runbooks/onboarding.md"'
fg D4  'printf "%s\n" "2026-07 時点" >> "$D/docs/runbooks/worktree.md"'
fg D5  'printf "%s\n" "git checkout develop" >> "$D/.claude/skills/plan-issue/SKILL.md"'
fg D6  'sed -i "/^\*\*ステップ5/a git checkout develop" "$D/docs/runbooks/issue-flow.md"'
fg D7  'printf "%s\n" "\"WorktreeCreate\"" >> "$D/.claude/settings.json"'
fg D8  'sed -i "/^backend\/\.env$/d" "$D/.worktreeinclude"'
fg D9  'sed -i "/^\.claude\/worktrees\/$/d" "$D/.gitignore"'
fg D10 'printf "%s\n" "$OLD" >> "$D/docs/runbooks/common-commands.md"'
fg D11 'printf "%s\n" "対応 worktree: wt-harness" >> "$D/.claude/skills/issue-bootstrap/SKILL.md"'
}

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
