#!/usr/bin/env bash
# issue-source.sh — I### のイシュー本文が「手元のイシューファイル」と「GitHub」のどちらにあるかを 1 か所で決める（I221）
#
# 使い方: bash scripts/claude/issue-source.sh <path|body|raw-body|snapshot|gh-number> I###
#   path      手元のイシューファイル（open → closed）のパスを出す。無ければ exit 1
#   body      本文を出す（手元のファイルがあればその中身。無く I${NEW_ISSUE_MIN} 以上なら GitHub の本文と、
#             その後ろにコメントの節「## GitHub のコメント」〔コメントが 1 件以上のときだけ〕）
#   raw-body  GitHub に書き戻す下書き用（/grill-me）。本文だけを出す（コメントも写しの見出しも付けない）。
#             手元のファイルが今までのイシューファイルならその中身、無いか本文の写しなら GitHub の本文
#   snapshot  /plan-issue 用。手元のファイルがあればそのパス。無く I${NEW_ISSUE_MIN} 以上なら
#             GitHub の本文の写し（body と同じ中身）を docs/issues/open/I###.md に書いてそのパスを出す（同期しない・正は GitHub）
#   gh-number GitHub のイシュー番号を出す（手元のファイルなら「GitHub Issue: #N」の行・新しいイシューなら番号そのもの）
#
# コメント（I639）: 各コメントを「### <日時> @<login>（<立場>）」と、1 行ずつ「> 」を付けた引用で出す（本文の「## 」の
#   見出しの切り出し〔check-memo-body-paths.sh〕と混ざらないため）。中身を出すのは立場が TRUSTED_ASSOCIATIONS の人だけ
#   （公開リポジトリで誰でもコメントできるため）。隠されたコメントも中身を出さない。改行は LF にそろえる。
#
# 番号の決まり（docs/runbooks/issue-flow.md「イシューの番号と置き場所（I221）」）:
#   - I${NEW_ISSUE_MIN} 以上で手元のファイルが無いもの = GitHub だけで管理する新しいイシュー（I＋GitHub の番号）
#   - それ未満 = 手元のイシューファイルで管理する番号。ファイルが無ければ GitHub を読まずに止める
#     （別のワークツリーにしか無い I196 で GitHub の #196 を黙って読まないため）
#   - GitHub の題名が「I###: 」で始まるもの（今までの流れで起票したもの）も新しいイシューとして扱わない
# 基準のフォルダはカレントディレクトリの git ルート（スクリプトの置き場所ではない）。
# 終了コード: 0=成功 / 1=path で手元のファイルが無い / 2=使えない（引数・番号・gh の失敗・PR の番号など）
set -uo pipefail

NEW_ISSUE_MIN=427
# コメントの中身を出す立場（GitHub の authorAssociation）。それ以外の人のコメントは、あることと書いた人だけを出す
TRUSTED_ASSOCIATIONS="OWNER,MEMBER,COLLABORATOR,CONTRIBUTOR"

die() { echo "⛔ issue-source: $*" >&2; exit 2; }

CMD="${1:-}"
ISSUE="${2:-}"
case "$CMD" in path|body|raw-body|snapshot|gh-number) ;; *) die "使い方: issue-source.sh <path|body|raw-body|snapshot|gh-number> I###" ;; esac
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

# 手元のファイルが、このスクリプトの書いた本文の写しか（3 行目の注記。本文は 6 行目からなので本文の中身では当たらない）。
# 人が注記を直して外れたときは、今までのイシューファイルとして扱う
is_snapshot() { case "$(sed -n 3p "$1")" in "> GitHub #${NUM} の本文の写し（"*) return 0 ;; esac; return 1; }

# GitHub の JSON から本文を組み立てる（jq は前提の道具に無いので python3 を使う。シェルに通さない。末尾に改行を足さない）
# $1 = body（コメントの節を付ける）／raw（本文だけ）
render() {
  python3 -I - "$FETCHED" "$1" "$TRUSTED_ASSOCIATIONS" <<'PY'
import datetime, json, sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
mode = sys.argv[2]
trusted = set(sys.argv[3].split(","))


def lf(s): return s.replace("\r\n", "\n").replace("\r", "\n")


def text(v):
    return v if isinstance(v, str) else ""


body = lf(text(data.get("body")))
comments = data.get("comments") or []
out = [body]
if mode == "body" and comments:
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [body.rstrip("\n"), f"\n\n## GitHub のコメント（{len(comments)} 件・読んだ時点 {now}・同期しない）\n"]
    for c in comments:
        login = text((c.get("author") or {}).get("login")) or "ghost"
        assoc = text(c.get("authorAssociation")) or "NONE"
        out.append(f"\n### {text(c.get('createdAt')) or '-'} @{login}（{assoc}）\n\n")
        if c.get("isMinimized"):
            shown = f"（中身は出さない: 隠されたコメント（{text(c.get('minimizedReason')) or '理由なし'}））"
        elif assoc not in trusted:
            shown = f"（中身は出さない: 立場が {assoc} の人のコメント。要るならユーザーに確かめる）"
        else:
            shown = lf(text(c.get("body"))).strip("\n")
        out.append("\n".join(("> " + line) if line else ">" for line in shown.split("\n")) + "\n")
sys.stdout.write("".join(out))
PY
}

# GitHub のイシューを 1 回だけ読み、PR の番号・今までの流れのイシューを拒否する（JSON は一時ファイル、題名は TITLE）
fetch() {
  local url
  FETCHED="$(mktemp)" || die "一時ファイルを作れません"
  gh issue view "$NUM" --json url,title,body,comments > "$FETCHED" || die "gh issue view ${NUM} に失敗しました"
  # url と題名を 1 回で読む（題名の改行は空白にする）
  { IFS= read -r url && IFS= read -r TITLE; } < <(python3 -I -c 'import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
for k in ("url", "title"):
    v = d.get(k)
    print((v if isinstance(v, str) else "").replace("\r", " ").replace("\n", " "))' "$FETCHED") \
    || die "gh の出力を読めません"
  [[ "$url" =~ /issues/${NUM}$ ]] || die "#${NUM} はイシューではありません（${url}）"
  [[ "$TITLE" =~ ^I[0-9]{3,}:\  ]] \
    && die "#${NUM} は今までの流れ（自前の番号）で起票したイシューです。題名の I### のイシューファイルで扱ってください"
  return 0
}

if [ "$CMD" = "path" ]; then
  [ -n "$LOCAL" ] || exit 1
  printf '%s\n' "$LOCAL"
  exit 0
fi

# 書き戻しの下書き: 今までのイシューファイルならその中身。写しなら GitHub の本文（下の新しいイシューの道へ）
if [ "$CMD" = "raw-body" ] && [ -n "$LOCAL" ]; then
  if is_snapshot "$LOCAL"; then LOCAL=""; else cat "$LOCAL"; exit 0; fi
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
  body|raw-body)
    fetch
    render "${CMD%-body}" || die "本文を取り出せません"   # body → body／raw-body → raw
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
      render body
    } > "$TMP_COPY" || die "写しを書けません"
    mv "$TMP_COPY" "$dest" || die "写しを置けません: $dest"
    printf '%s\n' "$dest"
    ;;
esac
