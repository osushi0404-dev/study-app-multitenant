#!/usr/bin/env bash
# I202（plan_I202.md §4・auto_test TC-01）: I197・I205 の台帳に残った指摘と、見送った共通化を片付ける。
#   R: 計画の見立てを超えた高リスクの目印（RISK=up・F5） L: 台帳の判定の穴 W: code-review.sh の本体の細部（gh・claude はスタブ）
#   A: adversarial-review.sh の細部（claude はスタブ） G: 共通化（gate-check の挙動を変えない） D: 指示ファイル
#   FG: 判定の要を一時コピーで壊すと、対応する項目が不合格になること
# 実行: bash scripts/claude/tests/test_i202_ledger_cleanup.sh
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
ADV="$REPO_ROOT/scripts/claude/adversarial-review.sh"
GC="$REPO_ROOT/scripts/claude/gate-check.sh"

# lib <code-review.sh の写し> <関数と引数…>: 関数だけを読み込んで 1 つ呼ぶ（cwd はそのまま）
lib() { local src="$1"; shift; REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1"; shift; "$@"' _ "$src" "$@"; }
# 壊した写し: [<元のファイル>] <置き換え前> <置き換え後>（置き換え前が無ければ印を残して最後に不合格）
broken_of() { local src="$1" f="$TMP/b_$RANDOM$RANDOM.sh"
  python3 -I -c 'import sys
s = open(sys.argv[1], encoding="utf-8").read()
if sys.argv[3] not in s: sys.exit(1)
open(sys.argv[2], "w", encoding="utf-8").write(s.replace(sys.argv[3], sys.argv[4]))' "$src" "$f" "$2" "$3" || : > "$TMP/broken_failed"
  echo "$f"; }
broken() { broken_of "$CR" "$1" "$2"; }

# ---------------- 一時のリポジトリ（台帳の関数用） ----------------
R="$TMP/repo"; mkdir -p "$R/backend" "$R/scripts/claude" "$R/.github/workflows" "$R/docs2"
git -C "$R" init -q -b develop
seq 1 20 | sed 's/^/x/' > "$R/backend/x.py"
seq 1 20 | sed 's/^/a/' > "$R/scripts/claude/a.sh"
seq 1 20 | sed 's/^/c/' > "$R/.github/workflows/ci.yml"
printf 'o\n' > "$R/.github/CODEOWNERS"
printf 'f\n' > "$R/..foo.sh"
git -C "$R" add -A; git -C "$R" commit -qm base
printf 'backend/x.py\t10\t10\nscripts/claude/a.sh\t10\t10\n.github/workflows/ci.yml\t10\t10\n' > "$TMP/hunks"
printf 'backend/x.py\nscripts/claude/a.sh\n.github/workflows/ci.yml\n' > "$TMP/bfiles"
# ledger <写し> <full|delta> <前の台帳|""> <FINDING 行…>: 台帳を $TMP/led に作る（形の崩れは PARSE_ERROR）
ledger() { local src="$1" kind="$2" prev="$3"; shift 3; printf '%s\n' "$@" > "$TMP/cur.md"
  (cd "$R" && lib "$src" ledger_update "$kind" "$prev" "$TMP/cur.md" "$TMP/hunks" "$TMP/bfiles") > "$TMP/led" 2>/dev/null || { : > "$TMP/led"; echo PARSE_ERROR; }; }
led_has() { grep -qE -- "$1" "$TMP/led" && echo yes || echo no; }
verdict() { lib "$CR" ledger_verdict "$TMP/led"; }

# ---------------- R 計画の見立てを超えた高リスクの目印（F5・AC1） ----------------
ledger "$CR" full "" 'FINDING: F1 SEV=Low STATUS=open FILE=backend/x.py LINE=10 SECURITY=no STOP=- RISK=up | 目印 | 再現: r' \
  'FINDING: F2 SEV=Low STATUS=open FILE=backend/x.py LINE=10 SECURITY=no STOP=- | 目印なし'
ck "R1 RISK=up の行を読み、台帳に RISK=up・目印の無い行は RISK=-" "yes yes" \
  "$(led_has '^LEDGER: F1 .* REPRO=yes RISK=up SECURITY=no \| 目印$') $(led_has '^LEDGER: F2 .* RISK=- SECURITY=no')"
cp "$TMP/led" "$TMP/led_up"
ck "R2 RISK=down は形の崩れ" PARSE_ERROR "$(ledger "$CR" full "" 'FINDING: F1 SEV=Low STATUS=open FILE=a LINE=1 SECURITY=no STOP=- RISK=down | x')"
ck "R2 RISK= は形の崩れ" PARSE_ERROR "$(ledger "$CR" full "" 'FINDING: F1 SEV=Low STATUS=open FILE=a LINE=1 SECURITY=no STOP=- RISK= | x')"
printf 'LEDGER: F1 SEV=Low STATUS=open SCOPE=delta KIND=app STOP=- REPRO=yes RISK=- SECURITY=no | x\n' > "$TMP/led_none"
printf 'LEDGER: F1 SEV=Low STATUS=open SCOPE=delta KIND=app STOP=- REPRO=yes SECURITY=no | i205\nLEDGER: F2 SEV=Medium STATUS=open SCOPE=delta SECURITY=no | i197\n' > "$TMP/led_old"
ck "R3 ledger_risk: RISK=up があれば YES・無い／前の形だけなら NO・複数のファイルのどれかにあれば YES" "YES NO NO YES" \
  "$(lib "$CR" ledger_risk "$TMP/led_up") $(lib "$CR" ledger_risk "$TMP/led_none") $(lib "$CR" ledger_risk "$TMP/led_old") $(lib "$CR" ledger_risk "$TMP/led_none" "$TMP/led_up")"
ck "R3 前の形（I205・I197）の台帳の行も読める（止める指摘の判定は今のまま）" "HIGH" "$(lib "$CR" ledger_verdict "$TMP/led_old")"
# R4: 前の周の RISK=up の止める指摘を、同じ番号で RISK なしに書き直しても up が残る
printf 'LEDGER: F1 SEV=High STATUS=open SCOPE=delta KIND=app STOP=- REPRO=yes RISK=up SECURITY=no | h\n' > "$TMP/r4_prev"
ledger "$CR" delta "$TMP/r4_prev" 'FINDING: F1 SEV=High STATUS=open FILE=backend/x.py LINE=10 SECURITY=no STOP=- | h | 再現: r' >/dev/null
ck "R4 書き直しで RISK=up が残る" yes "$(led_has '^LEDGER: F1 .* RISK=up ')"
B4=$(broken '"up" if "up" in (risk, o[8]) else "-"' 'risk')
ledger "$B4" delta "$TMP/r4_prev" 'FINDING: F1 SEV=High STATUS=open FILE=backend/x.py LINE=10 SECURITY=no STOP=- | h | 再現: r' >/dev/null
ck "FG-R4 up を残す処理を外すと R4 が不合格" no "$(led_has '^LEDGER: F1 .* RISK=up ')"
# R5: 目印は止めるかどうかを変えない
ledger "$CR" full "" 'FINDING: F1 SEV=Low STATUS=open FILE=scripts/claude/a.sh LINE=10 SECURITY=no STOP=- RISK=up | x | 再現: r' >/dev/null
ck "R5 harness・Low・STOP=-・RISK=up・再現あり → OK（止めない）" OK "$(verdict)"
B3=$(broken 'print("YES" if any(e[8] == "up"' 'print("NO" if any(e[8] == "up"')
ck "FG-R3 risk モードを壊すと R3 が不合格" NO "$(lib "$B3" ledger_risk "$TMP/led_up")"

# ---------------- L 台帳の判定の穴（AC2） ----------------
# L1 I205-F3: guard のファイルは、ブランチが変えたファイルなら行に関係なく差分の中
ledger "$CR" full "" 'FINDING: F1 SEV=High STATUS=open FILE=.github/workflows/ci.yml LINE=1 SECURITY=no STOP=- | g' >/dev/null
ck "L1 guard の変えたファイルの触っていない行の High（再現なし）→ delta・HIGH" "yes HIGH" "$(led_has 'SCOPE=delta KIND=guard') $(verdict)"
ledger "$CR" full "" 'FINDING: F1 SEV=High STATUS=open FILE=.github/CODEOWNERS LINE=1 SECURITY=no STOP=- | g' >/dev/null
ck "L1 ブランチが変えていない guard のファイルの High → outside・OK" "yes OK" "$(led_has 'SCOPE=outside KIND=guard') $(verdict)"
BL1=$(broken '        if kind_of(norm) == "guard" and norm.casefold() in hunks:' '        if False:')
ledger "$BL1" full "" 'FINDING: F1 SEV=High STATUS=open FILE=.github/workflows/ci.yml LINE=1 SECURITY=no STOP=- | g' >/dev/null
ck "FG-L1 guard のファイル単位の判定を外すと L1 が不合格" OK "$(verdict)"
# L2 I205-F4: 種類の判定は大文字・小文字を区別しない
printf '.GITHUB/workflows/ci.yml\nScripts/Claude/a.sh\nBackend/x.py\n' > "$TMP/kpaths"
ck "L2 .GITHUB/… は guard・Scripts/Claude/… は harness・Backend/… は app" "guard harness app" "$(lib "$CR" ledger_kinds "$TMP/kpaths" | cut -f1 | paste -sd' ' -)"
ck "FG-L2 casefold を外すと L2 が不合格" "app app app" \
  "$(lib "$(broken '    p = path.casefold()' '    p = path')" ledger_kinds "$TMP/kpaths" | cut -f1 | paste -sd' ' -)"
# L3 I205-F5: 最後の「| 再現:」で分ける・「なし」などは再現なし
ledger "$CR" full "" 'FINDING: F1 SEV=Low STATUS=open FILE=backend/x.py LINE=10 SECURITY=no STOP=- | 要約 A | 再現: x の中身 | 再現: 本当の再現' >/dev/null
ck "L3 要約の中の「| 再現:」で切れない・REPRO=yes" yes "$(led_has '^LEDGER: F1 .*REPRO=yes .*\| 要約 A \| 再現: x の中身$')"
l3() { ledger "$CR" full "" "FINDING: F1 SEV=Low STATUS=open FILE=backend/x.py LINE=10 SECURITY=no STOP=- | s | 再現:$1" >/dev/null; grep -oE 'REPRO=(yes|no)' "$TMP/led" | cut -d= -f2; }
ck "L3 「なし」「-」「None」「 N/A 」「（空）」は再現なし・「なしでも落ちる」は再現あり" "no no no no no yes" \
  "$(l3 ' なし') $(l3 ' -') $(l3 ' None') $(l3 '  N/A ') $(l3 '') $(l3 ' なしでも落ちる')"
BL3=$(broken '    m = ms[-1]' '    m = ms[0]')
ledger "$BL3" full "" 'FINDING: F1 SEV=Low STATUS=open FILE=backend/x.py LINE=10 SECURITY=no STOP=- | 要約 A | 再現: x の中身 | 再現: 本当の再現' >/dev/null
ck "FG-L3a 最初の「| 再現:」で分けると L3 が不合格（要約が切れる）" no "$(led_has '\| 要約 A \| 再現: x の中身$')"
BL3b=$(broken 'if (not body or body.casefold() in NO_REPRO)' 'if (not body)')
ledger "$BL3b" full "" 'FINDING: F1 SEV=Low STATUS=open FILE=backend/x.py LINE=10 SECURITY=no STOP=- | s | 再現: なし' >/dev/null
ck "FG-L3b 「なし」の判定を外すと L3 が不合格（REPRO=yes）" yes "$(led_has 'REPRO=yes')"
# L4 I197-F12: 1 回のレビューで同じ新しい番号を 2 回書いても 1 件
L4A='FINDING: F3 SEV=Low STATUS=open FILE=backend/x.py LINE=10 SECURITY=no STOP=- | 1 回目'
L4B='FINDING: F3 SEV=Medium STATUS=open FILE=backend/x.py LINE=10 SECURITY=no STOP=- | 2 回目'
ledger "$CR" full "" "$L4A" "$L4B" >/dev/null
ck "L4 F3 が 1 行だけ・F4 に振り直されない・重大度は上がる" "1 no yes" \
  "$(grep -c '^LEDGER: F3 ' "$TMP/led") $(led_has '^LEDGER: F4 ') $(led_has '^LEDGER: F3 SEV=Medium')"
printf 'LEDGER: F1 SEV=High STATUS=resolved SCOPE=delta KIND=app STOP=- REPRO=yes RISK=- SECURITY=no | 直った\n' > "$TMP/l4_prev"
ledger "$CR" delta "$TMP/l4_prev" 'FINDING: F1 SEV=High STATUS=open FILE=backend/x.py LINE=10 SECURITY=no STOP=- | 新しい | 再現: r' >/dev/null
ck "L4 前の周の resolved の番号を使った行は、今までどおり新しい番号（F2）に振り直す" "yes yes" \
  "$(led_has '^LEDGER: F1 SEV=High STATUS=resolved') $(led_has '^LEDGER: F2 SEV=High STATUS=open')"
ledger "$(broken '        seen.add(fid)' '        pass')" full "" "$L4A" "$L4B" >/dev/null
ck "FG-L4 seen を外すと L4 が不合格（F4 に振り直される）" yes "$(led_has '^LEDGER: F4 ')"
# L5 I197-F18: ..foo.sh はリポジトリの中・../x はリポジトリの外
ledger "$CR" full "" 'FINDING: F1 SEV=High STATUS=open FILE=..foo.sh LINE=1 SECURITY=no STOP=- | f | 再現: r' >/dev/null
ck "L5 リポジトリの中の実在のファイル ..foo.sh（範囲の外）→ outside" yes "$(led_has 'SCOPE=outside')"
ledger "$CR" full "" 'FINDING: F1 SEV=High STATUS=open FILE=../x LINE=1 SECURITY=no STOP=- | f | 再現: r' >/dev/null
ck "L5 ../x → delta（止める側）" yes "$(led_has 'SCOPE=delta')"
# L6 台帳の限界: 台帳の残り（止めない open の指摘）を resolved と書けば resolved。open で書けば新しい番号
printf 'LEDGER: F1 SEV=High STATUS=open SCOPE=delta KIND=harness STOP=flow REPRO=yes RISK=- SECURITY=no | 止める\nLEDGER: F2 SEV=Low STATUS=open SCOPE=delta KIND=harness STOP=- REPRO=no RISK=- SECURITY=no | 残り\n' > "$TMP/l6_prev"
L6_RES='FINDING: F2 SEV=Low STATUS=resolved FILE=scripts/claude/a.sh LINE=10 SECURITY=no STOP=- | 直した'
ledger "$CR" delta "$TMP/l6_prev" 'FINDING: F1 SEV=High STATUS=resolved FILE=scripts/claude/a.sh LINE=10 SECURITY=no STOP=flow | 直した' "$L6_RES" >/dev/null
ck "L6 台帳の残りの F2 を resolved と書く → F2 が resolved（振り直されない）" "yes no" "$(led_has '^LEDGER: F2 SEV=Low STATUS=resolved') $(led_has '^LEDGER: F3 ')"
ledger "$CR" delta "$TMP/l6_prev" 'FINDING: F2 SEV=High STATUS=open FILE=scripts/claude/a.sh LINE=10 SECURITY=no STOP=flow | 新しい穴 | 再現: r' >/dev/null
ck "L6 台帳の残りの番号を open で書く → 新しい F3（範囲で決め直す）・F2 は open のまま" "yes yes" \
  "$(led_has '^LEDGER: F3 SEV=High STATUS=open SCOPE=delta') $(led_has '^LEDGER: F2 SEV=Low STATUS=open')"
ledger "$CR" delta "$TMP/l6_prev" >/dev/null
ck "L6 書かなければ F2 は open のまま" yes "$(led_has '^LEDGER: F2 SEV=Low STATUS=open')"
ledger "$(broken 'keep = fid in seen or fid in shown or (fid in rest_ids and st == "resolved")' 'keep = fid in seen or fid in shown')" delta "$TMP/l6_prev" "$L6_RES" >/dev/null
ck "FG-L6 台帳の残りの resolved を受け付けないと L6 が不合格（F2 は open・F3 に振り直し）" "yes yes" "$(led_has '^LEDGER: F2 SEV=Low STATUS=open') $(led_has '^LEDGER: F3 ')"
# L7 ledger_open_rest
printf '%s\nLEDGER: F3 SEV=Low STATUS=resolved SCOPE=delta KIND=harness STOP=- REPRO=no RISK=- SECURITY=no | 済\n' "$(cat "$TMP/l6_prev")" > "$TMP/l7"
ck "L7 台帳の残り: open で止めない F2 だけ" F2 "$(lib "$CR" ledger_open_rest "$TMP/l7" | grep -oE '^LEDGER: F[0-9]+' | cut -d' ' -f2 | paste -sd' ' -)"

# ---------------- R・W 本体の通し（gh・claude はスタブ） ----------------
ES="$TMP/e2e_stub"; mkdir -p "$ES"
printf 'jobs:\n  j:\n    name: J\n' > "$ES/wf.yml"
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
# code-reviewer（--agent）には $E2E_REVIEW を stream-json で返し、入力を $E2E_IN に書く（$E2E_FAIL があれば何も返さず exit 1）。
# 組み込みのレビューには「指摘なし」。呼ばれた種類を $E2E_CALLS に 1 行ずつ書く
import json, os, sys
args = sys.argv[1:]
with open(os.environ["E2E_CALLS"], "a") as f:
    f.write(("agent" if "--agent" in args else "official") + "\n")
if "--agent" in args:
    open(os.environ["E2E_IN"], "w").write(sys.stdin.read())
    if os.environ.get("E2E_FAIL"):
        sys.exit(1)
    body = open(os.environ["E2E_REVIEW"]).read()
    print(json.dumps({"type": "system", "subtype": "init", "session_id": "s"}))
    print(json.dumps({"type": "result", "subtype": "success", "result": body, "permission_denials": []}))
else:
    print("指摘なし")
PY
chmod +x "$ES/gh" "$ES/claude"
# setup <名前> [<code-review.sh の写し>]: 一時のリポジトリ（develop に a.py・feature で 2 行目を足す）。計画レビューの判定は No
setup() { local E="$TMP/e_$1" O="$TMP/e_$1.git"
  mkdir -p "$E/scripts/claude" "$E/docs/issues/open" "$E/docs/reviews"
  cp "${2:-$CR}" "$E/scripts/claude/code-review.sh"; cp "$REPO_ROOT/scripts/claude/review-process-lib.sh" "$GC" "$E/scripts/claude/"
  printf '# I900\n' > "$E/docs/issues/open/I900.md"; printf 'l1\n' > "$E/a.py"
  printf '# 計画レビュー\n\n## 高リスク判定\n判定: No\n' > "$E/docs/reviews/I900_plan_review_20260101_0000.md"
  git init -q --bare "$O"; git -C "$E" init -q -b develop; git -C "$E" add -A; git -C "$E" commit -qm base
  git -C "$E" remote add origin "$O"; git -C "$E" push -q origin develop 2>/dev/null
  git -C "$E" checkout -q -b feature/I900-x; printf 'l2\n' >> "$E/a.py"; git -C "$E" add -A; git -C "$E" commit -qm change; }
# round <名前> <周の名前> <レビュー役の本文> [環境変数…]: 本体を丸ごと動かす。出力は $TMP/out_<周>、記録の名前を出す
round() { local name="$1" E="$TMP/e_$1" r="$2"; printf '%b' "$3" > "$TMP/review_$r.txt"; shift 3
  : > "$TMP/calls_$r"
  (cd "$E" && env PATH="$ES:$PATH" CLAUDE_BIN="$ES/claude" E2E_IN="$TMP/in_$r.txt" E2E_REVIEW="$TMP/review_$r.txt" E2E_CALLS="$TMP/calls_$r" \
     CI_WORKFLOWS="$ES/wf.yml" CI_WAIT_TIMEOUT=5 CI_POLL_INTERVAL=1 "$@" bash scripts/claude/code-review.sh I900 > "$TMP/out_$r" 2>&1)
  latest_rec "$name"; }
# 最新のコードレビューの記録（本体と同じ review_records の順）
latest_rec() { (cd "$TMP/e_$1" && lib "$CR" review_records I900 code_review | tail -1 | sed "s#^#$TMP/e_$1/#"); }
stage() { sed -n 's/^ADVERSARIAL_STAGE: //p' "$TMP/out_$1"; }
fv() { sed -n 's/^FINAL_VERDICT: //p' "$TMP/out_$1"; }
change() { printf '%s\n' "$2" >> "$TMP/e_$1/a.py"; git -C "$TMP/e_$1" add -A; git -C "$TMP/e_$1" commit -qm "$2"; }
# rename_rec <名前> <記録> <番号>: 同じ分に何度も動かすので、記録の名前の時刻を <番号> にずらしてコミットし、新しい名前を出す
# （ファイル名の時刻順で前の周を探すため）
rename_rec() { local to="${2%_*}_$3.md"; mv "$2" "$to"; git -C "$TMP/e_$1" add -A; git -C "$TMP/e_$1" commit -qm "rename $3"; echo "$to"; }
# record_only <名前>: 記録の場所（イシューファイル）だけを変えてコミットする
record_only() { printf 'x\n' >> "$TMP/e_$1/docs/issues/open/I900.md"; git -C "$TMP/e_$1" add -A; git -C "$TMP/e_$1" commit -qm "record only"; }
# remake <名前> <記録>: 記録の REVIEWED_COMMIT の 1 つ前から作り直す（rebase と同じく、前の REVIEWED_COMMIT が祖先でなくなる）
remake() { local sha; sha=$(lib "$CR" record_reviewed_commit "$2"); git -C "$TMP/e_$1" reset -q --soft "${sha}~1"; git -C "$TMP/e_$1" commit -qm "作り直し"; }
B_NONE='# r\n\n## 台帳\n指摘なし\n\nVERDICT: OK\n'
B_MARK='# r\n\n## 台帳\nFINDING: F1 SEV=Low STATUS=open FILE=a.py LINE=2 SECURITY=no STOP=- RISK=up | 計画が見ていない認可の変更\nFINDING: F2 SEV=Low STATUS=open FILE=a.py LINE=2 SECURITY=no STOP=- | 残り\n\nVERDICT: OK\n'

setup m
M1=$(round m m1 "$B_MARK")
ck "R6 計画レビュー No・パス NO でも、RISK=up の目印で ADVERSARIAL_STAGE: REQUIRED・FINAL OK" "REQUIRED OK" "$(stage m1) $(fv m1)"
ck "R6 記録の RISK: YES・証跡に「台帳の目印=YES」" "yes yes" "$(yn grep -qx 'RISK: YES' "$M1") $(yn grep -qF '台帳の目印=YES' "$M1")"
ck "W5 記録の止める指摘の節に「（再現は本文の同じ番号の FINDING 行）」" yes "$(yn grep -qxF '（再現は本文の同じ番号の FINDING 行）' "$M1")"
# R10: その記録で gate-check は敵対的レビューの記録を求める
(cd "$TMP/e_m" && GATE_BASE=origin/develop bash scripts/claude/gate-check.sh I900 > "$TMP/gc_m" 2>&1; echo $? > "$TMP/gc_m.rc")
ck "R10 gate-check: 敵対的レビューの記録が無いので exit 1・REASON=missing" "1 yes" "$(cat "$TMP/gc_m.rc") $(yn grep -q 'GATE_CHECK: FAIL REASON=missing' "$TMP/gc_m")"
# 2 周目（差分のレビュー・目印なし）: F2（台帳の残り）を直した
rename_rec m "$M1" 0001 >/dev/null
change m l3
M2=$(round m m2 '# r\n\n## 台帳\nFINDING: F2 SEV=Low STATUS=resolved FILE=a.py LINE=2 SECURITY=no STOP=- | 直した\n\nVERDICT: OK\n')
ck "R7 目印の無い差分のレビューでも REQUIRED のまま" REQUIRED "$(stage m2)"
ck "W1 差分のレビューの入力に「台帳の残り」の節と F1・F2" "yes yes yes" \
  "$(yn grep -qF '#### 台帳の残り' "$TMP/in_m2.txt") $(yn grep -q '^LEDGER: F1 ' "$TMP/in_m2.txt") $(yn grep -q '^LEDGER: F2 ' "$TMP/in_m2.txt")"
ck "L6（通し）2 周目の台帳で F2 が resolved" yes "$(yn grep -q '^LEDGER: F2 SEV=Low STATUS=resolved' "$M2")"
rename_rec m "$M2" 0002 >/dev/null
# 3 周目: 記録の場所だけを変えた → 範囲が空。レビュー役も組み込みのレビューも呼ばない
record_only m
M3=$(round m m3 '# 呼ばれないはず\n\nVERDICT: HIGH\n')
ck "W4 範囲が空: claude を 1 回も呼ばない・FINAL OK・LEDGER_ROUND: 3・台帳を引き継ぐ" "0 OK yes yes" \
  "$(grep -c . "$TMP/calls_m3") $(fv m3) $(yn grep -qx 'LEDGER_ROUND: 3' "$M3") $(yn grep -q '^LEDGER: F1 .*RISK=up' "$M3")"
M3=$(rename_rec m "$M3" 0003)
# 4 周目（R8）: 前の REVIEWED_COMMIT が祖先でなくなる → 全体のレビュー・目印なし
remake m "$M3"
round m m4 "$B_NONE" >/dev/null
ck "R8 rebase の後の全体のレビュー（目印なし）でも REQUIRED のまま" "yes REQUIRED" "$(yn grep -q '^全体のレビュー' "$TMP/out_m4") $(stage m4)"

# 目印が一度も無い通し（R9）・前の台帳が空（W2）・レビュー役の失敗（W3）
setup n
N1=$(round n n1 "$B_NONE")
ck "R9 目印なし → NOT_REQUIRED・RISK: NO" "NOT_REQUIRED yes" "$(stage n1) $(yn grep -qx 'RISK: NO' "$N1")"
rename_rec n "$N1" 0001 >/dev/null
change n l3
round n n2 "$B_NONE" >/dev/null
ck "W2 前の台帳が空: 「台帳の最大の番号: なし（新しい指摘は F1 から）」があり「最大の番号: F」が無い" "yes no" \
  "$(yn grep -qxF '台帳の最大の番号: なし（新しい指摘は F1 から）' "$TMP/in_n2.txt") $(yn grep -qE '^台帳の最大の番号: F($|（)' "$TMP/in_n2.txt")"
change n l4
N3=$(round n n3 'x' E2E_FAIL=1)
ck "W3 レビュー役の失敗: FINAL BLOCKER・証跡に「読める FINDING 行が無い」が無い" "BLOCKER no" "$(fv n3) $(yn grep -qF '読める FINDING 行が無い' "$N3")"

# FG（本体の通し）
setup f6 "$(broken 'RISK_FINAL=$(combine_risk "$RISK_FINAL" "$RISK_LEDGER")' 'RISK_FINAL=$RISK_FINAL')"
round f6 f6 "$B_MARK" >/dev/null
ck "FG-R6 台帳の目印を高リスクに入れないと R6 が不合格" NOT_REQUIRED "$(stage f6)"
setup f8 "$(broken 'RISK_LEDGER=$(ledger_risk "${CODE_REVIEWS[@]}")' 'RISK_LEDGER=$(ledger_risk "$LEDGER_FILE")')"
remake f8 "$(rename_rec f8 "$(round f8 f8a "$B_MARK")" 0001)"
round f8 f8b "$B_NONE" >/dev/null
ck "FG-R8 前の記録の台帳を見ないと R8 が不合格（rebase の後に NOT_REQUIRED）" NOT_REQUIRED "$(stage f8b)"
setup f3 "$(broken 'if [ "$REVIEWER_RAN" = "1" ] && [ "$LLM_VERDICT"' 'if [ "$LLM_VERDICT"')"
ck "FG-W3 REVIEWER_RAN の条件を外すと W3 が不合格（誤った原因が出る）" yes "$(yn grep -qF '読める FINDING 行が無い' "$(round f3 f3 'x' E2E_FAIL=1)")"
setup f4 "$(broken '    NO_DELTA=1; echo "起点の後に' '    NO_DELTA=0; echo "起点の後に')"
rename_rec f4 "$(round f4 f4a "$B_NONE")" 0001 >/dev/null
record_only f4
round f4 f4b "$B_NONE" >/dev/null
ck "FG-W4 空の範囲の扱いを外すと W4 が不合格（レビュー役が呼ばれる）" yes "$(yn grep -qx agent "$TMP/calls_f4b")"

# W4b（fix-loop F2）: 変更を develop の中身に戻す直しは、範囲（delta_files）が空でもレビュー役を呼び、取り消しの差分を見せる。
# 止める指摘が resolved になって OK に進める
B_APP_HIGH='# r\n\n## 台帳\nFINDING: F1 SEV=High STATUS=open FILE=a.py LINE=2 SECURITY=no STOP=- | 穴 | 再現: r\n\nVERDICT: HIGH\n'
B_APP_RES='# r\n\n## 台帳\nFINDING: F1 SEV=High STATUS=resolved FILE=a.py LINE=2 SECURITY=no STOP=- | 取り消した\n\nVERDICT: OK\n'
# revert_app <名前>: a.py を develop の中身に戻してコミットする
revert_app() { git -C "$TMP/e_$1" checkout -q origin/develop -- a.py; git -C "$TMP/e_$1" commit -qam "revert a.py"; }
setup w4b
rename_rec w4b "$(round w4b w4b1 "$B_APP_HIGH")" 0001 >/dev/null
ck "W4b 1 周目: アプリの High（再現あり）で HIGH" HIGH "$(fv w4b1)"
revert_app w4b
round w4b w4b2 "$B_APP_RES" >/dev/null
ck "W4b 取り消しの直し: レビュー役が呼ばれ、入力に a.py の取り消しの差分があり、F1 が resolved で OK" "yes yes OK" \
  "$(yn grep -qx agent "$TMP/calls_w4b2") $(yn grep -qx -- '-l2' "$TMP/in_w4b2.txt") $(fv w4b2)"
setup fw4b "$(broken 'if changed_outside_records "$SINCE" HEAD > "$OUTSIDE_SINCE_FILE"; then' 'if [ ! -s "$SCOPE_FILE" ]; then')"
rename_rec fw4b "$(round fw4b fw4b1 "$B_APP_HIGH")" 0001 >/dev/null
revert_app fw4b
round fw4b fw4b2 "$B_APP_RES" >/dev/null
ck "FG-W4b 範囲が空かで決める形に戻すと W4b が不合格（呼ばれずに HIGH のまま）" "no HIGH" "$(yn grep -qx agent "$TMP/calls_fw4b2") $(fv fw4b2)"

# ---------------- A adversarial-review.sh の細部（claude はスタブ） ----------------
AS="$TMP/adv_stub"
cat > "$AS" <<'PY'
#!/usr/bin/env python3
# レビュー役: 観点 1・2 は 1 回目に実験案、2 回目に ITEM を返す。観点 3 は ITEM だけ。$SD/nodenials_p<k> があれば permission_denials を出さない
# 実験役: 始まりと終わりの時刻を $SD/spans に書き、$SD/exec_sleep 秒眠る
import json, os, re, sys, time
args = sys.argv[1:]; sd = os.environ["SD"]; stdin = sys.stdin.read()
def out(d): print(json.dumps(d, ensure_ascii=False), flush=True)
def val(flag): return args[args.index(flag) + 1] if flag in args else None
if val("--tools") == "Bash":
    t0 = time.time()
    time.sleep(float(open(os.path.join(sd, "exec_sleep")).read()) if os.path.exists(os.path.join(sd, "exec_sleep")) else 0.5)
    open(os.path.join(sd, "spans"), "a").write(f"{t0} {time.time()}\n")
    out({"type": "system", "subtype": "init", "session_id": "exec", "permissionMode": "auto"})
    for m in re.finditer(r"<<<COMMAND ([A-Za-z0-9_-]+)\n(.*?)\nCOMMAND>>>", stdin, re.S):
        tid = "tu-" + m.group(1)
        out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": tid, "name": "Bash", "input": {"command": m.group(2)}}]}})
        out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "content": "ok", "is_error": False}]}})
    out({"type": "result", "subtype": "success", "result": "DONE", "session_id": "exec", "permission_denials": [], "total_cost_usd": 0.01})
    sys.exit(0)
