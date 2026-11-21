#!/usr/bin/env bash
# I599（plan_I599.md 4-2）: フックを、レビュー済みの中身で動かす起動役。
#   フック（.claude/settings.json の hooks）はサンドボックスの外で動く。scripts/claude/ に、このブランチが develop から
#   分かれた時点（git merge-base HEAD origin/develop＝BASE）と違う中身があるあいだは、BASE の scripts/claude の写しで
#   フックを動かす（書き換えた見張りは、マージされるまで外で動かない）。違いが無ければ作業ツリーのフックを動かす。
#   置き場所が .claude/hooks/ なのは、サンドボックスから書けず、Edit は承認が要るため（scripts/claude/ に置くと、
#   起動役そのものを書き換えられる）。
# 使い方: bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/reviewed-hook.sh scripts/claude/hooks/<名前>.py [引数…]
#   標準入力（フックの JSON）はそのままフックに渡す。写しの置き場所は ~/.cache/claude-reviewed-hooks/<BASE>/
#   （サンドボックスから書けない）。BASE を求められないときは、作業ツリーのフックを動かし、理由を標準エラーに出す
#   （フック全体を止めると Claude が何もできなくなり、見張りも直せない。plan_I599.md R4）。
set -uo pipefail

rel="${1:-}"
case "$rel" in
  scripts/claude/hooks/*.py) ;;
  *) echo "[reviewed-hook] 使い方: reviewed-hook.sh scripts/claude/hooks/<名前>.py" >&2; exit 2 ;;
esac
case "$rel" in *..*) echo "[reviewed-hook] パスに .. は使えません: $rel" >&2; exit 2 ;; esac
shift
root="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# .git/config はサンドボックスの中から書けるので、命令を動かす git の設定を無効にし、GIT_ の環境変数を外す
while IFS= read -r v; do unset "$v"; done < <(compgen -e | grep '^GIT_' || true)
g=(git -c core.fsmonitor=false -c core.hooksPath=/dev/null -c submodule.recurse=false -C "$root")

if ! base="$("${g[@]}" merge-base HEAD origin/develop 2>/dev/null)" || [ -z "$base" ]; then
  echo "[reviewed-hook] レビュー済みの基準（merge-base HEAD origin/develop）を求められないため、作業ツリーのフックを動かします: $rel" >&2
  exec python3 "$root/$rel" "$@"
fi

cache="${HOME}/.cache/claude-reviewed-hooks"
snap="$cache/$base"
# 写しがあればそれで動かす（変更が無いときも中身は作業ツリーと同じ。毎回の git の差の確かめを省く）
if [ -f "$snap/.complete" ] && [ -f "$snap/$rel" ]; then
  exec python3 "$snap/$rel" "$@"
fi
if "${g[@]}" diff --quiet --no-ext-diff --no-textconv "$base" -- scripts/claude 2>/dev/null \
    && [ -z "$("${g[@]}" ls-files --others --exclude-standard -- scripts/claude 2>/dev/null)" ]; then
  exec python3 "$root/$rel" "$@"
fi

if [ ! -f "$snap/.complete" ]; then
  mkdir -p "$cache" && chmod 700 "$cache"
  tmp="$(mktemp -d "$cache/.tmp.XXXXXX")" || tmp=""
  if [ -n "$tmp" ] && "${g[@]}" archive "$base" scripts/claude | tar -x -C "$tmp" && touch "$tmp/.complete"; then
    rm -rf "$snap"
    mv -T "$tmp" "$snap" 2>/dev/null || rm -rf "$tmp"   # 同時に作られたときは先の写しを使う
  else
    [ -n "$tmp" ] && rm -rf "$tmp"
  fi
fi
if [ ! -f "$snap/.complete" ] || [ ! -f "$snap/$rel" ]; then
  echo "[reviewed-hook] レビュー済みの写しを作れないため、作業ツリーのフックを動かします: $rel" >&2
  exec python3 "$root/$rel" "$@"
fi
exec python3 "$snap/$rel" "$@"
