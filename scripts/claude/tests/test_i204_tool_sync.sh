#!/usr/bin/env bash
# I204: ハーネスのテストが頼る道具の一覧（required-tools.txt）・その確認（check-tools.sh と run-all.sh の冒頭）・
# CI の Harness Tests との食い違い・「道具が無ければ SKIP」の分岐が無いことを確かめる。
# 項目は docs/tests/open/I204_auto_test.md の TC-01 の表（L・R・P・C・S）。否定の項目には写しで失敗注入（FG）を付ける。
# 実行: bash scripts/claude/tests/test_i204_tool_sync.sh
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)" || exit 1
cd "$REPO_ROOT" || exit 1
CHECK="scripts/claude/tests/check-tools.sh"
LIST="scripts/claude/tests/required-tools.txt"
CI=".github/workflows/ci.yml"
LIFECYCLE="scripts/claude/tests/test_review_commit_lifecycle.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=[%s] got=[%s]\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
# $1 の文字列に $2 があれば yes
has() { if grep -qF -- "$2" <<< "$1"; then echo yes; else echo no; fi; }
oks() { grep -c '^OK: ' <<< "$1"; }
# 写しの一覧を作る（$1=名前・残りの引数=行）
mklist() { local f="$TMP/$1.txt"; shift; printf '%s\n' "$@" > "$f"; echo "$f"; }
# 一覧の名前の列（コメント・空行を除く）
names() { local l; while IFS= read -r l; do [[ -z "$l" || "$l" == \#* ]] && continue; printf '%s\n' "${l%% | *}"; done < "$1"; }

# ---------- L: 一覧と check-tools.sh ----------
SPECS="$(bash "$CHECK" --pip-specs)"; rc=$?
ck "L1 実物の一覧の形が正しい（--pip-specs が exit 0）" 0 "$rc"
ck "L1 道具は 6 つ" "$(printf '%s\n' python3 PyYAML git 'docker compose' pre-commit shellcheck)" "$(names "$LIST")"

OUT="$(bash "$CHECK" 2>&1)"; rc=$?
ck "L2 実物の一覧で全部そろう（一覧の行の数だけ OK）" "0 $(names "$LIST" | wc -l)" "$rc $(oks "$OUT")"

# 本物の道具の確認（pre-commit・docker）は L2 の 1 回だけにする。ほかの行も確かめることは bash の行で見る
L3="$(mklist l3 'bash | bash --version | - | - | -' 'no-such-tool-i204 | no-such-tool-i204 --version | - | - | 入れ方の例')"
OUT="$(bash "$CHECK" "$L3" 2>&1)"; rc=$?
ck "FG-L3 通らない道具は exit 1・名前と入れ方・ほかは OK" "1 yes yes 1" \
   "$rc $(has "$OUT" '⛔ 足りない道具: no-such-tool-i204') $(has "$OUT" '入れ方: 入れ方の例') $(oks "$OUT")"

L4="$(mklist l4 'python3 | python3 --version | 99.0 | - | 入れ方の例')"
OUT="$(bash "$CHECK" "$L4" 2>&1)"; rc=$?
ck "FG-L4 下限より古い python3 は exit 1" "1 yes" "$rc $(has "$OUT" '⛔ 版が古い道具: python3')"

L5="$(mklist l5 'nover | echo none | 1.0 | - | 入れ方の例')"
OUT="$(bash "$CHECK" "$L5" 2>&1)"; rc=$?
ck "FG-L5 版を読めない道具は exit 1" "1 yes" "$rc $(has "$OUT" '⛔ 版を読めない道具: nover')"

for bad in 'a | true | - | -' 'a | true | abc | - | x' ' | true | - | - | x'; do
  L6="$(mklist l6 "$bad")"
  OUT="$(bash "$CHECK" "$L6" 2>&1)"; rc=$?
  ck "FG-L6a 形の崩れた行は exit 2（${bad}）" "2 yes" "$rc $(has "$OUT" '⛔ 一覧の行の形が違います')"
done

for spec in '--extra-index-url=http://example.invalid' 'PyYAML @ https://example.invalid/x.whl' '-e git+https://example.invalid/x' 'PyYAML>=6.0 --index-url=http://example.invalid'; do
  L6B="$(mklist l6b "x | true | - | ${spec} | x")"
  OUT="$(bash "$CHECK" --pip-specs "$L6B" 2>/dev/null)"; rc=$?
  ck "FG-L6b pip の指定は通さない（${spec}）" "2 []" "$rc [$OUT]"
done

ck "L7 --pip-specs は一覧の pip の列だけ" "$(printf '%s\n' 'PyYAML>=6.0' 'pre-commit>=4.0')" "$SPECS"

# ---------- R: run-all.sh の冒頭 ----------
R="$TMP/repo"
mkdir -p "$R/scripts/claude/tests" "$R/t"
git -C "$R" init -q
cp scripts/claude/tests/run-all.sh "$CHECK" "$R/scripts/claude/tests/"
printf '#!/usr/bin/env bash\ntouch "%s"\n' "$TMP/mark" > "$R/t/test_mark.sh"
printf '%s\n' 'no-such-tool-i204 | no-such-tool-i204 --version | - | - | 入れ方の例' > "$R/scripts/claude/tests/required-tools.txt"
OUT="$(cd "$R" && TEST_DIR=t bash scripts/claude/tests/run-all.sh 2>&1)"; rc=$?
MARK=no; [ -e "$TMP/mark" ] && MARK=yes
ck "FG-R1 道具が足りなければテストを流さず exit 1" "1 no yes yes" \
   "$rc $MARK $(has "$OUT" '⛔ 足りない道具: no-such-tool-i204') $(has "$OUT" 'テストは流していません')"

printf '%s\n' 'bash | bash --version | - | - | -' > "$R/scripts/claude/tests/required-tools.txt"
OUT="$(cd "$R" && TEST_DIR=t bash scripts/claude/tests/run-all.sh 2>&1)"; rc=$?
MARK=no; [ -e "$TMP/mark" ] && MARK=yes
ck "R2 道具がそろえばテストを流す" "0 yes" "$rc $MARK"

# ---------- P: TC-C1 は pre-commit が使えない・対象外でも合格にしない ----------
mkdir -p "$TMP/p1" "$TMP/p2"
printf '#!/usr/bin/env bash\nexit 127\n' > "$TMP/p1/pre-commit"
printf '#!/usr/bin/env bash\necho "shellcheck...........(no files to check)Skipped"\nexit 0\n' > "$TMP/p2/pre-commit"
chmod +x "$TMP/p1/pre-commit" "$TMP/p2/pre-commit"
OUT="$(PATH="$TMP/p1:$PATH" bash "$LIFECYCLE" 2>&1)"; rc=$?
NOSKIP=yes; grep -q '^SKIP' <<< "$OUT" && NOSKIP=no
ck "FG-P1 pre-commit が無いと TC-C1 は不合格（SKIP しない）" "no yes yes" \
   "$([ "$rc" -eq 0 ] && echo yes || echo no) $(has "$OUT" 'FAIL TC-C1-shellcheck') $NOSKIP"
OUT="$(PATH="$TMP/p2:$PATH" bash "$LIFECYCLE" 2>&1)"; rc=$?
ck "FG-P2 Skipped（対象外）でも TC-C1 は不合格" "no yes" \
   "$([ "$rc" -eq 0 ] && echo yes || echo no) $(has "$OUT" 'FAIL TC-C1-shellcheck')"

# ---------- C: CI の Harness Tests と一覧の食い違い ----------
# $1=ci.yml $2=一覧。食い違いを出して 1、無ければ 0
ci_check() {
  python3 -I - "$1" "$2" <<'PY'
import re, sys, yaml
ci_path, list_path = sys.argv[1], sys.argv[2]
py_min = None
for line in open(list_path, encoding="utf-8"):
    cols = [c.strip() for c in line.strip().split(" | ")]
    if cols[0] == "python3" and len(cols) == 5:
        py_min = cols[2]
errs = []
job = (yaml.safe_load(open(ci_path, encoding="utf-8")).get("jobs") or {}).get("harness-tests") or {}
steps = job.get("steps") or []
if not steps:
    errs.append("Harness Tests（harness-tests）のジョブの step がありません")
allowed = {"actions/checkout", "actions/setup-python"}
for s in steps:
    uses = s.get("uses")
    if uses and uses.split("@")[0] not in allowed:
        errs.append(f"一覧を通らない uses: {uses}")
    pv = str((s.get("with") or {}).get("python-version"))
    if uses and uses.startswith("actions/setup-python") and pv != py_min:
        errs.append(f"python-version {pv} が一覧の python3 の下限 {py_min} と違う")
INSTALL = re.compile(r"\b(?:pip3?|pipx|apt|apt-get|brew|npm|conda)\s+install\b")
runs = [s.get("run") or "" for s in steps]
installs = [r for r in runs if INSTALL.search(r)]
n = sum(len(INSTALL.findall(r)) for r in runs)
if n != 1 or "check-tools.sh --pip-specs" not in installs[0] or "pip install -r" not in installs[0]:
    errs.append(f"install は一覧を読む 1 つ（check-tools.sh --pip-specs と pip install -r）だけにする（今 {n} 個）")
if not steps or (steps[-1].get("run") or "").strip() != "bash scripts/claude/tests/run-all.sh":
    errs.append("最後の step が bash scripts/claude/tests/run-all.sh ではない")
for e in errs:
    print(e)
sys.exit(1 if errs else 0)
PY
}
# 写しの ci.yml を作る（$1=種類 $2=出力）
ci_mut() {
  python3 -I - "$CI" "$2" "$1" <<'PY'
import sys, yaml
src, dst, kind = sys.argv[1:4]
d = yaml.safe_load(open(src, encoding="utf-8"))
steps = d["jobs"]["harness-tests"]["steps"]
if kind == "py312":
    for s in steps:
        if (s.get("uses") or "").startswith("actions/setup-python"):
            s["with"]["python-version"] = "3.12"
elif kind == "extra_pip":
    steps.insert(-1, {"name": "extra", "run": "pip install foo"})
elif kind == "extra_uses":
    steps.insert(-1, {"uses": "some/setup-tool@v1"})
elif kind == "old_install":
    for s in steps:
        if "check-tools.sh --pip-specs" in (s.get("run") or ""):
            s["run"] = "pip install pyyaml"
yaml.safe_dump(d, open(dst, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
PY
}
OUT="$(ci_check "$CI" "$LIST")"; rc=$?
ck "C1 CI の Harness Tests は一覧に従う" "0 []" "$rc [$OUT]"
for kind in py312 extra_pip extra_uses old_install; do
  ci_mut "$kind" "$TMP/ci_$kind.yml"
  ci_check "$TMP/ci_$kind.yml" "$LIST" >/dev/null; rc=$?
  ck "FG-C 写しの ci.yml（${kind}）は食い違いで不合格" 1 "$rc"
done

# ---------- S: 「道具が無ければ SKIP」の分岐の規則 ----------
# 道具を探す行から 3 行以内に SKIP があれば当たり。規則の文字列は分けてつなぐ（このファイル自身が当たらないように）
skip_rule() {
  python3 -I - "$1" <<'PY'
import glob, re, sys
d = sys.argv[1]
FIND = re.compile(r"comm" r"and -v|shutil\.wh" r"ich|type -P")
MARK = "SK" "IP"
files = sorted(glob.glob(d + "/*.sh") + glob.glob(d + "/*.py"))
hits = []
for p in files:
    lines = open(p, encoding="utf-8").read().split("\n")
    for i, l in enumerate(lines):
        if FIND.search(l) and any(MARK in x for x in lines[i:i + 4]):
            hits.append(f"{p}:{i + 1}: {l.strip()}")
for h in hits:
    print(h)
print(f"files={len(files)}")
sys.exit(1 if hits else 0)
PY
}
OUT="$(skip_rule scripts/claude/tests)"; rc=$?
NF="${OUT##*files=}"
ck "S1 実物に「道具が無ければ SKIP」の分岐が無い" 0 "$rc"
[ "$rc" -eq 0 ] || printf '%s\n' "$OUT"
ck "S1 見たファイルが 40 本以上" yes "$([ "$NF" -ge 40 ] && echo yes || echo no)"

# 写し: CMDV・WHICH を置き換えて前の形を作る
CV="comm""and -v"; WH="shutil.wh""ich"
sample() { local dir="$TMP/s_$1"; mkdir -p "$dir"; shift; printf '%s\n' "$@" | sed -e "s/CMDV/$CV/g" -e "s/WHICH/$WH/g" > "$dir/x.sh"; echo "$dir"; }
D="$(sample c1 'if CMDV shellcheck >/dev/null 2>&1; then' '  ck_true TC-C1 shellcheck a.sh' 'else' "  printf 'SKIP TC-C1 (未インストール)\\n'" 'fi')"
skip_rule "$D" >/dev/null; ck "FG-S2 前の TC-C1 の形は当たる" 1 "$?"
D="$(sample compose 'if ! CMDV docker >/dev/null 2>&1; then' '  echo "SKIP: docker compose 未使用環境"' '  exit 0' 'fi')"
skip_rule "$D" >/dev/null; ck "FG-S2 前の test_compose_ports.sh の形は当たる" 1 "$?"
D="$(sample oracle '    if not WHICH("bash"):' '        print("SKIP: bash がありません")' '        return 0')"
skip_rule "$D" >/dev/null; ck "FG-S2 前の guard_bash_oracle.py の形は当たる" 1 "$?"
PAD=(); for _ in {1..9}; do PAD+=(''); done   # 道具を探す行と SKIP を 3 行より離す
# shellcheck disable=SC2016  # 写しの行そのもの（$(…) を展開しない）
D="$(sample ok 'BASH_BIN="$(CMDV bash)"' "${PAD[@]}" 'echo SKIP''echo "SKIP NOREG（origin/develop を取得できない環境）"')"
skip_rule "$D" >/dev/null; ck "S3 離れた SKIP・環境の状態の SKIP は当たらない" 0 "$?"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
