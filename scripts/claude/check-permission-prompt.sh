#!/usr/bin/env bash
set -uo pipefail
# check-permission-prompt: 操作に承認画面が出るかを、Claude が人に頼まずに確かめる（I187）。
# Usage: check-permission-prompt.sh bash '<コマンド>'
#        check-permission-prompt.sh mcp <操作名> ['<入力の JSON>']
#        check-permission-prompt.sh write <リポジトリの中の相対パス> <中身のファイル>（I200: Edit・Write の許可の確かめ。
#          書き先が無いか中身が同じときだけ動く。通ると実際に書かれるので、確かめ用の新しいファイルで行い後で消す）
#   - 公式の claude -p を通常モード（--permission-mode manual）・承認は誰も答えない（--permission-prompts none）で起動し、
#     その操作を 1 回だけ呼ばせる。承認が要る操作は画面を出さずに拒否され、出力の permission_denials に入る
#   - --setting-sources user と --settings .claude/settings.json で、ユーザー全体の設定とこのブランチの設定ファイルだけを読ませる
#     （ワークツリーのセッションは元のリポジトリの設定・手元の settings.local.json を読み、元のリポジトリが今いるブランチや
#     手元で足した許可で判定が変わるため。マージ後の develop と同じ判定にする）
#   - 承認なしで通る操作は実際に実行される（設定が壊れていれば、承認画面が出るはずの操作も実行される）。
#     危ない操作は、同じ許可ルール・見張りに当たり、実行されても困らない代わりの操作で確かめる
#   - 見張り（PreToolUse）が止めた操作は承認画面を出さないので 0 になる。出力の先頭を見て見分ける
# 終了コード: 0=承認なしで実行された・10=承認画面が出る（自動で拒否された）
#             2=判定できない（引数の誤り・操作が呼ばれない・コマンドが書き換えられた・モードが違う・claude の失敗）
# テスト用: CHECK_PERMISSION_PROMPT_LOG=<保存した stream-json> があれば claude を起動せずにそれを読む
#           CLAUDE_BIN=<コマンド> で起動する claude を差し替えられる（渡す引数を確かめる）
# 2 が出たら: もう 1 回流す。それでも 2 なら、その確認は NG として止めて報告する（ユーザーに「画面が出たか」を聞かない）
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
  write) ;;   # I200: 下で書き先を確かめてから組み立てる
  *) KIND="" ;;
esac
if [ -z "$KIND" ] || [ -z "$TARGET" ] || { [ "$KIND" = write ] && [ -z "$INPUT" ]; }; then
  echo "[check-permission-prompt] 使い方: $0 bash '<コマンド>' ／ $0 mcp <操作名> ['<入力の JSON>'] ／ $0 write <リポジトリの中の相対パス> <中身のファイル>" >&2
  exit 2
