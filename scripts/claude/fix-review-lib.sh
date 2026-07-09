#!/usr/bin/env bash
# fix-review-lib.sh — /fix-loop 多段サブエージェントレビュー（診断/実装/テスト）の共有ライブラリ（I074）。
#
# 呼び出し元: fix-diagnosis-review.sh / fix-implementation-review.sh / fix-test-review.sh
#   （各エントリポイントが本 lib を source し run_fix_review を呼ぶ）。
# テスト:   REVIEW_LIB_SOURCE_ONLY=1 source して helper 関数のみを取り出す（本体なし・ガードは末尾）。
#
# 環境変数:
#   FIX_REVIEW_TIMEOUT  claude -p のタイムアウト秒（既定 300）。超過（exit 124）は非ブロック SKIP に落とす。
#
# ゲート伝達契約:
#   - stdout 末尾に `FIX_GATE: PASS|REMAND|SKIP` を出力（ログ・可読性用の補助）。
#   - exit code が一次: PASS/SKIP=0（次段へ進んでよい）・REMAND=1（差し戻し）。
#   - skip（reviewer 不在・claude -p 失敗/空/タイムアウト・VERDICT 判定不能）は exit 0（非ブロック＝headless でも fix-loop が回る）。
#     ただし「レビュー未実施」を記録に残し素通りでなく明示 skip とする。

# レビュー結果の重大度判定: アンカー付き完全一致で末尾 VERDICT 行を採る（部分一致・非近接 decoy を排除）。
# VERDICT 行が無い場合は空文字（＝判定不能）。自動ゲートでは「不在→OK 既定」を採らない（false-green 回避）。
detect_fix_verdict() {
  local file="$1" v
  v=$(grep -oE '^VERDICT:[[:space:]]*(BLOCKER|HIGH|OK)[[:space:]]*$' "$file" 2>/dev/null \
        | tail -1 | grep -oE '(BLOCKER|HIGH|OK)' || true)
  printf '%s' "$v"
}

# 順次ゲートしきい値の単一の真実: BLOCKER|HIGH → REMAND（差し戻し）/ それ以外(OK) → PASS。
verdict_to_gate() {
  case "$1" in
    BLOCKER|HIGH) printf 'REMAND' ;;
    *)            printf 'PASS' ;;
  esac
}

# ゲート → exit code（決定論伝達の純関数）: REMAND=1 / PASS=0。
gate_exit_code() {
  case "$1" in
    REMAND) printf '1' ;;
    *)      printf '0' ;;
  esac
}

# 生産物（レビュー記録）を生産者がコミットする（feature ブランチのみ path-scoped・非ブロック）。
# 保護ブランチ（develop/main/detached/取得失敗）では commit せず未追跡のまま残す（絶対ルール3）。
commit_review_artifact() {
  local file="$1" issue="$2" kind="$3" branch
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
  case "$branch" in
    develop|main|HEAD|"")
      echo "ℹ️ ブランチ '${branch:-detached}' のため ${file} は commit しません。"
      return 0 ;;
  esac
  if ! git add -- "$file" 2>/dev/null; then
    echo "⚠️ git add 失敗（未追跡のまま）: ${file}"; return 0
  fi
  git commit -q -m "docs(${issue}): ${kind} 記録" -- "$file" 2>/dev/null \
    || echo "⚠️ git commit 失敗（未追跡のまま）: ${file}"
  return 0
}

# 中核: kind のレビューをサブエージェント（claude -p・読み取り専用）で実行しゲート判定する。
# 引数: issue kind reviewer_path context remand_target
run_fix_review() {
  local issue="$1" kind="$2" reviewer="$3" context="$4" remand="$5"
  local ts review_file review v g pr

  # 1) reviewer 不在 → 非ブロック SKIP
  if [ ! -f "$reviewer" ]; then
    echo "⚠️ reviewer 定義が見つかりません: ${reviewer}。${kind} レビューを skip します。"
    echo "FIX_GATE: SKIP"; return 0
  fi

  ts=$(date +%Y%m%d_%H%M)
  review_file="docs/reviews/${issue}_fix_${kind}_review_${ts}.md"
  mkdir -p "$(dirname "$review_file")"

  # 3) タイムアウト付き起動。失敗・空・タイムアウト(exit124) は全て非ブロック SKIP＋未実施記録
  if ! review=$(printf '%s' "$context" | timeout "${FIX_REVIEW_TIMEOUT:-300}" claude -p \
        --model claude-sonnet-4-6 \
        --system-prompt "$(cat "$reviewer")" \
        --tools "Read,Grep,Glob") || [ -z "$review" ]; then
    printf '# %s fix-%s レビュー（未実施）\n\nclaude -p の失敗/空/タイムアウトのためレビュー未実施（非ブロック skip）。\n\nFIX_GATE: SKIP\n' \
      "$issue" "$kind" > "$review_file"
    commit_review_artifact "$review_file" "$issue" "fix-${kind}-review"
    echo "⚠️ ${kind} レビュー未実施（claude -p 失敗/空/タイムアウト）: ${review_file}"
    echo "FIX_GATE: SKIP"; return 0
  fi

  # 4) 正規化・保存・commit・PR コメント（任意・非ブロック）
  printf '%s\n' "$review" | sed 's/[[:space:]]*$//' > "$review_file"
  commit_review_artifact "$review_file" "$issue" "fix-${kind}-review"
  pr=$(gh pr view --json number -q .number 2>/dev/null || echo "")
  if [ -n "$pr" ]; then
    gh pr review "$pr" --comment --body "$(cat "$review_file")" 2>/dev/null \
      || echo "ℹ️ PR コメント投稿を skip（非ブロック）。"
  fi

  # 5) ゲート判定（exit code 一次）
  v=$(detect_fix_verdict "$review_file")
  if [ -z "$v" ]; then
    echo "⚠️ VERDICT 行が無く判定不能（${review_file}）。${kind} レビューを SKIP 扱い（false-green 回避のため PASS にしない）。"
    echo "FIX_GATE: SKIP"; return 0
  fi
  g=$(verdict_to_gate "$v")
  if [ "$g" = "PASS" ]; then
    echo "✅ ${kind} レビュー PASS（VERDICT: ${v}）。次段へ進めます。記録: ${review_file}"
    echo "FIX_GATE: PASS"; return 0
  fi
  echo "⛔ ${kind} レビュー差し戻し（VERDICT: ${v}）→ ${remand}。記録: ${review_file}"
  echo "FIX_GATE: REMAND"
  return "$(gate_exit_code REMAND)"
}

# ---- source ガード（全関数定義の後・本体の前に配置）----
# 本 lib は関数定義のみで実行本体を持たない。テスト/エントリポイントは source して関数を利用する。
if [ "${REVIEW_LIB_SOURCE_ONLY:-}" = "1" ]; then return 0; fi
