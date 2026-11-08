#!/usr/bin/env bash
# issue-source.sh — I### のイシュー本文が「手元のイシューファイル」と「GitHub」のどちらにあるかを 1 か所で決める（I221）
#
# 使い方: bash scripts/claude/issue-source.sh <path|body|snapshot|gh-number> I###
#   path      手元のイシューファイル（open → closed）のパスを出す。無ければ exit 1
#   body      本文を出す（手元のファイルがあればその中身。無く I${NEW_ISSUE_MIN} 以上なら GitHub の本文）
#   snapshot  /plan-issue 用。手元のファイルがあればそのパス。無く I${NEW_ISSUE_MIN} 以上なら
#             GitHub の本文の写しを docs/issues/open/I###.md に書いてそのパスを出す（同期しない・正は GitHub）
#   gh-number GitHub のイシュー番号を出す（手元のファイルなら「GitHub Issue: #N」の行・新しいイシューなら番号そのもの）
#
# 番号の決まり（docs/runbooks/workflow.md「イシューの置き場所」）:
#   - I${NEW_ISSUE_MIN} 以上で手元のファイルが無いもの = GitHub だけで管理する新しいイシュー（I＋GitHub の番号）
#   - それ未満 = 手元のイシューファイルで管理する番号。ファイルが無ければ GitHub を読まずに止める
#     （別のワークツリーにしか無い I196 で GitHub の #196 を黙って読まないため）
#   - GitHub の題名が「I###: 」で始まるもの（今までの流れで起票したもの）も新しいイシューとして扱わない
# 基準のフォルダはカレントディレクトリの git ルート（スクリプトの置き場所ではない）。
# 終了コード: 0=成功 / 1=path で手元のファイルが無い / 2=使えない（引数・番号・gh の失敗・PR の番号など）
set -uo pipefail

NEW_ISSUE_MIN=427

die() { echo "⛔ issue-source: $*" >&2; exit 2; }

CMD="${1:-}"
ISSUE="${2:-}"
case "$CMD" in path|body|snapshot|gh-number) ;; *) die "使い方: issue-source.sh <path|body|snapshot|gh-number> I###" ;; esac
[[ "$ISSUE" =~ ^I[0-9]{3,}$ ]] || die "不正なイシュー番号です（期待する形: I###）: '${ISSUE}'"
NUM=$((10#${ISSUE#I}))

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || die "git リポジトリの中で実行してください"
cd "$ROOT" || die "git ルートに移れません: $ROOT"

FETCHED="" TMP_COPY="" TITLE=""
trap 'rm -f "$FETCHED" "$TMP_COPY"' EXIT

# 手元のイシューファイル（open → closed）。無ければ空
LOCAL=""
for f in "docs/issues/open/${ISSUE}.md" "docs/issues/closed/${ISSUE}.md"; do
  if [ -f "$f" ]; then LOCAL="$f"; break; fi
done

# GitHub の JSON の 1 項目をそのまま出す（jq は前提の道具に無いので python3 を使う。末尾に改行を足さない）
field() {
  python3 -I -c 'import json, sys
v = json.load(open(sys.argv[1], encoding="utf-8")).get(sys.argv[2])
sys.stdout.write(v if isinstance(v, str) else "")' "$FETCHED" "$1"
}

# GitHub のイシューを 1 回だけ読み、PR の番号・今までの流れのイシューを拒否する（JSON は一時ファイル、題名は TITLE）
fetch() {
  local url
  FETCHED="$(mktemp)" || die "一時ファイルを作れません"
  gh issue view "$NUM" --json url,title,body > "$FETCHED" || die "gh issue view ${NUM} に失敗しました"
  url="$(field url)" || die "gh の出力を読めません"
  [[ "$url" =~ /issues/${NUM}$ ]] || die "#${NUM} はイシューではありません（${url}）"
  TITLE="$(field title)" || die "gh の出力を読めません"
  [[ "$TITLE" =~ ^I[0-9]{3,}:\  ]] \
    && die "#${NUM} は今までの流れ（自前の番号）で起票したイシューです。題名の I### のイシューファイルで扱ってください"
  return 0
}

if [ "$CMD" = "path" ]; then
  [ -n "$LOCAL" ] || exit 1
  printf '%s\n' "$LOCAL"
  exit 0
fi

# 手元のファイルがある: 今までの流れ（GitHub を読まない）
if [ -n "$LOCAL" ]; then
  case "$CMD" in
    body) cat "$LOCAL" ;;
    snapshot) printf '%s\n' "$LOCAL" ;;
    gh-number)
      n="$(grep -oE 'GitHub Issue: #[0-9]+' "$LOCAL" | head -n 1 | grep -oE '[0-9]+$')"
      [ -n "$n" ] || die "${LOCAL} に「GitHub Issue: #番号」の行がありません"
      printf '%s\n' "$n"
      ;;
  esac
  exit 0
fi

# 手元のファイルが無い: 新しいイシューの番号でなければ GitHub を読まずに止める
[ "$NUM" -ge "$NEW_ISSUE_MIN" ] \
  || die "${ISSUE} は手元のイシューファイルで管理する番号（I${NEW_ISSUE_MIN} 未満）。ファイルが見つかりません。そのファイルのあるワークツリーで実行してください"

case "$CMD" in
  gh-number) printf '%s\n' "$NUM" ;;
  body)
    fetch
    field body || die "本文を取り出せません"
    ;;
  snapshot)
    fetch
    dest="docs/issues/open/${ISSUE}.md"
    mkdir -p docs/issues/open || die "docs/issues/open を作れません"
    TMP_COPY="$(mktemp "docs/issues/open/.${ISSUE}.XXXXXX")" || die "一時ファイルを作れません"
    {
      printf '# %s: %s\n\n' "$ISSUE" "${TITLE//$'\n'/ }"
      printf '> GitHub #%s の本文の写し（%s に /plan-issue が作成）。正は GitHub のイシュー。この写しは同期しない。\n' \
        "$NUM" "$(date -u '+%Y-%m-%d %H:%M UTC')"
      printf '> - GitHub Issue: #%s\n\n' "$NUM"
      field body
    } > "$TMP_COPY" || die "写しを書けません"
    mv "$TMP_COPY" "$dest" || die "写しを置けません: $dest"
    printf '%s\n' "$dest"
    ;;
esac
