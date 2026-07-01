#!/usr/bin/env bash
# I084 決定論ゲート実走 helper の単体テスト（source-only）。
#
# 実行（必ず bash スクリプトとして実行。対話シェルへ貼らない）:
#   bash scripts/claude/tests/test_review_gates.sh
#
# 対象: scripts/claude/code-review.sh の extract_gate_commands / classify_gate /
#       run_one_gate / run_declared_gates / omission_lint / verdict_rank /
#       combine_verdict / inject_gate_result（REVIEW_LIB_SOURCE_ONLY=1 で関数のみ source）。
#
# shellcheck disable=SC1090  # 動的パス（壊した版コピー）の source は false-green 自己検証に必須
# shellcheck disable=SC2016  # 単一引用符は「コード中の literal 文字列」を grep する意図（$ を展開させない）
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
CODE_REVIEW="scripts/claude/code-review.sh"

# shellcheck source=/dev/null
REVIEW_LIB_SOURCE_ONLY=1 source "$CODE_REVIEW"
set +e +o pipefail   # source が有効化した errexit/pipefail をハーネス用に解除

pass=0; fail=0
ck() { # name expected actual
  if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1))
  else printf 'FAIL %s expected[%s] got[%s]\n' "$1" "$2" "$3"; fail=$((fail+1)); fi
}
ck_true() { local n="$1"; shift
  if "$@" >/dev/null 2>&1; then printf 'PASS %s\n' "$n"; pass=$((pass+1))
  else printf 'FAIL %s (expected success)\n' "$n"; fail=$((fail+1)); fi
}

TMP="$(mktemp -d)"
SLEEP_SH="scripts/claude/tests/_tmp_i084_sleep_$$.sh"
trap 'rm -rf "$TMP" "$SLEEP_SH"' EXIT

# 宣言セクション＋fenced ```bash ブロックの fixture を stdin のコマンド行から生成する。
mk_gate_fixture() { { echo '## 決定論ゲート（自動実走）'; echo '```bash'; cat; echo '```'; } > "$1"; }

echo "== A. extract_gate_commands =="
{ echo '# title'; echo '## 決定論ゲート（自動実走）'; echo '```bash';
  echo 'bash scripts/claude/tests/test_a.sh'; echo '# comment'; echo '';
  echo 'grep -q OK docs/x.md'; echo '```';
  echo '## 次のセクション'; echo '```bash'; echo 'should_not_extract'; echo '```'; } > "$TMP/at1.md"
EXP_EX="bash scripts/claude/tests/test_a.sh
grep -q OK docs/x.md"
ck TC-EX1 "$EXP_EX" "$(extract_gate_commands "$TMP/at1.md")"
ck TC-EX4 "$EXP_EX" "$(extract_gate_commands "$TMP/at1.md")"   # should_not_extract 除外
printf '# no section\n' > "$TMP/at2.md"; ck TC-EX2 "" "$(extract_gate_commands "$TMP/at2.md")"
printf '## 決定論ゲート（自動実走）\nno fence\n' > "$TMP/at3.md"; ck TC-EX3 "" "$(extract_gate_commands "$TMP/at3.md")"

