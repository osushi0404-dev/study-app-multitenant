#!/usr/bin/env bash
# run-all.sh: ハーネスのテスト（scripts/claude/tests/test_*.sh）を順に全部流す（I193・I185 P8）。
# 呼び出し元: .github/workflows/ci.yml の Harness Tests ジョブ・test-gate
# 終了コード: 全部合格で 0、1 本でも失敗すれば 1。TEST_DIR で対象のフォルダを差し替えられる（失敗を入れた確認用）
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)" || exit 1
cd "$REPO_ROOT" || exit 1
TEST_DIR="${TEST_DIR:-scripts/claude/tests}"

pass=0; fail=0; failed=()
for t in "$TEST_DIR"/test_*.sh; do
  [ -f "$t" ] || continue
  if bash "$t" >/dev/null 2>&1; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1)); failed+=("$t")
    echo "FAIL $t"
  fi
done

echo "run-all: pass=${pass} fail=${fail}"
if [ "$pass" -eq 0 ] && [ "$fail" -eq 0 ]; then
  echo "⛔ テストが 1 本も見つかりません: ${TEST_DIR}/test_*.sh"
  exit 1
fi
if [ "$fail" -ne 0 ]; then
  echo "失敗したテスト（個別に実行すると詳細が出ます）:"
  printf '  bash %s\n' "${failed[@]}"
  exit 1
fi
exit 0
