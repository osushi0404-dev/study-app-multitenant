#!/usr/bin/env bash
set -euo pipefail

# ---- helper functions (テストは REVIEW_LIB_SOURCE_ONLY=1 で source して利用) ----

# open/closed 両方を検索してパスを返す（issues/tests/reviews 等の単一パターン用）
find_file() {
  local dir="$1" pattern="$2"
  if [ -f "docs/${dir}/open/${pattern}" ]; then echo "docs/${dir}/open/${pattern}"
  elif [ -f "docs/${dir}/closed/${pattern}" ]; then echo "docs/${dir}/closed/${pattern}"
  else echo ""
  fi
}

# 計画書専用: plan_I###*.md の連番を数値ソートし最大（最新）を返す。
# 無印=最古=0、_N=N。open/closed 横断で最大サフィックスを選ぶ（同値は open 優先）。該当なしは空文字。
find_plan_file() {
  local issue="$1" f n best="" best_n=-1
  for f in "docs/plans/open/plan_${issue}.md" docs/plans/open/plan_"${issue}"_*.md \
           "docs/plans/closed/plan_${issue}.md" docs/plans/closed/plan_"${issue}"_*.md; do
    [ -f "$f" ] || continue
    if [[ "$f" =~ plan_${issue}_([0-9]+)\.md$ ]]; then n="${BASH_REMATCH[1]}"; else n=0; fi
    if [ "$n" -gt "$best_n" ]; then best_n="$n"; best="$f"; fi
  done
  echo "$best"
}

# レビュー結果の重大度判定: 一次=機械可読 VERDICT 行 / 保険=装飾許容 grep（旧出力の後方互換）
detect_code_verdict() {
  local file="$1" v
  v=$(grep -oE '^VERDICT:[[:space:]]*(BLOCKER|HIGH|OK)[[:space:]]*$' "$file" 2>/dev/null | tail -1 | grep -oE '(BLOCKER|HIGH|OK)' || true)
  if [ -n "$v" ]; then echo "$v"; return; fi
  if grep -qE '^\|\s*\*{0,2}Blocker\b' "$file"; then echo "BLOCKER"; return; fi
  if grep -qE '^\|\s*\*{0,2}High\b'    "$file"; then echo "HIGH"; return; fi
  echo "OK"
}

# 案A(I069): レビュー記録（生産物）は生産者がコミットする。引数の1ファイルのみを path-scoped で
# add→commit（他の index/作業ツリーに触れない・auto-push しない・後続 close が push）。
# ブランチガード: 保護ブランチ（develop/main/detached HEAD/取得失敗）では commit せず未追跡のまま残す
#   （develop 直 commit 禁止＝絶対ルール3。未追跡分は close 案B が回収）。
# 非ブロック: add/commit が失敗してもレビューフロー（呼び出し元）は止めない。
commit_review_artifact() {
  local file="$1" issue="$2" kind="$3" branch
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
  case "$branch" in
    develop|main|HEAD|"")
      echo "ℹ️ ブランチ '${branch:-detached}' のため ${file} は commit しません（close 案B が回収）。"
      return 0 ;;
  esac
  if ! git add -- "$file" 2>/dev/null; then
    echo "⚠️ git add 失敗（未追跡のまま・close 案B が回収）: ${file}"
    return 0
  fi
  git commit -q -m "docs(${issue}): ${kind} 記録" -- "$file" 2>/dev/null \
    || echo "⚠️ git commit 失敗（未追跡のまま・close 案B が回収）: ${file}"
  return 0
}

# ---- I084: 決定論ゲート実走（auto_test.md 指定ゲートを実走し実 exit code を VERDICT に注入） ----

