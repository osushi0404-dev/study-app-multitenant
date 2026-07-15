#!/usr/bin/env bash
# I109: scheduled 依存監査 fail 時の GitHub イシュー自動起票（重複防止付き）
# 使い方: dependency-audit-issue.sh <backend|frontend> <監査出力ファイル>
# 前提: GH_TOKEN（issues:write）。GitHub Actions からは github.token を渡す。
# 重複防止: 監査種別（KIND）ごとに open イシュー最大 1 本。
#   既存があればコメント追記・なければ新規作成（判定は固定タイトルプレフィックスの前方一致）。
set -euo pipefail

KIND="${1:?usage: dependency-audit-issue.sh <backend|frontend> <audit-output-file>}"
OUT_FILE="${2:?usage: dependency-audit-issue.sh <backend|frontend> <audit-output-file>}"
case "$KIND" in
  backend|frontend) ;;
  *) echo "KIND は backend|frontend のみ（指定値: $KIND）" >&2; exit 2 ;;
esac
[ -f "$OUT_FILE" ] || { echo "監査出力ファイルが存在しない: $OUT_FILE" >&2; exit 2; }

LABEL="dependency-audit"
TITLE_PREFIX="[dependency-audit] ${KIND}:"
TITLE="${TITLE_PREFIX} 依存脆弱性を検知（scheduled audit）"

BODY_FILE="$(mktemp)"
trap 'rm -f "$BODY_FILE"' EXIT
{
  echo "## 検知内容（$(date -u +%Y-%m-%dT%H:%M:%SZ) UTC）"
  echo '```'
  cat "$OUT_FILE"
  echo '```'
  echo ""
  echo "## 対応手順"
  echo "docs/runbooks/dependency-audit.md を参照（/issue-bootstrap でローカルイシュー化して対応する）。"
} > "$BODY_FILE"

# --limit 50: gh issue list の既定上限 30 に暗黙依存しない（通常運用の open は種別ごと最大 1 本）
EXISTING="$(gh issue list --label "$LABEL" --state open --limit 50 --json number,title \
  --jq "[.[] | select(.title | startswith(\"${TITLE_PREFIX}\"))][0].number // empty")"

if [ -n "$EXISTING" ]; then
  gh issue comment "$EXISTING" --body-file "$BODY_FILE"
  echo "既存イシュー #${EXISTING} にコメント追記（重複起票を抑止）"
else
  gh issue create --title "$TITLE" --label "$LABEL" --body-file "$BODY_FILE"
  echo "新規イシューを起票"
fi
