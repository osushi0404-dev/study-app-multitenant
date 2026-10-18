#!/usr/bin/env bash
# I174（plan_I174.md 0-13）: guard_bash_oracle.py（本物の bash との差分テスト）を決定論ゲートの許可された形で呼ぶ。
# 実行: bash scripts/claude/tests/test_guard_bash_oracle.sh [-v]
set -uo pipefail
exec python3 "$(dirname "$0")/guard_bash_oracle.py" "$@"