fi
MATCH="$TARGET"
# I200: write は承認なしで通ると実際に書き込む。誤って既存のファイルを上書きしないよう、書き先が存在しないか、
# 渡した中身が今の中身と同じときだけ claude を起動する。書き先はリポジトリの中の相対パスだけ（絶対パス・.. は断る）
if [ "$KIND" = write ]; then
  WROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "[check-permission-prompt] git のワークツリー内で実行してください" >&2; exit 2; }
  case "$TARGET" in
    /*|..|../*|*/..|*/../*) echo "[check-permission-prompt] 判定できない: write の書き先はリポジトリの中の相対パスだけです: $TARGET" >&2; exit 2 ;;
  esac
  if [ ! -f "$INPUT" ]; then
    echo "[check-permission-prompt] 判定できない: 中身のファイルがありません: $INPUT" >&2; exit 2
  fi
  if [ -e "$WROOT/$TARGET" ] && ! cmp -s "$WROOT/$TARGET" "$INPUT"; then
    echo "[check-permission-prompt] 判定できない: 書き先が既にあり中身が違うので、上書きしないよう断りました: $TARGET" >&2; exit 2
  fi
  MATCH="$WROOT/$TARGET"
  PROMPT="Use the Write tool exactly once to write the file $MATCH with exactly the content between the BEGIN and END lines below (not including those two lines).
-----BEGIN-----
$(cat "$INPUT")
-----END-----
Do not call any other tool. Then reply with only DONE."
fi

if [ -n "${CHECK_PERMISSION_PROMPT_LOG:-}" ]; then
  LOG="$CHECK_PERMISSION_PROMPT_LOG"
else
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "[check-permission-prompt] git のワークツリー内で実行してください" >&2; exit 2; }
  cd "$ROOT" || exit 2
  LOG="$(mktemp)"
  trap 'rm -f "$LOG"' EXIT
  # bash の判定では MCP サーバーを起動しない（判定に要らず、起動の分だけ遅くなる）
  if [ "$KIND" = "mcp" ]; then MCP_ARGS=(--mcp-config .mcp.json); else MCP_ARGS=(--strict-mcp-config); fi
  if ! "${CLAUDE_BIN:-claude}" -p "$PROMPT" \
      --model haiku \
      --permission-mode manual \
      --permission-prompts none \
      --setting-sources user \
      --settings .claude/settings.json \
      "${MCP_ARGS[@]}" \
      --no-session-persistence \
      --max-budget-usd 1 \
      --output-format stream-json --verbose > "$LOG"; then
    echo "[check-permission-prompt] 判定できない: claude -p が失敗しました" >&2
    exit 2
  fi
fi

python3 -I - "$LOG" "$KIND" "$MATCH" <<'PY'
import json, os, sys

def unknown(msg, other=()):
    print(f"[check-permission-prompt] 判定できない: {msg}", file=sys.stderr)
    for o in other:
        print(f"  呼ばれた別の操作: {o}", file=sys.stderr)
    sys.exit(2)

# 想定外の形で落ちたときも 2（判定できない）で終える（fail-closed）
sys.excepthook = lambda tp, e, tb: unknown(f"出力を読めません（{tp.__name__}: {e}）")

log, kind, target = sys.argv[1:4]
want_name = {"bash": "Bash", "write": "Write"}.get(kind, target)


def wanted(name, inp):
    if name != want_name:
        return False
    if kind == "bash":
        return inp.get("command") == target
    if kind == "write":   # I200: 頼んだ書き先に書いたか（パスは正規化して比べる）
        p = inp.get("file_path")
        return isinstance(p, str) and os.path.realpath(p) == os.path.realpath(target)
    return True

mode, use_id, other, result, denied_events, output = None, None, [], None, set(), ""
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
        elif t == "system" and d.get("subtype") == "permission_denied":
            denied_events.add(d.get("tool_use_id"))
        elif t == "result":
            result = d
        msg = d.get("message")
        for c in (msg.get("content") or [] if isinstance(msg, dict) else []):
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                name, inp = c.get("name"), c.get("input") or {}
                if use_id is None and wanted(name, inp):
                    use_id = c.get("id")
                else:
                    other.append(f"{name} {json.dumps(inp, ensure_ascii=False)[:120]}")
            elif c.get("type") == "tool_result" and use_id and c.get("tool_use_id") == use_id:
                body = c.get("content")
                output = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)

if mode != "default":
    unknown(f"モードが default ではありません（{mode}）")
if result is None:
    unknown("最後の result の行がありません（途中で終わった）")
if result.get("subtype") != "success":
    unknown(f"result が success ではありません（{result.get('subtype')}）")
# 出力の形が変わったら「承認なし」と言わずに止める（permission_denials が無い・配列でない・要素に tool_use_id が無い）
denials = result.get("permission_denials")
if not isinstance(denials, list) or not all(isinstance(x, dict) and x.get("tool_use_id") for x in denials):
    unknown("result の permission_denials を読めません")
denied_ids = {x["tool_use_id"] for x in denials}
if not denied_events <= denied_ids:
    unknown("拒否の行と result の permission_denials が食い違っています")
if use_id is None:
    unknown("頼んだ操作が、そのままの形で呼ばれませんでした", other)
if use_id in denied_ids:
    print(f"[check-permission-prompt] 承認画面が出る: {target}")
    sys.exit(10)
print(f"[check-permission-prompt] 承認なしで実行された: {target}")
print("  出力の先頭: " + output[:200].replace("\n", " "))
sys.exit(0)
PY
