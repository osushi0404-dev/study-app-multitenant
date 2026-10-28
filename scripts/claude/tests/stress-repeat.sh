#!/usr/bin/env bash
# stress-repeat.sh <回数> <テストのスクリプト> [<負荷のプロセスの数（既定 nproc）>]
#   CPU を使い切るループを負荷の数だけ背景で動かし、テストを回数だけ順に流す（I210。実行の速さで結果が揺れないかを確かめる）。
#   毎回 RUN <n>: PASS|FAIL、最後に STRESS: <合格>/<回数> を出す。
# 終了コード: 0=全部合格 / 1=1 回でも失敗 / 2=使い方の誤り
# test_ で始まらないので run-all.sh（CI）は流さない。使う場面: plan_I210.md 手動 No.1
set -uo pipefail

N="${1:-}"; T="${2:-}"; LOAD="${3:-$(nproc)}"
if ! [[ "$N" =~ ^[1-9][0-9]*$ ]] || [ ! -f "$T" ] || ! [[ "$LOAD" =~ ^[0-9]+$ ]]; then
  echo "使い方: $0 <回数（1 以上）> <テストのスクリプト> [<負荷のプロセスの数>]" >&2
  exit 2
fi

LOAD_PIDS=()
# shellcheck disable=SC2317  # trap から呼ぶ
stop_load() { [ "${#LOAD_PIDS[@]}" -eq 0 ] || kill "${LOAD_PIDS[@]}" 2>/dev/null; wait 2>/dev/null; }
trap stop_load EXIT
trap 'exit 130' INT TERM
for _ in $(seq 1 "$LOAD"); do ( while :; do :; done ) & LOAD_PIDS+=("$!"); done

ok=0
for i in $(seq 1 "$N"); do
  if bash "$T" > /dev/null 2>&1; then ok=$((ok + 1)); echo "RUN ${i}: PASS"; else echo "RUN ${i}: FAIL"; fi
done
echo "STRESS: ${ok}/${N}"
[ "$ok" -eq "$N" ]
