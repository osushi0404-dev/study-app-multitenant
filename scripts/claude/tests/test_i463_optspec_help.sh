#!/usr/bin/env bash
# I463（必ず確かめる項目 V1）: 見張りの値を取る文字の表（_OPTSPEC・_OPTSPEC_OPTIONAL）が、手元のコマンドの --help と食い違わないかを
# 決定論で確かめる。値を取らない文字を「値あり」と表に入れると、その文字の後ろのまとめ書き（-Xc'DELETE …' の c など）を読まなくなり
# 止める側が減るので、それを失敗にする（表 ⊆ --help）。--help にあって表に無い文字は止める側に倒れる読み違いなので、警告だけ出す
# （手元と CI で版が違うと増減するため）。psql・python・Django の shell は手元に --help の形がそろわないので対象外（TC-09・TC-10 で見る）。
# 実行: bash scripts/claude/tests/test_i463_optspec_help.sh
# ケースは docs/tests/open/I463_auto_test.md の TC-13（13a・FG-13）と 1 対 1。0=全 PASS / 1=FAIL あり。
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1
GUARD=scripts/claude/hooks/pretooluse_guard.py
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

# check <見張り>: 表の各コマンドの --help と比べ、表にあって --help で値を取らない文字があれば exit 1
check() {
  python3 -I - "$1" <<'PY'
import importlib.util, re, subprocess, sys
spec = importlib.util.spec_from_file_location("guard", sys.argv[1])
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

def help_opts(cmd):
    """--help の各行の先頭の短いオプションのうち、値を取る文字と、くっつけたときだけ値を取る文字。"""
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LC_ALL": "C"}   # 訳された --help で形が変わらないように
    out = subprocess.run([cmd, "--help"], capture_output=True, text=True, timeout=30, env=env).stdout
    takes, optional = set(), set()
    for line in out.splitlines():
        m = re.match(r"^\s{1,8}(-[A-Za-z]\S*(?: \S+)*?(?:, --\S+(?: \S+)?)?)(?:\s{2,}|$)", line)
        if not m:
            continue
        s = m.group(1)
        if s[2:3] == "[" or "[=" in s:
            optional.add(s[1])
        elif "=" in s or "<" in s or re.match(r"-\w [A-Za-z]", s):
            takes.add(s[1])
    return takes, optional

bad = 0
for cmd in ("sed", "grep", "cp", "mv", "ln", "install", "su", "flock", "script"):
    takes, optional = help_opts(cmd)   # コマンドが無ければ例外で不合格（飛ばさない・I204。どれも OS の基本の道具）
    if not takes:
        print(f"NG {cmd}: --help から値を取る文字を 1 つも読めない（--help の形が変わった）")
        bad += 1
        continue
    table = set(g._OPTSPEC[cmd][0])
    table_opt = set(g._OPTSPEC_OPTIONAL.get(cmd, ""))
    extra = (table - takes) | (table_opt - optional - takes)
    if extra:
        print(f"NG {cmd}: 表にあるが --help では値を取らない文字 {''.join(sorted(extra))}")
        bad += 1
    missing = (takes - table) | (optional - table_opt)
    if missing:
        print(f"WARN {cmd}: --help では値を取るが表に無い文字 {''.join(sorted(missing))}（止める側に倒れる読み違い）")
sys.exit(1 if bad else 0)
PY
}

# 13a: 今の表は --help と食い違わない
check "$GUARD"; ck 13a 0 "$?"

# FG-13（失敗の注入）: sed の表に値を取らない文字 n を足した写しでは失敗する
python3 - "$GUARD" "$TMP/g_13.py" <<'PY'
import sys
src, dst = sys.argv[1:]
s = open(src, encoding="utf-8").read()
old = '"sed": ("efl",'
if s.count(old) != 1:
    sys.exit(3)
open(dst, "w", encoding="utf-8").write(s.replace(old, '"sed": ("efln",'))
PY
if [ -f "$TMP/g_13.py" ]; then
  check "$TMP/g_13.py"; ck FG-13 1 "$?"
else
  ck "FG-13 置き換え" ok NOPATCH
fi

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
