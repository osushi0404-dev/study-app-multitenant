#!/usr/bin/env bash
# I195: tui-capture.sh（tmux で起動した claude の対話画面を読む）を決定論検証する。
# 実行: bash scripts/claude/tests/test_tui_capture.sh
# 本物の tmux・claude は使わない。偽物の tmux（呼ばれた引数を記録し、capture-pane では決まった画面を出す）と
# claude（何もしない）を一時のフォルダに置いて PATH の先頭にする。本物での確かめは I195 の手動テスト。
# ケースは docs/tests/open/I195_auto_test.md の TC-01（T1〜T9・FG）と対応する。
# shellcheck disable=SC2016  # 写しの置き換え前後・照合の正規表現は、スクリプトの文字そのもの（展開させない）
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
SCRIPT="$REPO_ROOT/scripts/claude/tui-capture.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
BASH_BIN="$(command -v bash)"

FAKE="$TMP/fake"; mkdir -p "$FAKE"
cat > "$FAKE/tmux" <<'EOF'
#!/usr/bin/env bash
echo "$*" >> "$TUI_FAKE_LOG"
if [ "${1:-}" = capture-pane ]; then
  if [ -n "${TUI_FAKE_NOPROMPT:-}" ]; then echo "loading"; else printf '  ❯ /plan-issue  説明\n❯ /plan-\n'; fi
fi
exit 0
EOF
printf '#!/usr/bin/env bash\nexit 0\n' > "$FAKE/claude"
chmod +x "$FAKE/tmux" "$FAKE/claude"

LOG="$TMP/log"; OUT="$TMP/out"
# $1=PATH・$2=スクリプト・残り=引数。記録は $LOG・標準出力は $OUT。終了コードを出す
run_path() {
  local p="$1" s="$2"; shift 2
  : > "$LOG"
  (PATH="$p" TUI_FAKE_LOG="$LOG" "$BASH_BIN" "$s" "$@" > "$OUT" 2>/dev/null); echo $?
}
run_with() { local s="$1"; shift; run_path "$FAKE:$PATH" "$s" "$@"; }
run() { run_with "$SCRIPT" "$@"; }
# 本体の写しを作る（$1=名前・$2=置き換え前・$3=置き換え後）。置き換え前が無ければ空のパスを返し、FG を不合格にする
mutant() {
  local m="$TMP/$1.sh"
  if python3 - "$SCRIPT" "$m" "$2" "$3" <<'PY'
import sys
src, dst, a, b = sys.argv[1:5]
s = open(src, encoding="utf-8").read()
if a not in s: sys.exit(1)
open(dst, "w", encoding="utf-8").write(s.replace(a, b))
PY
  then echo "$m"; fi
}
# 写しが作れたか（0=作れた・1=作れなかった）
made() { if [ -n "$1" ]; then echo 0; else echo 1; fi; }

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }
rc() { "$@" >/dev/null 2>&1; echo $?; }

[ -f "$SCRIPT" ] || { echo "FAIL スクリプトがありません: $SCRIPT"; echo "pass=0 fail=1"; exit 1; }

# T1: 起動・入力・読み取り・後始末が 1 回ずつ、この順
t1() {
  local S
  S="$(sed -n 's/^new-session -d -s \(tui-capture-[0-9]*\) .*/\1/p' "$LOG" | head -1)"
  [ -n "$S" ] || return 1
  grep -qF "/plan-issue" "$OUT" || return 1
  [ "$(grep -cxF "kill-session -t $S" "$LOG")" -eq 1 ] || return 1
  # 4 つの行がこの順にある（どれかが無ければ行番号が空で不合格）: new-session < send-keys < 最後の capture-pane < kill-session
  local n s c k
  n=$(grep -nxF "new-session -d -s $S -x 200 -y 50 -c $REPO_ROOT claude --permission-mode manual" "$LOG" | cut -d: -f1)
  s=$(grep -nxF "send-keys -t $S -l -- /plan-" "$LOG" | cut -d: -f1)
  c=$(grep -nxF "capture-pane -p -t $S" "$LOG" | tail -1 | cut -d: -f1)
  k=$(grep -nxF "kill-session -t $S" "$LOG" | cut -d: -f1)
  [ -n "$n" ] && [ -n "$s" ] && [ -n "$c" ] && [ -n "$k" ] || return 1
  [ "$n" -lt "$s" ] && [ "$s" -lt "$c" ] && [ "$c" -lt "$k" ]
}
ck "T1 終了コード 0"                  0 "$(run --wait 0 '/plan-')"
ck "T1 起動・入力・読み取り・後始末"   0 "$(rc t1)"

# T2: ! で始まる入力は何も起動せずに止める
no_start() { ! grep -q '^new-session' "$LOG"; }
ck "T2a !ls"                          2 "$(run '!ls')"
ck "T2a 何も起動しない"                0 "$(rc no_start)"
ck "T2b 前に空白のある !ls"            2 "$(run '  !ls')"
ck "T2b 何も起動しない"                0 "$(rc no_start)"
ck "T2c 2 つ目の入力が !ls"            2 "$(run '/plan-' '!ls')"
ck "T2c 何も起動しない"                0 "$(rc no_start)"

# T3: 使い方の誤り
ck "T3a 入力なし"                     2 "$(run)"
ck "T3b --wait が数でない"             2 "$(run --wait abc '/x')"
ck "T3b 何も起動しない"                0 "$(rc no_start)"
ck "T3c --start-timeout が負"          2 "$(run --start-timeout -1 '/x')"
ck "T3c 何も起動しない"                0 "$(rc no_start)"

