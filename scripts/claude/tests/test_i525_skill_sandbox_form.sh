#!/usr/bin/env bash
# I525（plan_I525.md §4・auto_test TC-02）: 手順書（スキル）の `bash scripts/claude/` の起動が、サンドボックスの外に出る形のままか。
#   環境変数を前に付けた起動（`X=1 bash scripts/claude/...`）は .claude/settings.json の sandbox.excludedCommands
#   （`bash scripts/claude/*`）に当たらず、サンドボックスの中で動く。中では書き込みを止める場所に装置ファイルが差し込まれ、
#   作業ツリーの確かめ（adversarial-review.sh・gate-check.sh の git status）が DIRTY で止まる（I468 で起きた）。
#   S1: スキルに前置きの起動が無い S2: review-gate の延長の起動が引数の形 S3: その起動が excludedCommands の形に当たる
#   FG: 写し（一時のフォルダ）を壊すと、対応する項目が不合格になること（本物のファイルは書き換えない）
# 実行: bash scripts/claude/tests/test_i525_skill_sandbox_form.sh
# shellcheck disable=SC2016  # 単一引用符内の ` と $ は文字どおりの照合用
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
yn() { if "$@" >/dev/null 2>&1; then echo yes; else echo no; fi; }

EXT='bash scripts/claude/adversarial-review.sh --round-limit 3'

# S1 <根>: スキルに、環境変数を前に付けた `bash scripts/claude/` の起動が無い（あれば出して失敗）
s1() { ! grep -nE '(^|[`[:space:]$(])[A-Za-z_][A-Za-z0-9_]*=[^[:space:]`]*[[:space:]]+bash[[:space:]]+scripts/claude/' "$1"/.claude/skills/*/SKILL.md; }
# S2 <根>: review-gate の延長の起動が引数の形で書かれている
s2() { grep -qF -- "$EXT" "$1/.claude/skills/review-gate/SKILL.md"; }
# S3 <根>: S2 の起動（バッククォートの中）が、settings.json の excludedCommands の形のどれかに glob で当たる
s3() {
  local cmd pats p
  cmd=$(grep -oE -- "\`${EXT//./\\.}[^\`]*\`" "$1/.claude/skills/review-gate/SKILL.md" | head -1 | tr -d '`')
  [ -n "$cmd" ] || return 1
  pats=$(python3 -I -c 'import json, sys
for p in json.load(open(sys.argv[1], encoding="utf-8")).get("sandbox", {}).get("excludedCommands", []):
    print(p)' "$1/.claude/settings.json") || return 1
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    # shellcheck disable=SC2053  # 右辺は glob として照合する
    [[ "$cmd" == $p ]] && return 0
  done <<< "$pats"
  return 1
}

ck "S1 スキルに環境変数の前置きの起動が無い" yes "$(yn s1 "$REPO_ROOT")"
ck "S2 review-gate の延長の起動が --round-limit 3 の形" yes "$(yn s2 "$REPO_ROOT")"
ck "S3 延長の起動が sandbox.excludedCommands の形に当たる" yes "$(yn s3 "$REPO_ROOT")"

# ---------------- FG: 写しを壊すと落ちる ----------------
# copy_root <名前>: スキルと settings.json の写しを作り、その根を出す
copy_root() {
  local r="$TMP/$1"
  mkdir -p "$r/.claude"
  cp -r "$REPO_ROOT/.claude/skills" "$r/.claude/skills"
  cp "$REPO_ROOT/.claude/settings.json" "$r/.claude/settings.json"
  echo "$r"
}
R=$(copy_root fg1); printf '\nADV_ROUND_LIMIT=3 bash scripts/claude/adversarial-review.sh I###\n' >> "$R/.claude/skills/review-gate/SKILL.md"
ck "FG-S1 前置きの起動を書くと S1 が不合格" no "$(yn s1 "$R")"
R=$(copy_root fg1b); printf '\n`ADV_ROUND_LIMIT=3 bash scripts/claude/adversarial-review.sh I###`\n' >> "$R/.claude/skills/implement/SKILL.md"
ck "FG-S1 ほかのスキルのバッククォートの中でも S1 が不合格" no "$(yn s1 "$R")"
R=$(copy_root fg2); grep -vF -- "$EXT" "$REPO_ROOT/.claude/skills/review-gate/SKILL.md" > "$R/.claude/skills/review-gate/SKILL.md"
ck "FG-S2 延長の起動の行を消すと S2 が不合格" no "$(yn s2 "$R")"
R=$(copy_root fg3); python3 -I -c 'import json, sys
f = sys.argv[1]; d = json.load(open(f, encoding="utf-8"))
d["sandbox"]["excludedCommands"] = [p for p in d["sandbox"]["excludedCommands"] if p != "bash scripts/claude/*"]
json.dump(d, open(f, "w", encoding="utf-8"))' "$R/.claude/settings.json"
ck "FG-S3 excludedCommands から bash scripts/claude/* を消すと S3 が不合格" no "$(yn s3 "$R")"

echo "pass=${pass} fail=${fail}"
[ "$fail" -eq 0 ]
