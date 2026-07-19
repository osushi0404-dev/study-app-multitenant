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

printf 'RISK: NO\n中間テキスト\nRISK: YES\n' > "$TMP/r_multi.md"
ck "risk: 複数行は tail -1 優先" "YES" "$(detect_risk_flag "$TMP/r_multi.md")"

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
ck "path: アプリコードのみは NO" "NO" "$(path_risk_trigger "backend/app/views.py")"
ck "path: 空入力は NO" "NO" "$(path_risk_trigger "")"
MIXED="$(printf 'backend/app/views.py\nfrontend/src/App.tsx\nscripts/claude/hooks/guard.py')"
ck "path: 通常＋監視パスの混在は YES" "YES" "$(path_risk_trigger "$MIXED")"

# ---- 結線行の存在: SKILL が解析する機械可読 stdout ----
ck_true "wire: ADVERSARIAL_STAGE REQUIRED 行" grep -qF 'ADVERSARIAL_STAGE: REQUIRED' "$CODE_REVIEW"
ck_true "wire: ADVERSARIAL_STAGE NOT_REQUIRED 行" grep -qF 'ADVERSARIAL_STAGE: NOT_REQUIRED' "$CODE_REVIEW"
# shellcheck disable=SC2016  # スクリプト内のリテラル `${...}` 出力行を検索する意図（展開させない）
ck_true "wire: RISK 出力行" grep -qF 'RISK: ${RISK_FINAL}' "$CODE_REVIEW"
# shellcheck disable=SC2016
ck_true "wire: FINAL_VERDICT 出力行" grep -qF 'FINAL_VERDICT: ${FINAL_VERDICT}' "$CODE_REVIEW"

echo "----"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
