#!/usr/bin/env bash
# check-tools.sh: ハーネスのテストが頼る道具を一覧（required-tools.txt）で確かめる（I204）。
# 呼び出し元: run-all.sh の冒頭（CI の Harness Tests も手元も同じ）・.github/workflows/ci.yml（--pip-specs）・手元の準備（docs/runbooks/onboarding.md）
# 使い方: bash scripts/claude/tests/check-tools.sh [一覧のパス]
#         bash scripts/claude/tests/check-tools.sh --pip-specs [一覧のパス]   # CI で pip で入れるものを 1 行ずつ出す（道具は確かめない）
# 終了コード: 全部そろっていれば 0、足りない・古い・版を読めない道具が 1 つでもあれば 1、一覧が読めない・行の形が違うと 2
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"   # 確かめるコマンドはリポジトリのルートで流す（git が無くても場所が決まる）
MODE=check
if [ "${1:-}" = "--pip-specs" ]; then MODE=pip; shift; fi
LIST="${1:-$HERE/required-tools.txt}"

VER_RE='^[0-9]+(\.[0-9]+)*$'
# pip の列は「名前＋>= か ==＋版」だけ（-i・--extra-index-url・URL・-e などの pip の指定を CI の pip に渡さない）
PIP_RE='^[A-Za-z0-9][A-Za-z0-9._-]*(>=|==)[0-9]+(\.[0-9]+)*$'

trim() { local s="$1"; s="${s#"${s%%[![:space:]]*}"}"; s="${s%"${s##*[![:space:]]}"}"; printf '%s' "$s"; }
# 一覧の誤りは標準エラーに出す（--pip-specs の出力〔CI が pip に渡す〕に混ぜない）
bad_list() { echo "⛔ $1" >&2; exit 2; }
bad_line() { bad_list "一覧の行の形が違います: $1"; }

if [ ! -f "$LIST" ] || [ ! -r "$LIST" ]; then bad_list "一覧を読めません: $LIST"; fi

# 先に全部の行の形を確かめる（形の崩れた一覧で途中まで確かめない・--pip-specs で一部だけ出さない）
NAMES=(); PROBES=(); MINS=(); PIPS=(); HOWS=()
while IFS= read -r line || [ -n "$line" ]; do
  t="$(trim "$line")"
  [ -z "$t" ] && continue
  [ "${t:0:1}" = "#" ] && continue
  cols=(); s="$t"
  while [[ "$s" == *" | "* ]]; do cols+=("$(trim "${s%% | *}")"); s="${s#* | }"; done
  cols+=("$(trim "$s")")
  [ "${#cols[@]}" -eq 5 ] || bad_line "$t"
  if [ -z "${cols[0]}" ] || [ -z "${cols[1]}" ]; then bad_line "$t"; fi
  [ "${cols[2]}" = "-" ] || [[ "${cols[2]}" =~ $VER_RE ]] || bad_line "$t"
  [ "${cols[3]}" = "-" ] || [[ "${cols[3]}" =~ $PIP_RE ]] || bad_line "$t"
  NAMES+=("${cols[0]}"); PROBES+=("${cols[1]}"); MINS+=("${cols[2]}"); PIPS+=("${cols[3]}"); HOWS+=("${cols[4]}")
done < "$LIST"
[ "${#NAMES[@]}" -gt 0 ] || bad_list "一覧に道具の行がありません: $LIST"

if [ "$MODE" = pip ]; then
  for p in "${PIPS[@]}"; do [ "$p" = "-" ] || printf '%s\n' "$p"; done
  exit 0
fi

cd "$ROOT" || bad_list "リポジトリのルートに移れません: $ROOT"
missing=0
for i in "${!NAMES[@]}"; do
  name="${NAMES[$i]}"; probe="${PROBES[$i]}"; min="${MINS[$i]}"; how="${HOWS[$i]}"
  out="$(timeout 300 bash -c "$probe" 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "⛔ 足りない道具: ${name}（\`${probe}\` が通らない）。入れ方: ${how}"
    printf '%s\n' "$out" | tail -n 5 | sed 's/^/    /'
    missing=1; continue
  fi
  if [ "$min" = "-" ]; then
    echo "OK: ${name} ${out%%$'\n'*}"; continue
  fi
  if [[ "$out" =~ ([0-9]+(\.[0-9]+)+) ]]; then
    ver="${BASH_REMATCH[1]}"
  else
    echo "⛔ 版を読めない道具: ${name}（\`${probe}\` の出力に版が無い・下限 ${min}）。入れ方: ${how}"
    missing=1; continue
  fi
  if printf '%s\n%s\n' "$min" "$ver" | sort -V -C; then
    echo "OK: ${name} ${ver}（下限 ${min}）"
  else
    echo "⛔ 版が古い道具: ${name} ${ver}（下限 ${min}）。入れ方: ${how}"
    missing=1
  fi
done
exit "$missing"
