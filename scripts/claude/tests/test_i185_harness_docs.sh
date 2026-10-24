#!/usr/bin/env bash
# I185 P2・P4: スキル・手順書の書き換えを決定論検証する（docker/pytest 非依存）。
# 実行: bash scripts/claude/tests/test_i185_harness_docs.sh
#       bash scripts/claude/tests/test_i185_harness_docs.sh --update   # 固定した文章（fixtures）を今の内容で作り直す
#
# P2: 計画レビューを人の承認の前に済ませる（plan-issue が plan-issue-review.sh を実行する）
# P4: スキルの allowed-tools（事前許可）を外し、制限は disallowed-tools で書く
# P3（fix-loop の自動進行）はこのイシューから外した（敵対的レビュー 2 周で穴が続いたため・別イシュー）。
#
# 守りの部分は、文字列の一部ではなく「ブロックを丸ごと固定」して照合する（敵対的レビューで、部分一致の
# 照合は削除・反転・挿入を見逃すと 2 周続けて分かったため。粗くても確実に止まる側に倒す）。
# 守りの部分を変えるときは --update で fixtures を作り直し、その差分をレビューで見る。
# 検証するリポジトリのルートは環境変数 ROOT で差し替えられる（壊した版に当てて不合格になることの確認用）。
# 0=全 PASS / 1=FAIL あり。
# shellcheck disable=SC2016  # 単一引用符内の $ARGUMENTS・バッククォートは文書の文字どおりの照合用（展開させない意図）
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
ROOT="${ROOT:-$REPO_ROOT}"
FIXTURES="$REPO_ROOT/scripts/claude/tests/fixtures/i185"
SKILLS="$ROOT/.claude/skills"
PLAN_ISSUE="$SKILLS/plan-issue/SKILL.md"
FIX_LOOP="$SKILLS/fix-loop/SKILL.md"
SEC_REVIEW="$SKILLS/security-review/SKILL.md"
WORKFLOW="$ROOT/docs/runbooks/workflow.md"
ISSUE_FLOW="$ROOT/docs/runbooks/issue-flow.md"
ONBOARDING="$ROOT/docs/runbooks/onboarding.md"
REVIEW_RULES="$ROOT/docs/runbooks/review-rules.md"
PLAN_REVIEWER="$ROOT/.claude/review-agents/plan-reviewer.md"
LINT_SKILLS="$ROOT/scripts/migration_verify/lint_skills.py"

# block <file> <開始行の先頭> <終了行の先頭|EOF>: 開始行から終了行の手前まで（EOF なら最後まで）を出す。
# 開始行・終了行が見つからなければ非 0。
block() {
  python3 - "$1" "$2" "$3" <<'PY'
import sys
path, start, end = sys.argv[1:]
try:
    lines = open(path, encoding="utf-8").read().split("\n")
except OSError:
    sys.exit(2)
s = next((i for i, l in enumerate(lines) if l.startswith(start)), None)
if s is None:
    sys.exit(1)
if end == "EOF":
    e = len(lines)
else:
    e = next((i for i in range(s + 1, len(lines)) if lines[i].startswith(end)), None)
    if e is None:
        sys.exit(1)
sys.stdout.write("\n".join(lines[s:e]).rstrip("\n") + "\n")
PY
}

# 固定するブロックの一覧: 名前|ファイル|開始行の先頭|終了行の先頭（EOF は最後まで）
PINS=(
  "plan_issue_review_section@@$PLAN_ISSUE@@**計画レビュー（承認ポイント提示の前に実施@@EOF"
  "security_review_frontmatter@@$SEC_REVIEW@@---@@# /security-review"
  "workflow_flow_2_3@@$WORKFLOW@@2. /plan-issue I### →@@3.5. /security-review"
  "workflow_transition_rows@@$WORKFLOW@@| 計画書承認後（高リスク判定 No）@@| security-review Blocker なし後"
  "issue_flow_8_5@@$ISSUE_FLOW@@8.5. \`/plan-issue\` の中で計画レビュー@@=== フェーズ3"
  "issue_flow_step_8_5@@$ISSUE_FLOW@@**ステップ8.5: 計画レビュー@@#### フェーズ3"
)

# split_pin <エントリ>: 「@@」区切り（表の行の先頭の「|」とぶつからないように）を name/file/start/end に分ける
split_pin() {
  local rest="$1"
  name="${rest%%@@*}"; rest="${rest#*@@}"
  file="${rest%%@@*}"; rest="${rest#*@@}"
  start="${rest%%@@*}"; end="${rest#*@@}"
}

if [ "${1:-}" = "--update" ]; then
  mkdir -p "$FIXTURES"
  for p in "${PINS[@]}"; do
    split_pin "$p"
    block "$file" "$start" "$end" > "$FIXTURES/$name.txt" || { echo "取り出せません: $name"; exit 1; }
    echo "updated: $FIXTURES/$name.txt"
  done
  exit 0
fi