sid = val("--resume")
k = sid.split("-p")[-1] if sid else re.search(r"あなたの観点: (\d)", stdin).group(1)
sid = "sess-p" + k
first = val("--resume") is None
if k in "12" and first:
    body = f"EXPERIMENT_BEGIN P{k}-E1\necho {k}\nEXPERIMENT_END P{k}-E1\nITEM: V{k} RESULT=not_done\nNEW_CRITICAL: 0\nNEW_HIGH: 0\n"
elif k in "12":
    body = f"ITEM: V{k} RESULT=experiment EXP=P{k}-E1\nNEW_CRITICAL: 0\nNEW_HIGH: 0\n"
else:
    body = "ITEM: V3 RESULT=read\nNEW_CRITICAL: 0\nNEW_HIGH: 0\n"
out({"type": "system", "subtype": "init", "session_id": sid, "permissionMode": "manual"})
res = {"type": "result", "subtype": "success", "result": body, "session_id": sid, "total_cost_usd": 0.02}
if not os.path.exists(os.path.join(sd, f"nodenials_p{k}")):
    res["permission_denials"] = []
out(res)
PY
chmod +x "$AS"
APLAN='# I900 計画書

## 必ず確かめる項目
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | 実験で確かめる |
| V2 | 2 | 実験必須 | 実験で確かめる |
| V3 | 3 | 読んで可 | 読んで確かめる |
'
# amk <名前> [<adversarial-review.sh の写し>]: 一時のリポジトリ
amk() { local d="$TMP/a_$1"
  mkdir -p "$d/repo/scripts/claude" "$d/repo/docs/issues/open" "$d/repo/docs/plans/open" "$d/repo/docs/reviews" "$d/sd"
  cp "$CR" "$REPO_ROOT/scripts/claude/review-process-lib.sh" "$d/repo/scripts/claude/"
  cp "${2:-$ADV}" "$d/repo/scripts/claude/adversarial-review.sh"
  printf '# I900\n' > "$d/repo/docs/issues/open/I900.md"; printf '%s' "$APLAN" > "$d/repo/docs/plans/open/plan_I900.md"
  printf 'a\n' > "$d/repo/a.txt"
  git -C "$d/repo" init -q -b develop; git -C "$d/repo" add -A; git -C "$d/repo" commit -q -m base
  git -C "$d/repo" checkout -q -b feature/I900-x; printf 'b\n' >> "$d/repo/a.txt"; git -C "$d/repo" add -A; git -C "$d/repo" commit -q -m change; }