# 「## 決定論ゲート（自動実走）」直後の単一 fenced ```bash ブロックから
# 非空・非コメント行を 1 行 1 コマンドで抽出する（見出し不在なら空）。
extract_gate_commands() {
  local f="$1"
  [ -f "$f" ] || return 0
  awk '
    /^## 決定論ゲート（自動実走）/ { insec=1; next }
    insec && /^## /  { insec=0 }
    insec && /^```/  { infence = !infence; next }
    insec && infence {
      line=$0; sub(/[[:space:]]+$/, "", line)
      if (line ~ /^[[:space:]]*#/) next
      if (line ~ /^[[:space:]]*$/) next
      print line
    }
  ' "$f"
}

# ゲートコマンドを ALLOW（副作用なし・実走）/ HEAVY（/test 委譲・実走しない）/
# UNSAFE（allowlist 不一致・チェーン系＝実走しない fail-closed）に分類する。
# 判定順: HEAVY(先頭コマンド anchored) → allowlist(チェーンメタ文字ガード付き)ALLOW → UNSAFE。
classify_gate() {
  local cmd="$1"
  # 1. HEAVY: 先頭コマンド anchored（部分一致にしない。grep 引数の heavy 語で誤 defer しない）
  case "$cmd" in
    docker\ *|docker-compose\ *|npm\ *|npx\ *|pytest\ *|jest\ *|playwright\ *) echo HEAVY; return;;
    python\ -m\ pytest*|python3\ -m\ pytest*) echo HEAVY; return;;
    *manage.py\ test*) echo HEAVY; return;;
  esac
  # 2. チェーン/展開メタ文字を含む行は実走しない（実行する ALLOW のみに課す安全境界）
  # shellcheck disable=SC2016  # 単一引用符内は literal メタ文字（$( ` を展開させない意図）
  case "$cmd" in
    *';'*|*'|'*|*'&'*|*'`'*|*'$('*|*'>'*) echo UNSAFE; return;;
  esac
  # 3. allowlist 前方一致（副作用なし読み取り系）→ ALLOW
  case "$cmd" in
    bash\ scripts/claude/tests/*.sh|bash\ scripts/claude/tests/*.sh\ *) echo ALLOW; return;;
    grep\ *) echo ALLOW; return;;   # I084-CL-GREP: doc-sync 存在（grep -q）
    !\ grep\ *) echo ALLOW; return;;   # doc-sync 不在（! grep -q＝pattern が無いとき exit0）
    python3\ -m\ json.tool*)   echo ALLOW; return;;
    bash\ -n\ *)               echo ALLOW; return;;
    python3\ -m\ py_compile\ *) echo ALLOW; return;;
  esac
  echo UNSAFE
}

# 1 ゲートを timeout 付きで実走し exit code を返す（command not found / timeout も非ゼロ＝fail-closed）。
# GATE_TIMEOUT はテストで上書き可能（既定 120 秒）。
run_one_gate() {
  timeout "${GATE_TIMEOUT:-120}" bash -c "$1" >/dev/null 2>&1
}

# 宣言ゲートを分類・実走し、グローバル GATE_EVIDENCE（証跡 md）/ GATE_VERDICT（OK|BLOCKER）を設定する。
# サブシェル汚染を避けるため呼び出し元は $() を使わず直呼びすること（W1）。
run_declared_gates() {
  local f="$1" cmd cls code had=0
  GATE_VERDICT=OK; GATE_EVIDENCE=""
  while IFS= read -r cmd; do
    [ -n "$cmd" ] || continue
    had=1
    cls=$(classify_gate "$cmd")
    case "$cls" in
      ALLOW)
        code=0; run_one_gate "$cmd" || code=$?
        if [ "$code" -eq 0 ]; then
          GATE_EVIDENCE+="- \`${cmd}\` → exit=0 ✅"$'\n'
        else
          GATE_EVIDENCE+="- \`${cmd}\` → exit=${code} ❌ FAIL"$'\n'
          GATE_VERDICT=BLOCKER   # I084-RUN-FAIL: ALLOW 実走 FAIL は fail-closed
        fi ;;
      HEAVY)
        GATE_EVIDENCE+="- \`${cmd}\` → ⏭ /test に委譲（heavy・code-review では実走しない）"$'\n' ;;
      UNSAFE)
        GATE_EVIDENCE+="- \`${cmd}\` → ⚠️ 実走対象外（allowlist 不一致/チェーン系・fail-closed）"$'\n'
        GATE_VERDICT=BLOCKER ;;
    esac
  done < <(extract_gate_commands "$f")
  [ "$had" -eq 1 ] || GATE_EVIDENCE="(決定論ゲート宣言なし)"
}

# 宣言セクション外の fenced ```bash/```sh ブロック内に allowlist ゲートパターンがあれば HIGH。
# テーブルセル・インライン backtick・散文・heavy は非検出（本 auto_test.md 自身の自傷 HIGH を回避・W4）。
omission_lint() {
  local f="$1" outside hit
  [ -f "$f" ] || { echo OK; return; }
  outside=$(awk '
    /^## 決定論ゲート（自動実走）/ { insec=1; next }
    /^## / && insec { insec=0 }
    /^```/ { fence = !fence; next }
    { if (!insec && fence) print }
  ' "$f")
  hit=$(printf '%s\n' "$outside" | grep -oE '(bash[[:space:]]+scripts/claude/tests/[^[:space:]]+\.sh|grep[[:space:]]+-[qL]|python3[[:space:]]+-m[[:space:]]+json\.tool|bash[[:space:]]+-n[[:space:]]|python3[[:space:]]+-m[[:space:]]+py_compile)' | head -1)   # I084-OM-GREP
  [ -n "$hit" ] && echo HIGH || echo OK
}

# VERDICT 順位（BLOCKER>HIGH>OK）と、複数 VERDICT の最大を返す。
verdict_rank() { case "$1" in BLOCKER) echo 3;; HIGH) echo 2;; *) echo 1;; esac; }
combine_verdict() {
  local best=OK best_r=1 v r
  for v in "$@"; do
    r=$(verdict_rank "$v")
    if [ "$r" -gt "$best_r" ]; then best_r=$r; best="$v"; fi   # I084-CB-CMP
  done
  echo "$best"
}

# レビュー記録の先頭へ証跡セクションを prepend し、末尾の VERDICT 行を FINAL に書換える。
inject_gate_result() {
  local file="$1" evidence="$2" omission="$3" final="$4" tmp
  tmp=$(mktemp)
  {
    echo "## 決定論ゲート実行結果（code-review.sh 自動注入）"
    echo ""
    printf '%s\n' "$evidence"
    echo "- omission-lint: ${omission}"
    echo "- FINAL VERDICT（gate/omission/LLM 合成）: ${final}"
    echo ""
    echo "---"
    echo ""
    cat "$file"
  } > "$tmp"
  if grep -qE '^VERDICT:' "$tmp"; then
    sed -i -E "s/^VERDICT:.*/VERDICT: ${final}/" "$tmp"
  else
    printf '\nVERDICT: %s\n' "$final" >> "$tmp"
  fi
  mv "$tmp" "$file"
}