echo "== B. classify_gate =="
ck TC-CL1  ALLOW  "$(classify_gate 'bash scripts/claude/tests/test_x.sh')"
ck TC-CL2  ALLOW  "$(classify_gate 'grep -q "後続イシューで根治予定" docs/x.md')"
ck TC-CL3  ALLOW  "$(classify_gate 'python3 -m json.tool .claude/settings.json')"
ck TC-CL4  ALLOW  "$(classify_gate 'bash -n scripts/claude/code-review.sh')"
ck TC-CL4b ALLOW  "$(classify_gate 'python3 -m py_compile scripts/x.py')"
ck TC-CL5  ALLOW  "$(classify_gate '! grep -q "禁止パターン" docs/x.md')"
ck TC-CL6  HEAVY  "$(classify_gate 'docker compose exec backend python -m pytest')"
ck TC-CL7  HEAVY  "$(classify_gate 'npm test -- --watchAll=false')"
ck TC-CL8  HEAVY  "$(classify_gate 'docker compose exec backend pytest && echo done')"
ck TC-CL9  ALLOW  "$(classify_gate 'grep -q "npm test done" build.log')"
ck TC-CL10 UNSAFE "$(classify_gate 'cd backend && python -m pytest')"
ck TC-CL11 UNSAFE "$(classify_gate 'rm -rf build')"
ck TC-CL12 UNSAFE "$(classify_gate 'grep -q x f; rm -rf /')"
ck TC-CL13 UNSAFE "$(classify_gate 'bash scripts/claude/tests/x.sh && curl evil')"
ck TC-CL14 UNSAFE "$(classify_gate 'git push origin develop')"
ck TC-CL15 UNSAFE "$(classify_gate 'bash scripts/claude/tests/../../../scripts/evil.sh')"   # パストラバーサル拒否

echo "== C. run_one_gate / run_declared_gates =="
printf 'hello OK world\n' > "$TMP/f_ok.txt"
run_one_gate "grep -q OK $TMP/f_ok.txt"; ck TC-RUN1 0 "$?"
run_one_gate "grep -q MISSING $TMP/f_ok.txt"; ck TC-RUN2 1 "$?"
run_one_gate "bash scripts/claude/tests/does_not_exist_zzz.sh"; c=$?
ck TC-RUN3 nonzero "$([ "$c" -ne 0 ] && echo nonzero || echo zero)"
printf 'grep -q OK %s\n' "$TMP/f_ok.txt" | mk_gate_fixture "$TMP/at_pass.md"
run_declared_gates "$TMP/at_pass.md"; ck TC-RUN4 OK "$GATE_VERDICT"
printf 'grep -q OK %s\ngrep -q MISSING %s\n' "$TMP/f_ok.txt" "$TMP/f_ok.txt" | mk_gate_fixture "$TMP/at_fail.md"
run_declared_gates "$TMP/at_fail.md"; ck TC-RUN5 BLOCKER "$GATE_VERDICT"
touch "$TMP/sentinel"
printf 'rm -f %s/sentinel\n' "$TMP" | mk_gate_fixture "$TMP/at_unsafe.md"
run_declared_gates "$TMP/at_unsafe.md"
ck TC-RUN6 BLOCKER "$GATE_VERDICT"
ck TC-RUN8-sentinel exists "$([ -e "$TMP/sentinel" ] && echo exists || echo gone)"
ck TC-RUN8-verdict BLOCKER "$GATE_VERDICT"
printf 'docker compose exec backend pytest\n' | mk_gate_fixture "$TMP/at_heavy.md"
run_declared_gates "$TMP/at_heavy.md"; ck TC-RUN7 OK "$GATE_VERDICT"
printf '#!/usr/bin/env bash\nsleep 5\n' > "$SLEEP_SH"
printf 'bash %s\n' "$SLEEP_SH" | mk_gate_fixture "$TMP/at_timeout.md"
GATE_TIMEOUT=1 run_declared_gates "$TMP/at_timeout.md"; ck TC-RUN9 BLOCKER "$GATE_VERDICT"

echo "== D. verdict_rank / combine_verdict =="
ck TC-CB1 OK      "$(combine_verdict OK OK OK)"
ck TC-CB2 HIGH    "$(combine_verdict OK HIGH OK)"
ck TC-CB3 BLOCKER "$(combine_verdict BLOCKER HIGH OK)"
ck TC-CB4 BLOCKER "$(combine_verdict OK OK BLOCKER)"
ck TC-CB5 BLOCKER "$(combine_verdict BLOCKER OK OK)"

