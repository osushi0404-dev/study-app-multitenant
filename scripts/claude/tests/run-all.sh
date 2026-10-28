#!/usr/bin/env bash
# run-all.sh: ハーネスのテスト（scripts/claude/tests/test_*.sh）を順に全部流す（I193・I185 P8）。
# 呼び出し元: .github/workflows/ci.yml の Harness Tests ジョブ・test-gate・決定論ゲート
# 使い方: bash scripts/claude/tests/run-all.sh [テストのファイル ...]   # 引数を渡せばそれだけを流す（I211）
# 終了コード: 全部合格で 0、1 本でも失敗すれば 1。TEST_DIR で対象のフォルダを差し替えられる（失敗を入れた確認用）
# uv の環境（scripts/claude/tests/.venv）の外で呼ばれたら、uv run --locked で版をそろえて流し直す（I211。版の正は pyproject.toml・uv.lock・.python-version）
# 最初に、テストが頼る道具を一覧（required-tools.txt）で確かめ、合わなければテストを流さずに 1（I204。TEST_DIR によらない）
set -uo pipefail

cd "$(git rev-parse --show-toplevel)" || exit 1
REPO_ROOT="$(pwd -P)"
PROJ="scripts/claude/tests"
if [ "${VIRTUAL_ENV:-}" != "$REPO_ROOT/$PROJ/.venv" ]; then
  if [ -n "${HARNESS_UV_REEXEC:-}" ]; then
    echo "⛔ uv で流し直しても uv の環境に入れませんでした（VIRTUAL_ENV=${VIRTUAL_ENV:-}）"
    exit 1
  fi
  if ! command -v uv >/dev/null 2>&1; then
    echo "⛔ uv がありません。入れ方: docs/runbooks/onboarding.md「手元の準備（ハーネスのテスト）」。テストは流していません"
    exit 1
  fi
  HARNESS_UV_REEXEC=1 exec uv run --locked --project "$PROJ" bash "$PROJ/run-all.sh" "$@"
fi
if ! bash "$PROJ/check-tools.sh"; then
  echo "⛔ ハーネスのテストが頼る道具がそろっていません（一覧: $PROJ/required-tools.txt）。テストは流していません"
  exit 1
fi
TEST_DIR="${TEST_DIR:-$PROJ}"
if [ "$#" -gt 0 ]; then
  for t in "$@"; do [ -f "$t" ] || { echo "⛔ テストのファイルがありません: $t"; exit 1; }; done
  TESTS=("$@")
else
  TESTS=("$TEST_DIR"/test_*.sh)
fi

pass=0; fail=0; failed=()
LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT
for t in "${TESTS[@]}"; do
  [ -f "$t" ] || continue
  if bash "$t" >"$LOG" 2>&1; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1)); failed+=("$t")
    echo "FAIL $t"
    # CI のログで原因が分かるよう、失敗した項目と最後の数行を出す（PASS の行は出さない）
    grep -vE '^(PASS|OK:)' "$LOG" | tail -20 | sed 's/^/    /'
  fi
done

echo "run-all: pass=${pass} fail=${fail}"
if [ "$pass" -eq 0 ] && [ "$fail" -eq 0 ]; then
  echo "⛔ テストが 1 本も見つかりません: ${TEST_DIR}/test_*.sh"
  exit 1
fi
if [ "$fail" -ne 0 ]; then
  echo "失敗したテスト（個別に実行すると詳細が出ます）:"
  printf '  bash %s/run-all.sh %s\n' "$PROJ" "${failed[@]}"
  exit 1
fi
exit 0
