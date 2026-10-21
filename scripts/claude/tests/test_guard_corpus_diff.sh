#!/usr/bin/env bash
# I174（plan_I174.md 0-12）: guard_corpus_diff.py を決定論ゲートの許可された形（bash scripts/claude/tests/*.sh）で呼ぶ。
# 実行: bash scripts/claude/tests/test_guard_corpus_diff.sh [guard_corpus_diff.py の引数]
set -uo pipefail
exec python3 "$(dirname "$0")/guard_corpus_diff.py" "$@"
