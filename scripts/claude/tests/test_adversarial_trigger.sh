#!/usr/bin/env bash
# I086 回帰テスト: 高リスク判定の機械可読化（detect_risk_flag の fail-closed／
#                  path_risk_trigger のパス決定論トリガ）と敵対ステージ結線行の存在を検証する。
#
# 実行（必ずスクリプトとして bash 実行すること。対話シェルへ貼らない）:
#   bash scripts/claude/tests/test_adversarial_trigger.sh
#
# 理由: Claude Code の対話シェルでは grep が同梱 ugrep ラッパーに上書きされ -E/-o パイプが
#       誤動作する。bash サブプロセスでは実 GNU grep が使われるため決定論的に PASS する。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1

CODE_REVIEW="scripts/claude/code-review.sh"

pass=0; fail=0
ck() { # name expected actual
  if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1))
  else printf 'FAIL %s  expected[%s] got[%s]\n' "$1" "$2" "$3"; fail=$((fail+1)); fi
}
ck_true() { # name cmd... : expect exit 0
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then printf 'PASS %s\n' "$name"; pass=$((pass+1))
  else printf 'FAIL %s (expected success)\n' "$name"; fail=$((fail+1)); fi
}

# ---- 対象スクリプトから helper 関数のみを source（ガードで本体は実行されない） ----
# shellcheck source=/dev/null
REVIEW_LIB_SOURCE_ONLY=1 source "$CODE_REVIEW"   # detect_risk_flag / path_risk_trigger
set +e +o pipefail   # source が有効化した errexit/pipefail をテストハーネス用に解除

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ---- detect_risk_flag: RISK 行の anchored 解析・fail-closed ----
printf 'RISK: YES\nVERDICT: OK\n' > "$TMP/r_yes.md"
ck "risk: RISK YES" "YES" "$(detect_risk_flag "$TMP/r_yes.md")"

printf 'RISK: NO\nVERDICT: OK\n' > "$TMP/r_no.md"
ck "risk: RISK NO" "NO" "$(detect_risk_flag "$TMP/r_no.md")"

printf 'VERDICT: OK\n' > "$TMP/r_none.md"
ck "risk: 行欠落は fail-closed YES" "YES" "$(detect_risk_flag "$TMP/r_none.md")"

printf '**RISK: NO**\nVERDICT: OK\n' > "$TMP/r_deco.md"
ck "risk: 装飾付き行は不一致=fail-closed YES" "YES" "$(detect_risk_flag "$TMP/r_deco.md")"

# VERDICT 行直前の RISK 行を採用（正規出力）。複数の RISK/VERDICT では最終 VERDICT 直前を採る。
printf 'RISK: NO\n中間テキスト\nRISK: YES\nVERDICT: OK\n' > "$TMP/r_multi.md"
ck "risk: VERDICT 直前の RISK 行を採用" "YES" "$(detect_risk_flag "$TMP/r_multi.md")"

# H2 対応: 本文（fenced block・引用）に紛れた RISK 行は、直後が VERDICT 行でないため拾わない。
# RISK 行の正規出力が欠落していれば fail-closed YES（引用の NO で fail-open しない）。
# shellcheck disable=SC2016  # printf のフォーマット文字列はリテラル（展開させない）
printf '# レビュー\n```\nRISK: NO\n```\n本文\nVERDICT: OK\n' > "$TMP/r_quoted.md"
ck "risk: 引用内 RISK NO は無視し fail-closed YES" "YES" "$(detect_risk_flag "$TMP/r_quoted.md")"

# H2 対応: 引用の NO があっても、正規の VERDICT 直前 RISK 行が優先される。
# shellcheck disable=SC2016
printf '```\nRISK: NO\n```\nRISK: YES\nVERDICT: OK\n' > "$TMP/r_quoted_yes.md"
ck "risk: 引用 NO より正規 VERDICT 直前 YES を優先" "YES" "$(detect_risk_flag "$TMP/r_quoted_yes.md")"

# 正規の NO（VERDICT 直前）は NO を返す。
printf 'RISK: NO\nVERDICT: OK\n' > "$TMP/r_regnO.md"
ck "risk: VERDICT 直前の正規 NO は NO" "NO" "$(detect_risk_flag "$TMP/r_regnO.md")"

