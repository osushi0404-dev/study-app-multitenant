#!/usr/bin/env bash
# I197（plan_I197.md §4.8・auto_test TC-09）: 基本レビューの台帳・差分のレビュー・高リスクの判定・fix-loop の決定論テスト。
#   R: code-review.sh の関数（review_mode・delta_files・parse_findings・ledger_update・ledger_verdict・plan_risk・set_risk_line）と配線
#   FG: 判定の要を一時コピーで壊すと、対応する R が不合格になること
# 実行: bash scripts/claude/tests/test_i197_review_ledger.sh
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
CR="$REPO_ROOT/scripts/claude/code-review.sh"

# lib <code-review.sh の写し> <関数と引数…>: 関数だけを読み込んで 1 つ呼ぶ（cwd はそのまま）
lib() { local src="$1"; shift; REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1"; shift; "$@"' _ "$src" "$@"; }
# 壊した写し: <置き換え前> <置き換え後>（置き換え前が無ければ印を残して最後に不合格）
broken() { local f="$TMP/cr_$RANDOM.sh"
  python3 -I -c 'import sys
s = open(sys.argv[1], encoding="utf-8").read()
if sys.argv[3] not in s: sys.exit(1)
open(sys.argv[2], "w", encoding="utf-8").write(s.replace(sys.argv[3], sys.argv[4]))' "$CR" "$f" "$1" "$2" || : > "$TMP/broken_failed"
  echo "$f"; }

# ---------------- 一時のリポジトリ ----------------
R="$TMP/repo"; mkdir -p "$R/docs/reviews" "$R/scripts" "$R/backend"
git -C "$R" init -q -b develop
printf 'a\n' > "$R/scripts/a.sh"; printf 'b\n' > "$R/scripts/b.sh"; printf 'x\n' > "$R/backend/x.py"
git -C "$R" add -A; git -C "$R" commit -qm base
git -C "$R" checkout -q -b feature/I900-x
printf 'a2\n' >> "$R/scripts/a.sh"; printf 'b2\n' >> "$R/scripts/b.sh"; git -C "$R" add -A; git -C "$R" commit -qm "branch 1"
SINCE=$(git -C "$R" rev-parse HEAD)
printf 'a3\n' >> "$R/scripts/a.sh"; git -C "$R" add -A; git -C "$R" commit -qm "branch 2（a.sh だけ直す）"
# develop が進み（backend/x.py）、それをブランチに取り込む
git -C "$R" checkout -q develop; printf 'x2\n' >> "$R/backend/x.py"; git -C "$R" add -A; git -C "$R" commit -qm "develop"
git -C "$R" checkout -q feature/I900-x; git -C "$R" merge -q --no-edit develop
git -C "$R" checkout -q -b elsewhere develop~1; printf 'z\n' > "$R/z.txt"; git -C "$R" add -A; git -C "$R" commit -qm "別の枝"
NOT_ANC=$(git -C "$R" rev-parse HEAD); git -C "$R" checkout -q feature/I900-x
rec() {   # rec <名前> <中身>: 記録を置く
  printf '%s\n' "$2" > "$R/docs/reviews/I900_code_review_$1.md"; }
inR() { (cd "$R" && "$@"); }

# ---------------- R1 review_mode ----------------
ck "R1 記録が無い → full・1" "full|1||" "$(inR lib "$CR" review_mode I900 | tr '\t' '|')"
rec 20260101_0000 "# 古い形式
REVIEWED_COMMIT: ${SINCE}
VERDICT: HIGH"
ck "R1 LEDGER_ROUND の無い（古い形式・失敗した周）記録だけ → full" "full|1||" "$(inR lib "$CR" review_mode I900 | tr '\t' '|')"
rec 20260101_0001 "# 台帳あり
LEDGER_ROUND: 2
REVIEWED_COMMIT: ${SINCE}
VERDICT: HIGH"
ck "R1 LEDGER_ROUND: 2・祖先の REVIEWED_COMMIT → delta・3・起点" "delta|3|${SINCE}" "$(inR lib "$CR" review_mode I900 | cut -f1-3 | tr '\t' '|')"
rec 20260101_0002 "# 祖先でない
LEDGER_ROUND: 3
REVIEWED_COMMIT: ${NOT_ANC}
VERDICT: HIGH"
ck "R1 REVIEWED_COMMIT が HEAD の祖先でない → full" "full" "$(inR lib "$CR" review_mode I900 | cut -f1)"
rm -f "$R"/docs/reviews/I900_code_review_20260101_0002.md

# ---------------- R2 delta_files ----------------
ck "R2 起点の後にブランチが変えた a.sh だけ（develop の x.py・起点の後に変えていない b.sh は入らない）" "scripts/a.sh" "$(inR lib "$CR" delta_files develop "$SINCE" | paste -sd, -)"

# ---------------- R3 parse_findings ----------------
printf 'x\nFINDING: F1 SEV=High STATUS=open FILE=scripts/a.sh LINE=3 SECURITY=no STOP=flow | 要約 | 再現: r\n' > "$TMP/f_ok.md"
ck "R3 FINDING 行を読む（I205 の形）" "F1|High|open|scripts/a.sh|3|no|flow|要約 | 再現: r" "$(lib "$CR" parse_findings "$TMP/f_ok.md" | tr '\t' '|')"
printf 'FINDING: F1 SEV=Huge STATUS=open FILE=a LINE=1 SECURITY=no STOP=-\n' > "$TMP/f_bad1.md"
printf 'FINDING: F1 SEV=High STATUS=open LINE=1 SECURITY=no STOP=-\n' > "$TMP/f_bad2.md"
ck "R3 SEV の値が違う行 → 2" 2 "$(rc lib "$CR" parse_findings "$TMP/f_bad1.md")"
ck "R3 FILE の欄が無い行 → 2" 2 "$(rc lib "$CR" parse_findings "$TMP/f_bad2.md")"

# ---------------- R4〜R7 ledger_update・ledger_verdict ----------------
# verdict_of <kind> <前の記録|""> <今回の本文> <範囲>: 台帳を作って合否を出す。台帳は $TMP/last_ledger に残す
# 一時のリポジトリ（scripts/a.sh・scripts/b.sh がある）の中で動かす（範囲の外かどうかは、ファイルがあるかも見るため）
verdict_of() { local src="${5:-$CR}"
  (cd "$R" && lib "$src" ledger_update "$1" "$2" "$3" "$4") > "$TMP/last_ledger" || { echo "PARSE_ERROR"; return; }
  lib "$src" ledger_verdict "$TMP/last_ledger"; }
printf 'scripts/a.sh\t1\t999999999\n' > "$TMP/scope"
# I205: I197 の形の FINDING 行に LINE=1・STOP=-・再現を足す（scripts/a.sh などは app の種類。止める基準は Blocker・High・Medium）
body() { printf '%b\n' "$1" | sed -E '/^FINDING: /{/ LINE=/!s/ SECURITY=(yes|no)( \| (.*))?$/ LINE=1 SECURITY=\1 STOP=- | \3 | 再現: r/}' > "$TMP/$2"; }
body 'FINDING: F1 SEV=High STATUS=open FILE=scripts/a.sh SECURITY=no | h' full_h.md
body 'FINDING: F1 SEV=Blocker STATUS=open FILE=scripts/a.sh SECURITY=no | b' full_b.md
body 'FINDING: F1 SEV=Low STATUS=open FILE=scripts/a.sh SECURITY=no | m\nFINDING: F2 SEV=Low STATUS=open FILE=- SECURITY=yes | l' full_ml.md
ck "R4 全体: High → HIGH" HIGH "$(verdict_of full '' "$TMP/full_h.md" "$TMP/scope")"
ck "R4 全体: Blocker → BLOCKER" BLOCKER "$(verdict_of full '' "$TMP/full_b.md" "$TMP/scope")"
ck "R7 全体: Low だけ → OK（I205: アプリ本体の Medium は止まる・test_i205 の B2）" OK "$(verdict_of full '' "$TMP/full_ml.md" "$TMP/scope")"

# 1 周目（全体）: F1 High（a.sh）
verdict_of full '' "$TMP/full_h.md" "$TMP/scope" >/dev/null; { cat "$TMP/last_ledger"; echo "LEDGER_ROUND: 1"; } > "$TMP/round1.md"
body 'FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h' d_res.md
body 'FINDING: F2 SEV=Low STATUS=open FILE=scripts/a.sh SECURITY=no | 別件' d_missing.md
body 'FINDING: F1 SEV=High STATUS=open FILE=scripts/a.sh SECURITY=no | h' d_open.md
ck "R5 差分: 前の open の F1 が resolved → OK" OK "$(verdict_of delta "$TMP/round1.md" "$TMP/d_res.md" "$TMP/scope")"
ck "R5 差分: F1 の行が無い → HIGH" HIGH "$(verdict_of delta "$TMP/round1.md" "$TMP/d_missing.md" "$TMP/scope")"
cp "$TMP/last_ledger" "$TMP/round2.md"
ck "R5 差分: F1 が open のまま → HIGH" HIGH "$(verdict_of delta "$TMP/round1.md" "$TMP/d_open.md" "$TMP/scope")"
body 'FINDING: F3 SEV=Low STATUS=open FILE=scripts/a.sh SECURITY=no | 別件 2' d_missing2.md
ck "R5 累積: 2 周目に F1 の行が抜け、3 周目も無い → HIGH（消えない）" HIGH "$(verdict_of delta "$TMP/round2.md" "$TMP/d_missing2.md" "$TMP/scope")"
body 'FINDING: F1 SEV=Low STATUS=open FILE=scripts/a.sh SECURITY=no | 下げた' d_down.md
ck "R5 重大度は下げられない（High を Low と書き直しても HIGH）" HIGH "$(verdict_of delta "$TMP/round1.md" "$TMP/d_down.md" "$TMP/scope")"

body 'FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h\nFINDING: F2 SEV=High STATUS=open FILE=scripts/a.sh SECURITY=no | 中' d_new_in.md
body 'FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h\nFINDING: F2 SEV=High STATUS=open FILE=scripts/b.sh SECURITY=no | 外' d_new_out.md
body 'FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h\nFINDING: F2 SEV=Blocker STATUS=open FILE=scripts/b.sh SECURITY=yes | 外の秘密' d_new_out_sec.md
body 'FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h\nFINDING: F2 SEV=Blocker STATUS=open FILE=scripts/b.sh SECURITY=no | 外の Blocker' d_new_out_blk.md
body 'FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h\nFINDING: F2 SEV=High STATUS=open FILE=- SECURITY=no | ファイル不明' d_new_dash.md
ck "R6 新しい High・範囲の中 → HIGH" HIGH "$(verdict_of delta "$TMP/round1.md" "$TMP/d_new_in.md" "$TMP/scope")"
ck "R6 新しい High・範囲の外 → OK（止めない）" OK "$(verdict_of delta "$TMP/round1.md" "$TMP/d_new_out.md" "$TMP/scope")"
cp "$TMP/last_ledger" "$TMP/round2_out.md"
ck "R6 範囲の外・Blocker・SECURITY=yes → BLOCKER" BLOCKER "$(verdict_of delta "$TMP/round1.md" "$TMP/d_new_out_sec.md" "$TMP/scope")"
ck "R6 範囲の外・Blocker・SECURITY=no → OK" OK "$(verdict_of delta "$TMP/round1.md" "$TMP/d_new_out_blk.md" "$TMP/scope")"
ck "R6 FILE=- → 範囲の中とみなして HIGH" HIGH "$(verdict_of delta "$TMP/round1.md" "$TMP/d_new_dash.md" "$TMP/scope")"
body 'FINDING: F2 SEV=High STATUS=open FILE=scripts/b.sh SECURITY=no | 外' d_out_again.md
printf 'scripts/b.sh\t1\t999999999\n' > "$TMP/scope_b"
ck "R6 前の周で範囲の外だった High（止めない・入力に見せない）は、次の周も範囲の外なら止めない" OK "$(verdict_of delta "$TMP/round2_out.md" "$TMP/d_out_again.md" "$TMP/scope")"
# 台帳の 1 周目 F1 の修正: 入力に見せていない番号を書いた行は新しい指摘。その周に b.sh を直していれば（範囲の中）止める
ck "R6 同じ指摘でも、その周に b.sh を直していれば（範囲の中の新しい指摘として）止める" HIGH "$(verdict_of delta "$TMP/round2_out.md" "$TMP/d_out_again.md" "$TMP/scope_b")"
body 'FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h\nFINDING: F2 SEV=Low STATUS=open FILE=scripts/a.sh SECURITY=yes | m' d_med.md
ck "R7 差分: 範囲の中の Low（SECURITY=yes でも）→ OK" OK "$(verdict_of delta "$TMP/round1.md" "$TMP/d_med.md" "$TMP/scope")"
body 'FINDING: F1 SEV=High STATUS=resolved FILE=a SECURITY=no\nFINDING: F9 SEV=Bad STATUS=open FILE=a SECURITY=no' d_broken.md
ck "R3 形の崩れた FINDING 行があると台帳を作らない" PARSE_ERROR "$(verdict_of delta "$TMP/round1.md" "$TMP/d_broken.md" "$TMP/scope")"

# ---------------- R15・R16（台帳の 1 周目の F1・F2 の再発防止） ----------------
# R15: 入力に見せていない既存の番号（止めない F2・Medium）を新しい High に使っても、新しい指摘として振り直し、範囲の中なら止める
# 前の台帳: F1（High・範囲の中・open）と F2（Medium・範囲の外）。F2 は止めない指摘なので入力に見せない
printf 'LEDGER: F1 SEV=High STATUS=open SCOPE=delta SECURITY=no | h\nLEDGER: F2 SEV=Medium STATUS=open SCOPE=outside SECURITY=no | m\n' > "$TMP/r15_round1.md"
body 'FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h\nFINDING: F2 SEV=High STATUS=open FILE=scripts/a.sh SECURITY=no | 新しい穴' r15_delta.md
ck "R15 止めない既存の番号の再利用は新しい指摘（F3）として振り直し、範囲の中の High で止める" "HIGH yes yes" \
  "$(verdict_of delta "$TMP/r15_round1.md" "$TMP/r15_delta.md" "$TMP/scope") $(grep -q '^LEDGER: F3 SEV=High STATUS=open SCOPE=delta' "$TMP/last_ledger" && echo yes || echo no) $(grep -q '^LEDGER: F2 SEV=Medium' "$TMP/last_ledger" && echo yes || echo no)"
# R16: FILE は :行番号 を除いてリポジトリのルートからの相対パスにそろえて範囲と比べる（./・絶対パス・.. も同じファイル）。
# リポジトリの外・実在しないファイルは delta（止める側）
body 'FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h\nFINDING: F2 SEV=High STATUS=open FILE=./scripts/a.sh:12 SECURITY=no | ずれ' r16a.md
body 'FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h\nFINDING: F2 SEV=High STATUS=open FILE=scripts/no_such.sh SECURITY=no | 無い' r16b.md
ck "R16 ./・:行番号 のずれは範囲の中として止める" HIGH "$(verdict_of delta "$TMP/round1.md" "$TMP/r16a.md" "$TMP/scope")"
ck "R16 リポジトリに無いパスは範囲の中として止める" HIGH "$(verdict_of delta "$TMP/round1.md" "$TMP/r16b.md" "$TMP/scope")"
# 台帳の 2 周目 F2: 絶対パス・.. を含むパスも、リポジトリからの相対パスに揃えて範囲の中なら止める。リポジトリの外の絶対パスは止める側
body "FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h\nFINDING: F2 SEV=High STATUS=open FILE=$R/scripts/a.sh SECURITY=no | 絶対" r16c.md
body 'FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h\nFINDING: F2 SEV=High STATUS=open FILE=scripts/../scripts/a.sh SECURITY=no | ..' r16d.md
body "FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h\nFINDING: F2 SEV=High STATUS=open FILE=$REPO_ROOT/CLAUDE.md SECURITY=no | 外の実在" r16e.md
body "FINDING: F1 SEV=High STATUS=resolved FILE=scripts/a.sh SECURITY=no | h\nFINDING: F2 SEV=High STATUS=open FILE=$R/scripts/b.sh:3 SECURITY=no | 範囲の外の実在" r16f.md
ck "R16 絶対パスで範囲の中 → 止める" HIGH "$(verdict_of delta "$TMP/round1.md" "$TMP/r16c.md" "$TMP/scope")"
ck "R16 .. を含むパスで範囲の中 → 止める" HIGH "$(verdict_of delta "$TMP/round1.md" "$TMP/r16d.md" "$TMP/scope")"
ck "R16 リポジトリの外の実在のファイル → 止める側" HIGH "$(verdict_of delta "$TMP/round1.md" "$TMP/r16e.md" "$TMP/scope")"
ck "R16 絶対パス＋:行番号 で範囲の外の実在のファイル（b.sh）→ 止めない" OK "$(verdict_of delta "$TMP/round1.md" "$TMP/r16f.md" "$TMP/scope")"

# ---------------- R8 plan_risk ----------------
P="$TMP/prisk"; mkdir -p "$P/docs/reviews"
ck "R8 計画レビューの記録が無い → YES" YES "$(cd "$P" && lib "$CR" plan_risk I900)"
printf '# x\n\n## 高リスク判定\n判定: No\n該当条件: なし\n' > "$P/docs/reviews/I900_plan_review_20260101_0000.md"
ck "R8 判定: No → NO" NO "$(cd "$P" && lib "$CR" plan_risk I900)"
printf '# x\n\n## 高リスク判定\n判定: Yes\n' > "$P/docs/reviews/I900_plan_review_20260101_0001.md"
ck "R8 最新が 判定: Yes → YES" YES "$(cd "$P" && lib "$CR" plan_risk I900)"
printf '# x\n\n## 高リスク判定\nなにか\n\n## 次\n判定: No\n' > "$P/docs/reviews/I900_plan_review_20260101_0002.md"
ck "R8 節に判定の行が無い → YES" YES "$(cd "$P" && lib "$CR" plan_risk I900)"

# set_risk_line: RISK 行を 1 行にして最後の VERDICT の直前に置く（code-reviewer の RISK 行を上書き）
printf '本文\nRISK: YES\nVERDICT: OK\n' > "$TMP/risk.md"; lib "$CR" set_risk_line "$TMP/risk.md" NO
ck "R8 set_risk_line で RISK: NO が VERDICT の直前に 1 行" "本文|RISK: NO|VERDICT: OK" "$(paste -sd'|' "$TMP/risk.md")"

# ---------------- R12 失敗した周は台帳の周に数えない ----------------
# 台帳と LEDGER_ROUND は、ledger_update が成功した（＝レビュー役が正常に終わり FINDING 行を読めた）分岐の中でだけ足す
r12() { python3 -I - "$1" <<'PY'
import sys
lines = open(sys.argv[1], encoding="utf-8").read().split("\n")
i = next(k for k, l in enumerate(lines) if 'ledger_update "$REVIEW_KIND"' in l and l.lstrip().startswith("if [ \"$REVIEW_OK\" = \"1\" ]"))
j = next(k for k in range(i, len(lines)) if lines[k].strip() == "else")
block = "\n".join(lines[i:j])
sys.exit(0 if "printf 'LEDGER_ROUND: %s\\n' \"$LEDGER_N\"" in block and ">> \"$REVIEW_FILE\"" in block else 1)
PY
}
ck "R12 台帳と LEDGER_ROUND は正常に終わった周の分岐の中でだけ書く" 0 "$(rc r12 "$CR")"
# 止める指摘の一覧（差分のレビューの入力）は合否と同じ規則で選ぶ
printf 'LEDGER: F1 SEV=High STATUS=open SCOPE=delta SECURITY=no | a\nLEDGER: F2 SEV=High STATUS=open SCOPE=outside SECURITY=no | b\nLEDGER: F3 SEV=Blocker STATUS=open SCOPE=outside SECURITY=yes | c\nLEDGER: F4 SEV=Low STATUS=open SCOPE=delta SECURITY=no | d\nLEDGER: F5 SEV=High STATUS=resolved SCOPE=delta SECURITY=no | e\n' > "$TMP/blk.md"
ck "R13 ledger_blocking は止める指摘（F1・F3）だけを出す" "F1,F3" "$(lib "$CR" ledger_blocking "$TMP/blk.md" | awk '{print $2}' | paste -sd, -)"

# ---------------- R9 配線（静的） ----------------
r9() { grep -qF 'RISK_FINAL=$(combine_risk "$RISK_PLAN" "$RISK_PATH")' "$1" && grep -qF 'RISK_PLAN=$(plan_risk "$ISSUE")' "$1" \
       && ! grep -qF 'RISK_FINAL=$(combine_risk "$RISK_LLM"' "$1" && grep -qF 'run_official_review "/code-review medium ${REVIEW_RANGE}"' "$1" \
       && grep -qF 'LEDGER_VERDICT=$(ledger_verdict "$LEDGER_FILE")' "$1" && grep -qF '"$LEDGER_VERDICT" "$REVIEWER_VERDICT"' "$1" \
       && grep -qF 'review_mode "$ISSUE"' "$1"; }
ck "R9 本体が review_mode・plan_risk・ledger_verdict を使い、RISK_LLM を判定に使わない" 0 "$(rc r9 "$CR")"

# ---------------- R10・R11 fix-loop・定義・スキル（静的） ----------------
FL=.claude/skills/fix-loop/SKILL.md
r10() { local f; for f in scripts/claude/fix-implementation-review.sh scripts/claude/fix-test-review.sh \
          .claude/agents/fix-implementation-reviewer.md .claude/agents/fix-test-reviewer.md; do [ ! -e "$f" ] || return 1; done
        ! grep -qE 'fix-implementation-review|fix-test-review' "$1" && grep -qF 'bash scripts/claude/fix-diagnosis-review.sh' "$1"; }
ck "R10 実装・テストのレビューのスクリプト・定義が無く、fix-loop は診断だけを呼ぶ" 0 "$(rc r10 "$FL")"
r11() { grep -qF 'FINDING: F<n> SEV=' "$1" && grep -qF 'FILE=' "$1" && grep -qF 'SECURITY=' "$1" \
        && grep -qF '差分のレビュー' "$2" && grep -qF '台帳' "$2" && grep -qF '止める指摘（スクリプトが決めた' "$2"; }
ck "R11 code-reviewer に FINDING 行の形・review-gate に差分のレビューと台帳と止める指摘の節" 0 "$(rc r11 .claude/agents/code-reviewer.md .claude/skills/review-gate/SKILL.md)"

# ---------------- FG ----------------
ck "FG-R1 「台帳があれば delta」を消すと R1 が不合格（delta にならない）" full \
  "$(inR lib "$(broken 'printf '"'"'delta\t%s\t%s\t%s\n'"'"' "$(( n + 1 ))" "$sha" "$last"; return 0' ':')" review_mode I900 | cut -f1)"
B3=$(broken 'sys.exit(2)
        out.append' 'pass
        out.append')
ck "FG-R3 形の検査を消すと R3 が不合格（2 にならない）" 0 "$(rc lib "$B3" parse_findings "$TMP/f_ok.md")$(lib "$B3" parse_findings "$TMP/f_bad1.md" >/dev/null 2>&1; echo)"
B5=$(broken 'led = read_ledger(prev) if review_kind == "delta" else {}' 'led = {}')
ck "FG-R5 前の台帳を読まないと R5 が不合格（行が無くても OK）" OK "$(verdict_of delta "$TMP/round1.md" "$TMP/d_missing.md" "$TMP/scope" "$B5")"
B6=$(broken '    if scope != "delta":' '    if False:')
ck "FG-R6 「範囲の外は SECURITY=yes の Blocker だけ」をゆるめると R6 が不合格（外の High で止まる）" HIGH "$(verdict_of delta "$TMP/round1.md" "$TMP/d_new_out.md" "$TMP/scope" "$B6")"
B8=$(broken '[ -n "$f" ] || { echo YES; return; }' '[ -n "$f" ] || { echo NO; return; }')
ck "FG-R8 既定を NO にすると R8 が不合格" NO "$(cd "$TMP" && lib "$B8" plan_risk I999)"
B2=$(broken 'own=$(branch_own_files "$1") || return 2' 'own=$(git -c core.quotePath=false diff --name-only --no-renames "$2" HEAD)')
ck "FG-R2 「ブランチが変えたファイルに限る」を消すと R2 が不合格（develop の x.py が入る）" yes "$(inR lib "$B2" delta_files develop "$SINCE" | grep -qx backend/x.py && echo yes || echo no)"
B9=$(broken 'RISK_FINAL=$(combine_risk "$RISK_PLAN" "$RISK_PATH")' 'RISK_FINAL=$(combine_risk "$RISK_LLM" "$RISK_PATH")')
ck "FG-R9 RISK_LLM に戻すと R9 が不合格" 1 "$(rc r9 "$B9")"
{ cat "$FL"; printf '\nbash scripts/claude/fix-test-review.sh I###\n'; } > "$TMP/fl10.md"
ck "FG-R10 fix-loop に fix-test-review を足すと R10 が不合格" 1 "$(rc r10 "$TMP/fl10.md")"
# ---------------- R14 本体を丸ごと動かす（全体のレビュー → 直す → 差分のレビュー）。gh・claude はスタブ ----------------
# 関数だけのテストでは、本体の配線の誤り（I197: set -e の下で条件が偽の $( [ … ] && … ) が代入ごと止めた）を捕まえられないため
E="$TMP/e2e"; EO="$TMP/e2e_origin.git"; ES="$TMP/e2e_stub"; mkdir -p "$E/scripts/claude" "$E/docs/issues/open" "$E/docs/reviews" "$ES/calls"
cp "$CR" "$REPO_ROOT/scripts/claude/review-process-lib.sh" "$E/scripts/claude/"
printf '# I900\n' > "$E/docs/issues/open/I900.md"; printf 'a\n' > "$E/a.sh"
printf '# 計画レビュー\n\n## 高リスク判定\n判定: No\n' > "$E/docs/reviews/I900_plan_review_20260101_0000.md"
printf 'jobs:\n  j:\n    name: J\n' > "$ES/wf.yml"
git init -q --bare "$EO"; git -C "$E" init -q -b develop; git -C "$E" add -A; git -C "$E" commit -qm base
git -C "$E" remote add origin "$EO"; git -C "$E" push -q origin develop 2>/dev/null
git -C "$E" checkout -q -b feature/I900-x; printf 'a2\n' >> "$E/a.sh"; git -C "$E" add -A; git -C "$E" commit -qm change
cat > "$ES/gh" <<'SH'
#!/usr/bin/env bash
case "$*" in
  "pr list"*) echo 7 ;;
  *headRefOid*) git rev-parse HEAD ;;
  "pr checks"*"--json"*) printf 'pass\tJ\n' ;;
  *) exit 0 ;;
