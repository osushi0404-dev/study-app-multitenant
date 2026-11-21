#!/usr/bin/env bash
# I599（plan_I599.md 4-2）: フックを、レビュー済みの中身で動かす起動役。
#   フック（.claude/settings.json の hooks）はサンドボックスの外で動く。このブランチが develop から分かれた時点
#   （git merge-base HEAD origin/develop＝BASE）の scripts/claude の写しでフックを動かす（書き換えた見張りは、
#   マージされるまで外で動かない）。
#   I610: 変更が無くても写しで動かす（「変更があるか」の判定は持たない。差分・未追跡・git が無視するファイルの
#   数え方の食い違いを、判定ごと無くす）。作業ツリーのフックを動かすのは、BASE を求められない・写しを作れない
#   ときだけ（理由を標準エラーに出す）。写しは BASE ごとに 1 回だけ作る。フックは python3 -I で起こす
#   （スクリプトの置き場所・PYTHONPATH・利用者の site を読み込み先にしない）。
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
  exec python3 -I "$root/$rel" "$@"
fi

cache="${HOME}/.cache/claude-reviewed-hooks"
snap="$cache/$base"
# 写しがあればそれで動かす（BASE ごとに 1 回作った後は、git を呼ばない）
if [ -f "$snap/.complete" ] && [ -f "$snap/$rel" ]; then
  exec python3 -I "$snap/$rel" "$@"
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
  exec python3 -I "$root/$rel" "$@"
fi
exec python3 -I "$snap/$rel" "$@"