arun() { local d="$TMP/a_$1"; shift
  ( cd "$d/repo" && env CLAUDE_BIN="$AS" SD="$d/sd" ADV_BASE=develop ADV_DEADLINE=60 ADV_STEP_TIMEOUT=20 ADV_MIN_STEP=1 "$@" \
      bash scripts/claude/adversarial-review.sh I900 > "$d/out" 2>&1; echo $? > "$d/rc" ) ; }
arec() { sed -n 's/^ADVERSARIAL_RECORD: //p' "$TMP/a_$1/out" | head -1 | sed "s#^#$TMP/a_$1/repo/#"; }
av() { sed -n 's/^ADVERSARIAL_VERDICT: //p' "$TMP/a_$1/out"; }
# 区間が重ならないか（始まりの順に並べ、前の終わり <= 次の始まり）
no_overlap() { sort -n "$1" | awk 'NR > 1 && $1 < pe { bad = 1 } { pe = $2 } END { exit bad }'; }
amk a1; echo 1 > "$TMP/a_a1/sd/exec_sleep"; arun a1
ck "A1 2 観点の実験役が両方動き（区間 2 つ）、重ならない・判定 OK" "2 yes OK" \
  "$(grep -c . "$TMP/a_a1/sd/spans") $(yn no_overlap "$TMP/a_a1/sd/spans") $(av a1)"
