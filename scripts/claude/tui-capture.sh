#!/usr/bin/env bash
set -uo pipefail
# tui-capture: 対話画面（TUI）にだけ出る表示（/ の候補・ステータス行・ダイアログなど）を、tmux で起動した claude の
# 画面を読んで、Claude が人に頼まずに確かめる（I195）。
# Usage: tui-capture.sh [--wait <秒>] [--start-timeout <秒>] <入力> [<入力> ...]
#   - claude（通常モード〔--permission-mode manual。check-permission-prompt.sh と同じ〕・リポジトリのルート）を tmux の中で起動し（200x50）、プロンプトの行（行頭の ❯）が出るまで待つ
#     （--start-timeout 秒〔既定 30〕で出なければ 2）
#   - 入力を前から 1 つずつ送る（間は 0.5 秒）。ふつうの入力は文字のまま送る（send-keys -l --）。
#     {Enter} {Escape} {Tab} {Up} {Down} {BSpace} の 6 つだけはキーとして送る（ほかの {…} は文字）
#   - 最後の入力から --wait 秒（既定 2）待って画面を読み、標準出力に出す。終わるときは必ずセッションを閉じる
#   - 注意: {Enter} を送ると中の claude が動き、費用がかかり、通常モードの許可の範囲でツールを使う。
#     候補や画面の表示を見るだけなら {Enter} を送らない
#   - ! で始まる入力は送らない（claude の ! はシェルのコマンドを許可を通さずに動かすため）。
#     普通の書き方の事故を止めるためのもので、わざと避ける書き方は対象にしない
#   - 起動するコマンドは固定（引数で変えられない）。tmux を直接使う広い許可（Bash(tmux *)）を足さないための入口
# 終了コード: 0=画面を読めた・2=使い方の誤り／! の入力／tmux・claude が無い／起動しない
# 計画: docs/plans/open/plan_I195.md 4.1

err() { echo "[tui-capture] $*" >&2; exit 2; }

WAIT=2
START_TIMEOUT=30
while [ $# -gt 0 ]; do
  case "$1" in
    --wait)
      [[ "${2:-}" =~ ^[0-9]+(\.[0-9]+)?$ ]] || err "--wait は秒の数で指定してください"
      WAIT="$2"; shift 2;;
    --start-timeout)
      [[ "${2:-}" =~ ^[0-9]+$ ]] || err "--start-timeout は秒の整数で指定してください"
      START_TIMEOUT="$2"; shift 2;;
    *) break;;
  esac
done
[ $# -gt 0 ] || err "使い方: $0 [--wait <秒>] [--start-timeout <秒>] <入力> [<入力> ...]"
for x in "$@"; do
  if [[ "$x" =~ ^[[:space:]]*! ]]; then err "! で始まる入力は送りません（シェルのコマンドを動かすため）: $x"; fi
done
command -v tmux >/dev/null 2>&1 || err "tmux がありません"
command -v claude >/dev/null 2>&1 || err "claude がありません"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || err "git のワークツリー内で実行してください"

S="tui-capture-$$"
trap 'tmux kill-session -t "$S" >/dev/null 2>&1' EXIT
tmux new-session -d -s "$S" -x 200 -y 50 -c "$ROOT" "claude --permission-mode manual" || err "tmux のセッションを起動できません"

PROMPT_RE=$'(^|\n)❯'
waited=0
until [[ "$(tmux capture-pane -p -t "$S" 2>/dev/null)" =~ $PROMPT_RE ]]; do
  [ "$waited" -lt "$START_TIMEOUT" ] || err "claude のプロンプトが ${START_TIMEOUT} 秒たっても出ません"
  sleep 1; waited=$((waited + 1))
done

first=1
for x in "$@"; do
  [ "$first" = 1 ] || sleep 0.5
  first=0
  case "$x" in
    '{Enter}'|'{Escape}'|'{Tab}'|'{Up}'|'{Down}'|'{BSpace}')
      tmux send-keys -t "$S" "${x:1:-1}" || err "キーを送れません: $x";;
    *)
      tmux send-keys -t "$S" -l -- "$x" || err "入力を送れません: $x";;
  esac
done

sleep "$WAIT"
tmux capture-pane -p -t "$S" || err "画面を読めません"
