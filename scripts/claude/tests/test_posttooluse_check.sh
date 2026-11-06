#!/usr/bin/env bash
# I185 P1: posttooluse_check.py（編集直後の構文チェック）の終了コードを決定論検証する。
# 実行: bash scripts/claude/tests/test_posttooluse_check.sh
#
# 公式（hooks.md）では、PostToolUse で Claude に stderr を届けるのは exit 2 だけ。
# 構文エラーは exit 2＋stderr に "syntax error"、それ以外は exit 0 であることを確かめる。
# 検証対象は環境変数 HOOK で差し替えられる（変更前の版に当てて不合格になることの確認用）。
# 0=全 PASS / 1=FAIL あり。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="${HOOK:-$REPO_ROOT/scripts/claude/hooks/posttooluse_check.py}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
# run_hook <file_path or empty> → グローバル RC / ERR に結果を入れる
run_hook() {
  local input
  if [ -n "$1" ]; then
    input=$(printf '{"tool_input": {"file_path": "%s"}}' "$1")
  else
    input='{"tool_input": {}}'
  fi
  ERR="$(printf '%s' "$input" | python3 "$HOOK" 2>&1 >/dev/null)"; RC=$?
}
expect() {  # expect <name> <want_rc> <want_stderr_substring or empty>
  if [ "$RC" -ne "$2" ]; then
    printf 'FAIL %s expected rc=%s got rc=%s\n' "$1" "$2" "$RC"; fail=$((fail+1)); return
  fi
  if [ -n "$3" ] && ! grep -q "$3" <<< "$ERR"; then
    printf 'FAIL %s stderr に "%s" がない\n' "$1" "$3"; fail=$((fail+1)); return
  fi
  printf 'PASS %s\n' "$1"; pass=$((pass+1))
}

printf '{"a": }\n' > "$TMP/bad.json"
run_hook "$TMP/bad.json"; expect "TC-10a 壊れた .json は exit 2" 2 "syntax error"

printf 'def f(:\n    pass\n' > "$TMP/bad.py"
run_hook "$TMP/bad.py"; expect "TC-10b 壊れた .py は exit 2" 2 "syntax error"

printf '{"a": 1}\n' > "$TMP/good.json"
run_hook "$TMP/good.json"; expect "TC-10c 正しい .json は exit 0" 0 ""

printf 'x = 1\n' > "$TMP/good.py"
run_hook "$TMP/good.py"; expect "TC-10d 正しい .py は exit 0" 0 ""

printf '{"a": }\n' > "$TMP/bad.txt"
run_hook "$TMP/bad.txt"; expect "TC-10e 対象外の拡張子は exit 0" 0 ""

run_hook ""; expect "TC-10f file_path なしは exit 0" 0 ""

# I226: 自動テスト文書（docs/tests/open/I<数字>_auto_test.md）は、決定論ゲートの宣言漏れ（omission-lint）も見る
D="$TMP/docs/tests/open"; mkdir -p "$D"
auto_doc() {  # auto_doc <ファイル> <見出し>: 見出しの下の bash ブロックにゲートのコマンドを 1 行書く
  # shellcheck disable=SC2016  # バッククォートは文書の文字そのもの
  printf '# I999 自動テスト\n\n%s\n```bash\nbash scripts/claude/tests/test_i223_gh_app.sh\n```\n' "$2" > "$1"
}
auto_doc "$D/I999_auto_test.md" "## 決定論ゲート（自動実行）"
run_hook "$D/I999_auto_test.md"; expect "TC-10g 見出しを 1 語違えた auto_test は exit 2" 2 "宣言漏れ"
auto_doc "$D/I999_auto_test.md" "## 決定論ゲート（自動実走）"
run_hook "$D/I999_auto_test.md"; expect "TC-10h ひな形どおりの見出しの auto_test は exit 0" 0 ""
auto_doc "$D/I999_manual_test.md" "## 決定論ゲート（自動実行）"
run_hook "$D/I999_manual_test.md"; expect "TC-10i 対象外の名前（manual_test）は exit 0" 0 ""

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
