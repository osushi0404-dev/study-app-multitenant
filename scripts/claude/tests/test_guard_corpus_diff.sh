#!/usr/bin/env bash
# I174（plan_I174.md 0-12）: guard_corpus_diff.py を bash scripts/claude/tests/*.sh の形で呼ぶ。
# 実行: bash scripts/claude/tests/test_guard_corpus_diff.sh [guard_corpus_diff.py の引数]
# 所要は作業記録の件数に比例して数分かかる。auto_test の決定論ゲート（1 行 120 秒）には置かず、見張りを直したときに
# 手で流して結果を記録する（danger-ops.md「見張りを直したら、コミットの前に 3 つのテストを流す」・I444）。
# 作業記録が無い環境（CI）では SKIP。
set -uo pipefail
exec python3 "$(dirname "$0")/guard_corpus_diff.py" "$@"