ck "A4 note が空の観点の行に「報告あり（）」が無い" no "$(grep -qF '報告あり（）' "$(arec a1)" && echo yes || echo no)"
amk fa1 "$(broken_of "$ADV" '      flock 9' '      :')"; echo 1 > "$TMP/a_fa1/sd/exec_sleep"; arun fa1
ck "FG-A1 flock を外すと A1 が不合格（区間が重なる）" no "$(yn no_overlap "$TMP/a_fa1/sd/spans")"
# A1b: ロックの待ちの間に締め切りが迫る（残りが ADV_MIN_STEP 未満）→ 待った側は実験役を呼ばずに締め切り
amk a1b; echo 7 > "$TMP/a_a1b/sd/exec_sleep"; arun a1b ADV_DEADLINE=10 ADV_MIN_STEP=4
ck "A1b 実験役は 1 回だけ・締め切りの実験が記録にある・判定 HIGH" "1 yes HIGH" \
  "$(grep -c . "$TMP/a_a1b/sd/spans") $(grep -qF '実行していない（締め切り）' "$(arec a1b)" && echo yes || echo no) $(av a1b)"
# A3: 拒否の一覧を読めない（観点 3 の記録に permission_denials が無い）→ 読めない・HIGH・exit 1
amk a3; touch "$TMP/a_a3/sd/nodenials_p3"; arun a3
ck "A3 拒否が読めない → 記録に「読めない」・ADVERSARIAL_VERDICT: HIGH・exit 1" "yes HIGH 1" \
  "$(grep -qE '^\| 3 \| 報告あり \| .* \| 0（読めない記録あり） \|' "$(arec a3)" && echo yes || echo no) $(av a3) $(cat "$TMP/a_a3/rc")"