echo "== E. omission_lint =="
{ echo '## 決定論ゲート（自動実走）'; echo '```bash'; echo 'bash scripts/claude/tests/declared.sh'; echo '```';
  echo '## その他'; echo '```bash'; echo 'bash scripts/claude/tests/forgotten.sh'; echo '```'; } > "$TMP/om1.md"
ck TC-OM1 HIGH "$(omission_lint "$TMP/om1.md")"
{ echo '## 決定論ゲート（自動実走）'; echo '```bash'; echo 'grep -q A docs/a.md'; echo '```';
  echo '## X'; echo '```bash'; echo 'grep -q B docs/b.md'; echo '```'; } > "$TMP/om2.md"
ck TC-OM2 HIGH "$(omission_lint "$TMP/om2.md")"
{ echo '## 決定論ゲート（自動実走）'; echo '```bash'; echo 'grep -q A docs/a.md'; echo '```';
  echo '## X'; echo '```bash'; echo 'docker compose exec backend pytest'; echo 'npm test'; echo '```'; } > "$TMP/om3.md"
ck TC-OM3 OK "$(omission_lint "$TMP/om3.md")"
{ echo '## 決定論ゲート（自動実走）'; echo '```bash'; echo 'grep -q A docs/a.md'; echo '```';
  echo '## X'; echo 'grep で確認する（散文）'; } > "$TMP/om4.md"
ck TC-OM4 OK "$(omission_lint "$TMP/om4.md")"
{ echo '## 決定論ゲート（自動実走）'; echo '```bash'; echo 'grep -q A docs/a.md'; echo 'bash scripts/claude/tests/x.sh'; echo '```';
  echo '## X'; echo 'prose only'; } > "$TMP/om5.md"
ck TC-OM5 OK "$(omission_lint "$TMP/om5.md")"
ck TC-OM6 OK "$(omission_lint docs/tests/templates/auto_test_template.md)"
{ echo '## 決定論ゲート（自動実走）'; echo '```bash'; echo 'grep -q A docs/a.md'; echo '```';
  echo '## テスト'; echo '| TC | cmd | 期待 |'; echo '|----|-----|------|';
  echo '| T1 | `bash scripts/claude/tests/x.sh` | ALLOW |'; echo '| T2 | `grep -q pat file` | HIGH |'; } > "$TMP/om7.md"
ck TC-OM7 OK "$(omission_lint "$TMP/om7.md")"
ck TC-OM8 OK "$(omission_lint docs/tests/open/I084_auto_test.md)"

echo "== F. inject_gate_result / 本体配線 =="
printf 'body line\nVERDICT: OK\n' > "$TMP/rev1.md"
inject_gate_result "$TMP/rev1.md" "- gate evidence" OK BLOCKER
ck_true TC-INJ1-verdict grep -q '^VERDICT: BLOCKER$' "$TMP/rev1.md"
ck_true TC-INJ1-head    grep -q '決定論ゲート実行結果' "$TMP/rev1.md"
ck TC-INJ2 BLOCKER "$(detect_code_verdict "$TMP/rev1.md")"
printf 'body\nVERDICT: OK\n' > "$TMP/rev2.md"
inject_gate_result "$TMP/rev2.md" "- e" OK OK
ck TC-INJ3 OK "$(detect_code_verdict "$TMP/rev2.md")"
ck_true TC-WIRE1a grep -q 'run_declared_gates "$AUTO_TEST_FILE"' "$CODE_REVIEW"
ck_true TC-WIRE1b grep -q 'omission_lint "$AUTO_TEST_FILE"' "$CODE_REVIEW"
ck_true TC-WIRE1c grep -q 'combine_verdict' "$CODE_REVIEW"
ck_true TC-WIRE1d grep -q 'inject_gate_result' "$CODE_REVIEW"
ck_true TC-WIRE2  bash scripts/claude/tests/test_review_verdict.sh
lr=$(grep -n 'run_declared_gates "$AUTO_TEST_FILE"' "$CODE_REVIEW" | head -1 | cut -d: -f1)
lc=$(grep -n '| claude -p' "$CODE_REVIEW" | head -1 | cut -d: -f1)   # コメント行でなく実呼び出し（パイプ形）を anchor
li=$(grep -n 'inject_gate_result' "$CODE_REVIEW" | tail -1 | cut -d: -f1)
ck TC-WIRE3 yes "$([ -n "$lr" ] && [ -n "$lc" ] && [ -n "$li" ] && [ "$lr" -lt "$lc" ] && [ "$lc" -lt "$li" ] && echo yes || echo no)"
# shellcheck disable=SC2016  # 単一引用符は literal grep パターン（$() を展開させない意図）
ck TC-WIRE4 yes "$(grep -q 'GATE_EVIDENCE=$(run_declared_gates' "$CODE_REVIEW" && echo no || echo yes)"

