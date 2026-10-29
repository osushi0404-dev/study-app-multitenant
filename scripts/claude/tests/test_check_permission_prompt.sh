#!/usr/bin/env bash
# I187: check-permission-prompt.sh（承認画面が出るかを claude -p で確かめる判定）の読み取り部分を決定論検証する。
# 実行: bash scripts/claude/tests/test_check_permission_prompt.sh
# CHECK_PERMISSION_PROMPT_LOG に作り置きの stream-json を渡し、claude を起動せずに判定させる。
# ケースは docs/tests/open/I187_auto_test.md の TC-26（Q1〜Q9）と対応する。
# 別のスクリプトに当てるとき（false-green の確認）: CHECK=<スクリプト> bash scripts/claude/tests/test_check_permission_prompt.sh
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
CHECK="${CHECK:-$REPO_ROOT/scripts/claude/check-permission-prompt.sh}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

CMD='docker compose exec -T frontend npm run lint'
init()   { printf '{"type":"system","subtype":"init","permissionMode":"%s"}\n' "${1:-default}"; }
use()    { printf '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"t1","name":"%s","input":%s}]}}\n' "$1" "$2"; }
res()    { printf '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"t1","is_error":%s,"content":"out"}]}}\n' "$1"; }
done_ok(){ printf '{"type":"result","subtype":"success","permission_denials":[]}\n'; }
done_ng(){ printf '{"type":"result","subtype":"success","permission_denials":[{"tool_name":"%s","tool_use_id":"t1","tool_input":{}}]}\n' "$1"; }
bash_in(){ printf '{"command":"%s","description":"x"}' "$1"; }
# 本物の出力では、拒否されたときに message が文字列の system 行が入る
denied_ev(){ printf '{"type":"system","subtype":"permission_denied","tool_name":"%s","tool_use_id":"t1","message":"Permission for this tool use was denied."}\n' "$1"; }

# $1=ケース名・$2 以降=判定に渡す引数。標準入力=作り置きのログ
run() { local f="$TMP/$1.jsonl"; shift; cat > "$f"; CHECK_PERMISSION_PROMPT_LOG="$f" bash "$CHECK" "$@" >/dev/null 2>&1; echo $?; }

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

ck "Q1 bash・承認なしで実行"    0  "$( { init; use Bash "$(bash_in "$CMD")"; res false; done_ok; } | run q1 bash "$CMD")"
ck "Q2 bash・拒否された"        10 "$( { init; use Bash "$(bash_in "$CMD")"; res true; done_ng Bash; } | run q2 bash "$CMD")"
ck "Q3 操作が呼ばれない"        2  "$( { init; done_ok; } | run q3 bash "$CMD")"
ck "Q4 コマンドが書き換えられた" 2  "$( { init; use Bash "$(bash_in "$CMD --fix")"; res false; done_ok; } | run q4 bash "$CMD")"
ck "Q5 mcp・承認なしで実行"     0  "$( { init; use mcp__playwright__browser_navigate '{"url":"http://localhost:3010/login"}'; res false; done_ok; } | run q5 mcp mcp__playwright__browser_navigate '{"url":"http://localhost:3010/login"}')"
ck "Q6 mcp・拒否された"         10 "$( { init; use mcp__playwright__browser_evaluate '{"function":"() => 1"}'; res true; done_ng mcp__playwright__browser_evaluate; } | run q6 mcp mcp__playwright__browser_evaluate '{"function":"() => 1"}')"
ck "Q7 モードが default でない" 2  "$( { init auto; use Bash "$(bash_in "$CMD")"; res false; done_ok; } | run q7 bash "$CMD")"
ck "Q8a 引数なし"               2  "$( : | run q8a)"
ck "Q8b 種類が違う"             2  "$( { init; done_ok; } | run q8b shell "$CMD")"
ck "Q9 result の行が無い"       2  "$( { init; use Bash "$(bash_in "$CMD")"; res false; } | run q9 bash "$CMD")"
ck "Q10 本物の形の拒否（message が文字列の行あり）" 10 "$( { init; use Bash "$(bash_in "$CMD")"; denied_ev Bash; res true; done_ng Bash; } | run q10 bash "$CMD")"
ck "Q11 読めない形の result"    2  "$( { init; use Bash "$(bash_in "$CMD")"; res false; printf '{"type":"result","permission_denials":"x"}\n'; } | run q11 bash "$CMD")"
# 以下は敵対的レビュー 3 周目で足したケース（出力の形がずれたら 0 ではなく 2 にする・permission_denials で判定していること）
ck "Q12 permission_denials が無い" 2 "$( { init; use Bash "$(bash_in "$CMD")"; res true; printf '{"type":"result","subtype":"success"}\n'; } | run q12 bash "$CMD")"
ck "Q13 permission_denials が null" 2 "$( { init; use Bash "$(bash_in "$CMD")"; res true; printf '{"type":"result","subtype":"success","permission_denials":null}\n'; } | run q13 bash "$CMD")"
ck "Q14 拒否の要素に tool_use_id が無い" 2 "$( { init; use Bash "$(bash_in "$CMD")"; res true; printf '{"type":"result","subtype":"success","permission_denials":[{"tool_name":"Bash"}]}\n'; } | run q14 bash "$CMD")"
ck "Q15 result の subtype が success でない" 2 "$( { init; use Bash "$(bash_in "$CMD")"; res true; printf '{"type":"result","subtype":"error_during_execution","permission_denials":[]}\n'; } | run q15 bash "$CMD")"
ck "Q16 拒否の行があるのに permission_denials に無い" 2 "$( { init; use Bash "$(bash_in "$CMD")"; denied_ev Bash; res true; done_ok; } | run q16 bash "$CMD")"
ck "Q17 コマンドが失敗しただけ（is_error・拒否なし）" 0 "$( { init; use Bash "$(bash_in "$CMD")"; res true; done_ok; } | run q17 bash "$CMD")"

