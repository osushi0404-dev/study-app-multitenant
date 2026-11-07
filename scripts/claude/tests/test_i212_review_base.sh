#!/usr/bin/env bash
# I212（plan_I212.md §4-5・auto_test TC-02・TC-03）: 差分のレビューの起点を「見終えた最新の記録」にする・/security-review の判定の 1 行。
#   U: code-review.sh の関数（review_mode・official_security_verdict・neutralize_machine_lines。
#      I227: U9 差分なしは NO_DELTA で決める・U10 読めたかは種類ごとの決まった形〔JSON の配列・判定の行〕で決める）
#   E: 本体の通し（gh・claude はスタブ）と gate-check（I211・I213・I200 の再現）
#   FG: 判定の要を一時コピーで壊すと、対応する項目が不合格になること
# 実行: bash scripts/claude/tests/test_i212_review_base.sh
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
yn() { if "$@" >/dev/null 2>&1; then echo yes; else echo no; fi; }
CR="$REPO_ROOT/scripts/claude/code-review.sh"
GC="$REPO_ROOT/scripts/claude/gate-check.sh"

# lib <code-review.sh の写し> <関数と引数…>: 関数だけを読み込んで 1 つ呼ぶ（cwd はそのまま）
lib() { local src="$1"; shift; REVIEW_LIB_SOURCE_ONLY=1 bash -c '. "$1"; shift; "$@"' _ "$src" "$@"; }
# 壊した写し: <置き換え前> <置き換え後>（置き換え前が無ければ印を残して最後に不合格）
broken() { local f="$TMP/b_$RANDOM$RANDOM.sh"
  python3 -I -c 'import sys
s = open(sys.argv[1], encoding="utf-8").read()
if sys.argv[3] not in s: sys.exit(1)
open(sys.argv[2], "w", encoding="utf-8").write(s.replace(sys.argv[3], sys.argv[4]))' "$CR" "$f" "$1" "$2" || : > "$TMP/broken_failed"
  echo "$f"; }

# ---------------- U: 起点の選び方（一時のリポジトリ・記録はファイルを置くだけ） ----------------
R="$TMP/repo"; mkdir -p "$R/docs/reviews" "$R/scripts"
git -C "$R" init -q -b develop
printf 'a\n' > "$R/scripts/a.sh"; git -C "$R" add -A; git -C "$R" commit -qm base
git -C "$R" checkout -q -b elsewhere; printf 'z\n' > "$R/z.txt"; git -C "$R" add -A; git -C "$R" commit -qm "別の枝"
NOT_ANC=$(git -C "$R" rev-parse HEAD)
git -C "$R" checkout -q -b feature/I900-x develop
printf 'a2\n' >> "$R/scripts/a.sh"; git -C "$R" add -A; git -C "$R" commit -qm c1; C1=$(git -C "$R" rev-parse HEAD)
printf 'a3\n' >> "$R/scripts/a.sh"; git -C "$R" add -A; git -C "$R" commit -qm c2; C2=$(git -C "$R" rev-parse HEAD)
MB=$(git -C "$R" merge-base develop HEAD)
RD=docs/reviews/I900_code_review_20260101
# mk <番号> <周> <YES|NO|-（行なし）> <REVIEWED_COMMIT> [VERDICT]: 台帳のある記録を置く
mk() { local c=""; [ "$3" = "-" ] || c="REVIEW_COMPLETE: $3"
  printf '# r\nLEDGER_ROUND: %s\nREVIEWED_COMMIT: %s\nRISK: NO\nVERDICT: %s\n%s\n' "$2" "$4" "${5:-OK}" "$c" > "$R/${RD}_$1.md"; }
clear_recs() { rm -f "$R"/docs/reviews/I900_code_review_*.md; }
mode() { (cd "$R" && lib "${2:-$CR}" review_mode I900 "${1:-develop}" | tr '\t' '|'); }

