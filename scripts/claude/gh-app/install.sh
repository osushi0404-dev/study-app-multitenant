#!/usr/bin/env bash
# install.sh — GitHub App の鍵の仕組み（gh-app-token・gh の入口）をこの端末に入れる（I223）。
# 使い方: bash scripts/claude/gh-app/install.sh          # 入れる（前の版は ~/.cache/github-app/backup/ に写す）
#         bash scripts/claude/gh-app/install.sh --check  # 何も変えずに、入っているものと設定がそろっているかだけを見る
# 秘密の鍵ファイルは作らない・動かさない（docs/runbooks/github-app-setup.md の手順で人が置く）。
# 終了コード: 0=そろった（入れた）・1=前提が足りない／そろっていない（何も変えていないか、変えた所を出す）
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="${HOME}/.local/bin"
KEY="${GH_APP_KEY:-${HOME}/.config/github-app/app.pem}"
REAL_GH="${GH_APP_REAL_GH:-/usr/bin/gh}"
BACKUP="${GH_APP_CACHE_DIR:-${HOME}/.cache/github-app}/backup"
HELPER="!${BIN}/gh auth git-credential"
BOT_NAME='osushi0404-claude[bot]'
BOT_EMAIL='352511081+osushi0404-claude[bot]@users.noreply.github.com'
REPO="osushi0404-dev/${GH_APP_REPO:-study-app-multitenant}"
FILES=(gh-app-token gh)
HOSTS=(https://github.com https://gist.github.com)
MODE="${1:-install}"

ng=0
say() { echo "[gh-app/install] $*"; }
bad() { say "NG: $*"; ng=1; }

# ---- 前提（足りなければ何も変えずに止める）----
for c in openssl curl python3; do command -v "$c" >/dev/null 2>&1 || bad "$c がありません"; done
[ -x "$REAL_GH" ] || bad "本物の gh（$REAL_GH）がありません"
if [ ! -f "$KEY" ]; then
  bad "秘密の鍵ファイルがありません: $KEY（手順書の「秘密の鍵ファイルを置く」）"
elif [ "$(stat -c %a "$KEY")" != 600 ]; then
  bad "秘密の鍵ファイルの権限が 600 ではありません: $KEY（chmod 600）"
fi
first=""   # PATH で $BIN と /usr/bin のどちらが先に出るか
IFS=: read -ra parts <<< "$PATH"
for p in "${parts[@]}"; do
  if [ "$p" = "$BIN" ] || [ "$p" = /usr/bin ]; then first="$p"; break; fi
done
[ "$first" = "$BIN" ] || bad "PATH で $BIN が /usr/bin より前にありません"
if [ "$ng" -ne 0 ]; then say "前提が足りないので、何も変えずに止めました"; exit 1; fi

check() {
  local f rc=0
  for f in "${FILES[@]}"; do
    cmp -s "$HERE/$f" "$BIN/$f" || { say "NG: $BIN/$f がリポジトリの版と違います"; rc=1; }
  done
  local h
  for h in "${HOSTS[@]}"; do
    [ "$(git config --global --get-all "credential.${h}.helper" | tail -1)" = "$HELPER" ] \
      || { say "NG: credential.${h}.helper の最後が「${HELPER}」ではありません"; rc=1; }
  done
  [ "$(git -C "$HERE" config user.name)" = "$BOT_NAME" ] || { say "NG: git の作者の名前が ${BOT_NAME} ではありません"; rc=1; }
  [ "$(git -C "$HERE" config user.email)" = "$BOT_EMAIL" ] || { say "NG: git の作者のメールが ${BOT_EMAIL} ではありません"; rc=1; }
  return "$rc"
}

if [ "$MODE" = --check ]; then
  if check; then say "そろっています"; exit 0; fi
  exit 1
fi
if [ "$MODE" != install ]; then say "使い方: $0 [--check]"; exit 1; fi

# ---- 入れる ----
mkdir -p "$BIN"
stamp=$(date +%Y%m%d%H%M%S)
for f in "${FILES[@]}"; do
  if [ -e "$BIN/$f" ] && ! cmp -s "$HERE/$f" "$BIN/$f"; then
    (umask 077; mkdir -p "$BACKUP") && cp -p "$BIN/$f" "$BACKUP/$f.$stamp" && say "前の版を写しました: $BACKUP/$f.$stamp"
  fi
  install -m 755 "$HERE/$f" "$BIN/$f"
done
for h in "${HOSTS[@]}"; do
  git config --global --replace-all "credential.${h}.helper" ''
  git config --global --add "credential.${h}.helper" "$HELPER"
done
git -C "$HERE" config user.name "$BOT_NAME"
git -C "$HERE" config user.email "$BOT_EMAIL"

if ! check; then say "入れた後の確かめが合いません"; exit 1; fi
# 疎通（読むだけ）
if name=$("$BIN/gh" api "repos/${REPO}" --jq .full_name 2>/dev/null); then
  say "入れました（GitHub への疎通: ${name}）"
else
  say "NG: 入れましたが、GitHub に読みに行けません（鍵ファイル・App の Installation を確かめてください）"; exit 1
fi
