#!/usr/bin/env bash
# I512（plan_I512.md §4・auto_test TC-01〜TC-05。AC8〔I430 の一覧の行〕は CI で毎回確かめない＝manual_test No.4）: 計画で受け入れた残余リスクの目印（ACCEPTED=R<番号>）。
#   目印は計画書の「## 8. Risk & 回避策」の表で処遇が「受け入れ」の行と照合し、Medium 以下・再現なし・アプリ本体でない行だけを
#   後続イシューにせず一覧へ回す。止める判定は変えない。照合に合わなければ今までどおり（fail-closed）
#   FG: 判定の要を一時コピーで壊すと、対応する項目が不合格になること（本物は書き換えない）
# 実行: bash scripts/claude/tests/test_i512_accepted_risk.sh
# shellcheck disable=SC2016  # 単一引用符内の $ は文字どおりの照合用
# shellcheck disable=SC1090,SC1091  # code-review.sh（と壊した写し）は関数だけを読み込む
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.invalid GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.invalid

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
rc() { "$@" >/dev/null 2>&1; echo $?; }
yn() { if "$@" >/dev/null 2>&1; then echo yes; else echo no; fi; }
CR="$REPO_ROOT/scripts/claude/code-review.sh"

# lib <code-review.sh の写し> <関数と引数…>: 関数だけを読み込んで 1 つ呼ぶ
lib() { local src="$1"; shift; REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1"; shift; "$@"' _ "$src" "$@"; }
# 壊した写し: <置き換え前> <置き換え後>（置き換え前が無ければ印を残して最後に不合格）
broken() { local f="$TMP/b_$RANDOM$RANDOM.sh"
  python3 -I -c 'import sys
s = open(sys.argv[1], encoding="utf-8").read()
if sys.argv[3] not in s: sys.exit(1)
open(sys.argv[2], "w", encoding="utf-8").write(s.replace(sys.argv[3], sys.argv[4]))' "$CR" "$f" "$1" "$2" || : > "$TMP/broken_failed"
  echo "$f"; }

# route <写し> <issue|backlog> <台帳> [<計画書>]: 振り分けの標準出力 / ids: 番号だけを , でつなぐ
route() { lib "$1" ledger_route "$2" "$3" "${4:-}" 2>/dev/null; }
ids() { route "$@" | cut -d' ' -f2 | paste -sd, -; }
# L <番号> <SEV> <KIND> <REPRO> <SECURITY> <目印|-> [<STOP>]: 台帳の行（SCOPE=delta・FILE=x・要約は s<番号>）
L() { local acc=""; [ "$6" != "-" ] && acc=" ACCEPTED=$6"
  printf 'LEDGER: %s SEV=%s STATUS=open SCOPE=delta KIND=%s STOP=%s REPRO=%s RISK=-%s SECURITY=%s FILE=x | s%s\n' \
    "$1" "$2" "$3" "${7:--}" "$4" "$acc" "$5" "${1#F}"; }

# ---------------- 共通の計画書 ----------------
PLAN="$TMP/plan.md"
cat > "$PLAN" <<'EOF'
# I900 計画書: t

## 8. Risk & 回避策
<!--
  雛形と同じ注記。例の行は読まない:
| R9: x | y | 受け入れ |
-->
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: a | b | 回避 |
| R2: c | d | 受け入れ |
| R4：e | f |  受け入れ  |
| R6: g | h | 受け入れない |

## 9. 確定事項と自律判断
| R5: x | y | 受け入れ |
EOF

# ---------------- TC-01（AC1）: 目印が効く行は一覧へ・理由に「計画で受け入れ（R<番号>）」 ----------------
{ L F1 Medium guard no yes R2; L F2 Medium guard no no R4; L F3 Low harness no yes R2; L F4 Medium harness no yes R2; } > "$TMP/t1"
T1_LINE='- F1 SEV=Medium REPRO=no KIND=guard SECURITY=yes FILE=x | s1 | 一覧に回した理由: 再現なし／計画で受け入れ（R2）'
t1() { echo "I:$(ids "$1" issue "$TMP/t1" "$PLAN") B:$(ids "$1" backlog "$TMP/t1" "$PLAN")"; }
ck "TC-01 後続イシューは空・一覧に F1〜F4" "I: B:F1,F2,F3,F4" "$(t1 "$CR")"
route "$CR" backlog "$TMP/t1" "$PLAN" > "$TMP/t1_bl"
ck "TC-01 F1 の一覧の行が完全一致・F2 の理由は R4（全角コロン・前後の空白の行も読む）" "yes yes" \
  "$(yn grep -qxF -- "$T1_LINE" "$TMP/t1_bl") $(yn grep -qE -- '^- F2 .*一覧に回した理由: 再現なし／計画で受け入れ（R4）$' "$TMP/t1_bl")"
ck "FG-01a 受け入れた行で理由を外さないと不合格（F1・F2・F4 が後続イシュー）" "I:F1,F2,F4 B:F3" \
  "$(t1 "$(broken 'r = [x for x in route_reasons(e) if not (ok and x in ACCEPTED_DROPS)]' 'r = route_reasons(e)')")"
B01B=$(broken 'why.append(f"計画で受け入れ（{e[10]}）")' 'pass')
ck "FG-01b 一覧の理由に「計画で受け入れ」を足さないと不合格" no "$(yn grep -qxF -- "$T1_LINE" <(route "$B01B" backlog "$TMP/t1" "$PLAN"))"
ck "FG-01c 全角コロンを読まないと不合格（F2 が後続イシュー）" "I:F2 B:F1,F3,F4" \
  "$(t1 "$(broken 'PLAN_RISK_ROW = re.compile(r"\|\s*(R[0-9]+)\s*[:：]")' 'PLAN_RISK_ROW = re.compile(r"\|\s*(R[0-9]+)\s*[:]")')")"

# ---------------- TC-02（AC2・AC3）: 目印なし・High 以上・再現あり・アプリ本体は今までどおり（最優先も） ----------------
{ L F1 Medium guard no yes -; L F2 High guard no yes R2; L F3 Medium harness yes yes R2; L F4 Medium app no yes R2; } > "$TMP/t2"
T2_WANT='I:F1,F2,F3,F4 B: S:F1,F2,F3,F4 W:3'
# t2 <写し>: issue 側は 1 回だけ流し、標準出力・標準エラーから I・S・W を取り出す
t2() { lib "$1" ledger_route issue "$TMP/t2" "$PLAN" > "$TMP/t2_o" 2> "$TMP/t2_e"
  echo "I:$(cut -d' ' -f2 "$TMP/t2_o" | paste -sd, -) B:$(ids "$1" backlog "$TMP/t2" "$PLAN") \
S:$(awk -F'後続イシューにする理由: ' 'index($2, "SECURITY=yes") { split($1, a, " "); print a[2] }' "$TMP/t2_o" | paste -sd, -) \
W:$(grep -c '^目印を使わない: ' "$TMP/t2_e")"; }
ck "TC-02 4 行とも後続イシューで理由に SECURITY=yes・目印を使わない が 3 行" "$T2_WANT" "$(t2 "$CR")"
ck "TC-02 F4（アプリ本体）の理由は SECURITY=yes・アプリ本体" yes \
  "$(yn grep -qE -- '^- F4 .*\| 後続イシューにする理由: SECURITY=yes・アプリ本体$' "$TMP/t2_o")"
ck "FG-02a High 以上の条件を外すと不合格" no "$(yn [ "$(t2 "$(broken 'if RANK[e[0]] > 1:' 'if False:')")" = "$T2_WANT" ])"
ck "FG-02b 再現の条件を外すと不合格" no "$(yn [ "$(t2 "$(broken 'if e[5] != "no":' 'if False:')")" = "$T2_WANT" ])"
ck "FG-02c アプリ本体の条件を外すと不合格（F4 が最優先から外れる）" no "$(yn [ "$(t2 "$(broken 'if e[3] == "app":' 'if False:')")" = "$T2_WANT" ])"

# ---------------- TC-03（AC4）: 止める判定は目印で変わらない ----------------
{ L F1 High guard no yes R2; L F2 Medium harness yes no R2 flow; L F3 Medium app yes no R2; } > "$TMP/t3"
sed -E 's/ ACCEPTED=R[0-9]+//' "$TMP/t3" > "$TMP/t3_none"
blk() { lib "$1" ledger_blocking "$2" | cut -d' ' -f2 | paste -sd, -; }
t3() { echo "$(lib "$1" ledger_verdict "$TMP/t3") $(lib "$1" ledger_verdict "$TMP/t3_none") $(blk "$1" "$TMP/t3") $(blk "$1" "$TMP/t3_none")"; }
ck "TC-03 目印あり・なしで HIGH・止める指摘は F1,F2,F3" "HIGH HIGH F1,F2,F3 F1,F2,F3" "$(t3 "$CR")"
ck "TC-03 振り分けでも 3 行とも後続イシューで理由に止める指摘" 3 "$(route "$CR" issue "$TMP/t3" "$PLAN" | grep -c '後続イシューにする理由: 止める指摘')"
ck "FG-03 blocking() が目印を見ると不合格（目印ありで OK）" OK \
  "$(lib "$(broken 'def blocking(e):
' 'def blocking(e):
    if e[10] != "-": return False
')" ledger_verdict "$TMP/t3")"

# ---------------- TC-04（AC6）: 前の形の行・形の崩れ・書き直し ----------------
R="$TMP/repo"; mkdir -p "$R/scripts/claude"
git -C "$R" init -q -b develop
seq 1 20 | sed 's/^/a/' > "$R/scripts/claude/a.sh"
git -C "$R" add -A; git -C "$R" commit -qm base
printf 'scripts/claude/a.sh\t10\t10\n' > "$TMP/hunks"
printf 'scripts/claude/a.sh\n' > "$TMP/bfiles"
# upd <写し> <full|delta> <前の台帳|""> <FINDING 行…>: 台帳を出す（形の崩れは PARSE_ERROR）
upd() { local src="$1" kind="$2" prev="$3"; shift 3; printf '%s\n' "$@" > "$TMP/cur.md"
  (cd "$R" && lib "$src" ledger_update "$kind" "$prev" "$TMP/cur.md" "$TMP/hunks" "$TMP/bfiles") 2>/dev/null || echo PARSE_ERROR; }
FN='FINDING: F1 SEV=Low STATUS=open FILE=scripts/claude/a.sh LINE=10 SECURITY=no STOP=-'
OLD='LEDGER: F1 SEV=Low STATUS=open SCOPE=delta KIND=harness STOP=- REPRO=no RISK=- SECURITY=no FILE=scripts/claude/a.sh | s'
ck "TC-04a 目印の無い行の LEDGER 行は前の形と完全一致" "$OLD" "$(upd "$CR" full "" "$FN | s")"
ck "TC-04b 目印は RISK の後ろ（RISK=up のときも）" "yes yes" \
  "$(yn grep -qF 'RISK=- ACCEPTED=R2 SECURITY=no' <(upd "$CR" full "" "$FN ACCEPTED=R2 | s")) $(yn grep -qF 'RISK=up ACCEPTED=R2 SECURITY=no' <(upd "$CR" full "" "$FN RISK=up ACCEPTED=R2 | s"))"
printf '%s\n' "$FN | s" > "$TMP/p0"; printf '%s\n' "$FN RISK=up ACCEPTED=R2 | s" > "$TMP/p1"
ncol() { lib "$1" parse_findings "$2" | awk -F'\t' '{ print NF }'; }
ck "TC-04c parse の列は目印の有無で同じ 8 列" "8 8" "$(ncol "$CR" "$TMP/p0") $(ncol "$CR" "$TMP/p1")"
ck "TC-04d ACCEPTED=x・ACCEPTED= は形の崩れ" "PARSE_ERROR PARSE_ERROR" "$(upd "$CR" full "" "$FN ACCEPTED=x | s") $(upd "$CR" full "" "$FN ACCEPTED= | s")"
printf 'LEDGER: F1 SEV=High STATUS=open SCOPE=delta SECURITY=no | a\n' > "$TMP/o197"
printf '%s\n' 'LEDGER: F2 SEV=Low STATUS=open SCOPE=delta KIND=harness STOP=- REPRO=no SECURITY=no | b' \
  'LEDGER: F3 SEV=Low STATUS=open SCOPE=delta KIND=harness STOP=- REPRO=no RISK=- SECURITY=no | c' > "$TMP/o205"
ck "TC-04e 前の形の行: I197 形は HIGH・I205/I202 形は OK・一覧に F2,F3" "HIGH OK F2,F3" \
  "$(lib "$CR" ledger_verdict "$TMP/o197") $(lib "$CR" ledger_verdict "$TMP/o205") $(ids "$CR" backlog "$TMP/o205" "$PLAN")"
printf 'LEDGER: F1 SEV=High STATUS=open SCOPE=delta KIND=harness STOP=flow REPRO=yes RISK=- ACCEPTED=R2 SECURITY=no FILE=scripts/claude/a.sh | h\n' > "$TMP/prev"
F_RE='FINDING: F1 SEV=High STATUS=open FILE=scripts/claude/a.sh LINE=10 SECURITY=no STOP=flow | h | 再現: r'
ck "TC-04f 書き直しで目印を外すと台帳の目印も消える" no "$(yn grep -qF 'ACCEPTED=' <(upd "$CR" delta "$TMP/prev" "$F_RE"))"
ck "FG-04a 目印の無い行にも ACCEPTED=- を書くと不合格" no "$(yn [ "$(upd "$(broken 'if acc != "-" else ""' 'if True else ""')" full "" "$FN | s")" = "$OLD" ])"
ck "FG-04b parse に目印の列を出すと不合格（9 列）" 9 "$(ncol "$(broken 'g[:7] + g[9:]' 'g[:7] + g[8:]')" "$TMP/p1")"
ck "FG-04c 書き直しで前の目印を残すと不合格" yes \
  "$(yn grep -qF 'ACCEPTED=R2' <(upd "$(broken 'o[9] if o[9] != "-" else file, acc]' 'o[9] if o[9] != "-" else file, o[10] if o[10] != "-" else acc]')" delta "$TMP/prev" "$F_RE"))"

# ---------------- TC-05（AC5）: 照合の失敗では今までどおり後続イシュー ----------------
L F1 Medium guard no yes R2 > "$TMP/t5"
sed 's/^## 8\. Risk/## 7. Risk/' "$PLAN" > "$TMP/plan_nosec"
grep -v '^| R2:' "$PLAN" > "$TMP/plan_norow"
sed 's/^| R2: c | d | 受け入れ |/| R2: c | d | 回避 |/' "$PLAN" > "$TMP/plan_avoid"
for r in R5 R1 R6 R9; do sed "s/ACCEPTED=R2/ACCEPTED=$r/" "$TMP/t5" > "$TMP/t5_$r"; done
# 同じ R2 に回避の行もある計画書・8 の節の HTML コメントの中にだけ R2 の受け入れの行がある計画書（I512 retro F1）
sed 's/^| R2: c | d | 受け入れ |$/&\n| R2: z | z | 回避 |/' "$PLAN" > "$TMP/plan_dup"
sed 's/^## 8\. Risk & 回避策$/&\n<!--\n| R2: c | d | 受け入れ |\n-->/' "$TMP/plan_norow" > "$TMP/plan_cmt"
# review-gate 3 回目 F7・F8: 行の途中で開くコメント・閉じて開き直す行・閉じていないコメント・8 の節のコードの囲み
sed 's/^## 8\. Risk & 回避策$/&\nx <!--\n| R2: c | d | 受け入れ |\n-->/' "$TMP/plan_norow" > "$TMP/plan_mid"
sed 's/^## 8\. Risk & 回避策$/&\n<!-- a --> <!--\n| R2: c | d | 受け入れ |\n-->/' "$TMP/plan_norow" > "$TMP/plan_reopen"
# 閉じていないコメントは、共有の計画書の閉じたコメントより後ろ（8 の表の最後の行の後）で開く
sed 's/^| R6: g | h | 受け入れない |$/&\n<!--\n| R2: c | d | 受け入れ |/' "$TMP/plan_norow" > "$TMP/plan_open"
# review-gate 4 回目 F11・F12: 囲みは全文から先に取り除く。8 より前の節の囲みの中の 8 の例（``` と ~~~）・閉じていない囲み
sed 's/^## 8\. Risk & 回避策$/```\n## 8. Risk \& 回避策\n| R2: c | d | 受け入れ |\n```\n&/' "$TMP/plan_norow" > "$TMP/plan_fpre"
sed 's/^## 8\. Risk & 回避策$/~~~\n## 8. Risk \& 回避策\n| R2: c | d | 受け入れ |\n~~~\n&/' "$TMP/plan_norow" > "$TMP/plan_tpre"
sed 's/^## 8\. Risk & 回避策$/&\n```/' "$PLAN" > "$TMP/plan_func"
T5_WANT='- F1 SEV=Medium REPRO=no KIND=guard SECURITY=yes FILE=x | s1 | 後続イシューにする理由: SECURITY=yes・guard の Medium 以上'
# t5 <写し>: 17 通りの照合の失敗のうち、後続イシューに期待どおりの行が出た数
t5() { local n=0 c
  for c in "$TMP/t5|" "$TMP/t5|$TMP/nonexistent.md" "$TMP/t5|$TMP/plan_nosec" "$TMP/t5|$TMP/plan_norow" "$TMP/t5|$TMP/plan_avoid" \
           "$TMP/t5_R5|$PLAN" "$TMP/t5_R1|$PLAN" "$TMP/t5_R6|$PLAN" "$TMP/t5|$TMP/plan_dup" "$TMP/t5|$TMP/plan_cmt" \
           "$TMP/t5_R9|$PLAN" "$TMP/t5|$TMP/plan_mid" "$TMP/t5|$TMP/plan_reopen" "$TMP/t5|$TMP/plan_open" \
           "$TMP/t5|$TMP/plan_fpre" "$TMP/t5|$TMP/plan_tpre" "$TMP/t5|$TMP/plan_func"; do
    [ "$(route "$1" issue "${c%%|*}" "${c#*|}")" = "$T5_WANT" ] && n=$((n+1))
  done; echo "$n"; }
ck "TC-05 計画書なし・無いパス・節なし・行なし・処遇違い・節の外（R5）・回避（R1）・受け入れない（R6）・同じ番号の回避と受け入れ・コメントの中（4 形）・閉じていないコメント・前の節の囲みの中の 8 の例（2 形）・閉じていない囲みの 17 通りとも後続イシュー" 17 "$(t5 "$CR")"
ck "TC-05 作った計画書が意図どおり（dup に回避と受け入れの両方・cmt・mid・reopen・open・fpre・tpre・func に R2 の受け入れの行）" "yes yes yes yes yes yes yes yes yes" \
  "$(yn grep -qxF '| R2: z | z | 回避 |' "$TMP/plan_dup") $(yn grep -qxF '| R2: c | d | 受け入れ |' "$TMP/plan_dup") \
$(yn grep -qxF '| R2: c | d | 受け入れ |' "$TMP/plan_cmt") $(yn grep -qxF '| R2: c | d | 受け入れ |' "$TMP/plan_mid") \
$(yn grep -qxF '| R2: c | d | 受け入れ |' "$TMP/plan_reopen") $(yn grep -qxF '| R2: c | d | 受け入れ |' "$TMP/plan_open") \
$(yn grep -qxF '| R2: c | d | 受け入れ |' "$TMP/plan_fpre") $(yn grep -qxF '| R2: c | d | 受け入れ |' "$TMP/plan_tpre") $(yn grep -qxF '| R2: c | d | 受け入れ |' "$TMP/plan_func")"
ck "TC-05 囲みの計画書に本物の 8 の見出しが残っている（fpre・tpre は例と本物の 2 つ・func は 1 つ）" "2 2 1" \
  "$(grep -cxF '## 8. Risk & 回避策' "$TMP/plan_fpre") $(grep -cxF '## 8. Risk & 回避策' "$TMP/plan_tpre") $(grep -cxF '## 8. Risk & 回避策' "$TMP/plan_func")"
# 肯定: 8 より前の節の囲みの中に <!-- があっても、本物の 8 の R2 は効く（F12）
sed 's/^## 8\. Risk & 回避策$/```\nx <!-- y\n```\n&/' "$PLAN" > "$TMP/plan_fok"
fok() { yn grep -qE '^- F1 .*計画で受け入れ（R2）$' <(route "$1" backlog "$TMP/t5" "$TMP/plan_fok"); }
ck "TC-05 前の節の囲みの中の <!-- で本物の 8 が切られない（R2 が効く）" yes "$(fok "$CR")"
ck "FG-05a 目印があれば効くようにすると不合格" 0 "$(t5 "$(broken 'why_not = accepted_why_not(e, acc_set) if e[10] != "-" else "目印なし"' 'why_not = "" if e[10] != "-" else "目印なし"')")"
ck "FG-05b 節の終わりを見ないと不合格（R5 が効く）" 16 "$(t5 "$(broken 'inside = bool(PLAN_RISK_HEAD.match(line))' 'inside = inside or bool(PLAN_RISK_HEAD.match(line))')")"
ck "FG-05c 処遇を完全一致で見ないと不合格（R6 が効く）" 16 "$(t5 "$(broken '.strip() == "受け入れ"' '.strip().startswith("受け入れ")')")"
ck "FG-05e 受け入れでない同じ番号を引かないと不合格（dup が効く）" 16 "$(t5 "$(broken 'return acc - other' 'return acc')")"
PC_READ='PLAN_COMMENT.sub("", strip_fences(open(plan, encoding="utf-8", errors="replace").read())).split("<!--", 1)[0]'
ck "FG-05f コメントを取り除かないと不合格（cmt・R9・mid・reopen・open が効く）" 12 "$(t5 "$(broken "$PC_READ" 'strip_fences(open(plan, encoding="utf-8", errors="replace").read())')")"
ck "FG-05g 閉じていないコメントから後ろを切らないと不合格（open が効く）" 16 "$(t5 "$(broken "$PC_READ" 'PLAN_COMMENT.sub("", strip_fences(open(plan, encoding="utf-8", errors="replace").read()))')")"
B05H=$(broken "$PC_READ" 'PLAN_COMMENT.sub("", open(plan, encoding="utf-8", errors="replace").read()).split("<!--", 1)[0]')
ck "FG-05h 囲みを取り除かないと不合格（fpre・tpre・func が効き、fok が切られる）" "14 no" "$(t5 "$B05H") $(fok "$B05H")"
ck "FG-05i コメントが閉じない読み方だと不合格（TC-01 の R2・R4 が効かない）" no \
  "$(yn [ "$(t1 "$(broken 'PLAN_COMMENT = re.compile(r"<!--.*?-->", re.S)' 'PLAN_COMMENT = re.compile(r"<!--.*", re.S)')")" = "I: B:F1,F2,F3,F4" ])"
# 本物の入口 --route（一時のリポジトリ・台帳のある記録）
mkdir -p "$R/docs/reviews"
{ printf '# r\n\n## 台帳（累積・スクリプトが書く）\n'; cat "$TMP/t5"; printf 'LEDGER_ROUND: 1\n'; } > "$R/docs/reviews/I900_code_review_20260101_0000.md"
entry() { (cd "$R" && bash "$1" --route "$2" "$3" 2>"$TMP/entry_err"); }
ck "TC-05 入口: 計画書なしで後続イシュー・標準エラーに「計画書: なし」" "yes yes" \
  "$(yn [ "$(entry "$CR" issue I900)" = "$T5_WANT" ]) $(yn grep -qxF '計画書: なし' "$TMP/entry_err")"
mkdir -p "$R/docs/plans/open"; cp "$PLAN" "$R/docs/plans/open/plan_I900.md"
ck "TC-05 入口: open の計画書で受け入れた R2 は一覧・標準エラーに計画書のパス" "yes yes" \
  "$(yn grep -qE '^- F1 .*計画で受け入れ（R2）$' <(entry "$CR" backlog I900)) $(yn grep -qxF '計画書: docs/plans/open/plan_I900.md' "$TMP/entry_err")"
# 作り直しの計画書（plan_I900_2.md）があれば、レビュー役と同じくそちらを読む（find_plan_file）
cp "$TMP/plan_avoid" "$R/docs/plans/open/plan_I900.md"; cp "$PLAN" "$R/docs/plans/open/plan_I900_2.md"
ck "TC-05 入口: 連番の最新の計画書（plan_I900_2.md）で照合する" "yes yes" \
  "$(yn grep -qE '^- F1 .*計画で受け入れ（R2）$' <(entry "$CR" backlog I900)) $(yn grep -qxF '計画書: docs/plans/open/plan_I900_2.md' "$TMP/entry_err")"
ck "TC-05 入口: ../x・I9* は exit 2" "2 2" "$( (cd "$R" && rc bash "$CR" --route issue ../x) ) $( (cd "$R" && rc bash "$CR" --route issue 'I9*') )"
ck "FG-05d 第 3 引数の確かめを外すと不合格（I9* が通る）" 0 "$( (cd "$R" && rc bash "$(broken '[[ "$3" =~ ^I[0-9]+$ ]] ||' 'true ||')" --route issue 'I9*') )"

ck "FG の写しがすべて作れた（置き換え前の文字列が本体にある）" no "$([ -e "$TMP/broken_failed" ] && echo yes || echo no)"
printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