ck "U0 記録が無い → full" "full|1||" "$(mode)"
mk 0001 1 YES "$C1"; mk 0002 2 NO "$C2" HIGH
ck "U1 見終えた A（c1）→ 見終えていない B（c2）: 起点は A・周と前の記録は B" "delta|3|${C1}|${RD}_0002.md" "$(mode)"
mk 0003 3 NO "$C2" HIGH
ck "U2 見終えていない回が 2 つ続いても A まで遡る" "delta|4|${C1}|${RD}_0003.md" "$(mode)"
mk 0001 1 NO "$C1"
ck "U3 見終えた記録が無い → ブランチの分岐点が起点（台帳と周は最新から）" "delta|4|${MB}|${RD}_0003.md" "$(mode)"
ck "U3 比べる相手が無く、見終えた記録も無い → full" "full|1||" "$(mode nosuch-branch)"
clear_recs; mk 0001 1 YES "$C1"; mk 0002 2 YES "$C2" HIGH
ck "U4 指摘が残って HIGH でも見終えた回は起点（今までどおり）" "delta|3|${C2}|${RD}_0002.md" "$(mode)"
clear_recs; mk 0001 1 YES "$C1"; mk 0002 2 - "$C2" OK
ck "U5 REVIEW_COMPLETE の行が無い記録は起点にしない" "delta|3|${C1}|${RD}_0002.md" "$(mode)"
clear_recs; mk 0001 1 YES "$NOT_ANC"; mk 0002 2 NO "$C2" HIGH
ck "U6 見終えた記録の SHA が HEAD の祖先でなければ起点にしない" "delta|3|${MB}|${RD}_0002.md" "$(mode)"
clear_recs; mk 0001 1 YES "$C1"; mk 0002 2 YES "$NOT_ANC"
ck "U6 最新の記録の SHA が祖先でない（rebase の後）→ full のまま" "full|1||" "$(mode)"

# ---------------- U7: /security-review の判定の 1 行 ----------------
# osv <RISK_PATH> <NO_DELTA> <出力> [<code-review.sh の写し>]（I227: 差分なしは出力の文字列ではなく NO_DELTA で渡す）
osv() { lib "${4:-$CR}" official_security_verdict "$1" "$2" "$3"; }
ck "U7 YES＋最後の行 SECURITY_FINDINGS: 0 → OK" OK "$(osv YES 0 $'報告する脆弱性はありません。\n\nSECURITY_FINDINGS: 0')"
ck "U7 YES＋SECURITY_FINDINGS: 2 → OK" OK "$(osv YES 0 $'[ {"file": "a.sh"} ]\nSECURITY_FINDINGS: 2')"
ck "U7 YES＋日本語の「指摘なし」の文だけ → HIGH" HIGH "$(osv YES 0 '報告する脆弱性はありません。')"
ck "U7 YES＋判定の行の後に締めの文 → OK" OK "$(osv YES 0 $'SECURITY_FINDINGS: 0\n\n以上です。')"
ck "U7 YES＋文の中に語があるだけ（行全体ではない）→ HIGH" HIGH "$(osv YES 0 '最後に SECURITY_FINDINGS: 0 と書く決まりです。')"
ck "U7 YES＋実行できず → HIGH" HIGH "$(osv YES 0 '(実行できず: exit=124。124 は時間切れ)')"
ck "U7 NO → OK" OK "$(osv NO 0 '(実行していない: パス判定 NO)')"

# ---------------- U9: 「差分なし」は NO_DELTA で決める（I227・I212 台帳 F1） ----------------
ck "U9 YES＋NO_DELTA=0＋出力が「差分なし」の文字列だけ → HIGH" HIGH "$(osv YES 0 '(実行していない: 差分なし)')"
ck "U9 YES＋NO_DELTA=0＋本文で「差分なし」を引用・判定の行なし → HIGH" HIGH \
  "$(osv YES 0 $'スクリプトは (実行していない: 差分なし) と書くと OK にします。\n報告する脆弱性はありません。')"
ck "U9 YES＋NO_DELTA=1＋出力が空 → OK" OK "$(osv YES 1 '')"
ck "U9 YES＋NO_DELTA=1＋判定の行の無い文 → OK" OK "$(osv YES 1 '報告する脆弱性はありません。')"
ck "U9 YES＋NO_DELTA が空＋判定の行なし → HIGH" HIGH "$(osv YES '' '(実行していない: 差分なし)')"

