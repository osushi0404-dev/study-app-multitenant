#!/usr/bin/env bash
# gate-check.sh I###: 「最新のレビューが今の HEAD を見て OK」かを決定論で確かめる（I193 L13・I185 種類 B）。
# 呼び出し元: .claude/skills/test-gate/SKILL.md・.claude/skills/close/SKILL.md（どちらも最初の手順）
# 合格（exit 0）の条件をすべて満たすこと（どれかが欠ける・読めない・違うときは理由を出して exit 1＝fail-closed）:
#   1. 最新の docs/reviews/[closed/]I###_code_review_*.md の最後の VERDICT が OK で、
#      その REVIEWED_COMMIT の時点と今とで「ブランチ自身が変えたファイル」（比べる相手 GATE_BASE〔既定 origin/develop〕との
#      merge-base からの差・記録の場所を除く）の中身（blob）が同じ。auto_test.md の決定論ゲートの節も同じ
#   2. 高リスク（記録の RISK 行 OR このスクリプトが再評価するパス判定 path_risk_trigger）なら、最新の
#      I###_adversarial_review_*.md の最後の VERDICT が OK で、1 と同じ比べ方で後から変わっていない（OK の周の後に足した差分を通さない）
#   3. 作業ツリーに、記録の場所の外のコミットしていない変更（未追跡を含む）が無い
# 記録の場所: docs/reviews/・docs/issues/・docs/tests/{open,closed}/・docs/plans/{open,closed}/（テンプレートは含めない）
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

# 記録の場所は code-review.sh の is_record_path（docs/{issues,reviews,tests,plans}/ のうち templates/ 以外）を使う
# 比べる相手（既定は origin/develop。テストでは一時リポジトリの枝を渡す）。パス判定と「ブランチ自身の変更」の両方に使う
GATE_BASE="${GATE_BASE:-origin/develop}"

# fail <理由の種類> <説明>: 種類は dirty（作業ツリーの汚れ）/ unreviewed（レビューの後の変更）/
# verdict（VERDICT が OK でない）/ missing（記録・行が無い）/ base（比べる相手が無い）
fail() { local reason="$1"; shift; echo "⛔ gate-check NG: $*"; echo "GATE_CHECK: FAIL REASON=${reason}"; exit 1; }

# 最新の記録（ファイル名の <YYYYMMDD_HHMM> で並べた最後）。docs/reviews/ と docs/reviews/closed/ の両方を見る
# （並べ方は code-review.sh の review_records。I202 の共通化）
latest_record() {   # $1=種類（code_review / adversarial_review）
  review_records "$ISSUE" "$1" | tail -1
}

last_verdict() {   # $1=ファイル → BLOCKER/HIGH/OK/空
  grep -oE '^VERDICT:[[:space:]]*(BLOCKER|HIGH|OK)[[:space:]]*$' "$1" | tail -1 | grep -oE '(BLOCKER|HIGH|OK)' || true
}

reviewed_commit() { record_reviewed_commit "$1"; }   # $1=ファイル → SHA/空（code-review.sh の関数）

# ブランチ自身が変えたファイル（比べる相手との merge-base から rev まで・記録の場所を除く）の一覧（code-review.sh の関数）
branch_files() { branch_own_files "$GATE_BASE" "$1"; }   # $1=rev
# rev でのファイルの中身の ID（blob）。無ければ「(なし)」
blob_of() { git rev-parse -q --verify "$1:$2" 2>/dev/null || echo "(なし)"; }

