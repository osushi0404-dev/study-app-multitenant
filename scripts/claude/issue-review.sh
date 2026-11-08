#!/usr/bin/env bash
set -euo pipefail

# issue-review: イシューファイル単体を第三者サブエージェントでレビューし、自己完結度を判定する。
# 呼び出し元: .claude/skills/issue-bootstrap/SKILL.md（step 3.5・GitHub 登録前）
# 方針: ソフト・非ブロック。失敗しても呼び出し元（issue-bootstrap）のフローを止めない。
# PR コメントはしない（この時点で PR は未作成）。

# 使い方: issue-review.sh I###（手元のイシューファイル）／issue-review.sh --file <下書き>
#   --file は GitHub に登録する前の下書き（番号が決まる前・I221）。結果は docs/reviews/ に保存せず画面に出すだけ
#   （判定の 1 行は issue-bootstrap が本文に書く）。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel)"
DRAFT_FILE=""
if [ "${1:-}" = "--file" ]; then
  [ -f "${2:-}" ] || { echo "⚠️ 下書きのファイルが見つかりません: ${2:-}。issue-review をスキップします。"; exit 0; }
  DRAFT_FILE="$(realpath -- "$2")"
  ISSUE_FILE="$DRAFT_FILE"
  ISSUE="（登録前の下書き）"
  cd "$REPO_ROOT"
else
  ISSUE="${1:?Usage: $0 I### | --file <下書き>}"
  cd "$REPO_ROOT"
  # イシューファイルの探索は issue-source.sh の 1 か所（I221）。未検出でも非ブロックで終了する
  ISSUE_FILE="$(bash "$SCRIPT_DIR/issue-source.sh" path "$ISSUE" 2>/dev/null)" || {
    echo "⚠️ イシューファイルが見つかりません: ${ISSUE}.md。issue-review をスキップします。"
    exit 0
  }
fi

TIMESTAMP=$(date +%Y%m%d_%H%M)
REVIEW_FILE="docs/reviews/${ISSUE}_issue_review_${TIMESTAMP}.md"
REVIEWER_AGENT="issue-reviewer"   # 定義: .claude/agents/issue-reviewer.md（tools: Read, Grep, Glob）

# reviewer 定義の存在確認（非ブロック・防御的）
if [ ! -f ".claude/agents/${REVIEWER_AGENT}.md" ]; then
  echo "⚠️ issue-reviewer.md が見つかりません。issue-review をスキップします。"
  exit 0
fi

CONTEXT="イシュー番号: ${ISSUE}

### イシューファイル
$(cat "$ISSUE_FILE")"

# claude -p で第三者レビュー（I193: 公式のサブエージェント定義を --agent で呼ぶ。読み取り専用は定義の tools で効かせる）。
# 失敗・時間切れ（REVIEW_TIMEOUT・既定 900 秒）でも起票フローを止めない
if ! REVIEW=$(printf '%s' "$CONTEXT" | GH_APP_READONLY=1 timeout "${REVIEW_TIMEOUT:-900}" claude -p --agent "$REVIEWER_AGENT" --tools "Read,Grep,Glob" --strict-mcp-config --permission-prompts none); then
  echo "⚠️ issue-review をスキップしました（claude -p 失敗または時間切れ）。"
  exit 0
fi

if [ -z "$REVIEW" ]; then
  echo "⚠️ issue-review が空を返しました。スキップします。"
  exit 0
fi

# 出力正規化: 行末スペース除去
REVIEW_CLEAN=$(printf '%s\n' "$REVIEW" | sed 's/[[:space:]]*$//')

# 下書きのときは保存しない（番号が無く、手元に未追跡のファイルを残さない・I221）
if [ -n "$DRAFT_FILE" ]; then
  printf '%s\n' "$REVIEW_CLEAN"
  exit 0
fi

# ファイル保存
mkdir -p "$(dirname "$REVIEW_FILE")"
printf '%s\n' "$REVIEW_CLEAN" > "$REVIEW_FILE"

# 案A'(I069): この記録は commit しない（生産者コミットの例外）。issue-review は /issue-bootstrap 中に走り、
# その時点のブランチが develop の場合があるため、ここで commit すると develop 直 commit（絶対ルール3 違反）に
# なり得る。よって未追跡のまま残し、当該イシューの close（案B＝単一回収点）で git add→git mv して回収する。
# plan-issue-review / code-review（feature ブランチ前提）の案A とは扱いを分ける。

echo "📝 issue-review 結果: ${REVIEW_FILE}"
printf '%s\n' "$REVIEW_CLEAN"
# 判定はソフト。呼び出し元（issue-bootstrap）が判定（十分/要補足）を見て報告文を分岐する。
