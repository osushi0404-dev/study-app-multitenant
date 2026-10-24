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
# I193（I185 種類 C）: VERDICT 行も表の印も無い（レビューが正常に終わっていない）ときは OK にせず BLOCKER（fail-closed）
detect_code_verdict() {
  local file="$1" v
  v=$(grep -oE '^VERDICT:[[:space:]]*(BLOCKER|HIGH|OK)[[:space:]]*$' "$file" 2>/dev/null | tail -1 | grep -oE '(BLOCKER|HIGH|OK)' || true)
  if [ -n "$v" ]; then echo "$v"; return; fi
  if grep -qE '^\|\s*\*{0,2}Blocker\b' "$file"; then echo "BLOCKER"; return; fi
  if grep -qE '^\|\s*\*{0,2}High\b'    "$file"; then echo "HIGH"; return; fi
  echo "BLOCKER"
}

# I193（L13）: 最後の VERDICT 行の前に `REVIEWED_COMMIT: <sha>` を 1 行入れる（既存の REVIEWED_COMMIT 行は消す）。
# gate-check.sh が「このレビューが見た HEAD から今の HEAD までにコードの変更が無いか」を確かめるのに使う。
# 最後の VERDICT 行の直前が RISK 行なら、RISK 行のさらに前に入れる（detect_risk_flag は「直後が VERDICT の RISK 行」
# だけを採用するため、RISK と VERDICT を離すと RISK が読めず常に YES になる）。
add_reviewed_commit() {
  local file="$1" sha="$2" tmp
  tmp=$(mktemp)
  awk -v sha="$sha" '
    NR == FNR {
      if ($0 ~ /^REVIEWED_COMMIT:/) next
      n++; line[n] = $0
      if ($0 ~ /^VERDICT:/) last = n
      next
    }
    END {
      at = last
      if (at > 1 && line[at - 1] ~ /^RISK:/) at = at - 1
      for (i = 1; i <= n; i++) {
        if (i == at) print "REVIEWED_COMMIT: " sha
        print line[i]
      }
      if (last == 0) print "REVIEWED_COMMIT: " sha
    }
  ' "$file" /dev/null > "$tmp"
  mv "$tmp" "$file"
}

# I193（S5 の反省）: 組み込みレビューの出力が「対象を読めた結果」に見えるか（exit 0＝読めたとみなす）。
# 読めたとみなすのは、指摘の配列（"file": を持つ JSON）・空の配列だけの行・「指摘なし」に当たる文のどれかがあるときだけ。
# ファイル名が出てくるだけ・行頭が [ なだけ（Markdown のリンクなど）では読めたとみなさない（I193 の組み込みレビューの指摘）。
official_output_readable() {
  local out="$1"
  printf '%s\n' "$out" | grep -qE '"file"[[:space:]]*:' && return 0
  printf '%s\n' "$out" | grep -qE '^[[:space:]]*\[[[:space:]]*\][[:space:]]*$' && return 0
  printf '%s\n' "$out" | grep -qE '指摘(は)?(なし|ありません|見つかりません)|[Nn]o (findings|issues|bugs)( were)? (found|reported)|[Nn]o (findings|issues|bugs)\.?$' && return 0
  return 1
}

# I193: 組み込みのレビュー（/code-review・/security-review）を読み取り専用（plan モード）・時間上限つきで実行する。
# plan モードにするのは、claude -p にはプロジェクトの settings の許可（git push・rm など）がそのまま効くため
# （差分の中の文章に誘導された書き込み・push を仕組みで止める）。失敗・時間切れは本文に書いて返す（呼び出し元は止めない）。
run_official_review() {   # $1=プロンプト（例: /code-review medium origin/develop...HEAD）
  local prompt="$1" out rc=0
  out=$(timeout "${OFFICIAL_REVIEW_TIMEOUT:-900}" claude -p --permission-mode plan "$prompt" 2>&1 < /dev/null) || rc=$?
  if [ "$rc" -ne 0 ]; then
    printf '(実行できず: exit=%s。124 は時間切れ)\n' "$rc"
    return 0
  fi
  if ! official_output_readable "$out"; then
    printf '(注意: 出力に指摘の配列も「指摘なし」も無く、対象を読めていない可能性がある。この出力は判定の根拠にしない)\n'
  fi
  printf '%s\n' "$out" | neutralize_machine_lines
}

