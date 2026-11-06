#!/usr/bin/env bash
# 鍵が画面・会話の記録に出たときに、GitHub App の 1 時間の鍵を GitHub で失効させる（I225）。
# 使い方: bash scripts/claude/gh-app/revoke.sh
#           控えの 2 つ（token・token-readonly）の鍵を失効させ、無効になったこと（HTTP 401）を確かめてから控えを消す。
#           もともと無効な控え（期限切れ・失効済み）は、そう出して控えを消す
#         bash scripts/claude/gh-app/revoke.sh --stdin
#           控えに無い鍵（取り直しの後に気づいた・別のセッションで出た）を標準入力から 1 行読み、その鍵を失効させる（控えは触らない）
# 失効の前にも同じ鍵で読みに行き、有効を確かめてから失効させる（もともと無効な鍵を「失効を確認」と取り違えない・I226）
# 鍵の値は引数・画面に出さない（GH_TOKEN の環境変数で本物の gh に渡す。入口を通さない＝入口が別の鍵に差し替えない）
# 終了コード: 0=すべて無効を確認（控えが無いもの・もともと無効な控えを含む）・
#             1=無効を確かめられない鍵がある（控えは残す）、または --stdin の鍵が最初から無効（貼り間違いの疑い）・2=使い方の誤り
# テスト用: GH_APP_REAL_GH・GH_APP_CACHE_DIR で本物の gh と控えのフォルダを差し替えられる
# 手順書: docs/runbooks/github-app-setup.md「5.」
set -uo pipefail
REAL_GH="${GH_APP_REAL_GH:-/usr/bin/gh}"
CACHE_DIR="${GH_APP_CACHE_DIR:-${HOME}/.cache/github-app}"

usage() { echo "使い方: $0 [--stdin]" >&2; exit 2; }

# token_state <鍵>: その鍵で読みに行く。0=有効（読めた）・1=無効（HTTP 401）・2=確かめられない（通信の失敗など）
token_state() {
  local out
  out="$(GH_TOKEN="$1" "$REAL_GH" api installation/repositories --silent 2>&1 > /dev/null)" && return 0
  [[ "$out" == *"HTTP 401"* ]] && return 1
  return 2
}

# revoke_one <鍵>: 0=失効させ、無効（401）を確かめた・3=失効の前から無効（期限切れ・失効済み・貼り間違い。DELETE はしない）・
# 1=確かめられない（通信の失敗など。失効できていないのに「無効」と取り違えない）
revoke_one() {
  token_state "$1"
  case $? in 0) ;; 1) return 3 ;; *) return 1 ;; esac
  GH_TOKEN="$1" "$REAL_GH" api -X DELETE installation/token --silent > /dev/null 2>&1
  token_state "$1"
  [ $? = 1 ]
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
    revoke_one "$leaked"; rc=$?
    case "$rc" in
      0) echo "渡された鍵: 失効を確認しました"; exit 0 ;;
      3) echo "渡された鍵: この鍵は最初から無効でした。貼り間違い（末尾の欠け）がないか確かめてください。すでに失効済みなら対応は不要です" >&2 ;;
      *) echo "渡された鍵: $FAILED" >&2 ;;
    esac
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
  revoke_one "$tok"; r=$?
  case "$r" in
    0) rm -f "$f"; echo "$name: 失効を確認して控えを消しました" ;;
    3) rm -f "$f"; echo "$name: もともと無効でした（期限切れ・失効済み）。控えを消しました" ;;
    *) echo "$name: $FAILED（控えは残しました）" >&2; rc=1 ;;
  esac
done
exit "$rc"
