#!/usr/bin/env bash
# I074 テスト: fix-loop 多段サブエージェントレビュー順次ゲートの判定純関数・存在・回帰・false-green 反証。
#
# 実行（必ずスクリプトとして bash 実行すること。対話シェルへ貼らない）:
#   bash scripts/claude/tests/test_fix_review.sh
#
# 理由: Claude Code の対話シェルでは grep が同梱 ugrep ラッパーに上書きされ -E/-o パイプが
#       誤動作する。bash サブプロセスでは実 GNU grep が使われるため決定論的に PASS する。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1

LIB="scripts/claude/fix-review-lib.sh"
DIAG_SH="scripts/claude/fix-diagnosis-review.sh"
IMPL_SH="scripts/claude/fix-implementation-review.sh"
TEST_SH="scripts/claude/fix-test-review.sh"
DIAG_AGENT=".claude/review-agents/fix-diagnosis-reviewer.md"
IMPL_AGENT=".claude/review-agents/fix-implementation-reviewer.md"
TEST_AGENT=".claude/review-agents/fix-test-reviewer.md"
SKILL=".claude/skills/fix-loop/SKILL.md"

pass=0; fail=0
ck() { # name expected actual
  if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1))
  else printf 'FAIL %s  expected[%s] got[%s]\n' "$1" "$2" "$3"; fail=$((fail+1)); fi
}
ck_true() { # name cmd... : expect exit 0
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then printf 'PASS %s\n' "$name"; pass=$((pass+1))
  else printf 'FAIL %s (expected success)\n' "$name"; fail=$((fail+1)); fi
}
ck_grep() { # name file pattern  : expect >=1 match
  if grep -qE "$3" "$2" 2>/dev/null; then printf 'PASS %s\n' "$1"; pass=$((pass+1))
  else printf 'FAIL %s (pattern not found: %s in %s)\n' "$1" "$3" "$2"; fail=$((fail+1)); fi
}
ck_ngrep() { # name file pattern  : expect 0 match
  if grep -qE "$3" "$2" 2>/dev/null; then printf 'FAIL %s (unexpected match: %s in %s)\n' "$1" "$3" "$2"; fail=$((fail+1))
  else printf 'PASS %s\n' "$1"; pass=$((pass+1)); fi
}

# ---- 対象 lib から helper 関数のみを source（ガードで本体は実行されない） ----
# shellcheck source=/dev/null
REVIEW_LIB_SOURCE_ONLY=1 source "$LIB"
set +e +o pipefail   # source が有効化した errexit/pipefail をテストハーネス用に解除

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "== TC-01: source ガードで helper のみ定義（本体未実行） =="
ck_true TC-01-detect     declare -F detect_fix_verdict
ck_true TC-01-gate       declare -F verdict_to_gate
ck_true TC-01-exit       declare -F gate_exit_code
ck_true TC-01-commit     declare -F commit_review_artifact
ck_true TC-01-run        declare -F run_fix_review

echo "== TC-02〜05: detect_fix_verdict =="
printf 'body\nVERDICT: BLOCKER\n' > "$TMP/v_blocker.md"; ck TC-02 "BLOCKER" "$(detect_fix_verdict "$TMP/v_blocker.md")"
printf 'body\nVERDICT: HIGH\n'    > "$TMP/v_high.md";    ck TC-03 "HIGH"    "$(detect_fix_verdict "$TMP/v_high.md")"
printf 'body\nVERDICT: OK\n'      > "$TMP/v_ok.md";      ck TC-04 "OK"      "$(detect_fix_verdict "$TMP/v_ok.md")"
printf 'no verdict line here\n'   > "$TMP/v_none.md";    ck TC-05 ""        "$(detect_fix_verdict "$TMP/v_none.md")"

echo "== TC-06/07/07b: decoy（部分一致・非近接・中間行） =="
printf 'VERDICThHIGH inline\n# VERDICT: HIGH（例示・装飾）\nVERDICT: OK\n' > "$TMP/v_decoy1.md"
ck TC-06 "OK" "$(detect_fix_verdict "$TMP/v_decoy1.md")"
printf 'この文には BLOCKER や HIGH の語がある\nVERDICT: OK\n' > "$TMP/v_decoy2.md"
ck TC-07 "OK" "$(detect_fix_verdict "$TMP/v_decoy2.md")"
printf '対話例:\nVERDICT: HIGH\n本文つづき\nVERDICT: OK\n' > "$TMP/v_mid.md"
ck TC-07b "OK" "$(detect_fix_verdict "$TMP/v_mid.md")"

echo "== TC-08〜11: verdict_to_gate / gate_exit_code =="
ck TC-08 "REMAND" "$(verdict_to_gate BLOCKER)"
ck TC-09 "REMAND" "$(verdict_to_gate HIGH)"
ck TC-10 "PASS"   "$(verdict_to_gate OK)"
ck TC-11-pass "0" "$(gate_exit_code PASS)"
ck TC-11-remand "1" "$(gate_exit_code REMAND)"