esac
SH
cat > "$ES/claude" <<'PY'
#!/usr/bin/env python3
# code-reviewer（--agent）には $STUB/review_<n>.txt を stream-json で返す。組み込みのレビュー（plan モード）には「指摘なし」
import json, os, sys
st = os.environ["E2E_STUB"]; args = sys.argv[1:]
n = len([f for f in os.listdir(st + "/calls") if f.endswith(".args")])
open(f"{st}/calls/{n}.args", "w").write("\n".join(args))
if "--agent" in args:
    open(f"{st}/calls/{n}.in", "w").write(sys.stdin.read())
    k = len([f for f in os.listdir(st + "/calls") if f.endswith(".in")])
    body = open(f"{st}/review_{k}.txt").read()
    print(json.dumps({"type": "system", "subtype": "init", "session_id": "s"}))
    print(json.dumps({"type": "result", "subtype": "success", "result": body, "permission_denials": []}))
else:
    print("指摘なし")
PY
chmod +x "$ES/gh" "$ES/claude"
printf '# コードレビュー [I900]\n\n## 台帳\nFINDING: F1 SEV=High STATUS=open FILE=a.sh LINE=2 SECURITY=no STOP=- | a.sh の穴 | 再現: r\nFINDING: F2 SEV=Low STATUS=open FILE=a.sh LINE=2 SECURITY=no STOP=- | 軽い\n\nRISK: YES\nVERDICT: HIGH\n' > "$ES/review_1.txt"
printf '# コードレビュー [I900]\n\n## 台帳\nFINDING: F1 SEV=High STATUS=resolved FILE=a.sh LINE=2 SECURITY=no STOP=- | a.sh の穴\n\nVERDICT: HIGH\n' > "$ES/review_2.txt"
e2e() { (cd "$E" && PATH="$ES:$PATH" CLAUDE_BIN="$ES/claude" E2E_STUB="$ES" CI_WORKFLOWS="$ES/wf.yml" CI_WAIT_TIMEOUT=5 CI_POLL_INTERVAL=1 \
          bash scripts/claude/code-review.sh I900 > "$1" 2>&1; echo $? >> "$1.rc"); }
