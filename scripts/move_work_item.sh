#!/usr/bin/env bash
# move_work_item.sh — Work Item フォルダを open → closed に移動する
#
# Usage:
#   bash scripts/move_work_item.sh <issue_number>
#   bash scripts/move_work_item.sh --help
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORK_DIR="$ROOT/docs/work"

usage() {
  echo "Usage: bash scripts/move_work_item.sh <issue_number>"
  echo ""
  echo "  Moves docs/work/open/<issue>/ → docs/work/closed/<issue>/"
  echo "  Requires 90_closeout.md to exist in the issue folder."
  exit 0
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
fi

if [[ -z "${1:-}" ]]; then
  echo "ERROR: issue_number is required." >&2
  usage
fi

ISSUE="$1"
SRC="$WORK_DIR/open/$ISSUE"
DST="$WORK_DIR/closed/$ISSUE"

if [[ ! -d "$SRC" ]]; then
  echo "ERROR: $SRC does not exist." >&2
  exit 1
fi

if [[ ! -f "$SRC/90_closeout.md" ]]; then
  echo "ERROR: $SRC/90_closeout.md is required before closing." >&2
  exit 1
fi

if [[ -d "$DST" ]]; then
  echo "ERROR: $DST already exists. Remove it first if you want to re-close." >&2
  exit 1
fi

echo "Moving: $SRC → $DST"
git -C "$ROOT" mv "$SRC" "$DST"
echo "OK: moved to closed/$ISSUE"
echo "Next: run 'python3 scripts/build_indices.py' to refresh indices."
