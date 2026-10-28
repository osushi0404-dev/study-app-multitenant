#!/usr/bin/env bash
# check-tools.sh: ハーネスのテストが頼る道具を一覧（required-tools.txt）で確かめる（I204・I211）。
# 呼び出し元: run-all.sh の冒頭（CI の Harness Tests も手元も同じ。uv の環境で流れる）・手元の準備（docs/runbooks/onboarding.md）
# 使い方: bash scripts/claude/tests/check-tools.sh [一覧のパス]
# 版の列が lock の道具は、一覧と同じフォルダの正とぴったり比べる（python3 は .python-version、ほかは uv.lock）
# 終了コード: 全部そろっていれば 0、足りない・版が違う・版を読めない道具が 1 つでもあれば 1、一覧・版の正が読めない・行の形が違うと 2
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"   # 確かめるコマンドはリポジトリのルートで流す（git が無くても場所が決まる）
LIST="${1:-$HERE/required-tools.txt}"
LIST_DIR="$(cd "$(dirname "$LIST")" 2>/dev/null && pwd)"

trim() { local s="$1"; s="${s#"${s%%[![:space:]]*}"}"; s="${s%"${s##*[![:space:]]}"}"; printf '%s' "$s"; }
bad_list() { echo "⛔ $1" >&2; exit 2; }
bad_line() { bad_list "一覧の行の形が違います: $1"; }

if [ ! -f "$LIST" ] || [ ! -r "$LIST" ]; then bad_list "一覧を読めません: $LIST"; fi

# 版の正を WANT_V（版）・WANT_F（正のファイル）に入れる（$1=名前）。python3 は .python-version の 1 行目、
# ほかは uv.lock の [[package]] の name（小文字）の version。読めなければ 2 で止める
want_ver() {
  local f v
  if [ "$1" = python3 ]; then
    f="$LIST_DIR/.python-version"
    [ -r "$f" ] && IFS= read -r v < "$f"
  else
    f="$LIST_DIR/uv.lock"
    [ -r "$f" ] && v="$(awk -v n="\"${1,,}\"" '
      $0 == "[[package]]" { p = 0 }
      $1 == "name" && $3 == n { p = 1 }
      p && $1 == "version" { gsub(/"/, "", $3); print $3; exit }' "$f")"
  fi
  v="$(trim "${v:-}")"
  [ -n "$v" ] || bad_list "版の正が読めません: ${1}（${f}）"
  WANT_V="$v"; WANT_F="${f#"$ROOT"/}"
}

# 先に全部の行の形を確かめる（形の崩れた一覧で途中まで確かめない）
NAMES=(); PROBES=(); VERS=(); HOWS=()
while IFS= read -r line || [ -n "$line" ]; do
  t="$(trim "$line")"
  [ -z "$t" ] && continue
  [ "${t:0:1}" = "#" ] && continue
  cols=(); s="$t"
  while [[ "$s" == *" | "* ]]; do cols+=("$(trim "${s%% | *}")"); s="${s#* | }"; done
  cols+=("$(trim "$s")")
  [ "${#cols[@]}" -eq 4 ] || bad_line "$t"
  if [ -z "${cols[0]}" ] || [ -z "${cols[1]}" ]; then bad_line "$t"; fi
  [ "${cols[2]}" = "-" ] || [ "${cols[2]}" = "lock" ] || bad_line "$t"
  NAMES+=("${cols[0]}"); PROBES+=("${cols[1]}"); VERS+=("${cols[2]}"); HOWS+=("${cols[3]}")
done < "$LIST"
[ "${#NAMES[@]}" -gt 0 ] || bad_list "一覧に道具の行がありません: $LIST"

# 版の正も先に読む（読めなければ道具を確かめる前に 2 で止める）
WANTS=(); SRCS=()
for i in "${!NAMES[@]}"; do
  WANT_V=""; WANT_F=""
  [ "${VERS[$i]}" = lock ] && want_ver "${NAMES[$i]}"
  WANTS+=("$WANT_V"); SRCS+=("$WANT_F")
done

cd "$ROOT" || bad_list "リポジトリのルートに移れません: $ROOT"
missing=0
for i in "${!NAMES[@]}"; do
  name="${NAMES[$i]}"; probe="${PROBES[$i]}"; how="${HOWS[$i]}"
  out="$(timeout 300 bash -c "$probe" 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "⛔ 足りない道具: ${name}（\`${probe}\` が通らない）。入れ方: ${how}"
    [ -n "$out" ] && printf '%s\n' "$out" | tail -n 5 | sed 's/^/    /'
    missing=1; continue
  fi
  if [ "${VERS[$i]}" = "-" ]; then
    echo "OK: ${name} ${out%%$'\n'*}"; continue
  fi
  want="${WANTS[$i]}"; src="${SRCS[$i]}"
  if [[ "$out" =~ ([0-9]+(\.[0-9]+)+) ]]; then
    ver="${BASH_REMATCH[1]}"
  else
    echo "⛔ 版を読めない道具: ${name}（\`${probe}\` の出力に版が無い・正 ${want}）。入れ方: ${how}"
    missing=1; continue
  fi
  if [ "$ver" = "$want" ]; then
    echo "OK: ${name} ${ver}（正 ${src}）"
  else
    echo "⛔ 版が違う道具: ${name} ${ver}（正 ${want}・${src}）。入れ方: ${how}"
    missing=1
  fi
done
exit "$missing"