# テストから関数のみを source するためのガード（本体は実行しない）
if [ "${REVIEW_LIB_SOURCE_ONLY:-}" = "1" ]; then return 0; fi

ISSUE="${1:?Usage: $0 I###}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

TIMESTAMP=$(date +%Y%m%d_%H%M)
REVIEW_FILE="docs/reviews/${ISSUE}_code_review_${TIMESTAMP}.md"
REVIEWER=".claude/review-agents/code-reviewer.md"

# CI 待機（最大 10 分）
PR_NUM=$(gh pr view --json number -q .number 2>/dev/null || echo "")
CI_OUTPUT=""
if [ -n "$PR_NUM" ]; then
  echo "CI を確認しています (PR #${PR_NUM})..."
  TIMEOUT=600
  ELAPSED=0
  while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
    CI_OUTPUT=$(gh pr checks "$PR_NUM" 2>&1 || true)
    if ! echo "$CI_OUTPUT" | grep -q "pending"; then
      break
    fi
    echo "  pending... ${ELAPSED}s / ${TIMEOUT}s"
    sleep 15
    ELAPSED=$((ELAPSED + 15))
  done
  if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    echo "⚠️ CI タイムアウト（${TIMEOUT}秒）。"
  fi
  if echo "$CI_OUTPUT" | grep -q "fail"; then
    echo "⛔ CI が失敗しています。修正後に再 push してください。"
    echo "$CI_OUTPUT"
    exit 1
  fi
fi

ISSUE_FILE=$(find_file "issues" "${ISSUE}.md")
PLAN_FILE=$(find_plan_file "$ISSUE")

[ -z "$ISSUE_FILE" ] && { echo "⚠️ イシューファイルが見つかりません"; exit 1; }

# git 情報取得（最大 100KB、|| true で SIGPIPE による pipefail を抑制）
GIT_DIFF=$(git diff origin/develop...HEAD | head -c 102400 || true)
GIT_LOG=$(git log origin/develop...HEAD --oneline)
GIT_FILES=$(git diff origin/develop...HEAD --name-only)

