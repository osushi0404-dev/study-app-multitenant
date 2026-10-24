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

# frontmatter（先頭の --- と次の --- の間）に、その 1 行がそのまま入っているか
in_frontmatter() {
  python3 - "$1" "$2" <<'PY'
import sys
lines = open(sys.argv[1], encoding="utf-8").read().split("\n")
if not lines or lines[0] != "---" or "---" not in lines[1:]:
    sys.exit(1)
sys.exit(0 if sys.argv[2] in lines[1:lines.index("---", 1)] else 1)
PY
}

# 文字列 A を含む最初の行が、文字列 B を含む最初の行より前にあるか（両方あること）
before() {
  python3 - "$1" "$2" "$3" <<'PY'
import sys
lines = open(sys.argv[1], encoding="utf-8").read().split("\n")
a = next((i for i, l in enumerate(lines) if sys.argv[2] in l), None)
b = next((i for i, l in enumerate(lines) if sys.argv[3] in l), None)
sys.exit(0 if a is not None and b is not None and a < b else 1)
PY
}

# ① ②（P4）
ckt "TC-14① どの SKILL.md にも allowed-tools 行がない" no_allowed_tools
ckt "TC-14② security-review の frontmatter に disallowed-tools がある" in_frontmatter "$SEC_REVIEW" 'disallowed-tools: Write, NotebookEdit'
# ③ ④（P2）
ckt "TC-14③a plan-issue が plan-issue-review.sh を実行する" has "$PLAN_ISSUE" 'bash scripts/claude/plan-issue-review.sh $ARGUMENTS'
ckt "TC-14③b plan-issue に「承認後に /plan-issue-review」の案内がない" hasnt "$PLAN_ISSUE" '承認後の次のステップ: `/plan-issue-review'
ckt "TC-14③c 計画レビューの実行が、承認ポイントの提示より前にある" before "$PLAN_ISSUE" 'bash scripts/claude/plan-issue-review.sh $ARGUMENTS' '承認ポイントに含めて提示し、停止する'
ckt "TC-14③d 「完了したら承認ポイントを提示して停止」（レビュー前の停止）がない" hasnt "$PLAN_ISSUE" '完了したら「承認ポイント」を提示して停止する'
ckt "TC-14③e スクリプトの「/implement を実行」の案内を承認前に伝えない" has "$PLAN_ISSUE" 'ここではユーザーに伝えない'
ckt "TC-14③f スクリプトが判定前に失敗したら承認ポイントを出さない" has "$PLAN_ISSUE" '承認ポイントを出さずに停止し、失敗したことを報告する'
ckt "TC-14④ workflow.md に「計画書承認後 → /plan-issue-review を入力」がない" hasnt "$WORKFLOW" '| 計画書承認後 | 「`/plan-issue-review I###` を入力してください」'
# ⑤ ⑥（P3）
ckt "TC-14⑤a fix-loop 手順 4 に推奨案で進む条件がある" has "$FIX_LOOP" '次の 6 つを**すべて**満たすときは、推奨案で進めて手順 5 へ'
ckt "TC-14⑤b 条件 ⑥（守りの仕組みに触れない）がある" has "$FIX_LOOP" '認証・認可・テナント境界・秘密情報の扱い・権限設定・フック・GitHub Actions'
ckt "TC-14⑤b2 条件 ⑥ がレビュー・判定の仕組みも除外する" has "$FIX_LOOP" 'レビュー・判定の仕組み（'
ckt "TC-14⑤f 条件 ① 診断レビューが PASS" has "$FIX_LOOP" '1. 手順3.5 が `FIX_GATE: PASS`（SKIP ではない）'
ckt "TC-14⑤g 条件 ② 価値判断でない" has "$FIX_LOOP" '2. 推奨案が 1 つに決まり、他案との違いが価値判断'
ckt "TC-14⑤h 条件 ③ 計画を変えない" has "$FIX_LOOP" '3. 計画の方式・範囲・受け入れ条件を変えない'
ckt "TC-14⑤i 条件 ④ 危険操作を含まない" has "$FIX_LOOP" '4. 危険操作'
ckt "TC-14⑤j 条件 ⑤ 簡略化を使わない" has "$FIX_LOOP" '5. 軽微例外による実装/テストレビューの簡略化を使わない'
ckt "TC-14⑤k 満たさないときは停止する" has "$FIX_LOOP" '1 つでも満たさないときは承認待ちで停止する'
ckt "TC-14⑤c 診断レビューの関所が残る" has "$FIX_LOOP" 'fix-diagnosis-review.sh'
ckt "TC-14⑤d 実装レビューの関所が残る" has "$FIX_LOOP" 'fix-implementation-review.sh'
ckt "TC-14⑤e テストレビューの関所が残る" has "$FIX_LOOP" 'fix-test-review.sh'
ckt "TC-14⑥a 共通ルール (b) が新しい言い方になっている" has "$FIX_LOOP" '手順4（新案なので条件を判定し直す）'
ckt "TC-14⑥b 共通ルール (b) に古い言い方が残っていない" hasnt "$FIX_LOOP" '手順4 ユーザー承認（新案のため）'
# ⑧（P4 の消費箇所: allowed-tools を必須・最小権限として扱う古い基準が残っていない）
ckt "TC-14⑧a review-rules.md に古い基準がない" hasnt "$ROOT/docs/runbooks/review-rules.md" '`allowed-tools` で最小権限が設定されているか'
ckt "TC-14⑧b plan-reviewer.md に古い基準がない" hasnt "$ROOT/.claude/review-agents/plan-reviewer.md" '`allowed-tools` で最小権限が設定されているか'
ckt "TC-14⑧c lint_skills.py が allowed-tools を必須にしていない" hasnt "$ROOT/scripts/migration_verify/lint_skills.py" 'REQUIRED_FIELDS = ["name", "description", "allowed-tools"]'
# ⑦（P2 の消費箇所）
ckt "TC-14⑦a issue-flow.md に新しい順番の説明がある" has "$ISSUE_FLOW" '`/plan-issue` の中で計画レビュー'
ckt "TC-14⑦b onboarding.md に新しい順番の説明がある" has "$ONBOARDING" '`/plan-issue` の中で計画レビュー'

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
