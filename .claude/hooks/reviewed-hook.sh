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
#   I615: 写しの作り方の正はこのファイルの reviewed_snapshot（入口の起動役 .claude/hooks/unreviewed.py run も
#   `--snapshot` で同じ写しを使う）。写しは一時フォルダから mv -T で置き、置いてある写しを消さない（I610 F1）。
# 使い方: bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/reviewed-hook.sh scripts/claude/hooks/<名前>.py [引数…]
#         bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/reviewed-hook.sh --snapshot   （写しの最上位を出す。0／3=基準なし／4=作れない）
#   標準入力（フックの JSON）はそのままフックに渡す。写しの置き場所は ~/.cache/claude-reviewed-snapshots/<BASE>/
#   （サンドボックスから書けない。I610 までの ~/.cache/claude-reviewed-hooks/ は使わない）。BASE を求められないときは、作業ツリーのフックを動かし、理由を標準エラーに出す
#   （フック全体を止めると Claude が何もできなくなり、見張りも直せない。plan_I599.md R4）。
set -uo pipefail

# git は命令を動かす設定（.git/config はサンドボックスの中から書ける）を無効にして呼ぶ
_reviewed_git() {
  git -c core.fsmonitor=false -c core.hooksPath=/dev/null -c submodule.recurse=false -C "$1" "${@:2}"
}

# 写しを作る（I615・I610 F1）。一時フォルダに広げて .complete を置いてから mv -T で置く（途中の写しを見せない）。
# 置いてある写しは消さない（先に別の起動役が置いていれば、自分の一時の写しだけを消してそれを使う）。
# 戻り値 0＝写しあり（標準出力に場所）／4＝作れない。テストは有無の確かめを飛ばしてこれを直接呼ぶ（TC-05）
_reviewed_snapshot_make() {
  local root="$1" base="$2" cache="$3" snap tmp
  snap="$cache/$base"
  if mkdir -p "$cache" 2>/dev/null && chmod 700 "$cache" && tmp="$(mktemp -d "$cache/.tmp.XXXXXX" 2>/dev/null)"; then
    if _reviewed_git "$root" archive "$base" scripts/claude | tar -x -C "$tmp" && touch "$tmp/.complete"; then
      mv -T "$tmp" "$snap" 2>/dev/null || rm -rf "$tmp"
    else
      rm -rf "$tmp"
    fi
  fi
  if [ -f "$snap/.complete" ]; then
    printf '%s\n' "$snap"
    return 0
  fi
  echo "[reviewed-snapshot] レビュー済みの写しを作れません: $snap" >&2
  return 4
}

# 写しの作り方の正（I615）: BASE を求め、写しが無ければ作り、写しの最上位を標準出力に出す。
# 戻り値 0＝写しあり／3＝基準を求められない／4＝写しを作れない。写しは BASE ごとに 1 回だけ作る
reviewed_snapshot() {
  local root="$1" base cache
  if ! base="$(_reviewed_git "$root" merge-base HEAD origin/develop 2>/dev/null)" || [ -z "$base" ]; then
    echo "[reviewed-snapshot] レビュー済みの基準（merge-base HEAD origin/develop）を求められません" >&2
    return 3
  fi
  cache="${HOME}/.cache/claude-reviewed-snapshots"
  if [ -f "$cache/$base/.complete" ]; then   # 作った後は git を merge-base の 1 回しか呼ばない
    printf '%s\n' "$cache/$base"
    return 0
  fi
  _reviewed_snapshot_make "$root" "$base" "$cache"
}

_reviewed_main() {
  local root rel snap rc v
  root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
  # GIT_ の環境変数を外す（git の参照先・設定を差し替えさせない。組み込みだけで、毎回のツール呼び出しでプロセスを増やさない）
  for v in ${!GIT_*}; do unset "$v"; done
  if [ "${1:-}" = "--snapshot" ]; then   # 入口の起動役（.claude/hooks/unreviewed.py run）が写しの場所だけを受け取る
    reviewed_snapshot "$root" </dev/null
    return
  fi
  rel="${1:-}"
  case "$rel" in
    scripts/claude/hooks/*.py) ;;
    *) echo "[reviewed-hook] 使い方: reviewed-hook.sh scripts/claude/hooks/<名前>.py | reviewed-hook.sh --snapshot" >&2; return 2 ;;
  esac
  case "$rel" in *..*) echo "[reviewed-hook] パスに .. は使えません: $rel" >&2; return 2 ;; esac
  shift
  snap="$(reviewed_snapshot "$root" </dev/null)"
  rc=$?
  if [ "$rc" -eq 0 ] && [ -f "$snap/$rel" ]; then
    exec python3 -I "$snap/$rel" "$@"
  fi
  # 基準を求められない・写しを作れないときは、作業ツリーのフックを動かし、理由を出す（フック全体を止めると
  # Claude が何もできなくなり、見張りも直せない。plan_I599.md R4）
  # 理由（基準なし・作れない）は reviewed_snapshot が [reviewed-snapshot] の行で出している
  echo "[reviewed-hook] レビュー済みの写しで動かせないため、作業ツリーのフックを動かします（rc=$rc）: $rel" >&2
  exec python3 -I "$root/$rel" "$@"
}

# 直接実行したときだけ動く（読み込んだとき〔.〕は関数を定義するだけ・TC-05）
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  _reviewed_main "$@"
  exit $?
fi
