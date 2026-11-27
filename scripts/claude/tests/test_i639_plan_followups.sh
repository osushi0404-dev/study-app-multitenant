#!/usr/bin/env bash
# shellcheck disable=SC2317,SC2016  # 場面の関数は "$s" "$SRC"・fg から間接に呼ぶ／sed の式の $ は文字そのもの
# I639: scripts/claude/check-plan-followups.sh（計画書の番号の付いていない「別イシュー」「後続」の行を拾う）を
# 決定論で確かめる（docs/tests/open/I639_auto_test.md の TC-05）。
# 守るもの: 計画で後に回すと決めた項目が起票されないまま close まで進む（I466）。
# 実行: bash scripts/claude/tests/test_i639_plan_followups.sh（0=全 PASS / 1=FAIL あり）
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SRC="$REPO_ROOT/scripts/claude/check-plan-followups.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail=0
ok()  { printf 'PASS %s\n' "$1"; }
ng()  { printf 'FAIL %s\n' "$1" >&2; fail=1; }
res() { if [ "$2" -eq 0 ]; then ok "$1"; else ng "$1"; fi; }

R="$TMP/repo"
I466_LINE='- 残す: モデル・admin・マイグレーション。表の削除は別イシュー（Danger Ops）で行う'

# plan <open|closed> <本文>: 一時のリポジトリに plan_I777.md だけを置く
plan() {
  rm -rf "$R"; mkdir -p "$R/docs/plans/$1"; git -C "$R" init -q
  printf '# I777 計画書: x\n\n## 9. 確定事項と自律判断\n%s\n' "$2" > "$R/docs/plans/$1/plan_I777.md"
}
# run <スクリプト> <期待の終了コード> [引数]: 出力は $TMP/out
run() {
  local arg=I777
  [ $# -ge 3 ] && arg="$3"
  (cd "$R" && bash "$1" "$arg") > "$TMP/out" 2>&1
  [ $? -eq "$2" ]
}

p1() { plan open "$I466_LINE"; run "$1" 1 && grep -qF "docs/plans/open/plan_I777.md:4: ${I466_LINE}" "$TMP/out"; }
p2() { plan open "${I466_LINE} → #492"; run "$1" 0; }
p3() { plan open '- 要るなら別イシュー（起票しない: 仮の話）'; run "$1" 0; }
p4() { plan open $'```\n後続\n```'; run "$1" 0; }
p5() { plan open '- I777 の後続で直す'; run "$1" 1; }
p6() { plan open $'- I778 の後続で直す\n- 別のイシュー I1000 に同梱'; run "$1" 0; }
p7() {
  plan open $'- a は別イシュー\n- b は後続で'
  run "$1" 1 && grep -qF ':4: - a は別イシュー' "$TMP/out" && grep -qF ':5: - b は後続で' "$TMP/out"
}
p8() { plan closed "$I466_LINE"; run "$1" 1 && grep -qF 'docs/plans/closed/plan_I777.md:4:' "$TMP/out"; }
p9() {
  plan open "$I466_LINE"
  local a
  for a in I77 ../I777 "" I888; do run "$1" 2 "$a" || return 1; done
}
p10() { plan open '- 関係のない行'; run "$1" 0; }
p11() { # 連番の計画書があれば最新（_2）を見る（find_plan_file）
  plan open '- 関係のない行'
  printf '%s\n' "$I466_LINE" > "$R/docs/plans/open/plan_I777_2.md"
  run "$1" 1 && grep -qF 'docs/plans/open/plan_I777_2.md:1:' "$TMP/out"
}

for s in p1 p2 p3 p4 p5 p6 p7 p8 p9 p10 p11; do
  "$s" "$SRC"; res "TC-05 ${s^^}" $?
done

# ---- 失敗の注入 ----
mkdir -p "$TMP/fg"
cp "$REPO_ROOT/scripts/claude/code-review.sh" "$TMP/fg/"   # 壊した写しも find_plan_file を読める（読めないと exit 2 で FG が空振りする）
fg() { # $1=名前 $2=場面 $3=sed 式
  local broken="$TMP/fg/check_$1.sh"
  sed -e "$3" "$SRC" > "$broken"
  if cmp -s "$broken" "$SRC"; then ng "FG-$1（sed が当たらない）"; return; fi
  if "$2" "$broken" >/dev/null 2>&1; then ng "FG-$1（壊しても合格した）"; else ok "FG-$1"; fi
}
fg P5 p5 's/^    gsub(own_re, "", line)$/    line = line/'
fg P4 p4 's/^  fence { next }$/  0 { next }/'
fg P3 p3 's/^  index(\$0, opt) { next }$/  0 { next }/'
fg P2 p2 's/^    if (line ~ NUM_RE) next$/    line = line/'

exit "$fail"