# I084: auto_test.md の決定論ゲートをスクリプト自身で実走し、実 exit code を証跡化する。
# 直呼び（$() 不可）で GATE_EVIDENCE / GATE_VERDICT をグローバル設定する（W1）。
AUTO_TEST_FILE=$(find_file "tests" "${ISSUE}_auto_test.md")
GATE_VERDICT=OK; OMISSION_VERDICT=OK; GATE_EVIDENCE="(決定論ゲート宣言なし)"
if [ -n "$AUTO_TEST_FILE" ]; then
  run_declared_gates "$AUTO_TEST_FILE"
  OMISSION_VERDICT=$(omission_lint "$AUTO_TEST_FILE")
fi

# コンテキスト組み立て
CONTEXT="イシュー番号: ${ISSUE}

### イシューファイル
$(cat "$ISSUE_FILE")

### 計画書
$([ -n "$PLAN_FILE" ] && cat "$PLAN_FILE" || echo "(計画書なし)")

### 決定論ゲート実行結果（スクリプト実走済み・実 exit code／読解で上書きしないこと）
${GATE_EVIDENCE}
omission-lint: ${OMISSION_VERDICT}

### git log (origin/develop...HEAD)
${GIT_LOG}

### 変更ファイル一覧
${GIT_FILES}

### git diff (origin/develop...HEAD, max 100KB)
\`\`\`diff
${GIT_DIFF}
\`\`\`"

# claude -p でレビュー実行（--tools でホワイトリスト制限: Read/Grep/Glob のみ）
REVIEW=$(printf '%s' "$CONTEXT" | claude -p \
  --model claude-sonnet-4-6 \
  --system-prompt "$(cat "$REVIEWER")" \
  --tools "Read,Grep,Glob")

[ -z "$REVIEW" ] && { echo "⚠️ claude -p が空を返しました。終了します。"; exit 1; }

# 出力正規化
REVIEW_CLEAN=$(printf '%s\n' "$REVIEW" | sed 's/[[:space:]]*$//')

# ファイル保存
mkdir -p "$(dirname "$REVIEW_FILE")"
printf '%s\n' "$REVIEW_CLEAN" > "$REVIEW_FILE"

# I084: 決定論ゲート結果で VERDICT を決定論的に上書きする（LLM 出力非依存）。
# FINAL = max(gate, omission, LLM)。証跡を記録先頭へ注入し末尾 VERDICT 行を FINAL に書換え。
LLM_VERDICT=$(detect_code_verdict "$REVIEW_FILE")
FINAL_VERDICT=$(combine_verdict "$GATE_VERDICT" "$OMISSION_VERDICT" "$LLM_VERDICT")
inject_gate_result "$REVIEW_FILE" "$GATE_EVIDENCE" "$OMISSION_VERDICT" "$FINAL_VERDICT"

# 案A(I069): 生産物（レビュー記録）を生産者がコミットする（feature ブランチ時のみ・path-scoped）。
commit_review_artifact "$REVIEW_FILE" "$ISSUE" "code-review"

# PR コメント投稿
if [ -n "$PR_NUM" ]; then
  gh pr review "$PR_NUM" --comment --body "$(cat "$REVIEW_FILE")" \
    || echo "⚠️ PR コメント投稿失敗。手動で実行: gh pr review $PR_NUM --comment --body \"\$(cat $REVIEW_FILE)\""
fi

# 判定とユーザー案内（一次=VERDICT 行 / 保険=装飾許容 grep）
case "$(detect_code_verdict "$REVIEW_FILE")" in
  BLOCKER)
    # shellcheck disable=SC2016
    printf '\n⛔ Blocker が残っています。`/fix-loop %s` で修正後、`/code-review %s` を再実行してください。\n' "$ISSUE" "$ISSUE" ;;
  HIGH)
    # shellcheck disable=SC2016
    printf '\n❌ レビュー NG。`/fix-loop %s` を実行してください。fix-loop 完了後は `/code-review %s` に戻ってください。\n' "$ISSUE" "$ISSUE" ;;
  *)
    # shellcheck disable=SC2016
    printf '\n✅ コードレビュー完了。`/test %s` を実行してください。\n' "$ISSUE" ;;
esac