pass=0; fail=0
ckt() { local name="$1"; shift
        if "$@"; then printf 'PASS %s\n' "$name"; pass=$((pass+1));
        else printf 'FAIL %s\n' "$name"; fail=$((fail+1)); fi; }
has_line() { grep -qxF -- "$2" "$1"; }            # その 1 行が丸ごとある
hasnt()    { [ -f "$1" ] && ! grep -qF -- "$2" "$1"; }   # ファイルがあり、文字どおり含まない

pinned() {  # pinned <name> <file> <start> <end>: ブロックが固定した文章と 1 文字も違わない
  local got
  got="$(block "$2" "$3" "$4")" || return 1
  [ -f "$FIXTURES/$1.txt" ] && [ "$got" = "$(cat "$FIXTURES/$1.txt")" ]
}

no_allowed_tools_in_frontmatter() {
  python3 - "$SKILLS" <<'PY'
import glob, os, sys
files = sorted(glob.glob(os.path.join(sys.argv[1], "*", "SKILL.md")))
bad = []
for f in files:
    lines = open(f, encoding="utf-8").read().split("\n")
    if lines[:1] != ["---"] or "---" not in lines[1:]:
        bad.append(f); continue
    fm = lines[1:lines.index("---", 1)]
    if any(l.split(":", 1)[0].strip() == "allowed-tools" for l in fm):
        bad.append(f)
for f in bad:
    print("  allowed-tools が残っている（または frontmatter が無い）:", f)
sys.exit(0 if files and not bad else 1)
PY
}

stop_only_in_review_section() {  # 計画レビューの節より前に「停止」の指示がない（承認の前に止まる手順を差し込ませない）
  python3 - "$PLAN_ISSUE" <<'PY'
import sys
lines = open(sys.argv[1], encoding="utf-8").read().split("\n")
s = next((i for i, l in enumerate(lines) if l.startswith("**計画レビュー（承認ポイント提示の前に実施")), None)
sys.exit(0 if s is not None and not any("停止" in l for l in lines[:s]) else 1)
PY
}

lint_does_not_require_allowed_tools() {  # 書式によらず REQUIRED_FIELDS の中身を読む
  python3 - "$LINT_SKILLS" <<'PY'
import ast, sys
tree = ast.parse(open(sys.argv[1], encoding="utf-8").read())
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "REQUIRED_FIELDS" for t in node.targets):
        value = ast.literal_eval(node.value)
        sys.exit(0 if "allowed-tools" not in value and {"name", "description"} <= set(value) else 1)
sys.exit(1)
PY
}

# 固定したブロック（P2・P4）
for p in "${PINS[@]}"; do
  split_pin "$p"
  ckt "TC-14pin $name が固定した文章と一致" pinned "$name" "$file" "$start" "$end"
done
ckt "TC-14③ 計画レビューの節より前に「停止」の指示がない" stop_only_in_review_section
ckt "TC-14④ workflow.md に「計画書承認後 → /plan-issue-review を入力」がない" hasnt "$WORKFLOW" '| 計画書承認後 | 「`/plan-issue-review I###` を入力してください」'
ckt "TC-14⑦ onboarding.md の流れが新しい順番" has_line "$ONBOARDING" '/issue-bootstrap → /grill-me → /plan-issue（計画レビューまで）'
# P4
ckt "TC-14① どの SKILL.md の frontmatter にも allowed-tools がない" no_allowed_tools_in_frontmatter
ckt "TC-14⑧a review-rules.md のスキル変更チェック 1 が新しい基準" has_line "$REVIEW_RULES" '| 1 | 使えるツールを絞る必要があるスキルは `disallowed-tools` で制限しているか。`allowed-tools` は「確認なしで使ってよい」事前許可で制限にはならないので、付けるなら本当に事前許可が要るものだけに絞っているか（素の `Bash` を事前許可していないか）（I185 P4） | セキュリティ |'
ckt "TC-14⑧b plan-reviewer.md の観点が新しい基準" has_line "$PLAN_REVIEWER" '- 使えるツールを絞る必要があるスキルは `disallowed-tools` で制限しているか（`allowed-tools` は事前許可で制限にはならない。付けるなら本当に事前許可が要るものだけで、素の `Bash` を事前許可していないか）'
ckt "TC-14⑧c lint_skills.py の必須項目に allowed-tools がない" lint_does_not_require_allowed_tools
# P3 を外したこと（fix-loop は人が案を選ぶ形のまま）
ckt "TC-14⑤a fix-loop 手順 4 は承認待ちで停止" has_line "$FIX_LOOP" '4) 承認待ちで停止（ユーザーが案を選択。軽微例外による実装/テストレビュー簡略化の可否もここで判断）'
ckt "TC-14⑤b fix-loop に推奨案で自動に進む手順がない" hasnt "$FIX_LOOP" '推奨案で進めて'
ckt "TC-14⑤c 共通ルール (b) は新案のユーザー承認のまま" grep -qF '手順4 ユーザー承認（新案のため）' "$FIX_LOOP"

printf 'pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