# I193: 機械が読む行（VERDICT: など）を行頭から外す。組み込みのレビューの出力を記録に貼るとき、
# その中の行（差分の中の文章を引用したものを含む）が判定の行として読まれないようにする。
neutralize_machine_lines() {
  sed -E 's/^([[:space:]]*)(VERDICT|RISK|REVIEWED_COMMIT|STAGE_DONE|NEW_CRITICAL|NEW_HIGH|ROUNDS|FIX_GATE|FINAL_VERDICT|ADVERSARIAL_STAGE|CI_WAIT):/\1> \2:/'
}

# I193: CI 待ち。CI_WAIT_TIMEOUT 秒（既定 600）まで CI_POLL_INTERVAL 秒（既定 15）ごとに
# `gh pr checks --json bucket` を見る（bucket は pass / fail / pending / skipping / cancel）。
# - チェックが 1 つも無い（push 直後で CI が始まっていない）・gh が失敗した → まだ終わっていないとみなして待つ
# - fail か cancel が 1 つでもある → 失敗
# - pending が 1 つでもある → 待つ
# - 全部 pass か skipping → 成功
# 戻り値: 0=成功（CI_WAIT: OK）/ 1=失敗あり（CI_WAIT: FAIL）/ 3=時間切れ（CI_WAIT: TIMEOUT）
wait_ci() {
  local pr="$1" timeout_s="${CI_WAIT_TIMEOUT:-600}" interval="${CI_POLL_INTERVAL:-15}" elapsed=0 buckets=""
  while [ "$elapsed" -lt "$timeout_s" ]; do
    buckets=$(gh pr checks "$pr" --json bucket --jq '.[].bucket' 2>/dev/null || true)
    if printf '%s\n' "$buckets" | grep -qxE 'fail|cancel'; then
      gh pr checks "$pr" 2>&1 || true
      echo "CI_WAIT: FAIL"
      return 1
    fi
    if [ -n "$buckets" ] && ! printf '%s\n' "$buckets" | grep -qx 'pending'; then
      echo "CI_WAIT: OK"
      return 0
    fi
    echo "  pending... ${elapsed}s / ${timeout_s}s"
    sleep "$interval"
    elapsed=$((elapsed + interval))
  done
  echo "CI_WAIT: TIMEOUT"
  return 3
}