e2e "$TMP/e2e1.out"
E1_REC=$(find "$E/docs/reviews" -name 'I900_code_review_*.md' | LC_ALL=C sort | tail -1)
ck "R14 全体のレビュー: 最後まで動き FINAL_VERDICT: HIGH（台帳の F1 High）" "HIGH" "$(sed -n 's/^FINAL_VERDICT: //p' "$TMP/e2e1.out")"
ck "R14 全体: 記録に LEDGER_ROUND: 1・LEDGER: F1・RISK: NO（計画レビュー No・パス NO）" "yes yes yes" \
  "$(grep -qx 'LEDGER_ROUND: 1' "$E1_REC" && echo yes || echo no) $(grep -q '^LEDGER: F1 SEV=High STATUS=open SCOPE=delta' "$E1_REC" && echo yes || echo no) $(grep -qx 'RISK: NO' "$E1_REC" && echo yes || echo no)"
ck "R14 全体: 組み込みの /code-review には origin/develop...HEAD" yes "$(grep -lx '/code-review medium origin/develop...HEAD' "$ES"/calls/*.args >/dev/null 2>&1 && echo yes || echo no)"
git -C "$E" checkout -q feature/I900-x; printf 'a3\n' >> "$E/a.sh"; git -C "$E" add -A; git -C "$E" commit -qm fix
E1_SHA=$(sed -n 's/^REVIEWED_COMMIT: //p' "$E1_REC" | tail -1)
e2e "$TMP/e2e2.out"
E2_REC=$(find "$E/docs/reviews" -name 'I900_code_review_*.md' | LC_ALL=C sort | tail -1)
ck "R14 差分のレビュー: F1 が resolved なら OK（code-reviewer の VERDICT: HIGH は差分では使わない）" OK "$(sed -n 's/^FINAL_VERDICT: //p' "$TMP/e2e2.out")"
ck "R14 差分: 記録に LEDGER_ROUND: 2・F1 は resolved・Low の F2 は台帳に残る" "yes yes yes" \
  "$(grep -qx 'LEDGER_ROUND: 2' "$E2_REC" && echo yes || echo no) $(grep -q '^LEDGER: F1 SEV=High STATUS=resolved' "$E2_REC" && echo yes || echo no) $(grep -q '^LEDGER: F2 SEV=Low STATUS=open' "$E2_REC" && echo yes || echo no)"
