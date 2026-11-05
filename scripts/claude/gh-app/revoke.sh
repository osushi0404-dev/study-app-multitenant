#!/usr/bin/env bash
# 鍵が画面・会話の記録に出たときに、GitHub App の 1 時間の鍵を GitHub で失効させる（I225）。
# 使い方: bash scripts/claude/gh-app/revoke.sh
#           控えの 2 つ（token・token-readonly）の鍵を失効させ、無効になったこと（HTTP 401）を確かめてから控えを消す
#         bash scripts/claude/gh-app/revoke.sh --stdin
#           控えに無い鍵（取り直しの後に気づいた・別のセッションで出た）を標準入力から 1 行読み、その鍵を失効させる（控えは触らない）
# 鍵の値は引数・画面に出さない（GH_TOKEN の環境変数で本物の gh に渡す。入口を通さない＝入口が別の鍵に差し替えない）
# 終了コード: 0=すべて無効を確認（控えが無いものを含む）・1=無効を確かめられない鍵がある（控えは残す）・2=使い方の誤り
# テスト用: GH_APP_REAL_GH・GH_APP_CACHE_DIR で本物の gh と控えのフォルダを差し替えられる
# 手順書: docs/runbooks/github-app-setup.md「5.」
set -uo pipefail
REAL_GH="${GH_APP_REAL_GH:-/usr/bin/gh}"
CACHE_DIR="${GH_APP_CACHE_DIR:-${HOME}/.cache/github-app}"

usage() { echo "使い方: $0 [--stdin]" >&2; exit 2; }

# revoke_one <鍵>: 失効させ、その鍵で読みに行って 401 が返れば 0。
# 通信の失敗などで 401 を確かめられないときは 1（失効できていないのに「無効」と取り違えない）
revoke_one() {
  local out
  GH_TOKEN="$1" "$REAL_GH" api -X DELETE installation/token --silent > /dev/null 2>&1
  out="$(GH_TOKEN="$1" "$REAL_GH" api installation/repositories --silent 2>&1 > /dev/null)" && return 1
  [[ "$out" == *"HTTP 401"* ]]
}

FAILED="無効を確かめられませんでした。GitHub に届くかを確かめて流し直してください（docs/runbooks/github-app-setup.md「7.」「8.」）"

case "$#:${1:-}" in
  0:) ;;
  1:--stdin)
    [ -t 0 ] && echo "出た鍵を貼って Enter を押してください（画面には出ません）:" >&2
    leaked=""
    IFS= read -rs leaked || true
    leaked="${leaked//[[:space:]]/}"
    [ -n "$leaked" ] || { echo "revoke: 鍵が渡されませんでした" >&2; exit 2; }
    if revoke_one "$leaked"; then echo "渡された鍵: 失効を確認しました"; exit 0; fi
    echo "渡された鍵: $FAILED" >&2
    exit 1 ;;
  *) usage ;;
esac

rc=0
for name in token token-readonly; do
  f="$CACHE_DIR/$name"
  if [ ! -f "$f" ]; then echo "$name: 控えがありません"; continue; fi
  tok=""
  read -r _ tok < "$f" || true
  if [ -z "$tok" ]; then rm -f "$f"; echo "$name: 控えが空なので消しました"; continue; fi
  if revoke_one "$tok"; then
    rm -f "$f"
    echo "$name: 失効を確認して控えを消しました"
  else
    echo "$name: $FAILED（控えは残しました）" >&2
    rc=1
  fi
done
exit "$rc"
