#!/usr/bin/env bash
set -uo pipefail
# check-manual-test-executor: 手動テスト文書で、Claude が自分で確かめられる項目を Human に振っていないかを確かめる（I187）。
# Usage: check-manual-test-executor.sh I###
#   - docs/tests/{open,closed}/I###_manual_test.md の表のうち、見出し行に「実施者」の列がある表を読む
#   - 実施者の列が Human（太字・「ユーザー」「人」を含む）の行について
#     ・行に「承認」「確認プロンプト」「確認が出」「確認画面」「確認なし」「ダイアログ」を含み、「試した手段:」に
#       check-permission-prompt.sh では確かめられないわけ（スクリプトの名前を含む）が無い → 不合格
#       （承認画面が出るかは check-permission-prompt.sh で Claude が確かめる。考えずに Human に振った行を止める）
#     ・「試した手段:」の後ろに中身が無い → 不合格（I195。前の書き方「Claude で確かめられない理由:」だけの行も不合格）
#       中身の正しさは文字では見ない（計画レビュー役 .claude/agents/plan-reviewer.md が見る）
#   - 文字列の判定は普通の書き方の事故を止めるためのもので、わざと避ける書き方は対象にしない
#   - 書き方の基準: docs/runbooks/plan-writing-rules.md「実施者の区別」
# 終了コード: 0=合格・1=不合格・2=使い方の誤り／文書が無い
# 計画: docs/plans/closed/plan_I187.md 5-2-8・docs/plans/open/plan_I195.md 4.2

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

# 表の見出し行で「実施者」の列の位置を覚え、データ行のうちその列が Human（太字・「ユーザー」「人」も同じ扱い）の行を
# 「<No>\t<行全体>」で出す。セルの中の \| は列の区切りにしない（GFM の書き方。パイプ付きのコマンドでよく出る）。
# 「実施者」の列がある表が 1 つも無ければ、最後に NO_EXECUTOR_COLUMN を出す（判定できないので 2 にする）
ROWS="$(awk '
  !/^[[:space:]]*\|/ { col = 0; inhdr = 0; next }
  {
    line = $0; gsub(/\\\|/, "\001", line)
    nf = split(line, f, "|")
  }
  col == 0 && !inhdr {
    inhdr = 1
    for (i = 2; i < nf; i++) { c = f[i]; gsub(/^[[:space:]]+|[[:space:]]+$/, "", c); if (c ~ /^実施者/) { col = i; found = 1 } }
    next
  }
  col == 0 { next }
  line ~ /^[[:space:]]*\|[-:| ]+\|[[:space:]]*$/ { next }
  {
    c = f[col]; gsub(/[*_[:space:]]/, "", c)
    if (c ~ /^([Hh][Uu][Mm][Aa][Nn]|ユーザー|人)/) { n = f[2]; gsub(/^[[:space:]]+|[[:space:]]+$/, "", n); print n "\t" $0 }
  }
  END { if (!found) print "NO_EXECUTOR_COLUMN" }
' "$REC")"

if [[ "$ROWS" == *NO_EXECUTOR_COLUMN* ]]; then
  echo "[check-manual-test-executor] 判定できない: ${REC} に「実施者」の列がある表がありません" >&2
  exit 2
fi

# 承認画面の確認を言い換えた書き方（過去の記録に実際に出てくるもの）もまとめて止める
PROMPT_WORDS='承認|確認プロンプト|確認が出|確認画面|確認なし|ダイアログ|permission prompt'
ng=0
while IFS=$'\t' read -r no line; do
  [ -n "$line" ] || continue
  tried=""
  if [[ "$line" =~ 試した手段[:：]([^|]*) ]]; then
    tried="${BASH_REMATCH[1]}"
    tried="${tried//[[:space:]]/}"
  fi
  # 言葉が当たっても、check-permission-prompt.sh では確かめられないわけまで書いてあれば通す
  # （GitHub の Approve・アプリのダイアログの操作感など、Claude Code の承認画面ではない正当な Human の行を止めない）
  if [[ "$line" =~ $PROMPT_WORDS ]] && [[ "$tried" != *check-permission-prompt.sh* ]]; then
    ng=$((ng + 1)); echo "  ${no}: 承認画面が出るかの確認（「${BASH_REMATCH[0]}」）を Human にしているように見えます。check-permission-prompt.sh で Claude が確かめる行にしてください（Claude Code の承認画面の話ではない場合は、「試した手段:」に check-permission-prompt.sh では確かめられないわけを書く）" >&2
  fi
  if [ -z "$tried" ]; then
    ng=$((ng + 1)); echo "  ${no}: Human の行に「試した手段: …」がありません（docs/runbooks/plan-writing-rules.md「実施者の区別」の観測手段のどれを試し、なぜ観測できなかったかを書く）" >&2
  fi
done <<< "$ROWS"

if [ "$ng" -eq 0 ]; then
  echo "[check-manual-test-executor] 合格: ${REC}"
  exit 0
fi
echo "[check-manual-test-executor] 不合格: ${REC} の Human の行を見直してください（${ng} 件）。基準: docs/runbooks/plan-writing-rules.md「実施者の区別」" >&2
exit 1
