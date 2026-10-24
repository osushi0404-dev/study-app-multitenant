#!/usr/bin/env bash
set -uo pipefail
# check-manual-test-executor: 手動テスト文書で、Claude が自分で確かめられる項目を Human に振っていないかを確かめる（I187）。
# Usage: check-manual-test-executor.sh I###
#   - docs/tests/{open,closed}/I###_manual_test.md の表のうち、見出し行に「実施者」の列がある表を読む
#   - 実施者の列が Human で始まる行について
#     ・行に「承認画面」を含む → 不合格（承認画面が出るかは check-permission-prompt.sh で Claude が確かめる）
#     ・「Claude で確かめられない理由:」の後ろに理由が無い → 不合格
#   - 文字列の判定は普通の書き方の事故を止めるためのもので、わざと避ける書き方は対象にしない
# 終了コード: 0=合格・1=不合格・2=使い方の誤り／文書が無い
# 計画: docs/plans/open/plan_I187.md 5-2-8

ISSUE="${1:-}"
if ! [[ "$ISSUE" =~ ^I[0-9]{3}$ ]]; then
  echo "[check-manual-test-executor] 使い方: $0 I###" >&2
  exit 2
fi
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "[check-manual-test-executor] git のワークツリー内で実行してください" >&2; exit 2; }
cd "$ROOT" || exit 2

REC="docs/tests/open/${ISSUE}_manual_test.md"
[ -f "$REC" ] || REC="docs/tests/closed/${ISSUE}_manual_test.md"
if [ ! -f "$REC" ]; then
  echo "[check-manual-test-executor] 判定できない: ${ISSUE}_manual_test.md がありません" >&2
  exit 2
fi

# 表の見出し行で「実施者」の列の位置を覚え、データ行のうちその列が Human で始まる行を「<No>\t<行全体>」で出す
ROWS="$(awk -F'|' '
  !/^\|/ { col = 0; inhdr = 0; next }
  col == 0 && !inhdr {
    inhdr = 1
    for (i = 2; i < NF; i++) { c = $i; gsub(/^[[:space:]]+|[[:space:]]+$/, "", c); if (c == "実施者") col = i }
    next
  }
  col == 0 { next }
  /^\|[-:| ]+\|[[:space:]]*$/ { next }
  {
    c = $col; gsub(/^[[:space:]]+/, "", c)
    if (c ~ /^Human/) { n = $2; gsub(/^[[:space:]]+|[[:space:]]+$/, "", n); print n "\t" $0 }
  }
' "$REC")"

ng=0
while IFS=$'\t' read -r no line; do
  [ -n "$line" ] || continue
  if [[ "$line" == *承認画面* ]]; then
    ng=$((ng + 1)); echo "  ${no}: 承認画面が出るかの確認を Human にしています。check-permission-prompt.sh で Claude が確かめる行にしてください" >&2
  fi
  reason=""
  if [[ "$line" =~ Claude\ で確かめられない理由[:：]([^|]*) ]]; then
    reason="${BASH_REMATCH[1]}"
    reason="${reason//[[:space:]]/}"
  fi
  if [ -z "$reason" ]; then
    ng=$((ng + 1)); echo "  ${no}: Human の行に「Claude で確かめられない理由: …」がありません（Claude で確かめる手段を公式の機能まで探し、無かった理由を書く）" >&2
  fi
done <<< "$ROWS"

if [ "$ng" -eq 0 ]; then
  echo "[check-manual-test-executor] 合格: ${REC}"
  exit 0
fi
echo "[check-manual-test-executor] 不合格: ${REC} の Human の行を見直してください（${ng} 件）。基準: docs/runbooks/plan-writing-rules.md「実施者の区別」" >&2
exit 1