# T4: 決まった 6 つのキーは -l なしで送る
ck "T4 キーを送る"                     0 "$(run --wait 0 '/config' '{Down}' '{Enter}' '{Escape}')"
t4() { grep -qE '^send-keys -t tui-capture-[0-9]+ -l -- /config$' "$LOG" &&
       grep -qE '^send-keys -t tui-capture-[0-9]+ Down$' "$LOG" &&
       grep -qE '^send-keys -t tui-capture-[0-9]+ Enter$' "$LOG" &&
       grep -qE '^send-keys -t tui-capture-[0-9]+ Escape$' "$LOG"; }
ck "T4 記録"                           0 "$(rc t4)"

# T5: 決まった 6 つ以外の {…} は文字として送る
ck "T5 {Foo}"                          0 "$(run --wait 0 '{Foo}')"
ck "T5 記録"                           0 "$(rc grep -qE '^send-keys -t tui-capture-[0-9]+ -l -- \{Foo\}$' "$LOG")"

# T6: プロンプトが出なければ時間切れで 2、入力は送らず、セッションは閉じる
t6() { ! grep -q '^send-keys' "$LOG" && grep -qE '^kill-session -t tui-capture-[0-9]+$' "$LOG"; }
ck "T6 時間切れ"                       2 "$(TUI_FAKE_NOPROMPT=1 run --start-timeout 0 --wait 0 '/x')"
ck "T6 入力を送らず閉じる"             0 "$(rc t6)"

# T7: tmux・claude が無い
MIN="$TMP/min"; mkdir -p "$MIN"
ln -s "$(command -v git)" "$MIN/git"; ln -s "$(command -v sleep)" "$MIN/sleep"
NOTMUX="$TMP/notmux"; cp -r "$MIN" "$NOTMUX"; cp "$FAKE/claude" "$NOTMUX/claude"
NOCLAUDE="$TMP/noclaude"; cp -r "$MIN" "$NOCLAUDE"; cp "$FAKE/tmux" "$NOCLAUDE/tmux"
ck "T7a tmux が無い"   2 "$(run_path "$NOTMUX" "$SCRIPT" '/x')"
ck "T7b claude が無い" 2 "$(run_path "$NOCLAUDE" "$SCRIPT" '/x')"
ck "T7b 何も起動しない" 0 "$(rc no_start)"

# T8: 起動の行は固定の文字で、引数から組み立てない
t8() { local f="$1" line
       line="$(grep -F 'new-session' "$f" | grep -v '^[[:space:]]*#')" || return 1
       grep -qF 'claude --permission-mode manual' <<< "$line" || return 1
       ! grep -qE '\$(1|@|\*|\{1|\{@|\{\*)' <<< "$line"; }
ck "T8 起動の行は固定"                 0 "$(rc t8 "$SCRIPT")"

# T9: - で始まる入力もオプションにならない（-- のあとに送る）
ck "T9 -x hello"                       0 "$(run --wait 0 '-x hello')"
ck "T9 記録"                           0 "$(rc grep -qE '^send-keys -t tui-capture-[0-9]+ -l -- -x hello$' "$LOG")"

# ---------------- FG（失敗注入）: 判定の要を壊した写しで、対応する項目が不合格になる ----------------
M="$(mutant fg_t1 "trap 'tmux kill-session" "trap ': tmux-kill-session")"
ck "FG の写し T1 が作れた" 0 "$(made "$M")"
[ -n "$M" ] && { run_with "$M" --wait 0 '/plan-' >/dev/null; ck "FG-T1 後始末を消すと T1 不合格" 1 "$(rc t1)"; }

M="$(mutant fg_t2 '=~ ^[[:space:]]*!' '=~ ^NEVER-MATCH')"
ck "FG の写し T2 が作れた" 0 "$(made "$M")"
[ -n "$M" ] && ck "FG-T2 ! の判定を消すと通ってしまう" 0 "$(run_with "$M" --wait 0 '!ls')"

M="$(mutant fg_t4 "'{Enter}'|'{Escape}'|'{Tab}'|'{Up}'|'{Down}'|'{BSpace}')" "'{NEVER}')")"
ck "FG の写し T4 が作れた" 0 "$(made "$M")"
[ -n "$M" ] && { run_with "$M" --wait 0 '/config' '{Down}' '{Enter}' '{Escape}' >/dev/null; ck "FG-T4 キーの判定を消すと T4 不合格" 1 "$(rc t4)"; }

M="$(mutant fg_t6 '[ "$waited" -lt "$START_TIMEOUT" ] ||' 'break;')"
ck "FG の写し T6 が作れた" 0 "$(made "$M")"
[ -n "$M" ] && ck "FG-T6 時間切れの判定を消すと 0 になる" 0 "$(TUI_FAKE_NOPROMPT=1 run_with "$M" --start-timeout 0 --wait 0 '/x')"

M="$(mutant fg_t8 '"claude --permission-mode manual"' '"claude --permission-mode manual $*"')"
ck "FG の写し T8 が作れた" 0 "$(made "$M")"
[ -n "$M" ] && ck "FG-T8 起動の行に引数を足すと T8 不合格" 1 "$(rc t8 "$M")"

M="$(mutant fg_t9 '-l -- "$x"' '-l "$x"')"
ck "FG の写し T9 が作れた" 0 "$(made "$M")"
[ -n "$M" ] && { run_with "$M" --wait 0 '-x hello' >/dev/null
                 ck "FG-T9 -- を消すと T9 不合格" 1 "$(rc grep -qE '^send-keys -t tui-capture-[0-9]+ -l -- -x hello$' "$LOG")"; }

echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