# ---- path_risk_trigger: 監視パスの決定論トリガ ----
ck "path: hooks 配下" "YES" "$(path_risk_trigger "scripts/claude/hooks/pretooluse_guard.py")"
ck "path: git-hooks 配下" "YES" "$(path_risk_trigger "scripts/git-hooks/pre-push")"
ck "path: settings.json" "YES" "$(path_risk_trigger ".claude/settings.json")"
ck "path: settings.local.json" "YES" "$(path_risk_trigger ".claude/settings.local.json")"
ck "path: claude 直下 .sh" "YES" "$(path_risk_trigger "scripts/claude/code-review.sh")"
ck "path: skills 配下" "YES" "$(path_risk_trigger ".claude/skills/code-review/SKILL.md")"
ck "path: review-agents 配下" "YES" "$(path_risk_trigger ".claude/review-agents/code-reviewer.md")"
ck "path: tests 配下 .sh も一致（glob が / を跨ぐ仕様の固定化）" "YES" \
   "$(path_risk_trigger "scripts/claude/tests/test_review_gates.sh")"
# H4 対応: 指示階層ファイル（レビュー/ガードの挙動を規定する上位文書）も監視対象。
ck "path: CLAUDE.md（最上位指示）" "YES" "$(path_risk_trigger "CLAUDE.md")"
ck "path: workflow.md（フロー定義）" "YES" "$(path_risk_trigger "docs/runbooks/workflow.md")"
ck "path: review-rules.md（非権威化規定）" "YES" "$(path_risk_trigger "docs/runbooks/review-rules.md")"
ck "path: .claude/agents 配下（構造制限の昇格先）" "YES" "$(path_risk_trigger ".claude/agents/reviewer.md")"
ck "path: アプリコードのみは NO" "NO" "$(path_risk_trigger "backend/app/views.py")"
ck "path: 他の runbook は NO（監視は中核文書に限定）" "NO" "$(path_risk_trigger "docs/runbooks/common-commands.md")"
ck "path: 空入力は NO" "NO" "$(path_risk_trigger "")"
MIXED="$(printf 'backend/app/views.py\nfrontend/src/App.tsx\nscripts/claude/hooks/guard.py')"
ck "path: 通常＋監視パスの混在は YES" "YES" "$(path_risk_trigger "$MIXED")"

# ---- H5 対応: 配線ロジックの挙動（OR 合成・ステージ要否）を関数として固定化 ----
# 本体フローに直書きすると OR→AND 変異や REQUIRED/NOT_REQUIRED 反転を文字列 grep が検出できず
# false-green になるため、関数の真理値表をここで固定する。
ck "combine: YES/YES → YES" "YES" "$(combine_risk YES YES)"
ck "combine: YES/NO → YES"  "YES" "$(combine_risk YES NO)"
ck "combine: NO/YES → YES"  "YES" "$(combine_risk NO YES)"
ck "combine: NO/NO → NO"    "NO"  "$(combine_risk NO NO)"
ck "decision: YES → REQUIRED"     "REQUIRED"     "$(adversarial_stage_decision YES)"
ck "decision: NO → NOT_REQUIRED"  "NOT_REQUIRED" "$(adversarial_stage_decision NO)"

# ---- 結線行の存在: SKILL が解析する機械可読 stdout ----
# shellcheck disable=SC2016  # スクリプト内のリテラル `$(...)` 出力行を検索する意図（展開させない）
ck_true "wire: ADVERSARIAL_STAGE 出力行" grep -qF 'ADVERSARIAL_STAGE: $(adversarial_stage_decision' "$CODE_REVIEW"
# shellcheck disable=SC2016  # スクリプト内のリテラル `${...}` 出力行を検索する意図（展開させない）
ck_true "wire: RISK 出力行" grep -qF 'RISK: ${RISK_FINAL}' "$CODE_REVIEW"
# shellcheck disable=SC2016
ck_true "wire: FINAL_VERDICT 出力行" grep -qF 'FINAL_VERDICT: ${FINAL_VERDICT}' "$CODE_REVIEW"
# 本体が配線関数を実際に通ること（直書き回帰の防止）
# shellcheck disable=SC2016
ck_true "wire: 本体が combine_risk を使用" grep -qF 'RISK_FINAL=$(combine_risk' "$CODE_REVIEW"

echo "----"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
