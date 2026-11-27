#!/usr/bin/env bash
# check-plan-followups.sh — 計画書で「別イシュー」「後続」に回した行に番号が付いているかを確かめる（I639）
#
# 使い方: bash scripts/claude/check-plan-followups.sh I###
#   計画書は git ルートの docs/plans/{open,closed}/plan_I###.md（連番 plan_I###_N.md があれば最新）。呼び出し元は retro の手順 4-1。
# 拾う行（全部に当たるもの）:
#   - DEFER_RE の語を含む（「起票」は話題として出ることが多く誤検出が多いので入れない・plan_I639.md 調査結果 6）
#   - 自分の番号（I###）を除いて、#数字 も I数字 3 桁以上 も含まない
#   - OPT_OUT の印を含まない（後に回す話でない行〔仮の話・範囲の説明〕に、理由と一緒に書く）
#   - ``` で囲んだコードの中でない
# 出力: 拾った行ごとに「<計画書のパス>:<行番号>: <行>」。gh・ネットワークを使わない。書くのは標準出力・標準エラーだけ。
# 終了コード: 0=拾う行なし / 1=拾う行あり / 2=使えない（引数の形・計画書が無い・git の外）
set -uo pipefail

DEFER_RE='別イシュー|別のイシュー|後続'
OPT_OUT='起票しない'

die() { echo "⛔ check-plan-followups: $*" >&2; exit 2; }

ISSUE="${1:-}"
[[ "$ISSUE" =~ ^I[0-9]{3,}$ ]] || die "不正なイシュー番号です（期待する形: I###）: '${ISSUE}'"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || die "git リポジトリの中で実行してください"
cd "$ROOT" || die "git ルートに移れません: $ROOT"

# 計画書の探し方（open/closed・連番の plan_I###_N.md の最新）は code-review.sh の find_plan_file の 1 か所にそろえる
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/claude/code-review.sh disable=SC1091  # -x なしの単体の検査でもたどらない（読み込み先は別に検査される）
REVIEW_LIB_SOURCE_ONLY=1 . "$SCRIPT_DIR/code-review.sh" || die "code-review.sh を読み込めません"
PLAN="$(find_plan_file "$ISSUE")"
[ -n "$PLAN" ] || die "計画書が見つかりません: plan_${ISSUE}.md"

hits="$(awk -v own_re="${ISSUE}([^0-9]|$)" -v re="$DEFER_RE" -v opt="$OPT_OUT" -v path="$PLAN" '
  BEGIN { NUM_RE = "#[0-9]+|I[0-9]+" }   # 桁の数は問わない（{3,} は awk の実装で効かないことがある・3 桁固定は I569 で禁止）
  /^[[:space:]]*```/ { fence = !fence; next }
  fence { next }
  $0 !~ re { next }
  index($0, opt) { next }
  {
    line = $0
    gsub(own_re, "", line)
    if (line ~ NUM_RE) next
    print path ":" NR ": " $0
  }
' "$PLAN")" || die "計画書を読めません: $PLAN"

[ -z "$hits" ] && exit 0
printf '%s\n' "$hits"
echo "→ 各行に、起票か同梱をした先の #番号 を書く。後に回す話でない行には「${OPT_OUT}: 理由」を書く（retro の手順 4-1）" >&2
exit 1