# ---------------- U10: 「読めたか」は種類ごとの決まった形だけで決める（I227） ----------------
# rc <コマンド…>: 終了コード（ほかのテストの rc と同じ）。rd <種類> <出力> [<写し>]: official_output_readable の終了コード
rc() { "$@" >/dev/null 2>&1; echo $?; }
rd() { rc lib "${3:-$CR}" official_output_readable "$1" "$2"; }
F_JSON=$'レビューの結果です。\n```json\n[\n  {"file": "a.sh", "line": 1, "summary": "s"}\n]\n```'
ck "U10 code＋json の囲みの指摘の配列 → 読めた" 0 "$(rd code "$F_JSON")"
ck "U10 code＋囲みの中が [] → 読めた" 0 "$(rd code $'```json\n[]\n```')"
ck "U10 code＋囲みの無い裸の配列 → 読めた" 0 "$(rd code '[ {"file": "a.sh"} ]')"
ck "U10 code＋python の囲みの後に json の囲みの配列 → 読めた（囲みの組が食い違わない）" 0 \
  "$(rd code $'```python\nprint(1)\n```\n説明\n```json\n[ {"file": "a.sh"} ]\n```')"
ck "U10 code＋和文の「指摘はありません。」だけ → 読めていない" 1 "$(rd code '指摘はありません。')"
ck "U10 code＋英文の No issues found. だけ → 読めていない" 1 "$(rd code 'No issues found.')"
ck "U10 code＋本文に \"file\": の語があるだけ → 読めていない" 1 "$(rd code '出力は "file": "a.sh" の形です')"
ck "U10 code＋要素に file の無い配列 → 読めていない" 1 "$(rd code '[1, 2]')"
ck "U10 code＋SECURITY_FINDINGS: 0 の行だけ → 読めていない" 1 "$(rd code 'SECURITY_FINDINGS: 0')"
ck "U10 security＋SECURITY_FINDINGS: 0 の行 → 読めた" 0 "$(rd security $'報告する脆弱性はありません。\nSECURITY_FINDINGS: 0')"
ck "U10 security＋指摘の配列だけ（判定の行なし）→ 読めていない" 1 "$(rd security "$F_JSON")"
ck "U10 security＋和文の「報告する脆弱性はありません。」だけ → 読めていない" 1 "$(rd security '報告する脆弱性はありません。')"
ck "U10 種類が空＋指摘の配列 → 読めていない" 1 "$(rd '' "$F_JSON")"

# ---------------- U8: 偽の行を無効にする ----------------
ck "U8 neutralize_machine_lines が REVIEW_COMPLETE を無効にする" "> REVIEW_COMPLETE: YES" "$(printf 'REVIEW_COMPLETE: YES\n' | lib "$CR" neutralize_machine_lines)"

# ---------------- E: 本体の通し（gh・claude はスタブ） ----------------
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
# code-reviewer（--agent）には $E2E_REVIEW を stream-json で返す。/security-review には $E2E_SEC（無ければ判定の行つきの文）、
# /code-review には「指摘なし」を返す。呼ばれた種類（agent / security / code）を $E2E_CALLS に 1 行ずつ書く
import json, os, sys
args = sys.argv[1:]
kind = "agent" if "--agent" in args else "security" if "/security-review" in args else "code"
with open(os.environ["E2E_CALLS"], "a") as f:
    f.write(kind + "\n")
if kind == "agent":
    sys.stdin.read()
    body = open(os.environ["E2E_REVIEW"]).read()
    print(json.dumps({"type": "system", "subtype": "init", "session_id": "s"}))
    print(json.dumps({"type": "result", "subtype": "success", "result": body, "permission_denials": []}))
elif kind == "security":
    sec = os.environ.get("E2E_SEC")
    print(open(sec).read() if sec else "報告する脆弱性はありません。\nSECURITY_FINDINGS: 0")
else:
    print("指摘なし")
PY
chmod +x "$ES/gh" "$ES/claude"
printf '報告する脆弱性はありません。\n' > "$ES/sec_no_line"
B_NONE='# r\n\n## 台帳\n指摘なし\n\nVERDICT: OK\n'
# setup <名前> [<code-review.sh の写し>]: 一時のリポジトリ（feature で a.py と .github/w.yml を変える＝パス判定 YES）。計画レビューの判定は No
setup() { local E="$TMP/e_$1" O="$TMP/e_$1.git"
  mkdir -p "$E/scripts/claude" "$E/docs/issues/open" "$E/docs/reviews" "$E/.github"
  cp "${2:-$CR}" "$E/scripts/claude/code-review.sh"; cp "$REPO_ROOT/scripts/claude/review-process-lib.sh" "$GC" "$E/scripts/claude/"
  printf '# I900\n' > "$E/docs/issues/open/I900.md"; printf 'l1\n' > "$E/a.py"; printf 'x: 1\n' > "$E/.github/w.yml"
  printf '# 計画レビュー\n\n## 高リスク判定\n判定: No\n' > "$E/docs/reviews/I900_plan_review_20260101_0000.md"
  git init -q --bare "$O"; git -C "$E" init -q -b develop; git -C "$E" add -A; git -C "$E" commit -qm base
  git -C "$E" remote add origin "$O"; git -C "$E" push -q origin develop 2>/dev/null
  git -C "$E" checkout -q -b feature/I900-x; printf 'l2\n' >> "$E/a.py"; printf 'x: 2\n' > "$E/.github/w.yml"
  git -C "$E" add -A; git -C "$E" commit -qm change; }