# I086: 高リスク判定の機械可読解析。
# RISK 行は VERDICT 行の直前（隣接行）に出力される正規仕様（code-reviewer.md）。
# 本文中の引用（fenced block・テーブル・fixture 等）に紛れた `RISK: NO` を拾って
# fail-open するのを防ぐため、「直後の行が VERDICT 行である RISK 行」のみを候補とし、
# その最後（＝最終 VERDICT 直前）を採用する。候補が無ければ YES（fail-closed）。
# （I086 敵対レビュー H2 対応: 本文全体 grep + tail -1 は引用注入で破れる）
detect_risk_flag() {
  local file="$1" v
  v=$(awk '
    /^RISK:[[:space:]]*YES[[:space:]]*$/ { pend="YES"; next }
    /^RISK:[[:space:]]*NO[[:space:]]*$/  { pend="NO";  next }
    /^VERDICT:/ { if (pend != "") last=pend; pend=""; next }
    { pend="" }
    END { if (last != "") print last }
  ' "$file" 2>/dev/null)
  if [ -n "$v" ]; then echo "$v"; return; fi
  echo "YES"
}

# I086→I181: パス決定論トリガ。「GitHub から復旧できない例外」（docs/runbooks/danger-ops.md
# 「GitHub から復旧できる範囲（I182）」）に関わるファイルの変更だけを強制 YES にする。
# それ以外の手元のハーネス（スキル・スクリプト・レビュー指示・中核文書・テスト）は GitHub が最後の守り
# （docs/runbooks/review-rules.md）なので対象外。LLM 側（code-reviewer.md・plan-reviewer.md）も同じ集合。
# case glob の * は / にも一致するため .github/* はワークフロー・CODEOWNERS を含む配下すべてに一致する。
path_risk_trigger() {
  local files="$1" f
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in
      .github/*|.pre-commit-config.yaml|.secrets.baseline|scripts/claude/hooks/pretooluse_guard.py|.claude/settings.json|.claude/settings.local.json) echo YES; return;;
    esac
  done <<< "$files"
  echo NO
}

# I086: 高リスク判定の合成（LLM RISK OR パス決定論）と敵対ステージ要否の決定を関数化する。
# 本体フローに直書きすると配線（OR・分岐）を壊してもテストが文字列存在のみで素通りする
# false-green になるため、挙動を関数として固定しユニットテストで検証する（敵対レビュー H5 対応）。
combine_risk() {   # $1=RISK_LLM $2=RISK_PATH → YES/NO
  if [ "$1" = "YES" ] || [ "$2" = "YES" ]; then echo YES; else echo NO; fi
}
adversarial_stage_decision() {   # $1=RISK_FINAL → REQUIRED/NOT_REQUIRED
  if [ "$1" = "YES" ]; then echo REQUIRED; else echo NOT_REQUIRED; fi
}
# I086 敵対レビュー H6 対応: SKILL が解析する機械可読行の emit を関数に集約する。
# 本体直書きだと RISK 行と ADVERSARIAL_STAGE 行が別変数を参照する誤配線をしても
# 前方一致 grep が素通りする（false-green）。引数 $2（risk_final）が両行を一貫して
# 決める構造に固定し、入出力対応をユニットテストで担保する。副作用なしの純関数。
emit_decision_lines() {   # $1=review_file $2=risk_final $3=final_verdict
  echo "REVIEW_FILE: $1"
  echo "RISK: $2"
  echo "FINAL_VERDICT: $3"
  echo "ADVERSARIAL_STAGE: $(adversarial_stage_decision "$2")"
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

# ゲートコマンドを ALLOW（副作用なし・実走）/ HEAVY（test-gate 委譲・実走しない）/
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
  # パストラバーサル拒否: case glob の `*` は `/` にもマッチするため、allowlist の
  # `bash scripts/claude/tests/*.sh` 経由で `.../../evil.sh` を実走させない（安全境界）。
  case "$cmd" in *'../'*) echo UNSAFE; return;; esac
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
# 不在検証 `! grep …` は特別扱い: 生 `!` はエラー(exit≥2・ファイル不在等)まで 0 に反転し
# false-PASS になるため、内側コマンドの exit を見て「一致なし(1)＝pass / それ以外＝fail-closed」に正す。
run_one_gate() {
  local cmd="$1" rc
  case "$cmd" in
    '! grep '*)
      timeout "${GATE_TIMEOUT:-120}" bash -c "${cmd#! }" >/dev/null 2>&1; rc=$?
      [ "$rc" -eq 1 ] && return 0 || return 1 ;;   # grep 一致なし(1)のみ pass・エラー(≥2)は fail
  esac
  timeout "${GATE_TIMEOUT:-120}" bash -c "$cmd" >/dev/null 2>&1
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
        GATE_EVIDENCE+="- \`${cmd}\` → ⏭ test-gate に委譲（heavy・code-review では実走しない）"$'\n' ;;
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
REVIEWER_AGENT="code-reviewer"   # 定義: .claude/agents/code-reviewer.md（tools: Read, Grep, Glob）

# I193: 比べる相手（origin/develop）を最新にする（古い develop と比べて無関係の差分を見ないため）
if ! git fetch -q origin develop; then
  echo "⛔ git fetch origin develop に失敗しました。比べる相手が古いままなので止めます。"
  exit 1
fi

ISSUE_FILE=$(find_file "issues" "${ISSUE}.md")
PLAN_FILE=$(find_plan_file "$ISSUE")

[ -z "$ISSUE_FILE" ] && { echo "⚠️ イシューファイルが見つかりません"; exit 1; }

# このレビューが見る HEAD（記録の REVIEWED_COMMIT になる）
REVIEWED_HEAD=$(git rev-parse HEAD)

# git 情報取得（最大 100KB、|| true で SIGPIPE による pipefail を抑制）
GIT_DIFF=$(git diff origin/develop...HEAD | head -c 102400 || true)
GIT_LOG=$(git log origin/develop...HEAD --oneline)
# I086 敵対レビュー H3 対応: core.quotePath=false で取得する。git 既定（true）は非 ASCII を含む
# パスを "..."（八進エスケープ）で丸ごとクォートし、path_risk_trigger の先頭リテラル glob が
# 不一致になって監視パスを NO に落とす（日本語ファイル名で安全網が fail-open する）ため。
# I181: --no-renames で名前変更を「元の場所の削除＋新しい場所の追加」として両方出す（既定は新しい名前だけで、
# 監視しているファイルを外へ移す変更が path_risk_trigger をすり抜けるため）。
GIT_FILES=$(git -c core.quotePath=false diff origin/develop...HEAD --name-only --no-renames)

# I193: 組み込みのレビュー（公式）を背景で同時に走らせ、CI 待ちと重ねる（互いに依存しないため）。
# パス判定（決定論）が YES のときは組み込みの /security-review も走らせる。結果は自作のレビュー役に渡す。
RISK_PATH=$(path_risk_trigger "$GIT_FILES")
OFFICIAL_DIR=$(mktemp -d)
OFFICIAL_PIDS=()
cleanup_official() {
  local p
  for p in "${OFFICIAL_PIDS[@]}"; do kill "$p" 2>/dev/null || true; done
  rm -rf "$OFFICIAL_DIR"
}
trap cleanup_official EXIT
echo "組み込みの /code-review を背景で実行しています..."
run_official_review "/code-review medium origin/develop...HEAD" > "$OFFICIAL_DIR/code" &
OFFICIAL_PIDS+=("$!")
if [ "$RISK_PATH" = "YES" ]; then
  # /security-review は「origin の既定のブランチ」との差分を見る。手元の origin/HEAD が develop でなければ記録に残す
  if [ "$(git symbolic-ref -q refs/remotes/origin/HEAD || true)" != "refs/remotes/origin/develop" ]; then
    echo "(注意: 手元の origin/HEAD が origin/develop を指していないため、/security-review が develop 以外と比べた可能性がある)" > "$OFFICIAL_DIR/security_note"
  fi
  echo "組み込みの /security-review を背景で実行しています..."
  run_official_review "/security-review" > "$OFFICIAL_DIR/security" &
  OFFICIAL_PIDS+=("$!")
fi

# CI 待機（I193: 時間切れは exit 3・失敗は exit 1。打ち切った後に先へ進まない）
PR_NUM=$(gh pr view --json number -q .number 2>/dev/null || echo "")
if [ -n "$PR_NUM" ]; then
  echo "CI を確認しています (PR #${PR_NUM})..."
  CI_RC=0
  wait_ci "$PR_NUM" || CI_RC=$?
  if [ "$CI_RC" -eq 3 ]; then
    echo "⛔ CI が ${CI_WAIT_TIMEOUT:-600} 秒で終わりませんでした。"
    exit 3
  fi
  if [ "$CI_RC" -ne 0 ]; then
    echo "⛔ CI が失敗しています。"
    exit 1
  fi
fi

# I084: auto_test.md の決定論ゲートをスクリプト自身で実走し、実 exit code を証跡化する。
# 直呼び（$() 不可）で GATE_EVIDENCE / GATE_VERDICT をグローバル設定する（W1）。
AUTO_TEST_FILE=$(find_file "tests" "${ISSUE}_auto_test.md")
GATE_VERDICT=OK; OMISSION_VERDICT=OK; GATE_EVIDENCE="(決定論ゲート宣言なし)"
if [ -n "$AUTO_TEST_FILE" ]; then
  run_declared_gates "$AUTO_TEST_FILE"
  OMISSION_VERDICT=$(omission_lint "$AUTO_TEST_FILE")
fi

# 組み込みのレビューの終わりを待って結果を受け取る（それぞれ OFFICIAL_REVIEW_TIMEOUT で止まる）
wait "${OFFICIAL_PIDS[@]}" 2>/dev/null || true
OFFICIAL_PIDS=()
OFFICIAL_CODE=$(cat "$OFFICIAL_DIR/code" 2>/dev/null || echo "(実行できず: 結果のファイルが無い)")
OFFICIAL_SECURITY="(実行していない: パス判定 NO)"
if [ "$RISK_PATH" = "YES" ]; then
  OFFICIAL_SECURITY="$(cat "$OFFICIAL_DIR/security_note" 2>/dev/null || true)
$(cat "$OFFICIAL_DIR/security" 2>/dev/null || echo "(実行できず: 結果のファイルが無い)")"
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
\`\`\`

### 組み込み /code-review の指摘（公式・plan モード。file・line・summary・failure_scenario）
${OFFICIAL_CODE}

### 組み込み /security-review の指摘（公式・plan モード。パス判定 YES のときだけ実行）
${OFFICIAL_SECURITY}"

# claude -p でレビュー実行（I193: 公式のサブエージェント定義を --agent で呼ぶ。読み取り専用は定義の tools で効かせる）
# 時間上限 REVIEW_TIMEOUT（既定 900 秒）。時間切れ・失敗・空は、その旨の記録を残して BLOCKER にする（fail-closed）
REVIEW_RC=0
REVIEW=$(printf '%s' "$CONTEXT" | timeout "${REVIEW_TIMEOUT:-900}" claude -p --agent "$REVIEWER_AGENT" --tools "Read,Grep,Glob") || REVIEW_RC=$?
if [ "$REVIEW_RC" -ne 0 ] || [ -z "$REVIEW" ]; then
  echo "⚠️ レビュー役が終わりませんでした（claude -p exit=${REVIEW_RC}。124 は時間切れ）。BLOCKER として記録します。"
  REVIEW="# コードレビュー [${ISSUE}]（未完了）

レビュー役の claude -p が正常に終わらなかった（exit=${REVIEW_RC}。124 は時間切れ・0 は空の出力）。判定できないため BLOCKER とする。

RISK: YES
VERDICT: BLOCKER"
fi

# 出力正規化
REVIEW_CLEAN=$(printf '%s\n' "$REVIEW" | sed 's/[[:space:]]*$//')

# ファイル保存（組み込みのレビューの出力も記録に残す）
mkdir -p "$(dirname "$REVIEW_FILE")"
{
  printf '%s\n' "$REVIEW_CLEAN"
  printf '\n## 組み込みのレビューの出力（公式・参考）\n\n### 組み込み /code-review の指摘\n\n%s\n\n### 組み込み /security-review の指摘\n\n%s\n' \
    "$OFFICIAL_CODE" "$OFFICIAL_SECURITY"
} > "$REVIEW_FILE"

# I086: 高リスク判定（LLM RISK 行 OR パス決定論トリガ）。証跡は注入セクションに残す。
RISK_LLM=$(detect_risk_flag "$REVIEW_FILE")
RISK_FINAL=$(combine_risk "$RISK_LLM" "$RISK_PATH")
GATE_EVIDENCE+="- 高リスク判定: ${RISK_FINAL}（LLM=${RISK_LLM} / path=${RISK_PATH}）"$'\n'

# I084: 決定論ゲート結果で VERDICT を決定論的に上書きする（LLM 出力非依存）。
# FINAL = max(gate, omission, LLM)。証跡を記録先頭へ注入し末尾 VERDICT 行を FINAL に書換え。
LLM_VERDICT=$(detect_code_verdict "$REVIEW_FILE")
FINAL_VERDICT=$(combine_verdict "$GATE_VERDICT" "$OMISSION_VERDICT" "$LLM_VERDICT")
inject_gate_result "$REVIEW_FILE" "$GATE_EVIDENCE" "$OMISSION_VERDICT" "$FINAL_VERDICT"
# I193（L13）: このレビューが見た HEAD を記録する（gate-check.sh が読む）
add_reviewed_commit "$REVIEW_FILE" "$REVIEWED_HEAD"

# 案A(I069): 生産物（レビュー記録）を生産者がコミットする（feature ブランチ時のみ・path-scoped）。
commit_review_artifact "$REVIEW_FILE" "$ISSUE" "code-review"

# PR コメント投稿
if [ -n "$PR_NUM" ]; then
  gh pr review "$PR_NUM" --comment --body "$(cat "$REVIEW_FILE")" \
    || echo "⚠️ PR コメント投稿失敗。手動で実行: gh pr review $PR_NUM --comment --body \"\$(cat $REVIEW_FILE)\""
fi

# I086: SKILL（オーケストレーション層）が解析する機械可読行（emit を関数に集約・H6 対応）
emit_decision_lines "$REVIEW_FILE" "$RISK_FINAL" "$FINAL_VERDICT"

echo "REVIEWED_COMMIT: ${REVIEWED_HEAD}"

# 判定の要約（次の段階は review-gate スキルが FINAL_VERDICT・ADVERSARIAL_STAGE の行で決める。I193）
case "$(detect_code_verdict "$REVIEW_FILE")" in
  BLOCKER) printf '\n⛔ Blocker が残っています（修正へ）。\n' ;;
  HIGH)    printf '\n❌ レビュー NG（修正へ）。\n' ;;
  *)
    if [ "$RISK_FINAL" = "YES" ]; then
      printf '\n⚠️ 高リスク判定 YES（敵対的レビューへ）。\n'
    else
      printf '\n✅ コードレビュー完了（テストへ）。\n'
    fi ;;
esac
