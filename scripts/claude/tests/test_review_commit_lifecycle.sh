#!/usr/bin/env bash
# I069 テスト: レビュー記録（timestamped review）の commit ライフサイクル根治を検証する。
#  - 案A : plan-issue-review.sh / code-review.sh の commit_review_artifact（ブランチガード・path-scoped・他 index 不可侵）
#  - 案A': issue-review.sh は commit を配線しない（develop 直 commit 回避・意図コメントを明記）
#  - 案B : close/SKILL.md の timestamped 回収ループが未追跡 review でも git mv を失敗させない（add→mv）
#
# 実行（必ず bash スクリプトとして実行。対話シェルへ貼らない＝同梱 ugrep ラッパーで -E/-o が誤動作するため）:
#   bash scripts/claude/tests/test_review_commit_lifecycle.sh
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1

PLAN_REVIEW="scripts/claude/plan-issue-review.sh"
CODE_REVIEW="scripts/claude/code-review.sh"
ISSUE_REVIEW="scripts/claude/issue-review.sh"
CLOSE_SKILL=".claude/skills/close/SKILL.md"
TEST_SELF="scripts/claude/tests/test_review_commit_lifecycle.sh"

pass=0; fail=0; skip=0
ck() { # name expected actual
  if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1))
  else printf 'FAIL %s  expected[%s] got[%s]\n' "$1" "$2" "$3"; fail=$((fail+1)); fi
}
ck_true() { # name cmd... : expect exit 0
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then printf 'PASS %s\n' "$name"; pass=$((pass+1))
  else printf 'FAIL %s (expected success)\n' "$name"; fail=$((fail+1)); fi
}
ck_false() { # name cmd... : expect non-zero
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then printf 'FAIL %s (expected non-zero)\n' "$name"; fail=$((fail+1))
  else printf 'PASS %s\n' "$name"; pass=$((pass+1)); fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 使い捨て git fixture を作る（$1=サブディレクトリ名）。パスを echo で返す。
mk_repo() {
  local d="$TMP/$1"
  mkdir -p "$d/docs/reviews/closed"
  (
    cd "$d" || exit 1
    git init -q
    git config user.email t@example.com
    git config user.name tester
    git config commit.gpgsign false
    echo init > README.md
    git add README.md
    git commit -qm init
  ) >/dev/null 2>&1
  echo "$d"
}

# HEAD コミットが触れたファイル一覧（空行除去）
head_files() { git show --pretty=format: --name-only HEAD | sed '/^$/d'; }

echo "== TC-A1/A1b: source ガードで commit_review_artifact が定義（本体未実行） =="
# 対象スクリプトは冒頭で set -euo pipefail する。source 後にテストハーネス用へ解除する（review Info1）。
# shellcheck source=/dev/null
REVIEW_LIB_SOURCE_ONLY=1 source "$PLAN_REVIEW"
set +e +o pipefail
ck_true TC-A1-plan-fn   declare -F commit_review_artifact
# shellcheck source=/dev/null
REVIEW_LIB_SOURCE_ONLY=1 source "$CODE_REVIEW"
set +e +o pipefail
ck_true TC-A1b-code-fn  declare -F commit_review_artifact

echo "== TC-A2: feature ブランチで review 1ファイルが commit される =="
r="$(mk_repo a2)"; cd "$r" || exit 1
git checkout -qb feature/x
rf="docs/reviews/I900_plan_review_20260619_0000.md"; echo body > "$rf"
before="$(git rev-list --count HEAD)"
commit_review_artifact "$rf" I900 plan-review >/dev/null 2>&1
after="$(git rev-list --count HEAD)"
ck TC-A2-newcommit 1 "$((after - before))"
ck TC-A2-onlyfile "$rf" "$(head_files)"
ck_true TC-A2-tracked git ls-files --error-unmatch "$rf"
cd "$REPO_ROOT" || exit 1

echo "== TC-A3: 他 index 不可侵（事前 staged の無関係ファイルを commit に含めない） =="
r="$(mk_repo a3)"; cd "$r" || exit 1
git checkout -qb feature/y
echo other > other.txt; git add other.txt          # 事前 staging（無関係）
rf="docs/reviews/I900_plan_review_20260619_0001.md"; echo body > "$rf"
commit_review_artifact "$rf" I900 plan-review >/dev/null 2>&1
ck TC-A3-onlyfile "$rf" "$(head_files)"             # other.txt は commit に含まれない
ck_true TC-A3-other-staged sh -c 'git diff --cached --name-only | grep -qx other.txt'
cd "$REPO_ROOT" || exit 1

echo "== TC-A4: develop では commit せず未追跡で残す（ブランチガード） =="
r="$(mk_repo a4)"; cd "$r" || exit 1
git branch -M develop
rf="docs/reviews/I900_plan_review_20260619_0002.md"; echo body > "$rf"
before="$(git rev-list --count HEAD)"
out="$(commit_review_artifact "$rf" I900 plan-review 2>&1)"; rc=$?
after="$(git rev-list --count HEAD)"
ck TC-A4-rc 0 "$rc"
ck TC-A4-nocommit 0 "$((after - before))"
ck_false TC-A4-untracked git ls-files --error-unmatch "$rf"
ck_true  TC-A4-msg sh -c "printf '%s' \"\$1\" | grep -q 'commit しません'" _ "$out"
cd "$REPO_ROOT" || exit 1

echo "== TC-A5: detached HEAD でも commit せずスキップ =="
r="$(mk_repo a5)"; cd "$r" || exit 1
git checkout -q "$(git rev-parse HEAD)"             # detached
rf="docs/reviews/I900_plan_review_20260619_0003.md"; echo body > "$rf"
before="$(git rev-list --count HEAD)"
commit_review_artifact "$rf" I900 plan-review >/dev/null 2>&1; rc=$?
after="$(git rev-list --count HEAD)"
ck TC-A5-rc 0 "$rc"
ck TC-A5-nocommit 0 "$((after - before))"
ck_false TC-A5-untracked git ls-files --error-unmatch "$rf"
cd "$REPO_ROOT" || exit 1

echo "== TC-A6/A6b: issue-review.sh は案A'（commit 配線なし＋意図コメントあり） =="
# 配線検査はコメント行を除外（review W1）。実コードに commit_review_artifact / git commit が無いこと＝マッチ無し。
ck_false TC-A6-no-wiring sh -c "grep -vE '^[[:space:]]*#' '$ISSUE_REVIEW' | grep -E 'commit_review_artifact|git commit'"
# 意図コメントの存在（review W2）。commit しない／案A' の明記。
ck_true  TC-A6b-intent grep -qE 'commit しない|コミットしない|案A' "$ISSUE_REVIEW"

echo "== TC-B1: 未追跡 issue-review を回収ループ（add→mv）が git mv 失敗させない（AC1 再発防止） =="
r="$(mk_repo b1)"; cd "$r" || exit 1
f="docs/reviews/I900_issue_review_20260619_0200.md"; echo review > "$f"   # 未追跡
git add -- "$f"                                     # 案B: mv 前に追跡化
git mv "$f" docs/reviews/closed/ ; rc=$?
ck TC-B1-mv-rc 0 "$rc"
ck_true TC-B1-moved test -f "docs/reviews/closed/I900_issue_review_20260619_0200.md"
ck_true TC-B1-staged sh -c 'git diff --cached --name-only | grep -q "docs/reviews/closed/I900_issue_review_20260619_0200.md"'
cd "$REPO_ROOT" || exit 1

echo "== TC-B2: close/SKILL.md の timestamped 回収ループで git add が git mv の前に配線されている =="
# shellcheck disable=SC2016  # awk プログラム内の $f/NR は awk 変数（シェル展開しないため単一引用符が正）
ck_true TC-B2-add-before-mv awk '
  /git add -- "\$f"/ { add=NR }
  /git mv "\$f" docs\/reviews\/closed\// { if (add && NR-add<=3) found=1 }
  END { exit(found?0:1) }
' "$CLOSE_SKILL"

echo "== TC-B3: I067 決定論ゲート（step 3）が close/SKILL.md に非退行で残存 =="
ck_true TC-B3-scoped-add grep -qF 'git add -u' "$CLOSE_SKILL"
# shellcheck disable=SC2016  # 単一引用符はリテラル grep の意図（$ISSUE_NUM を展開しない）
ck_true TC-B3-gate grep -qF 'grep -vE "I${ISSUE_NUM}' "$CLOSE_SKILL"

echo "== TC-C1: shellcheck（pre-commit 同等。未インストール環境は SKIP） =="
if command -v shellcheck >/dev/null 2>&1; then
  ck_true TC-C1-shellcheck shellcheck "$PLAN_REVIEW" "$CODE_REVIEW" "$ISSUE_REVIEW" "$TEST_SELF"
else
  printf 'SKIP TC-C1-shellcheck (shellcheck 未インストール・pre-commit/CI で検査)\n'; skip=$((skip+1))
fi

echo "== TC-C2: bash -n 構文チェック（変更4スクリプト） =="
ck_true TC-C2-syntax-plan  bash -n "$PLAN_REVIEW"
ck_true TC-C2-syntax-code  bash -n "$CODE_REVIEW"
ck_true TC-C2-syntax-issue bash -n "$ISSUE_REVIEW"
ck_true TC-C2-syntax-self  bash -n "$TEST_SELF"

echo "== TC-C3: 既存テスト（test_review_verdict.sh）非退行 =="
ck_true TC-C3-verdict-regression bash scripts/claude/tests/test_review_verdict.sh

printf '\n==== I069 commit-lifecycle tests: PASS=%d FAIL=%d SKIP=%d ====\n' "$pass" "$fail" "$skip"
[ "$fail" -eq 0 ]
