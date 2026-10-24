#!/usr/bin/env bash
# I185 P2〜P4: スキル・手順書の書き換えを決定論検証する（docker/pytest 非依存）。
# 実行: bash scripts/claude/tests/test_i185_harness_docs.sh
#
# P2: 計画レビューを人の承認の前に済ませる（plan-issue が plan-issue-review.sh を実行する）
# P3: fix-loop 手順 4 は条件を満たすときだけ推奨案で進む（3 つの関所は残す）
# P4: スキルの allowed-tools（事前許可）を外し、制限は disallowed-tools で書く
# 検証するリポジトリのルートは環境変数 ROOT で差し替えられる（変更前のファイルに当てて不合格になることの確認用）。
# 0=全 PASS / 1=FAIL あり。
# shellcheck disable=SC2016  # 単一引用符内の $ARGUMENTS・バッククォートは文書の文字どおりの照合用（展開させない意図）
set -uo pipefail

ROOT="${ROOT:-$(git rev-parse --show-toplevel)}"
SKILLS="$ROOT/.claude/skills"
PLAN_ISSUE="$SKILLS/plan-issue/SKILL.md"
FIX_LOOP="$SKILLS/fix-loop/SKILL.md"
SEC_REVIEW="$SKILLS/security-review/SKILL.md"
WORKFLOW="$ROOT/docs/runbooks/workflow.md"
ISSUE_FLOW="$ROOT/docs/runbooks/issue-flow.md"
ONBOARDING="$ROOT/docs/runbooks/onboarding.md"

pass=0; fail=0
ckt() { local name="$1"; shift
        if "$@"; then printf 'PASS %s\n' "$name"; pass=$((pass+1));
        else printf 'FAIL %s\n' "$name"; fail=$((fail+1)); fi; }
has()    { grep -qF -- "$2" "$1"; }          # 文字どおり含む
hasnt()  { [ -f "$1" ] && ! grep -qF -- "$2" "$1"; }   # ファイルがあり、文字どおり含まない

no_allowed_tools() {
  local f found=0 n=0
  for f in "$SKILLS"/*/SKILL.md; do
    [ -f "$f" ] || continue
    n=$((n+1))
    if grep -q '^allowed-tools:' "$f"; then printf '  allowed-tools が残っている: %s\n' "$f"; found=1; fi
  done
  [ "$n" -gt 0 ] && [ "$found" -eq 0 ]
}

# ① ②（P4）
ckt "TC-14① どの SKILL.md にも allowed-tools 行がない" no_allowed_tools
ckt "TC-14② security-review に disallowed-tools がある" grep -qx 'disallowed-tools: Bash, Write, NotebookEdit' "$SEC_REVIEW"
# ③ ④（P2）
ckt "TC-14③a plan-issue が plan-issue-review.sh を実行する" has "$PLAN_ISSUE" 'bash scripts/claude/plan-issue-review.sh $ARGUMENTS'
ckt "TC-14③b plan-issue に「承認後に /plan-issue-review」の案内がない" hasnt "$PLAN_ISSUE" '承認後の次のステップ: `/plan-issue-review'
ckt "TC-14④ workflow.md に「計画書承認後 → /plan-issue-review を入力」がない" hasnt "$WORKFLOW" '| 計画書承認後 | 「`/plan-issue-review I###` を入力してください」'
# ⑤ ⑥（P3）
ckt "TC-14⑤a fix-loop 手順 4 に推奨案で進む条件がある" has "$FIX_LOOP" '推奨案で進めて手順 5 へ'
ckt "TC-14⑤b 条件 ⑥（守りの仕組みに触れない）がある" has "$FIX_LOOP" '認証・認可・テナント境界・秘密情報の扱い・権限設定・フック・GitHub Actions に触れない'
ckt "TC-14⑤c 診断レビューの関所が残る" has "$FIX_LOOP" 'fix-diagnosis-review.sh'
ckt "TC-14⑤d 実装レビューの関所が残る" has "$FIX_LOOP" 'fix-implementation-review.sh'
ckt "TC-14⑤e テストレビューの関所が残る" has "$FIX_LOOP" 'fix-test-review.sh'
ckt "TC-14⑥a 共通ルール (b) が新しい言い方になっている" has "$FIX_LOOP" '手順4（新案なので条件を判定し直す）'
ckt "TC-14⑥b 共通ルール (b) に古い言い方が残っていない" hasnt "$FIX_LOOP" '手順4 ユーザー承認（新案のため）'
# ⑦（P2 の消費箇所）
ckt "TC-14⑦a issue-flow.md に新しい順番の説明がある" has "$ISSUE_FLOW" '`/plan-issue` の中で計画レビュー'
ckt "TC-14⑦b onboarding.md に新しい順番の説明がある" has "$ONBOARDING" '`/plan-issue` の中で計画レビュー'

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