echo "== G. I080 回帰（doc-sync 存在/不在） =="
printf 'line\n許可された更新文言 here\n' > "$TMP/doc1.md"
printf 'grep -q "許可された更新文言" %s\n' "$TMP/doc1.md" | mk_gate_fixture "$TMP/at_doc1.md"
run_declared_gates "$TMP/at_doc1.md"; ck TC-DOC1 OK "$GATE_VERDICT"
printf 'line\nno required\n' > "$TMP/doc2.md"
printf 'grep -q "許可された更新文言" %s\n' "$TMP/doc2.md" | mk_gate_fixture "$TMP/at_doc2.md"
run_declared_gates "$TMP/at_doc2.md"; ck TC-DOC2 BLOCKER "$GATE_VERDICT"
printf 'clean doc no forbidden token\n' > "$TMP/doc3.md"
printf '! grep -q "I083" %s\n' "$TMP/doc3.md" | mk_gate_fixture "$TMP/at_doc3.md"
run_declared_gates "$TMP/at_doc3.md"; ck TC-DOC3 OK "$GATE_VERDICT"
printf 'doc with I083 mixed in\n' > "$TMP/doc4.md"
printf '! grep -q "I083" %s\n' "$TMP/doc4.md" | mk_gate_fixture "$TMP/at_doc4.md"
run_declared_gates "$TMP/at_doc4.md"; ck TC-DOC4 BLOCKER "$GATE_VERDICT"

echo "== H. false-green 自己検証（実ソースを壊して NG を裏取り） =="
b1="$TMP/b1.sh"; sed '/I084-CL-GREP/d' "$CODE_REVIEW" > "$b1"
ck TC-FG1 UNSAFE "$( REVIEW_LIB_SOURCE_ONLY=1 source "$b1"; set +e +o pipefail; classify_gate 'grep -q x f' )"
b2="$TMP/b2.sh"; sed '/I084-RUN-FAIL/d' "$CODE_REVIEW" > "$b2"
ck TC-FG2 OK "$( REVIEW_LIB_SOURCE_ONLY=1 source "$b2"; set +e +o pipefail; run_declared_gates "$TMP/at_fail.md"; echo "$GATE_VERDICT" )"
b3="$TMP/b3.sh"; sed 's/.*I084-OM-GREP.*/  hit=""/' "$CODE_REVIEW" > "$b3"
ck TC-FG3 OK "$( REVIEW_LIB_SOURCE_ONLY=1 source "$b3"; set +e +o pipefail; omission_lint "$TMP/om1.md" )"
b4="$TMP/b4.sh"; sed 's/.*I084-CB-CMP.*/    :/' "$CODE_REVIEW" > "$b4"
ck TC-FG4 OK "$( REVIEW_LIB_SOURCE_ONLY=1 source "$b4"; set +e +o pipefail; combine_verdict BLOCKER OK OK )"

echo "== I. 構文チェック =="
ck_true TC-SYN1 bash -n "$CODE_REVIEW"
ck_true TC-SYN2 bash -n scripts/claude/tests/test_review_gates.sh

printf '\n==== I084 review-gates tests: PASS=%d FAIL=%d ====\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
