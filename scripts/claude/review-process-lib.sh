#!/usr/bin/env bash
# review-process-lib.sh — 別プロセスの検証役（claude -p）を起動し、その記録を読む関数（I197）。
#
# 呼び出し元: scripts/claude/adversarial-review.sh・scripts/claude/code-review.sh（source して使う）
# 考え方:
#   - claude -p は「時間上限つき・承認なし（--permission-prompts none）・途中の出力をすべて残す（stream-json）」で起動する。
#     承認が要る操作は待たずに拒否され、出力の permission_denials に残る（黙って止まる経路を作らない）
#   - 記録の各行の先頭に受け取り時刻（epoch 秒）とタブを付け、最後に「閉じた」行を足す。時間切れで止めても、
#     最後のツール呼び出し・その結果・そこからの経過を後から取り出せる
#   - 出力の形が読めないときは「拒否なし」「実行した」と言わない（呼び出し元が止まる側に倒す）
# テスト用: CLAUDE_BIN=<コマンド> で起動する claude を差し替えられる
# 計画: docs/plans/open/plan_I197.md §4.4

# run_claude_logged <秒> <ログ> <入力ファイル> <claude の引数…>
#   引数に「--permission-prompts none」が無ければ呼ばずに 2（承認なしの付け忘れを仕組みで止める）。
#   戻り値は claude の終了コード（124 は時間切れ）
run_claude_logged() {
  local secs="$1" log="$2" input="$3" a prev="" ok=0
  shift 3
  for a in "$@"; do
    [ "$prev" = "--permission-prompts" ] && [ "$a" = "none" ] && ok=1
    prev="$a"
  done
  if [ "$ok" -ne 1 ]; then
    echo "[review-process-lib] --permission-prompts none の無い claude -p は起動しません" >&2
    return 2
  fi
  timeout "$secs" "${CLAUDE_BIN:-claude}" -p "$@" --output-format stream-json --verbose < "$input" 2> "${log}.err" \
    | python3 -I -u -c '
import json, sys, time
for line in sys.stdin:
    sys.stdout.write(f"{int(time.time())}\t{line}")
    sys.stdout.flush()
sys.stdout.write(f"{int(time.time())}\t" + json.dumps({"type": "__log_closed__"}) + "\n")
' > "$log"
  return "${PIPESTATUS[0]}"
}

# 記録を読む本体（python）。使い方: _claude_log <mode> <ログ> [<コマンドのファイル>]
_CLAUDE_LOG_PY='
import json, sys

def fail(code):
    sys.exit(code)

mode, log = sys.argv[1], sys.argv[2]
events = []
try:
    with open(log, encoding="utf-8", errors="replace") as f:
        for raw in f:
            ts, _, body = raw.partition("\t")
            try:
                d = json.loads(body)
            except ValueError:
                continue
            if isinstance(d, dict):
                events.append((int(ts) if ts.isdigit() else 0, d))
except OSError:
    fail(2)

result = None
init = None
denied_events = set()
uses, results = [], {}
for ts, d in events:
    t = d.get("type")
    if t == "result":
        result = d
    elif t == "system" and d.get("subtype") == "init":
        init = d
    elif t == "system" and d.get("subtype") == "permission_denied":
        denied_events.add(d.get("tool_use_id"))
    msg = d.get("message")
    for c in (msg.get("content") or [] if isinstance(msg, dict) else []):
        if not isinstance(c, dict):
            continue
        if c.get("type") == "tool_use":
            uses.append((ts, c))
        elif c.get("type") == "tool_result":
            results[c.get("tool_use_id")] = (ts, c)

def text_of(c):
    body = c.get("content")
    return body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)

def denials():
    # result の permission_denials が無い・配列でない・要素に tool_use_id が無い → 読めない（None）
    if result is None:
        return None
    ds = result.get("permission_denials")
    if not isinstance(ds, list) or not all(isinstance(x, dict) and x.get("tool_use_id") for x in ds):
        return None
    ids = {x["tool_use_id"] for x in ds}
    if not denied_events <= ids:
        return None
    return ds

if mode == "result":
    if result is None or not isinstance(result.get("result"), str):
        fail(1)
    sys.stdout.write(result["result"])
elif mode == "subtype":
    print("" if result is None else (result.get("subtype") or ""))
elif mode == "session":
    sid = (result or {}).get("session_id") or (init or {}).get("session_id") or ""
    if not sid:
        fail(1)
    print(sid)
elif mode == "mode":
    print((init or {}).get("permissionMode") or "")
elif mode == "cost":
    print((result or {}).get("total_cost_usd", ""))
elif mode == "denials":
    ds = denials()
    if ds is None:
        fail(2)
    for x in ds:
        cmd = (x.get("tool_input") or {}).get("command") or json.dumps(x.get("tool_input"), ensure_ascii=False)
        print(x["tool_use_id"] + "\t" + str(cmd).replace("\n", " ")[:200])
elif mode == "ran":
    with open(sys.argv[3], encoding="utf-8") as f:
        want = f.read()
    ds = denials()
    if ds is None:
        fail(2)          # 読めない（時間切れ・形の変化）: 実行したとは言わない
    denied = {x["tool_use_id"] for x in ds}
    for ts, c in uses:
        if c.get("name") == "Bash" and (c.get("input") or {}).get("command") == want:
            if c.get("id") in denied:
                fail(10)
            r = results.get(c.get("id"))
            if r is None:
                fail(1)
            print("is_error=" + str(bool(r[1].get("is_error"))).lower())
            sys.stdout.write(text_of(r[1])[:2000])
            sys.exit(0)
    fail(1)
elif mode == "last_tool":
    closed = max([ts for ts, d in events if d.get("type") == "__log_closed__"] or [0])
    last_ev = max([ts for ts, d in events if d.get("type") != "__log_closed__"] or [closed])
    if not uses:
        print("(なし)\t\t\t" + str(max(0, closed - last_ev)))
    else:
        ts, c = uses[-1]
        inp = json.dumps(c.get("input"), ensure_ascii=False).replace("\n", " ")[:120]
        r = results.get(c.get("id"))
        res = text_of(r[1]).replace("\n", " ").replace("\t", " ")[:120] if r else "(結果なし)"
        name = c.get("name")
        print(f"{name}\t{inp}\t{res}\t{max(0, closed - last_ev)}")
else:
    fail(2)
'
_claude_log() { python3 -I -c "$_CLAUDE_LOG_PY" "$@"; }

# 最後の result の本文（無ければ 1）
claude_log_result()  { _claude_log result "$1"; }
# result の subtype（success など。無ければ空）
claude_log_subtype() { _claude_log subtype "$1"; }
# session_id（無ければ 1）
claude_log_session() { _claude_log session "$1"; }
# init の permissionMode（無ければ空）
claude_log_mode()    { _claude_log mode "$1"; }
# total_cost_usd（無ければ空）
claude_log_cost()    { _claude_log cost "$1"; }
# 拒否の一覧（<tool_use_id>\t<コマンドの先頭>）。読めなければ 2
claude_log_denials() { _claude_log denials "$1"; }
# <ログ> <コマンドのファイル>: 完全一致の Bash 呼び出しが 実行された=0（is_error= と出力の先頭を出す）・拒否=10・呼ばれていない=1・読めない=2
claude_log_ran()     { _claude_log ran "$1" "$2"; }
# 最後のツール呼び出し: <名前>\t<入力の先頭>\t<結果の先頭>\t<最後の出来事から閉じるまでの秒>
claude_log_last_tool() { _claude_log last_tool "$1"; }
