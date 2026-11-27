#!/usr/bin/env bash
# reviewer-agents-lib.sh — レビュー役の定義を、このファイルと同じ版（写しから動けば写しの版）から渡す（I593・plan_I593.md 4-2）。
#
# 審査の入口（code-review.sh・adversarial-review.sh・plan-issue-review.sh・issue-review.sh・fix-review-lib.sh）は、
# .claude/hooks/unreviewed.py run が BASE（git merge-base HEAD origin/develop）の写し（~/.cache/claude-reviewed-snapshots/<BASE>/）
# から動かす。`claude -p --agent <名前>` は作業フォルダからたどる .claude/agents/ の定義（＝ブランチの版）を読むので、
# 写しの定義を `--agents <ファイル>`（同じ名前のプロジェクトの定義より優先される・公式 sub-agents.md）で渡す。
# 審査の入口はこのファイルを `$(dirname "${BASH_SOURCE[0]}")` から読む（写しから動けば写しのこのファイル）。
#
# 使い方: . "$(dirname "${BASH_SOURCE[0]}")/reviewer-agents-lib.sh"
#         reviewer_agent_args <名前> <一時フォルダ> || exit …   → 配列 REVIEWER_ARGS を claude -p に渡す
# 判定は呼ぶ側の --tools "Read,Grep,Glob" でも読み取り専用にする（定義の tools だけに頼らない）。

# このファイルの 2 つ上（写しから動けば写しの最上位、作業ツリーから動けばリポジトリの最上位）
reviewer_src_root() {
  (cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
}

# 写しから動いているか（最上位に .complete があり、リポジトリの最上位と違う）
reviewer_from_snapshot() {
  local src top
  src="$(reviewer_src_root)" || return 1
  top="$(git rev-parse --show-toplevel 2>/dev/null)" || top=""
  [ -n "$top" ] && top="$(cd "$top" && pwd -P)"
  [ -f "$src/.complete" ] && [ "$src" != "$top" ]
}

# 定義（.md）を --agents の JSON にする（標準出力）。前書きは name・description・tools・model だけを受け付ける。
# 引数: <定義のファイル> <名前> <決まりの参照の置き換え先（空なら置き換えない）>
_REVIEWER_AGENT_JSON_PY='
import json, sys
path, name, rules = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path, encoding="utf-8").read()
lines = text.split("\n")
if not lines or lines[0].strip() != "---":
    sys.exit("前書き（---）がありません: " + path)
try:
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
except StopIteration:
    sys.exit("前書きが閉じていません: " + path)
meta = {}
for raw in lines[1:end]:
    if not raw.strip():
        continue
    key, sep, val = raw.partition(":")
    key = key.strip()
    if not sep or key not in ("name", "description", "tools", "model") or key in meta or raw[:1].isspace():
        sys.exit("前書きの行を読めません（受け付けるのは name・description・tools・model の 1 行ずつ）: " + raw)
    meta[key] = val.strip()
if meta.get("name") != name:
    sys.exit("前書きの name がファイル名と違います: " + path)
if not meta.get("description"):
    sys.exit("前書きに description がありません: " + path)
body = "\n".join(lines[end + 1:]).strip("\n") + "\n"
if rules:
    body = body.replace("docs/runbooks/review-rules.md", rules)
agent = {"description": meta["description"], "prompt": body}
if meta.get("tools"):
    agent["tools"] = [t.strip() for t in meta["tools"].split(",") if t.strip()]
if meta.get("model"):
    agent["model"] = meta["model"]
json.dump({name: agent}, sys.stdout, ensure_ascii=False)
'

# REVIEWER_ARGS=(--agents <ファイル> --agent <名前> [--add-dir <写し>]) を作る。定義が無い・読めないときは非 0（fail-closed）
reviewer_agent_args() {
  local name="$1" dir="$2" src def rules="" snap=0
  REVIEWER_ARGS=()
  case "$name" in ''|*[!a-z0-9-]*) echo "[reviewer-agents] レビュー役の名前が不正です: '${name}'" >&2; return 2 ;; esac
  src="$(reviewer_src_root)" || return 2
  def="$src/.claude/agents/${name}.md"
  reviewer_from_snapshot && snap=1
  if [ ! -f "$def" ]; then
    echo "[reviewer-agents] レビュー役の定義がありません: ${def}" >&2
    if [ "$snap" = 1 ]; then
      echo "[reviewer-agents] 古い形の写しです。${src} を消してからやり直してください（I593）" >&2
    fi
    return 2
  fi
  if [ "$snap" = 1 ]; then
    rules="$src/docs/runbooks/review-rules.md"
    [ -f "$rules" ] || { echo "[reviewer-agents] 写しにレビューの決まりがありません: ${rules}（${src} を消してからやり直す・I593）" >&2; return 2; }
  fi
  mkdir -p "$dir" || return 2
  python3 -I -c "$_REVIEWER_AGENT_JSON_PY" "$def" "$name" "$rules" > "$dir/agents.json" || {
    echo "[reviewer-agents] レビュー役の定義を変換できません: ${def}" >&2; return 2; }
  REVIEWER_ARGS=(--agents "$dir/agents.json" --agent "$name")
  if [ -n "$rules" ]; then REVIEWER_ARGS+=(--add-dir "$src"); fi
  return 0
}