E2_IN=$(find "$ES/calls" -name '*.in' | LC_ALL=C sort -V | tail -1)
ck "R14 差分: 入力に差分のレビューの指示・止める指摘 F1・範囲の a.sh" "yes yes yes" \
  "$(grep -qF '差分のレビュー（台帳の 2 周目）' "$E2_IN" && echo yes || echo no) $(grep -q '^LEDGER: F1 SEV=High STATUS=open' "$E2_IN" && echo yes || echo no) $(grep -qx 'a.sh' "$E2_IN" && echo yes || echo no)"
ck "R14 差分: 組み込みの /code-review には <起点>...HEAD" yes "$(grep -lx "/code-review medium ${E1_SHA}...HEAD" "$ES"/calls/*.args >/dev/null 2>&1 && echo yes || echo no)"

# R14 3 周目（台帳の 1 周目の F4 の再発防止）: 差分のレビューで、VERDICT: HIGH なのに読める FINDING 行が無い → BLOCKER
printf '# コードレビュー [I900]\n\n| High | 表の中にだけ書いた指摘 |\n\nVERDICT: HIGH\n' > "$ES/review_3.txt"
printf 'a4\n' >> "$E/a.sh"; git -C "$E" add -A; git -C "$E" commit -qm fix2
e2e "$TMP/e2e3.out"
ck "R14 差分: VERDICT: HIGH なのに FINDING 行が無い → BLOCKER" BLOCKER "$(sed -n 's/^FINAL_VERDICT: //p' "$TMP/e2e3.out")"

