#!/usr/bin/env bash
# I210（plan_I210.md 4.8・auto_test TC-01b）: pipefail のシェルスクリプトに「! <コマンド> | grep -q …」の形が無いことを確かめる。
#   pipefail の下では grep -q が先に終わると前のコマンドが SIGPIPE（141）で終わり、パイプ全体が 0 以外になって、
#   ! が「見つからなかった」に反転する（I195 台帳 F3・#352）。粗い文字列の規則で、普通の書き方の事故を止める
#   （行をまたぐ書き方・grep -q 以外の先に終わるコマンド・意図した回避は対象外）。除外の印は作らない（抜け道にしない）。
# 実行: bash scripts/claude/tests/test_pipefail_negated_grep.sh
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

# negated_grep <ファイル…>: pipefail を含むファイルの、コメントでない行で当たる行を「パス:行:中身」で出して 1。無ければ 0。
# NEGATED_GREP_COUNT=1 のときは、見た pipefail のファイルの数を最後に「checked=<数>」で標準エラーに出す
negated_grep() {
  python3 -I - "$@" <<'PY'
import os, re, sys
PF = re.compile(r"^\s*set\s+(?:[^#\n]*\s)?-[A-Za-z]*o\s+pipefail\b", re.M)
BAD = re.compile(r"(?:^|[\s;&({])!\s.*[^|]\|\s*grep\s(?:[^|]*\s)?(?:-[A-Za-z]*q[A-Za-z]*|--quiet|--silent)(?:\s|$)")
bad = checked = 0
for path in sys.argv[1:]:
    s = open(path, encoding="utf-8", errors="replace").read()
    if not PF.search(s):
        continue
    checked += 1
    for i, line in enumerate(s.split("\n"), 1):
        if line.lstrip().startswith("#"):
            continue
        if BAD.search(line):
            print(f"{path}:{i}:{line}")
            bad = 1
if os.environ.get("NEGATED_GREP_COUNT") == "1":
    print(f"checked={checked}", file=sys.stderr)
sys.exit(bad)
PY
}
rc() { "$@" >/dev/null 2>&1; echo $?; }
# fx <名前> <set の行> <本文の行…>: 写しを作る。本文の NOT は ! に置き換える（このファイルの行そのものが規則に当たらないように）
fx() { local f="$TMP/$1.sh"; shift; printf '#!/usr/bin/env bash\n' > "$f"
  [ -n "$1" ] && printf '%s\n' "$1" >> "$f"; shift
  printf '%s\n' "$@" | sed 's/NOT/!/g' >> "$f"; echo "$f"; }

mapfile -t FILES < <(find scripts/claude -type f -name '*.sh' | sort)
# G1（AC7）: 実物に当たりが無い（当たれば、その行を出す）。G2 の数も同じ 1 回の走査で取る
NEGATED_GREP_COUNT=1 negated_grep "${FILES[@]}" 2> "$TMP/g1.err"; G1=$?
ck "G1 scripts/claude の pipefail のスクリプトに、否定とパイプの grep -q の形が無い" 0 "$G1"
# G2: 対象が空のまま合格しない
CHECKED=$(sed -n 's/^checked=//p' "$TMP/g1.err")
ck "G2 見た pipefail のスクリプトが 20 本以上" yes "$([ "${CHECKED:-0}" -ge 20 ] && echo yes || echo no)"

PF='set -uo pipefail'
ck "FG-G3a 前の check-frontend-evidence.sh の形に当たる" 1 \
  "$(rc negated_grep "$(fx g3a "$PF" "if NOT printf '%s\n' \"\$X\" | grep -q '^a/'; then :; fi")")"
ck "FG-G3b 引用符の中に | がある形（前の test_i193 の形）に当たる" 1 \
  "$(rc negated_grep "$(fx g3b "$PF" "f() { NOT grep -hE 'a|b' \"\$@\" | grep -qvF 'c'; }")")"
ck "FG-G3c 2 段のパイプ（前の d3_bl の形）に当たる" 1 \
  "$(rc negated_grep "$(fx g3c "$PF" "d() { NOT cat x | grep -E '^- F' | grep -qvE \"\$Y\"; }")")"
ck "FG-G3d && の後（前の test_posttooluse_check.sh の形）に当たる" 1 \
  "$(rc negated_grep "$(fx g3d "$PF" "if [ -n \"\$3\" ] && NOT printf '%s' \"\$E\" | grep -q \"\$3\"; then :; fi")")"
ck "FG-G3e set -o pipefail と --quiet に当たる" 1 \
  "$(rc negated_grep "$(fx g3e1 'set -o pipefail' 'NOT a | grep --quiet b')")"
ck "FG-G3e set -euo pipefail と grep -E -q に当たる" 1 \
  "$(rc negated_grep "$(fx g3e2 'set -euo pipefail' 'NOT a | grep -E -q b')")"
ck "G4 pipefail の無いスクリプトには当たらない（反転しない）" 0 \
  "$(rc negated_grep "$(fx g4 '' "if NOT printf '%s\n' \"\$X\" | grep -q '^a/'; then :; fi")")"
ck "G5 コメントの行・直した形には当たらない" 0 \
  "$(rc negated_grep "$(fx g5 "$PF" '# NOT a | grep -q b' \
     "if [[ \$'\\n'\"\$X\" != *\$'\\n'a/* ]]; then :; fi" \
     "awk '/a/ { f = 1 } END { exit f }' x" \
     'NOT grep -q a f')")"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
