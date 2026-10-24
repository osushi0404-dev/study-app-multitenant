#!/usr/bin/env bash
# gate-check.sh I###: 「最新のレビューが今の HEAD を見て OK」かを決定論で確かめる（I193 L13・I185 種類 B）。
# 呼び出し元: .claude/skills/test-gate/SKILL.md・.claude/skills/close/SKILL.md（どちらも最初の手順）
# 合格（exit 0）の条件をすべて満たすこと（どれかが欠ける・読めない・違うときは理由を出して exit 1＝fail-closed）:
#   1. 最新の docs/reviews/[closed/]I###_code_review_*.md の最後の VERDICT が OK で、
#      その REVIEWED_COMMIT から HEAD までの差分が「記録の場所」の中だけ
#   2. 高リスク（記録の RISK 行 OR このスクリプトが再評価するパス判定 path_risk_trigger。比べる相手は GATE_BASE・
#      既定 origin/develop）なら、最新の I###_adversarial_review_*.md の最後の VERDICT が OK で、
#      その REVIEWED_COMMIT から HEAD までの差分も記録の場所の中だけ（OK の周の後に足した差分を通さない）
#   3. 作業ツリーに、記録の場所の外のコミットしていない変更（未追跡を含む）が無い
# 記録の場所: docs/reviews/・docs/tests/・docs/issues/・docs/plans/
# 失敗のときは `GATE_CHECK: FAIL REASON=<dirty|unreviewed|verdict|missing|base>` を出す（test-gate・close が戻り先を決める）
# ファイル名は core.quotePath=false・--no-renames で取る（日本語名・名前の変更ですり抜けない。I086・I181）
set -uo pipefail

ISSUE="${1:-}"
if ! [[ "$ISSUE" =~ ^I[0-9]{3}$ ]]; then
  echo "⛔ 使い方: $0 I###（受け取った値: '${ISSUE}'）"
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)" || { echo "⛔ git リポジトリの中で実行してください"; exit 1; }
cd "$REPO_ROOT" || exit 1

# RISK 行の読み方は code-review.sh と同じ関数を使う（直後が VERDICT の RISK 行だけを採用・無ければ YES）
# shellcheck source=scripts/claude/code-review.sh
REVIEW_LIB_SOURCE_ONLY=1 . "${GATE_CHECK_LIB:-scripts/claude/code-review.sh}" || { echo "⛔ code-review.sh を読み込めません"; exit 1; }
set +e   # code-review.sh の set -e を引き継がない（失敗の理由を出してから終わるため）

RECORD_RE='^docs/(reviews|tests|issues|plans)/'
# 高リスクのパス判定で比べる相手（既定は origin/develop。テストでは一時リポジトリの枝を渡す）
GATE_BASE="${GATE_BASE:-origin/develop}"

# fail <理由の種類> <説明>: 種類は dirty（作業ツリーの汚れ）/ unreviewed（レビューの後の変更）/
# verdict（VERDICT が OK でない）/ missing（記録・行が無い）/ base（比べる相手が無い）
fail() { local reason="$1"; shift; echo "⛔ gate-check NG: $*"; echo "GATE_CHECK: FAIL REASON=${reason}"; exit 1; }

# 最新の記録（ファイル名の <YYYYMMDD_HHMM> で並べた最後）。docs/reviews/ と docs/reviews/closed/ の両方を見る
latest_record() {   # $1=種類（code_review / adversarial_review）
  local kind="$1"
  find docs/reviews -maxdepth 2 -type f -name "${ISSUE}_${kind}_*.md" 2>/dev/null \
    | awk -F/ '{ print $NF "\t" $0 }' | LC_ALL=C sort | tail -1 | cut -f2
}

last_verdict() {   # $1=ファイル → BLOCKER/HIGH/OK/空
  grep -oE '^VERDICT:[[:space:]]*(BLOCKER|HIGH|OK)[[:space:]]*$' "$1" | tail -1 | grep -oE '(BLOCKER|HIGH|OK)' || true
}

