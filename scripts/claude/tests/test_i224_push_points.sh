#!/usr/bin/env bash
# I224: GitHub への書き込みの時点（push は 3 時点だけ・イシュー本文の書き換えは grill-me だけ）を、
# スキルの手順の文字で確かめる。決まりを知らずに「commit/push」を書き足す事故を止めるためのもの。
# 決まりの正: docs/runbooks/workflow.md「GitHub への書き込みの時点」
# 実行: bash scripts/claude/tests/test_i224_push_points.sh
# FG: このスクリプトの中で、一時フォルダの写しを壊して各決まりが不合格になることを確かめる。
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
pass=0; fail=0
ck() {  # ck <名前> <期待> <実際>
  if [ "$2" = "$3" ]; then echo "PASS $1"; pass=$((pass + 1))
  else echo "FAIL $1（期待: $2 / 実際: $3）"; fail=$((fail + 1)); fi
}

# check <ルート>: P1〜P4 を見て、不合格の決まりを 1 行ずつ出す（無ければ何も出さない）。合格=exit 0
check() {
  python3 -I - "$1" <<'PY'
import glob, os, re, sys
root = sys.argv[1]
FIX = "決まりの正は docs/runbooks/workflow.md「GitHub への書き込みの時点」。push の時点を意図して変えるなら、その節とこのテストの数を一緒に直す"
PUSH_WORDS = re.compile(r"commit/push|commit・push|コミット・push|git push")
PUSH_LINE = re.compile(r"^\s*git push\b")
ALLOWED = {"plan-issue": 2, "review-gate": 1, "close": 1}   # 行の先頭の git push の数
bad = []
for path in sorted(glob.glob(os.path.join(root, ".claude", "skills", "*", "SKILL.md"))):
    name = os.path.basename(os.path.dirname(path))
    rel = os.path.relpath(path, root)
    lines = open(path, encoding="utf-8").read().split("\n")
    if name not in ALLOWED:
        for i, l in enumerate(lines, 1):
            if PUSH_WORDS.search(l):
                bad.append(f"P1 {rel}:{i}: push の指示は plan-issue・review-gate・close だけ（ほかの段階は commit だけ）")
    else:
        n = sum(1 for l in lines if PUSH_LINE.search(l))
        if n != ALLOWED[name]:
            bad.append(f"P2 {rel}: 行の先頭の git push が {n} 行（決めた数は {ALLOWED[name]}）")
    if name != "grill-me":
        for i, l in enumerate(lines, 1):
            if "gh issue edit" in l:
                bad.append(f"P3 {rel}:{i}: イシュー本文の書き換え（gh issue edit）は grill-me の終わりだけ")
wf = os.path.join(root, "docs", "runbooks", "workflow.md")
if not (os.path.isfile(wf) and re.search(r"^## GitHub への書き込みの時点", open(wf, encoding="utf-8").read(), re.M)):
    bad.append("P4 docs/runbooks/workflow.md: 「## GitHub への書き込みの時点」の節が無い")
for b in bad:
    print(b)
if bad:
    print(FIX)
sys.exit(1 if bad else 0)
PY
}

# ---- 本物（リポジトリの版）----
out=$(check "$REPO_ROOT"); rc=$?
[ "$rc" = 0 ] || printf '%s\n' "$out"
ck "P1〜P4 リポジトリの版で合格" 0 "$rc"

# ---- FG: 壊した写しでは、その決まりで不合格になる ----
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
fg() {  # fg <決まり> <説明> <写しのファイル（ルートからの相対）> <sed の式>
  local d="$T/fg.$RANDOM" before
  # 写すのは check が読むものだけ（primary では .claude/worktrees に全ワークツリーが入るので .claude を丸ごと写さない）
  mkdir -p "$d/docs/runbooks" "$d/.claude"
  cp -r "$REPO_ROOT/.claude/skills" "$d/.claude/"
  cp "$REPO_ROOT/docs/runbooks/workflow.md" "$d/docs/runbooks/"
  before=$(cat "$d/$3")
  sed -i "$4" "$d/$3"
  if [ "$(cat "$d/$3")" = "$before" ]; then ck "FG $1 $2 の書き換えが当たる" changed unchanged; return; fi
  check "$d" > "$d/out"
  ck "FG $1 $2 で不合格になる" 1 "$?"
  local shown=no
  if grep -q "^$1 " "$d/out"; then shown=yes; fi
  ck "FG $1 $2 は $1 として出る" yes "$shown"
}
fg P1 "retro の結線に commit/push を書く" .claude/skills/retro/SKILL.md '1s/^/commit\/push する\n/'
fg P2 "review-gate の git push を 2 行にする" .claude/skills/review-gate/SKILL.md 's/^\([[:space:]]*\)git push$/\1git push\n\1git push/'
fg P3 "retro に gh issue edit を書く" .claude/skills/retro/SKILL.md '1s/^/gh issue edit 1 --body-file x\n/'
fg P4 "正の節の見出しを消す" docs/runbooks/workflow.md 's/^## GitHub への書き込みの時点.*$/## 別の見出し/'

echo "---"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