# $1=SHA。レビューの後に「ブランチ自身が変えたファイル」の中身が変わっていれば、そのファイル名を出して exit 1。
# レビュー時点と今の一覧の和集合のファイルごとに、REVIEWED_COMMIT と HEAD での中身（blob）を比べる（差分の文字ではなく
# 中身そのものなので、バイナリも行番号・文脈行のずれも関係しない。I193 3 回目 M3・M5）。develop の取り込みで入った
# develop 側だけの変更は、ブランチが変えたファイルではないので数えない。ブランチが変えたファイルを develop も
# 変えていたときは、取り込み後の中身が変わるので数える（粗く、止まる側。そのときは review-gate を通り直す）
diff_outside_records() {
  local sha="$1" before after f out=""
  git cat-file -e "${sha}^{commit}" 2>/dev/null || { echo "(REVIEWED_COMMIT ${sha} がこのリポジトリにありません)"; return 1; }
  before=$(branch_files "$sha") || { echo "(比べる相手 ${GATE_BASE} との差分を取れません)"; return 1; }
  after=$(branch_files HEAD) || { echo "(比べる相手 ${GATE_BASE} との差分を取れません)"; return 1; }
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    [ "$(blob_of "$sha" "$f")" = "$(blob_of HEAD "$f")" ] || out+="${f}"$'\n'
  done < <(printf '%s\n%s\n' "$before" "$after" | LC_ALL=C sort -u)
  # 粗く止まる側: レビューの後に取り込んだ比べる相手（develop）の進み分が、ブランチの変えたファイルにも触れていたら数える。
  # 取り込みでブランチ側の中身を残す（develop の変更を捨てる）と、中身は同じでも PR の差分に「develop の変更の取り消し」が
  # 入り、それは誰もレビューしていないため（I193 3 回目・G19）
  local mb_then mb_now
  if ! mb_then=$(git merge-base "$GATE_BASE" "$sha") || ! mb_now=$(git merge-base "$GATE_BASE" HEAD); then
    echo "(比べる相手 ${GATE_BASE} との merge-base を取れません)"; return 1
  fi
  if [ "$mb_then" != "$mb_now" ]; then
    while IFS= read -r -d '' f; do
      grep -qxF -- "$f" <<< "${before}"$'\n'"${after}" && out+="${f}（develop 側も変えていた）"$'\n'
    done < <(git -c core.quotePath=false diff -z --name-only --no-renames "$mb_then" "$mb_now")
  fi
  # 計画書が宣言する決定論ゲート（auto_test.md の「## 決定論ゲート（自動実走）」）は、記録の場所にあっても
  # 実行するコマンドの正なので、レビューの後に変えたら数える（I193 M2）
  local gate_now gate_then path
  for path in "docs/tests/open/${ISSUE}_auto_test.md" "docs/tests/closed/${ISSUE}_auto_test.md"; do
    [ -f "$path" ] || continue
    gate_now=$(extract_gate_commands "$path")
    gate_then=$( { git show "${sha}:docs/tests/open/${ISSUE}_auto_test.md" 2>/dev/null || git show "${sha}:docs/tests/closed/${ISSUE}_auto_test.md" 2>/dev/null; } > "$GC_TMP/auto_then.md"; extract_gate_commands "$GC_TMP/auto_then.md")
    [ "$gate_now" = "$gate_then" ] || out+="${path}（決定論ゲートの節）"$'\n'
  done
  if [ -n "$out" ]; then printf '%s' "$out"; return 1; fi
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

GC_TMP=$(mktemp -d)
trap 'rm -rf "$GC_TMP"' EXIT

# コミットしていない変更（未追跡を含む）。-z で読む（空白や引用符を含むパスも、そのままの名前で比べる。I193 M3）。
# 先に確かめる（汚れはレビューをやり直しても直らないので、理由を dirty として区別する）
DIRTY=""
while IFS= read -r -d '' entry; do
  p="${entry:3}"
  is_record_path "$p" || DIRTY+="${p}"$'\n'
done < <(git status --porcelain=v1 -z --untracked-files=all --no-renames)
[ -z "$DIRTY" ] || fail dirty "記録の場所の外に、コミットしていない変更があります:
${DIRTY}"
git rev-parse -q --verify "$GATE_BASE" >/dev/null || fail base "比べる相手 ${GATE_BASE} がありません（git fetch origin develop をしてから）"

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