amk fa3 "$(broken_of "$ADV" '|| [ "$DENIALS_UNREADABLE" -eq 1 ]; then VERDICT=HIGH' '; then VERDICT=HIGH')"; touch "$TMP/a_fa3/sd/nodenials_p3"; arun fa3
ck "FG-A3 読めない拒否を判定に入れないと A3 が不合格（OK）" OK "$(av fa3)"
# A2: review_base は、前の記録の REVIEWED_COMMIT が HEAD の祖先でなければ比べる相手を返す
amk a2; AR="$TMP/a_a2/repo"
git -C "$AR" checkout -q --orphan other; git -C "$AR" commit -q --allow-empty -m other; OTHER=$(git -C "$AR" rev-parse HEAD); git -C "$AR" checkout -q feature/I900-x
ANC=$(git -C "$AR" rev-parse HEAD~1)
rb() { printf 'REVIEWED_COMMIT: %s\nROUNDS: 1\nVERDICT: HIGH\n' "$2" > "$AR/docs/reviews/I900_adversarial_review_20260101_0000.md"
  (cd "$AR" && ISSUE=I900 ADV_BASE=develop REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1"; review_base' _ "$1"); }
ck "A2 祖先の SHA はそのまま・祖先でない SHA は比べる相手（develop）" "$ANC develop" \
  "$(rb "$AR/scripts/claude/adversarial-review.sh" "$ANC") $(rb "$AR/scripts/claude/adversarial-review.sh" "$OTHER")"
cp "$(broken_of "$ADV" ' && git merge-base --is-ancestor "$sha" HEAD 2>/dev/null; then' '; then')" "$AR/scripts/claude/adv_broken.sh"
ck "FG-A2 祖先の確認を外すと A2 が不合格（祖先でない SHA が返る）" "$OTHER" "$(rb "$AR/scripts/claude/adv_broken.sh" "$OTHER")"

# ---------------- G 共通化（gate-check の挙動を変えない） ----------------
G="$TMP/g"; mkdir -p "$G/docs/reviews/closed"
: > "$G/docs/reviews/I900_code_review_20260101_0000.md"; : > "$G/docs/reviews/I900_code_review_20260101_0000_2.md"
: > "$G/docs/reviews/closed/I900_code_review_20260101_0001.md"; : > "$G/docs/reviews/I900_adversarial_review_20260101_0002.md"
ck "G1 review_records: 時刻順（同じ分の _2 はその後ろ・closed も含む・種類で絞る）" \
  "docs/reviews/I900_code_review_20260101_0000.md docs/reviews/I900_code_review_20260101_0000_2.md docs/reviews/closed/I900_code_review_20260101_0001.md" \
  "$(cd "$G" && lib "$CR" review_records I900 code_review | paste -sd' ' -)"
printf 'REVIEWED_COMMIT: aaaaaaa\nx\nREVIEWED_COMMIT: bbbbbbb\n' > "$TMP/rc1"; printf 'x\n' > "$TMP/rc2"
ck "G2 record_reviewed_commit: 最後の SHA・無ければ空" "bbbbbbb|" "$(lib "$CR" record_reviewed_commit "$TMP/rc1")|$(lib "$CR" record_reviewed_commit "$TMP/rc2")"
mkdir -p "$R/docs/reviews"; git -C "$R" checkout -q -b feature/I900-g
printf 'q\n' > "$R/docs2/a [b].md"; printf 'r\n' > "$R/docs/reviews/I900_x.md"; git -C "$R" add -A; git -C "$R" commit -qm g3
ck "G3 branch_own_files: 空白・[ を含むパスはそのまま・記録の場所は出ない" "docs2/a [b].md" "$(cd "$R" && lib "$CR" branch_own_files develop | paste -sd'|' -)"
# G4: 付け替える前（develop 33d2e29）の gate-check.sh と code-review.sh と、出力の GATE_CHECK の行・終了コードが同じ
OLD="$TMP/old"; mkdir -p "$OLD"
git -C "$REPO_ROOT" show 33d2e29:scripts/claude/gate-check.sh > "$OLD/gate-check.sh"
git -C "$REPO_ROOT" show 33d2e29:scripts/claude/code-review.sh > "$OLD/code-review.sh"
GR="$TMP/gr"; mkdir -p "$GR/docs/reviews"
printf 'a\n' > "$GR/a.sh"; git -C "$GR" init -q -b develop; git -C "$GR" add -A; git -C "$GR" commit -qm base
git -C "$GR" checkout -q -b feature/I900-x; printf 'b\n' >> "$GR/a.sh"; git -C "$GR" add -A; git -C "$GR" commit -qm change
gcrun() { (cd "$GR" && GATE_BASE=develop GATE_CHECK_LIB="$2" bash "$1" I900 2>&1; echo "rc=$?") | grep -E '^(GATE_CHECK:|rc=)' | paste -sd' ' -; }
same() { local a b; a=$(gcrun "$OLD/gate-check.sh" "$OLD/code-review.sh"); b=$(gcrun "$GC" "$CR"); [ "$a" = "$b" ] && echo "yes:$b" || echo "no:$a|$b"; }
printf 'REVIEWED_COMMIT: %s\nRISK: NO\nVERDICT: OK\n' "$(git -C "$GR" rev-parse HEAD)" > "$GR/docs/reviews/I900_code_review_20260101_0000.md"
ck "G4 OK の記録: 前と同じ（GATE_CHECK: OK）" "yes:GATE_CHECK: OK rc=0" "$(same)"
printf 'c\n' >> "$GR/a.sh"; git -C "$GR" add -A; git -C "$GR" commit -qm after
ck "G4 レビューの後の変更: 前と同じ（unreviewed）" "yes:GATE_CHECK: FAIL REASON=unreviewed rc=1" "$(same)"
mkdir -p "$GR/.github"; printf 'x\n' > "$GR/.github/x.yml"; git -C "$GR" add -A; git -C "$GR" commit -qm guard
printf 'REVIEWED_COMMIT: %s\nRISK: NO\nVERDICT: OK\n' "$(git -C "$GR" rev-parse HEAD)" > "$GR/docs/reviews/I900_code_review_20260101_0001.md"
ck "G4 高リスク（パス）で敵対的レビューなし: 前と同じ（missing）" "yes:GATE_CHECK: FAIL REASON=missing rc=1" "$(same)"
# G5（I205-F12）: 行の塊と差分のレビューの git diff は、パスを glob として読まない（4 か所すべて --literal-pathspecs。
# 行の塊の 2 本・差分のレビューの範囲のファイル・範囲が空で記録の場所の外が変わったとき〔fix-loop F2〕）
g5() { [ "$(grep -c "xargs -d '\\\\n' git --literal-pathspecs" "$1")" -eq 4 ]; }
ck "G5 4 か所の git diff に --literal-pathspecs" yes "$(yn g5 "$CR")"
ck "FG-G5 1 か所外すと G5 が不合格" no "$(yn g5 "$(broken 'GIT_DIFF=$(xargs -d '"'"'\n'"'"' git --literal-pathspecs diff' 'GIT_DIFF=$(xargs -d '"'"'\n'"'"' git diff')")"

# ---------------- D 指示ファイル ----------------
CRV=.claude/agents/code-reviewer.md; RG=.claude/skills/review-gate/SKILL.md; RR=docs/runbooks/review-rules.md
d1() { grep -qF 'RISK=up' "$1" && grep -qF '台帳の残り' "$1" && grep -qF '消した位置の HEAD の行番号' "$1" && ! grep -qF '触れていれば Blocker として FINDING 行に書く' "$1"; }
d2() { grep -qF '台帳の目印' "$1" && grep -qF '必ず確かめる項目' "$1" && ! grep -qF '計画レビューの判定とパスの判定で決まり、周ごとに変わらない' "$1"; }
d3() { grep -qF '台帳の目印' "$1" && ! grep -qF '計画レビューの判定とパスの判定で決め、周ごとに変えない' "$1"; }
without() { local o="$TMP/w_$RANDOM$RANDOM"; grep -vF -- "$2" "$1" > "$o"; echo "$o"; }
ck "D1 code-reviewer.md" yes "$(yn d1 "$CRV")"
ck "D2 review-gate/SKILL.md" yes "$(yn d2 "$RG")"
ck "D3 review-rules.md" yes "$(yn d3 "$RR")"
ck "FG-D1 RISK=up の語を消すと D1 が不合格" no "$(yn d1 "$(without "$CRV" 'RISK=up')")"
ck "FG-D2 台帳の目印の語を消すと D2 が不合格" no "$(yn d2 "$(without "$RG" '台帳の目印')")"
ck "FG-D3 台帳の目印の語を消すと D3 が不合格" no "$(yn d3 "$(without "$RR" '台帳の目印')")"

ck "FG の写しがすべて作れた（置き換え前の文字列が本体にある）" no "$([ -e "$TMP/broken_failed" ] && echo yes || echo no)"
printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
