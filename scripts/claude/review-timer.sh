#!/usr/bin/env bash
# review-timer.sh <秒>: review-gate の敵対的レビューのタイマー（I193）。指定の秒数だけ待って終わる。
# 呼び出し元: .claude/skills/review-gate/SKILL.md 3-1（Bash ツールの run_in_background で起動し、完了の通知を「時間切れ」の合図にする）
# 手順に `sleep` を直接書くと settings の allow に一致せず承認画面が出るので、スクリプトにしてある（`Bash(bash scripts/claude/*)`）
set -euo pipefail
SECS="${1:-}"
if ! [[ "$SECS" =~ ^[0-9]+$ ]] || [ "$SECS" -lt 1 ] || [ "$SECS" -gt 3600 ]; then
  echo "⛔ 使い方: $0 <1〜3600 の秒数>（受け取った値: '${SECS}'）"
  exit 2
fi
sleep "$SECS"
echo "REVIEW_TIMER: DONE ${SECS}s"