echo "== TC-12/13: false-green 反証 =="
# 壊した複製（BLOCKER のみ REMAND）は HIGH を誤って PASS にする。正規は REMAND。
verdict_to_gate_broken() { case "$1" in BLOCKER) echo REMAND;; *) echo PASS;; esac; }
ck TC-12-broken "PASS"   "$(verdict_to_gate_broken HIGH)"
ck TC-12-real   "REMAND" "$(verdict_to_gate HIGH)"
# ゲートが常時 0 の空振りでない: HIGH/BLOCKER は exit1
ck TC-13-high   "1" "$(gate_exit_code "$(verdict_to_gate HIGH)")"
ck TC-13-ok     "0" "$(gate_exit_code "$(verdict_to_gate OK)")"

echo "== TC-14/15: reviewer 3 定義の存在・契約・観点 =="
for a in "$DIAG_AGENT" "$IMPL_AGENT" "$TEST_AGENT"; do
  ck_true "TC-14-exists $(basename "$a")" test -f "$a"
  ck_grep "TC-14-verdict $(basename "$a")" "$a" 'VERDICT:.*(BLOCKER|HIGH|OK)'
  ck_grep "TC-14-readonly $(basename "$a")" "$a" 'Read.*Grep.*Glob'
done
ck_grep TC-15-diag "$DIAG_AGENT" '影響調査'
ck_grep TC-15-diag2 "$DIAG_AGENT" '同型'
ck_grep TC-15-impl "$IMPL_AGENT" '回帰'
ck_grep TC-15-impl2 "$IMPL_AGENT" '副作用'
ck_grep TC-15-test "$TEST_AGENT" 'false-green|否定|異常系'

echo "== TC-16/17/18: スクリプトの存在・起動契約・最小権限・入力 =="
for s in "$LIB" "$DIAG_SH" "$IMPL_SH" "$TEST_SH"; do
  ck_true "TC-16-exists $(basename "$s")" test -f "$s"
done
ck_grep TC-16-claude "$LIB" 'claude -p'
ck_grep TC-16-tools  "$LIB" '\-\-tools[[:space:]]+"Read,Grep,Glob"'
ck_grep TC-16-model  "$LIB" 'claude-sonnet-4-6'
# TC-17: --tools 引用符内に書込ツールが無い（コメントで false-positive しない）
for s in "$LIB" "$DIAG_SH" "$IMPL_SH" "$TEST_SH"; do
  ck_ngrep "TC-17-nowrite $(basename "$s")" "$s" '\-\-tools[[:space:]]+"[^"]*(Write|Edit|Bash|MultiEdit)[^"]*"'
done
# TC-17 反証: 注入文字列は検出される
printf '%s\n' '  --tools "Read,Write,Glob"' > "$TMP/inject.txt"
ck_grep TC-17-decoy "$TMP/inject.txt" '\-\-tools[[:space:]]+"[^"]*(Write|Edit|Bash|MultiEdit)[^"]*"'
# TC-18: fix-test-review が全差分＋結果＋untracked を入力にする
ck_grep TC-18-diff "$TEST_SH" 'git diff'
ck_grep TC-18-untracked "$TEST_SH" 'ls-files --others --exclude-standard'

echo "== TC-19〜22: SKILL.md の手順・ゲート・導線・fail-safe =="
ck_grep TC-19-35 "$SKILL" '3\.5'
ck_grep TC-19-55 "$SKILL" '5\.5'
ck_grep TC-19-65 "$SKILL" '6\.5'
ck_grep TC-20-blocker "$SKILL" 'BLOCKER'
ck_grep TC-20-high "$SKILL" 'HIGH'
ck_grep TC-20-cap "$SKILL" '連続 NG.*2|2 *回'
ck_grep TC-21-diag "$SKILL" '診断'
ck_grep TC-21-remand "$SKILL" '差し戻し'
ck_grep TC-22-failsafe "$SKILL" 'fail-safe|実 diff|再判定'
ck_grep TC-22-minor "$SKILL" '軽微例外'
ck_grep TC-22-skip "$SKILL" '未実施'

echo "== TC-23/24: 既存手順1〜7 の非後退（回帰）＋反証 =="
regress_ok() { # $1=file : 既存 lint/scan キーワードが全て残っているか
  local f="$1"
  for kw in pytest flake8 bandit Jest ESLint 'npm audit'; do
    grep -qF "$kw" "$f" || return 1
  done
  return 0
}
ck_true TC-23-regress regress_ok "$SKILL"
# 反証: 1 キーワード（bandit）を削除した複製は NG（非ゼロ）
sed 's/bandit//g' "$SKILL" > "$TMP/skill_broken.md"
if regress_ok "$TMP/skill_broken.md"; then
  printf 'FAIL TC-24-decoy (broken copy passed regression)\n'; fail=$((fail+1))
else
  printf 'PASS TC-24-decoy\n'; pass=$((pass+1))
fi

echo "== TC-25: 新規 docs/fixes/ を作らない =="
ck_true TC-25-nofixesdir test ! -d "docs/fixes"
ck_grep TC-25-path "$LIB" 'docs/reviews/'

echo
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