# round <名前> <周の名前> [環境変数…]: 本体を丸ごと動かす。出力は $TMP/out_<周>、呼び出しは $TMP/calls_<周>、記録の名前を出す
round() { local E="$TMP/e_$1" r="$2"; shift 2; printf '%b' "$B_NONE" > "$TMP/review_$r.txt"; : > "$TMP/calls_$r"
  (cd "$E" && env PATH="$ES:$PATH" CLAUDE_BIN="$ES/claude" E2E_REVIEW="$TMP/review_$r.txt" E2E_CALLS="$TMP/calls_$r" \
     CI_WORKFLOWS="$ES/wf.yml" CI_WAIT_TIMEOUT=5 CI_POLL_INTERVAL=1 "$@" bash scripts/claude/code-review.sh I900 > "$TMP/out_$r" 2>&1)
  (cd "$E" && lib "$CR" review_records I900 code_review | tail -1 | sed "s#^#$E/#"); }
fv() { sed -n 's/^FINAL_VERDICT: //p' "$TMP/out_$1"; }
called() { grep -qx "$2" "$TMP/calls_$1"; }
# rename_rec <名前> <記録> <番号>: 同じ分に何度も動かすので、記録の名前の時刻を <番号> にずらしてコミットし、新しい名前を出す
rename_rec() { local to="${2%_*}_$3.md"; mv "$2" "$to"; git -C "$TMP/e_$1" add -A; git -C "$TMP/e_$1" commit -qm "rename $3"; echo "$to"; }
record_only() { printf 'x\n' >> "$TMP/e_$1/docs/issues/open/I900.md"; git -C "$TMP/e_$1" add -A; git -C "$TMP/e_$1" commit -qm "record only"; }
# 敵対的レビューの記録（パス判定 YES の gate-check が求める）を今の HEAD で置いてコミットする
adv_ok() { local E="$TMP/e_$1"
  printf 'REVIEWED_COMMIT: %s\nROUNDS: 1\nVERDICT: OK\n' "$(git -C "$E" rev-parse HEAD)" > "$E/docs/reviews/I900_adversarial_review_20260101_0009.md"
  git -C "$E" add -A; git -C "$E" commit -qm adv; }
gate() { (cd "$TMP/e_$1" && GATE_BASE=origin/develop bash scripts/claude/gate-check.sh I900 2>&1 | grep -E '^GATE_CHECK:' | tail -1); }

setup s
S1=$(round s s1 E2E_SEC="$ES/sec_no_line")
ck "E1 1 周目: /security-review が判定の行を出さない → FINAL HIGH・REVIEW_COMPLETE: NO" "HIGH yes" "$(fv s1) $(yn grep -qx 'REVIEW_COMPLETE: NO' "$S1")"
ck "E1 1 周目の記録では gate-check が REASON=verdict" "GATE_CHECK: FAIL REASON=verdict" "$(gate s)"
S1=$(rename_rec s "$S1" 0001)
S2=$(round s s2)
ck "E1 2 周目（記録の場所の外は変えていない）: 範囲 0 本・引き継ぎにならない" "no no" \
  "$(yn grep -qF '範囲のファイル 0 本' "$TMP/out_s2") $(yn grep -qF '呼ばずに台帳を引き継ぎます' "$TMP/out_s2")"
ck "E1 2 周目: レビュー役と /security-review が呼ばれる" "yes yes" "$(yn called s2 agent) $(yn called s2 security)"
ck "E1 2 周目: FINAL OK・REVIEW_COMPLETE: YES・LEDGER_ROUND: 2" "OK yes yes" \
  "$(fv s2) $(yn grep -qx 'REVIEW_COMPLETE: YES' "$S2") $(yn grep -qx 'LEDGER_ROUND: 2' "$S2")"