# Q18（BP 周）: claude に渡す引数を守る。CLAUDE_BIN に、受け取った引数を書き出して作り置きのログを返す偽物を渡す
fake="$TMP/fake-claude.sh"; args="$TMP/args.txt"; { init; use Bash "$(bash_in "$CMD")"; res false; done_ok; } > "$TMP/q18.jsonl"
printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$@" > %q\ncat %q\n' "$args" "$TMP/q18.jsonl" > "$fake"; chmod +x "$fake"
rc="$(CLAUDE_BIN="$fake" bash "$CHECK" bash "$CMD" >/dev/null 2>&1; echo $?)"
got="$(tr '\n' ' ' < "$args" 2>/dev/null)"
ok=1
for want in "--permission-mode manual" "--permission-prompts none" "--setting-sources user" "--settings .claude/settings.json" "--strict-mcp-config" "--output-format stream-json"; do
  [[ " $got " == *" $want "* ]] || { ok=0; echo "  Q18 引数が無い: $want" >&2; }
done
[[ " $got " == *" --mcp-config "* ]] && { ok=0; echo "  Q18 bash の判定で MCP を読み込んでいる" >&2; }
ck "Q18 claude に渡す引数（bash）" "0 1" "$rc $ok"
rm -f "$args"
{ init; use mcp__playwright__browser_navigate '{"url":"x"}'; res false; done_ok; } > "$TMP/q18.jsonl"
rc="$(CLAUDE_BIN="$fake" bash "$CHECK" mcp mcp__playwright__browser_navigate '{"url":"x"}' >/dev/null 2>&1; echo $?)"
got="$(tr '\n' ' ' < "$args" 2>/dev/null)"
ck "Q18 claude に渡す引数（mcp は .mcp.json を読む）" "0 yes yes" "$rc $([[ " $got " == *" --mcp-config .mcp.json "* ]] && echo yes || echo no) $([[ " $got " == *" --setting-sources user "* ]] && echo yes || echo no)"

# I200 TC-06b: write（Edit・Write の許可の確かめ）。書き先はリポジトリの中の相対パス・無いか同じ中身のときだけ動く
WT=".i200_probe_$$.yml"; WABS="$REPO_ROOT/$WT"; printf 'x: 1\n' > "$TMP/body.txt"
write_in(){ printf '{"file_path":"%s","content":"x: 1\\n"}' "$1"; }
ck "06b-1 write・承認なしで実行" 0  "$( { init; use Write "$(write_in "$WABS")"; res false; done_ok; } | run w1 write "$WT" "$TMP/body.txt")"
ck "06b-2 write・拒否された"     10 "$( { init; use Write "$(write_in "$WABS")"; denied_ev Write; res true; done_ng Write; } | run w2 write "$WT" "$TMP/body.txt")"
ck "06b-3 write・別のパスに書いた" 2 "$( { init; use Write "$(write_in "$REPO_ROOT/other.yml")"; res false; done_ok; } | run w3 write "$WT" "$TMP/body.txt")"
# 06b-4/5: claude を起動せずに断る（CLAUDE_BIN を呼ばれたら印を残す偽物にする）
called="$TMP/called"; printf '#!/usr/bin/env bash\ntouch %q\nexit 1\n' "$called" > "$TMP/never.sh"; chmod +x "$TMP/never.sh"
printf 'different\n' > "$TMP/diff.txt"
rc="$(CLAUDE_BIN="$TMP/never.sh" bash "$CHECK" write README.md "$TMP/diff.txt" >/dev/null 2>&1; echo $?)"
ck "06b-4 既にあり中身が違う書き先は断る" "2 no" "$rc $([ -e "$called" ] && echo yes || echo no)"
rc1="$(CLAUDE_BIN="$TMP/never.sh" bash "$CHECK" write ../outside.txt "$TMP/body.txt" >/dev/null 2>&1; echo $?)"
rc2="$(CLAUDE_BIN="$TMP/never.sh" bash "$CHECK" write "$TMP/outside.txt" "$TMP/body.txt" >/dev/null 2>&1; echo $?)"
ck "06b-5 リポジトリの外の書き先は断る" "2 2 no" "$rc1 $rc2 $([ -e "$called" ] && echo yes || echo no)"
cp "$REPO_ROOT/README.md" "$TMP/same.txt"
ck "06b-6 既にあり中身が同じなら判定に進む" 0 "$( { init; use Write "$(write_in "$REPO_ROOT/README.md")"; res false; done_ok; } | run w6 write README.md "$TMP/same.txt")"

echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