# FG-R15・FG-R16（I202 F19: .. の検査と isfile の検査を別々に壊す）
B15=$(broken '        elif fid in led and not keep:' '        elif False:')
ck "FG-R15 振り直しを消すと R15 が不合格（F2 に合流して止まらない）" OK "$(verdict_of delta "$TMP/r15_round1.md" "$TMP/r15_delta.md" "$TMP/scope" "$B15")"
B16=$(broken 'if norm == ".." or norm.startswith("../") or not os.path.isfile(norm):' 'if not os.path.isfile(norm):')
ck "FG-R16a リポジトリの外の検査を外すと R16 が不合格（外の実在のファイルが止まらない）" OK "$(verdict_of delta "$TMP/round1.md" "$TMP/r16e.md" "$TMP/scope" "$B16")"
B16b=$(broken 'if norm == ".." or norm.startswith("../") or not os.path.isfile(norm):' 'if norm == ".." or norm.startswith("../"):')
ck "FG-R16b 実在の検査を外すと R16 が不合格（存在しないパスが止まらない）" OK "$(verdict_of delta "$TMP/round1.md" "$TMP/r16b.md" "$TMP/scope" "$B16b")"

# FG-R14c（I202 F15: R17 の文字列の検査の代わり）: 3 周目の食い違いの検査を外した写しでは、同じ 3 周目が BLOCKER にならない
cp "$(broken 'if [ "$REVIEWER_RAN" = "1" ] && [ "$LLM_VERDICT" != "OK" ] && ! grep -qE' 'if false && ! grep -qE')" "$E/scripts/claude/code-review.sh"
cp "$ES/review_3.txt" "$ES/review_4.txt"
printf 'a5\n' >> "$E/a.sh"; git -C "$E" add -A; git -C "$E" commit -qm fg3
e2e "$TMP/e2e3fg.out"
ck "FG-R14c 食い違いの検査を外すと R14 の 3 周目が不合格（BLOCKER にならない）" yes \
  "$(grep -q '^FINAL_VERDICT:' "$TMP/e2e3fg.out" && [ "$(sed -n 's/^FINAL_VERDICT: //p' "$TMP/e2e3fg.out")" != BLOCKER ] && echo yes || echo no)"

# FG-R14: 条件が偽の $( [ … ] && … ) を本体の代入に戻すと、R14 が不合格（FINAL_VERDICT の行が出ない）
B14=$(broken 'FILES_NOTE=""; [ "$REVIEW_KIND" = "delta" ] && FILES_NOTE="（差分のレビューの範囲と、取り消したファイル）"' 'FILES_NOTE="$([ "$REVIEW_KIND" = "delta" ] && echo x)"')
cp "$B14" "$E/scripts/claude/code-review.sh"; rm -f "$E"/docs/reviews/I900_code_review_*.md
git -C "$E" add -A; git -C "$E" commit -qm reset
e2e "$TMP/e2e_fg.out"
ck "FG-R14 本体の set -e の誤りを戻すと R14 が不合格（FINAL_VERDICT が出ない）" no "$(grep -q '^FINAL_VERDICT:' "$TMP/e2e_fg.out" && echo yes || echo no)"
ck "FG の写しがすべて作れた（置き換え前の文字列が本体にある）" no "$([ -e "$TMP/broken_failed" ] && echo yes || echo no)"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