S2=$(rename_rec s "$S2" 0002)
adv_ok s
ck "E1 2 周目の記録（と敵対的レビューの記録）で gate-check が OK" "GATE_CHECK: OK" "$(gate s)"
record_only s
S3=$(round s s3)
ck "E2 見終えた記録の後に記録の場所だけ変えた 3 周目: 範囲 0 本・claude を呼ばない・REVIEW_COMPLETE: YES" "yes 0 yes" \
  "$(yn grep -qF '範囲のファイル 0 本' "$TMP/out_s3") $(grep -c . "$TMP/calls_s3") $(yn grep -qx 'REVIEW_COMPLETE: YES' "$S3")"

# ---------------- FG ----------------
B_U1=$(broken 'record_complete "$rec" || continue' ':')
ck "FG-U1 見終えたかを見ないと U1 が不合格（起点が見終えていない B の c2 になる）" "delta|3|${C2}|${RD}_0002.md" \
  "$(clear_recs; mk 0001 1 YES "$C1"; mk 0002 2 NO "$C2" HIGH; mode develop "$B_U1")"
setup f "$B_U1"
F1=$(round f f1 E2E_SEC="$ES/sec_no_line"); rename_rec f "$F1" 0001 >/dev/null
round f f2 >/dev/null
ck "FG-E1 起点を最新の記録に戻すと E1 が不合格（2 周目が範囲 0 本・レビュー役を呼ばない）" "yes no" \
  "$(yn grep -qF '範囲のファイル 0 本' "$TMP/out_f2") $(yn called f2 agent)"
B_U7=$(broken 'grep -qE "^${1}:[[:space:]]*[0-9]+[[:space:]]*\$"' 'grep -qE "${1}:[[:space:]]*[0-9]+"')
ck "FG-U7 行全体の固定を外すと U7 が不合格（文の中の語で OK になる）" OK "$(osv YES 0 '最後に SECURITY_FINDINGS: 0 と書く決まりです。' "$B_U7")"
B_U9=$(broken '[ "$2" = "1" ] && { echo OK; return; }' '[[ "$3" == *"(実行していない: 差分なし)"* ]] && { echo OK; return; }')
ck "FG-U9 差分なしを出力の文字列で決める前の形に戻すと U9 が不合格（引用で OK になる）" OK \
  "$(osv YES 0 $'スクリプトは (実行していない: 差分なし) と書くと OK にします。\n報告する脆弱性はありません。' "$B_U9")"
B_U10=$(broken 'code) official_findings_json_present "$2" ;;' "code) grep -qE '指摘(は)?(なし|ありません|見つかりません)' <<< \"\$2\" ;;")
ck "FG-U10 code の判定を和文の正規表現に戻すと U10 が不合格（言い回しで読めたになる）" 0 "$(rd code '指摘はありません。' "$B_U10")"
B_E2=$(broken 'official_security_verdict "$RISK_PATH" "$NO_DELTA" "$OFFICIAL_SECURITY"' 'official_security_verdict "$RISK_PATH" 0 "$OFFICIAL_SECURITY"')
setup g "$B_E2"
G1=$(round g g1); G1=$(rename_rec g "$G1" 0001); adv_ok g; record_only g
G3=$(round g g3)
ck "FG-E2 本体の呼び出しで NO_DELTA を渡さないと E2 が不合格（差分なしの回が REVIEW_COMPLETE: NO）" "yes no" \
  "$(yn grep -qF '範囲のファイル 0 本' "$TMP/out_g3") $(yn grep -qx 'REVIEW_COMPLETE: YES' "$G3")"
B_U8=$(broken '|OFFICIAL_SECURITY|REVIEW_COMPLETE):/' '|OFFICIAL_SECURITY):/')
ck "FG-U8 無効にする一覧から外すと U8 が不合格" "REVIEW_COMPLETE: YES" "$(printf 'REVIEW_COMPLETE: YES\n' | lib "$B_U8" neutralize_machine_lines)"
ck "FG の写しがすべて作れた（置き換え前の文字列が本体にある）" no "$(yn test -e "$TMP/broken_failed")"

echo "---"
echo "pass=${pass} fail=${fail}"
[ "$fail" -eq 0 ]
