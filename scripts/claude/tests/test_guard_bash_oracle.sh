#!/usr/bin/env bash
# I174（plan_I174.md 0-13）: guard_bash_oracle.py（本物の bash との差分テスト）を決定論ゲートの許可された形で呼ぶ。
# 実行: bash scripts/claude/tests/test_guard_bash_oracle.sh [-v]
set -uo pipefail
# 見張りの「信頼する場所」の起点（I174 0-16）。外から渡された値で一時リポジトリが信頼されなくならないよう消す
unset CLAUDE_PROJECT_DIR
exec python3 "$(dirname "$0")/guard_bash_oracle.py" "$@"