reviewed_commit() {   # $1=ファイル → SHA/空
  grep -oE '^REVIEWED_COMMIT:[[:space:]]*[0-9a-f]{7,40}[[:space:]]*$' "$1" | tail -1 | grep -oE '[0-9a-f]{7,40}' || true
}

# $1=SHA。SHA から HEAD までに記録の場所の外の変更があれば、そのファイル名を出して exit 1
diff_outside_records() {
  local sha="$1" files outside
  git cat-file -e "${sha}^{commit}" 2>/dev/null || { echo "(REVIEWED_COMMIT ${sha} がこのリポジトリにありません)"; return 1; }
  files=$(git -c core.quotePath=false diff --name-only --no-renames "$sha" HEAD) || { echo "(git diff に失敗)"; return 1; }
  outside=$(printf '%s\n' "$files" | grep -vE "$RECORD_RE" | grep -v '^$' || true)
  if [ -n "$outside" ]; then printf '%s\n' "$outside"; return 1; fi
  return 0
}

check_record() {   # $1=種類の表示名 $2=ファイル
  local label="$1" file="$2" v sha out
  [ -n "$file" ] || fail missing "${label}の記録がありません（${ISSUE}）"
  v=$(last_verdict "$file")
  [ "$v" = "OK" ] || fail verdict "${label}の最新の記録 ${file} の VERDICT が OK ではありません（${v:-読めない}）"
  sha=$(reviewed_commit "$file")
  [ -n "$sha" ] || fail missing "${label}の記録 ${file} に REVIEWED_COMMIT 行がありません"
  if ! out=$(diff_outside_records "$sha"); then
    fail unreviewed "${label}（${file}・REVIEWED_COMMIT ${sha}）の後に、レビューを通っていない変更があります:
${out}"
  fi
  echo "✅ ${label}: ${file}（VERDICT OK・REVIEWED_COMMIT ${sha} 以降は記録の場所だけ）"
}

# コミットしていない変更（未追跡を含む）。porcelain の 4 文字目以降がパス。
# 先に確かめる（汚れはレビューをやり直しても直らないので、理由を dirty として区別する）
DIRTY=$(git -c core.quotePath=false status --porcelain --untracked-files=all --no-renames | cut -c4- | grep -vE "$RECORD_RE" | grep -v '^$' || true)
[ -z "$DIRTY" ] || fail dirty "記録の場所の外に、コミットしていない変更があります:
${DIRTY}"

CODE_REVIEW=$(latest_record code_review)
check_record "コードレビュー" "$CODE_REVIEW"

# 高リスク = 記録の RISK 行（レビュー役の判定）OR パス判定（決定論・このスクリプト自身が再評価する）。
# パス判定を記録の文字に頼らないのは、レビュー役が RISK: NO を出しても安全装置の変更を見落とさないため（I193 F1）
BASE_SHA=$(git merge-base "$GATE_BASE" HEAD 2>/dev/null) || fail base "比べる相手 ${GATE_BASE} がありません（git fetch origin develop をしてから）"
BRANCH_FILES=$(git -c core.quotePath=false diff --name-only --no-renames "$BASE_SHA" HEAD) || fail base "${GATE_BASE} との差分を取れません"
RISK_RECORD=$(detect_risk_flag "$CODE_REVIEW")
RISK_PATH=$(path_risk_trigger "$BRANCH_FILES")
if [ "$(combine_risk "$RISK_RECORD" "$RISK_PATH")" = "YES" ]; then
  echo "（高リスク: 記録=${RISK_RECORD} / パス=${RISK_PATH}。敵対的レビューの記録も確かめる）"
  check_record "敵対的レビュー" "$(latest_record adversarial_review)"
fi

echo "GATE_CHECK: OK"
exit 0
