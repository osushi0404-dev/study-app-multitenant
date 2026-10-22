#!/usr/bin/env bash
# I182（plan_I182.md 4-2）: 見張りの判定中の例外・メモリ超過が素通し（exit 0/2 以外）にならず、確認になることを、
# 見張りの複製に失敗を注入して決定論検証する（本物は書き換えない）。時間切れ・異常終了の停止は公式のフック設定
# （"timeout"・"onFailure": "block"）の役目なので、ここでは扱わない（設定は test_settings_permissions.sh の S13）。
# 実行: bash scripts/claude/tests/test_i182_guard_failsafe.sh
set -uo pipefail
unset CLAUDE_PROJECT_DIR
REPO_ROOT="$(git rev-parse --show-toplevel)"
GUARD="$REPO_ROOT/scripts/claude/hooks/pretooluse_guard.py"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -r "$TMP"' EXIT

bash_json() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1"; }
edit_json() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Edit","tool_input":{"file_path":sys.argv[1],"old_string":"a","new_string":"b"}}))' "$1"; }
# 判定: 0＝素通し / 2＝停止 / ASK＝確認 / それ以外は終了コード。理由（ask の文言）は $TMP/last_out に残す
run() { local out code; out=$(printf '%s' "$2" | python3 "$1" 2>/dev/null); code=$?; printf '%s' "$out" > "$TMP/last_out"
        if [ "$code" = "0" ] && printf '%s' "$out" | grep -q '"permissionDecision":[[:space:]]*"ask"'; then echo "ASK"; else echo "$code"; fi; }
# 複製を作り、関数の定義行の直後に 1 行差し込む（差し込めなければ "NOINJECT"＝その TC を不合格にする）
inject() {  # inject <名前> <関数の定義行> <差し込む行>
  python3 - "$GUARD" "$TMP/$1.py" "$2" "$3" <<'PY'
import sys
src, dst, head, line = sys.argv[1:]
s = open(src, encoding="utf-8").read()
if s.count(head + "\n") != 1:
    sys.exit(3)
s = s.replace(head + "\n", head + "\n    " + line + "\n")
open(dst, "w", encoding="utf-8").write(s)
PY
}

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
# 確認の理由（JSON は \uXXXX で書かれるので読み解いてから探す）に $1 があるか
has() { python3 - "$TMP/last_out" "$1" <<'PY'
import json, sys
try:
    r = json.load(open(sys.argv[1], encoding="utf-8"))["hookSpecificOutput"]["permissionDecisionReason"]
except Exception:
    r = ""
print("yes" if sys.argv[2] in r else "no")
PY
}

inject f1 "def main():" 'raise RuntimeError("i182")' || echo "NOINJECT f1"
ck "F1 main の例外は確認" ASK "$(run "$TMP/f1.py" "$(bash_json ls)")"
ck "F1 理由に型名がある" yes "$(has RuntimeError)"
ck "F1 理由に例外のメッセージ（i182）が無い" no "$(has i182)"

inject f3 "def main():" 'bytearray(1024 ** 3)' || echo "NOINJECT f3"
ck "F3 メモリ超過（1GB の確保）は確認" ASK "$(run "$TMP/f3.py" "$(bash_json ls)")"
ck "F3 理由にメモリの上限" yes "$(has 'メモリの上限')"

inject f4 "def _edit_path(data: dict) -> str:" 'raise ValueError("i182")' || echo "NOINJECT f4"
ck "F4 Edit の分岐の例外は確認" ASK "$(run "$TMP/f4.py" "$(edit_json docs/x.md)")"
ck "F4 理由に型名がある" yes "$(has ValueError)"

inject f5 "def _danger_reasons(cmd: str, pcmd: str) -> list:" 'raise KeyError("i182")' || echo "NOINJECT f5"
ck "F5 今まで包まれていなかった判定の例外は確認" ASK "$(run "$TMP/f5.py" "$(bash_json ls)")"

ck "F6 本物: ls は素通し" 0 "$(run "$GUARD" "$(bash_json ls)")"
ck "F6 本物: 保護ブランチへの push は停止" 2 "$(run "$GUARD" "$(bash_json 'git push origin develop')")"
ck "F6 本物: docs の Edit は素通し" 0 "$(run "$GUARD" "$(edit_json docs/x.md)")"

# 偽合格の防止: 包みを外した複製（修正前の作り）では、F1 と同じ注入で exit 1（ASK でも 2 でもない）になる
python3 - "$TMP/f1.py" "$TMP/fg1.py" <<'PY'
import sys
s = open(sys.argv[1], encoding="utf-8").read()
head = 'if __name__ == "__main__":'
if s.count(head) != 1:
    sys.exit(3)
s = s.replace(head, 'if __name__ == "__main__" and False:') + "\nmain()\n"
open(sys.argv[2], "w", encoding="utf-8").write(s)
PY
ck "FG-F1 包みが無いと F1 の注入は exit 1（F1 が包みの欠落を捕まえる）" 1 "$(run "$TMP/fg1.py" "$(bash_json ls)")"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
