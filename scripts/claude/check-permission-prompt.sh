#!/usr/bin/env bash
set -uo pipefail
# check-permission-prompt: 操作に承認画面が出るかを、Claude が人に頼まずに確かめる（I187）。
# Usage: check-permission-prompt.sh bash '<コマンド>'
#        check-permission-prompt.sh mcp <操作名> ['<入力の JSON>']
#   - 公式の claude -p を通常モード（--permission-mode manual）・承認は誰も答えない（--permission-prompts none）で起動し、
#     その操作を 1 回だけ呼ばせる。承認が要る操作は画面を出さずに拒否され、出力の permission_denials に入る
#   - --settings .claude/settings.json でワークツリーの許可を読ませる（ワークツリーのセッションの許可は
#     元のリポジトリの設定で判定されるため、ブランチで足した allow を確かめるのに要る）
#   - 承認なしで通る操作は実際に実行される。実行して困るもの（データの削除・外部への送信など）には使わない
#   - 見張り（PreToolUse）が止めた操作は承認画面を出さないので 0 になる。出力の先頭を見て見分ける
# 終了コード: 0=承認なしで実行された・10=承認画面が出る（自動で拒否された）
#             2=判定できない（引数の誤り・操作が呼ばれない・コマンドが書き換えられた・モードが違う・claude の失敗）
# テスト用: CHECK_PERMISSION_PROMPT_LOG=<保存した stream-json> があれば claude を起動せずにそれを読む
# 計画: docs/plans/open/plan_I187.md 5-2-8

KIND="${1:-}"
TARGET="${2:-}"
INPUT="${3:-}"
case "$KIND" in
  bash) PROMPT="Use the Bash tool exactly once to run this command verbatim, without changing, quoting differently, or splitting it:
$TARGET
Do not call any other tool. Then reply with only DONE." ;;
  mcp) PROMPT="Call the tool $TARGET exactly once${INPUT:+ with this input: $INPUT}.
Do not call any other tool. Then reply with only DONE." ;;
  *) KIND="" ;;
esac
if [ -z "$KIND" ] || [ -z "$TARGET" ]; then
  echo "[check-permission-prompt] 使い方: $0 bash '<コマンド>' ／ $0 mcp <操作名> ['<入力の JSON>']" >&2
  exit 2
fi

if [ -n "${CHECK_PERMISSION_PROMPT_LOG:-}" ]; then
  LOG="$CHECK_PERMISSION_PROMPT_LOG"
else
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "[check-permission-prompt] git のワークツリー内で実行してください" >&2; exit 2; }
  cd "$ROOT" || exit 2
  LOG="$(mktemp)"
  trap 'rm -f "$LOG"' EXIT
  if ! claude -p "$PROMPT" \
      --model haiku \
      --permission-mode manual \
      --permission-prompts none \
      --settings .claude/settings.json \
      --mcp-config .mcp.json \
      --no-session-persistence \
      --max-budget-usd 1 \
      --output-format stream-json --verbose > "$LOG"; then
    echo "[check-permission-prompt] 判定できない: claude -p が失敗しました" >&2
    exit 2
  fi
fi

python3 -I - "$LOG" "$KIND" "$TARGET" <<'PY'
import json, sys

def unknown(msg, other=()):
    print(f"[check-permission-prompt] 判定できない: {msg}", file=sys.stderr)
    for o in other:
        print(f"  呼ばれた別の操作: {o}", file=sys.stderr)
    sys.exit(2)

# 想定外の形で落ちたときも 2（判定できない）で終える（fail-closed）
sys.excepthook = lambda tp, e, tb: unknown(f"出力を読めません（{tp.__name__}: {e}）")

log, kind, target = sys.argv[1:4]
want_name = "Bash" if kind == "bash" else target
mode, use_id, other, result_seen, denied_ids, output = None, None, [], False, set(), ""
with open(log, encoding="utf-8") as f:
    for line in f:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        t = d.get("type")
        if t == "system" and d.get("subtype") == "init":
            mode = d.get("permissionMode")
        elif t == "result":
            result_seen = True
            denied_ids = {x["tool_use_id"] for x in d.get("permission_denials") or [] if isinstance(x, dict) and "tool_use_id" in x} \
                if isinstance(d.get("permission_denials") or [], list) else None
        msg = d.get("message")
        for c in (msg.get("content") or [] if isinstance(msg, dict) else []):
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                name, inp = c.get("name"), c.get("input") or {}
                if use_id is None and name == want_name and (kind != "bash" or inp.get("command") == target):
                    use_id = c.get("id")
                else:
                    other.append(f"{name} {json.dumps(inp, ensure_ascii=False)[:120]}")
            elif c.get("type") == "tool_result" and use_id and c.get("tool_use_id") == use_id:
                body = c.get("content")
                output = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)

if mode != "default":
    unknown(f"モードが default ではありません（{mode}）")
if not result_seen:
    unknown("最後の result の行がありません（途中で終わった）")
if denied_ids is None:
    unknown("result の permission_denials を読めません")
if use_id is None:
    unknown("頼んだ操作が、そのままの形で呼ばれませんでした", other)
if use_id in denied_ids:
    print(f"[check-permission-prompt] 承認画面が出る: {target}")
    sys.exit(10)
print(f"[check-permission-prompt] 承認なしで実行された: {target}")
print("  出力の先頭: " + output[:200].replace("\n", " "))
sys.exit(0)
PY
