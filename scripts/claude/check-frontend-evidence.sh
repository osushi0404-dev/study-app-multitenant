#!/usr/bin/env bash
set -uo pipefail
# check-frontend-evidence: frontend/src を変えたイシューで、画面確認の記録と画像の実在を確かめる（I187）。
# Usage: [BASE_REF=origin/develop] check-frontend-evidence.sh I###
#   - git diff <BASE_REF>...HEAD に frontend/src/ の変更が無ければ「対象外」で合格
#   - あれば docs/tests/{open,closed}/I###_manual_test.md の「## 画面確認」の表を読み、各行の最後の列（画像）を確かめる
#     ・「理由: …」（理由が空でない）→ 合格の行
#     ・カンマ区切りのファイル名がすべて .evidence/I###/<名前> に実在 → 合格の行
#     ・それ以外（空・実在しない・/ や .. を含む名前）→ 不合格の行
#   - 合格の行が 1 行以上・不合格の行が 0 行なら合格
# 終了コード: 0=合格（対象外を含む）・1=不合格・2=使い方の誤り／判定できない（git の外・基準が無い）
# 手順: docs/runbooks/frontend-verify.md ・ 計画: docs/plans/open/plan_I187.md 5-2-5

ISSUE="${1:-}"
if ! [[ "$ISSUE" =~ ^I[0-9]{3}$ ]]; then
  echo "[check-frontend-evidence] 使い方: $0 I###" >&2
  exit 2
fi
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "[check-frontend-evidence] git のワークツリー内で実行してください" >&2; exit 2; }
cd "$ROOT" || exit 2
BASE="${BASE_REF:-origin/develop}"

if ! CHANGED="$(git diff --name-only "$BASE"...HEAD 2>/dev/null)"; then
  echo "[check-frontend-evidence] 変更ファイルを取得できません（基準: $BASE）。判定できないので不合格にします" >&2
  exit 2
fi
# パイプで渡さない（pipefail の下で grep -q が先に終わると前の printf が SIGPIPE で終わり、「対象外」に反転する・I210）
if ! grep -q '^frontend/src/' <<< "$CHANGED"; then
  echo "[check-frontend-evidence] 対象外: frontend/src を変えていません（基準: $BASE）"
  exit 0
fi

REC="docs/tests/open/${ISSUE}_manual_test.md"
[ -f "$REC" ] || REC="docs/tests/closed/${ISSUE}_manual_test.md"
if [ ! -f "$REC" ]; then
  echo "[check-frontend-evidence] 不合格: frontend/src を変えていますが、テスト記録 ${ISSUE}_manual_test.md がありません" >&2
  exit 1
fi

# 「## 画面確認」の節の表のデータ行（見出し行・区切り行を除く）の、最後の列だけを 1 行ずつ出す
CELLS="$(awk '
  /^## / { insec = ($0 ~ /^## 画面確認[[:space:]]*$/); n = 0; next }
  !insec || !/^\|/ { next }
  { n++ }
  n == 1 { next }                                   # 見出し行
  /^\|[-:| ]+\|[[:space:]]*$/ { next }              # 区切り行
  {
    line = $0; sub(/[[:space:]]+$/, "", line); sub(/\|$/, "", line)
    k = split(line, a, "|"); cell = a[k]
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", cell)
    print "<" cell ">"
  }
' "$REC")"

ok=0; ng=0; i=0
while IFS= read -r raw; do
  [ -n "$raw" ] || continue
  i=$((i + 1))
  cell="${raw#<}"; cell="${cell%>}"
  if [[ "$cell" =~ ^理由[:：](.*)$ ]]; then
    reason="${BASH_REMATCH[1]}"
    reason="${reason#"${reason%%[![:space:]]*}"}"
    if [ -n "$reason" ]; then ok=$((ok + 1)); else ng=$((ng + 1)); echo "  ${i} 行目: 理由が空です" >&2; fi
    continue
  fi
  if [ -z "$cell" ]; then
    ng=$((ng + 1)); echo "  ${i} 行目: 画像の列が空です（画像のファイル名か「理由: …」を書く）" >&2
    continue
  fi
  row_ok=1
  IFS=',' read -r -a names <<< "$cell"
  for n in "${names[@]}"; do
    n="${n#"${n%%[![:space:]]*}"}"; n="${n%"${n##*[![:space:]]}"}"
    if [ -z "$n" ] || [[ "$n" == *..* ]] || ! [[ "$n" =~ ^[A-Za-z0-9._-]+$ ]]; then
      row_ok=0; echo "  ${i} 行目: 使えないファイル名です: '${n}'（.evidence/${ISSUE}/ 直下の名前だけを書く）" >&2
    elif [ ! -f ".evidence/${ISSUE}/${n}" ]; then
      row_ok=0; echo "  ${i} 行目: 画像がありません: .evidence/${ISSUE}/${n}" >&2
    fi
  done
  if [ "$row_ok" -eq 1 ]; then ok=$((ok + 1)); else ng=$((ng + 1)); fi
done <<< "$CELLS"

if [ "$ok" -ge 1 ] && [ "$ng" -eq 0 ]; then
  echo "[check-frontend-evidence] 合格: 画面確認 ${ok} 行（${REC}）"
  exit 0
fi
echo "[check-frontend-evidence] 不合格: frontend/src を変えたので、${REC} の「## 画面確認」に、確かめた行（画像は .evidence/${ISSUE}/）か「理由: …」の行が要ります（合格 ${ok} 行・不合格 ${ng} 行）。手順: docs/runbooks/frontend-verify.md" >&2
exit 1
