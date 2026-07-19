#!/usr/bin/env bash
# I134: イシュー文書の **背景**:/**目的**: ラベル 2 行の全件存在チェック（合格=exit 0）
# 使い方: bash scripts/claude/check-issue-background.sh [対象ディレクトリ]（既定: docs/issues/open）
set -u
DIR="${1:-docs/issues/open}"
missing=0
for f in "$DIR"/*.md; do
  [ -f "$f" ] || continue
  if ! grep -q '^\*\*背景\*\*:' "$f" || ! grep -q '^\*\*目的\*\*:' "$f"; then
    echo "MISSING: $f"
    missing=$((missing + 1))
  fi
done
if [ "$missing" -gt 0 ]; then
  echo "NG: ${missing} file(s) missing 背景/目的 labels"
  exit 1
fi
echo "OK: all files have 背景/目的 labels"
exit 0
