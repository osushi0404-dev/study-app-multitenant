#!/usr/bin/env bash
# I463: 止めるべき形の一覧（guard_must_stop_cases.txt）を、変更前と作業ツリーの見張りの両方に流して比べる
# （guard_corpus_diff.py --cases）。作業ツリーで通す形・変更前より弱い判定・異常終了が 1 件でもあれば失敗する。
# 作業記録を使わないので CI（run-all）でも流れる。見張りを直したら流す（docs/runbooks/danger-ops.md）。
# 実行: bash scripts/claude/tests/test_guard_must_stop_cases.sh
# ケースは docs/tests/open/I463_auto_test.md の TC-09（09a〜09c）と 1 対 1。0=全 PASS / 1=FAIL あり。
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1
DIFF=scripts/claude/tests/guard_corpus_diff.py
CASES=scripts/claude/tests/guard_must_stop_cases.txt
GUARD=scripts/claude/hooks/pretooluse_guard.py
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
rc() { python3 "$DIFF" "$@"; echo "$?" >"$TMP/rc"; }   # 出力はそのまま見せ、終了コードを $TMP/rc に残す
# 失敗の注入: 元のファイルの old（ちょうど 1 回だけあること）を new に置き換えた写しを作る（test_i463_guard_optspec.sh と同じ）
patch() {  # patch <元> <出力> <old> <new>
  python3 - "$@" <<'PY'
import sys
src, dst, old, new = sys.argv[1:]
s = open(src, encoding="utf-8").read()
if s.count(old) != 1:
    sys.exit(3)
open(dst, "w", encoding="utf-8").write(s.replace(old, new))
PY
}

# 09a: 一覧のすべてが作業ツリーで確認か停止・変更前より弱い判定 0 件
rc --cases "$CASES"
ck 09a 0 "$(cat "$TMP/rc")"

# 09b（失敗の注入）: 破壊的 SQL の停止を外した見張りの写しでは、変更前より弱い判定を出して失敗する
# （確かめたいのは失敗することだけなので、一覧のうち DELETE の行だけを流す）
grep 'DELETE' "$CASES" >"$TMP/cases_09b.txt"
if patch "$GUARD" "$TMP/g_09b.py" 'r.append("destructive SQL requires DANGER_OK=1")' 'pass'; then
  rc --cases "$TMP/cases_09b.txt" --guard "$TMP/g_09b.py"
  ck 09b 1 "$(cat "$TMP/rc")"
else
  ck "09b 置き換え" ok NOPATCH
fi

# 09c（失敗の注入）: 通す形（echo hi）を一覧に入れると、作業ツリーで通す形があるとして失敗する
echo 'echo hi' >"$TMP/cases_09c.txt"
rc --cases "$TMP/cases_09c.txt"
ck 09c 1 "$(cat "$TMP/rc")"

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
