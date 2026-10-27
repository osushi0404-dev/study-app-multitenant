#!/usr/bin/env bash
set -euo pipefail

# ---- helper functions (テストは REVIEW_LIB_SOURCE_ONLY=1 で source して利用) ----

# I197: レビュー役が正常に終わらなかったときの記録（BLOCKER）。最後のツール呼び出し・その結果・経過を残す。
# claude_log_last_tool は review-process-lib.sh の関数（本体と、この関数を使う呼び出し元が読み込む）
reviewer_failure_record() {   # $1=イシュー $2=claude の終了コード $3=ログ
  local issue="$1" rc="$2" log="$3" last name inp res secs
  last=$(claude_log_last_tool "$log" 2>/dev/null || true)
  IFS=$'\t' read -r name inp res secs <<< "${last:-(読めない)}"
  cat <<EOF
# コードレビュー [${issue}]（未完了）

レビュー役の claude -p が正常に終わらなかった（exit=${rc}。124 は時間切れ・0 は空の出力）。判定できないため BLOCKER とする。

- 最後のツール呼び出し: ${name:-(なし)} ${inp:-}
- その結果（先頭）: ${res:-(なし)}
- 最後の出来事から止まるまで: ${secs:-?} 秒

RISK: YES
VERDICT: BLOCKER
EOF
}

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
  # here-string で渡す（printf | grep -q だと、大きな出力で grep が先に終わり、pipefail の下で 141 になって誤判定する。I193 L1）
  grep -qE '"file"[[:space:]]*:' <<< "$out" && return 0
  grep -qE '^[[:space:]]*\[[[:space:]]*\][[:space:]]*$' <<< "$out" && return 0
  grep -qE '指摘(は)?(なし|ありません|見つかりません)|(脆弱性|問題|指摘)[^。]*見つかりませんでした|[Nn]o (findings|issues|bugs|vulnerabilities)( were)? (found|reported)|[Nn]o (findings|issues|bugs)\.?$' <<< "$out" && return 0
  return 1
}

# I193: claude が先頭に出す手元の設定の警告（「Permission allow rule (…) is not matched …」）を除く。
# レビューの中身ではないので、記録にも「読めたか」の判定にも混ぜない
drop_cli_warnings() {
  grep -vE '^Permission allow rule \(' || true
}

# I193: 「記録の場所」（レビューの後に変えてもレビューを通り直さなくてよい場所）。gate-check.sh もこの関数を使う。
# docs/{issues,reviews,tests,plans}/ の下のうち templates/ 以外（テンプレートは次のイシューの決まりなので含めない）
is_record_path() {   # $1=パス → 記録の場所なら exit 0
  case "$1" in
    docs/issues/templates/*|docs/reviews/templates/*|docs/tests/templates/*|docs/plans/templates/*) return 1 ;;
    docs/issues/*|docs/reviews/*|docs/tests/*|docs/plans/*) return 0 ;;
  esac
  return 1
}

# I193: 2 つのコミットの間で、記録の場所の外のファイルが変わったか（変わったファイル名を出して exit 1）
changed_outside_records() {   # $1=from $2=to
  local f out=""
  while IFS= read -r -d '' f; do
    is_record_path "$f" || out+="${f}"$'\n'
  done < <(git -c core.quotePath=false diff -z --name-only --no-renames "$1" "$2")
  if [ -n "$out" ]; then printf '%s' "$out"; return 1; fi
  return 0
}

# I193 4 回目 H1: 今のブランチの開いている PR の番号を出す。戻り値: 0=見つかった / 1=gh の失敗 / 2=開いている PR が無い。
# 「PR を取れない」と「PR が無い」を区別し、どちらも呼び出し元が止める（CI 待ちを飛ばさない）
find_pr_num() {
  local branch num
  branch=$(git rev-parse --abbrev-ref HEAD) || return 1
  num=$(gh pr list --head "$branch" --state open --json number --jq '.[0].number // empty' 2>/dev/null) || return 1
  [ -n "$num" ] || return 2
  printf '%s\n' "$num"
}

# I193: 指定した PID と、その子孫のプロセスをすべて止める（背景の組み込みレビューの timeout・claude まで届かせる）。
# ps --ppid は Linux（procps）のもの。このリポジトリの実行環境（WSL・CI の ubuntu）は Linux だけ
kill_tree() {
  local pid="$1" child
  for child in $(ps -o pid= --ppid "$pid" 2>/dev/null); do kill_tree "$child"; done
  kill "$pid" 2>/dev/null || true
}

# I193: 組み込みのレビュー（/code-review・/security-review）を読み取り専用（plan モード）・時間上限つきで実行する。
# plan モードにするのは、claude -p にはプロジェクトの settings の許可（git push・rm など）がそのまま効くため
# （差分の中の文章に誘導された書き込み・push を仕組みで止める）。失敗・時間切れは本文に書いて返す（呼び出し元は止めない）。
run_official_review() {   # $1=プロンプト（例: /code-review medium origin/develop...HEAD）
  local prompt="$1" out rc=0
  # I197: 承認が要る操作は待たずに拒否する（--permission-prompts none。黙って止まる経路を作らない）
  out=$(timeout "${OFFICIAL_REVIEW_TIMEOUT:-900}" claude -p --permission-mode plan --permission-prompts none "$prompt" 2>&1 < /dev/null) || rc=$?
  if [ "$rc" -ne 0 ]; then
    printf '(実行できず: exit=%s。124 は時間切れ)\n' "$rc"
    return 0
  fi
  out=$(printf '%s\n' "$out" | drop_cli_warnings)
  if ! official_output_readable "$out"; then
    printf '(注意: 出力に指摘の配列も「指摘なし」も無く、対象を読めていない可能性がある。この出力は判定の根拠にしない)\n'
  fi
  printf '%s\n' "$out" | neutralize_machine_lines
}

# I193: 機械が読む行（VERDICT: など）を行頭から外す。組み込みのレビューの出力を記録に貼るとき、
# その中の行（差分の中の文章を引用したものを含む）が判定の行として読まれないようにする。
# I197: 敵対的レビューの記録が読む行（ITEM・EXPERIMENT_BEGIN/END・合計の行）も対象にする
neutralize_machine_lines() {
  sed -E -e 's/^([[:space:]]*)(VERDICT|RISK|REVIEWED_COMMIT|STAGE_DONE|NEW_CRITICAL|NEW_HIGH|NEW_CRITICAL_TOTAL|NEW_HIGH_TOTAL|UNVERIFIED|ROUNDS|ITEM|FINDING|LEDGER|LEDGER_ROUND|FIX_GATE|FINAL_VERDICT|ADVERSARIAL_STAGE|ADVERSARIAL_VERDICT|CI_WAIT|OFFICIAL_SECURITY):/\1> \2:/' \
    -e 's/^([[:space:]]*)(EXPERIMENT_BEGIN|EXPERIMENT_END)([[:space:]]|$)/\1> \2\3/'
}

# I193 7 回目 H2: 高リスク（パス判定 YES）で組み込みの /security-review が動かなかった（実行できず・読めていない）ら HIGH。
# 公式のセキュリティレビューは高リスクのときの多層防御の 1 枚なので、抜けたまま OK にしない（止まる側）
official_security_verdict() {   # $1=RISK_PATH（YES/NO） $2=組み込みの /security-review の出力
  if [ "$1" = "YES" ] && [[ "$2" == *"(実行できず"* || "$2" == *"(注意: 出力に指摘の配列も"* ]]; then
    echo HIGH
  else
    echo OK
  fi
}

# I193: PR で動くワークフローのジョブ名（jobs.<id>.name。無ければ id）を 1 行ずつ出す。
# 対象は CI_WORKFLOWS（空白区切り・既定 .github/workflows/ci.yml .github/workflows/e2e.yml）。読めなければ何も出さない。
expected_ci_jobs() {
  # shellcheck disable=SC2086  # CI_WORKFLOWS は空白区切りの一覧として分ける
  python3 - ${CI_WORKFLOWS:-.github/workflows/ci.yml .github/workflows/e2e.yml} <<'PY' 2>/dev/null || true
import sys, yaml
for path in sys.argv[1:]:
    d = yaml.safe_load(open(path, encoding="utf-8")) or {}
    for jid, job in (d.get("jobs") or {}).items():
        print((job or {}).get("name") or jid)
PY
}

# I193: CI 待ち。CI_WAIT_TIMEOUT 秒（既定 1200。直近の実測は最長 5.5 分）まで CI_POLL_INTERVAL 秒（既定 15）ごとに見る。
# - PR の最新のコミット（headRefOid）が手元の HEAD と違う → 手元のコミットを CI が見ていない（CI_WAIT: NOT_PUSHED・失敗）
# - fail か cancel が 1 つでもある → 失敗
# - PR で動くワークフローのジョブ（expected_ci_jobs）が全部、pass か skipping で出そろったときだけ成功。
#   チェックがまだ無い・一部しか登録されていない（push 直後）・ジョブ名を読めない・gh が失敗した → 待つ（時間切れで止まる）
# 戻り値: 0=成功（CI_WAIT: OK）/ 1=失敗（CI_WAIT: FAIL・NOT_PUSHED）/ 3=時間切れ（CI_WAIT: TIMEOUT）
wait_ci() {
  local pr="$1" timeout_s="${CI_WAIT_TIMEOUT:-1200}" interval="${CI_POLL_INTERVAL:-15}" elapsed=0
  local head pr_head checks expected name state missing
  head=$(git rev-parse HEAD)
  pr_head=$(gh pr view "$pr" --json headRefOid -q .headRefOid 2>/dev/null || true)
  if [ "$pr_head" != "$head" ]; then
    echo "⛔ PR の最新のコミット（${pr_head:-取得できず}）が手元の HEAD（${head}）と違います。push してから実行してください。"
    echo "CI_WAIT: NOT_PUSHED"
    return 1
  fi
  expected=$(expected_ci_jobs)
  if [ -z "$expected" ]; then
    # 握りつぶして待ち続けると、CI が全部緑でも時間切れになるだけなので、理由を出して止める（I193 M5）
    echo "⛔ PR で動くワークフローのジョブ名を読めません（${CI_WORKFLOWS:-.github/workflows/ci.yml .github/workflows/e2e.yml}。python3 と PyYAML が要る）。"
    echo "CI_WAIT: NO_JOBS"
    return 1
  fi
  while [ "$elapsed" -lt "$timeout_s" ]; do
    checks=$(gh pr checks "$pr" --json name,bucket --jq '.[] | "\(.bucket)\t\(.name)"' 2>/dev/null || true)
    if printf '%s\n' "$checks" | grep -qE '^(fail|cancel)	'; then
      gh pr checks "$pr" 2>&1 || true
      echo "CI_WAIT: FAIL"
      return 1
    fi
    missing=""
    while IFS= read -r name; do
      [ -n "$name" ] || continue
      state=$(printf '%s\n' "$checks" | awk -F'\t' -v n="$name" '$2 == n { print $1 }' | head -1)
      case "$state" in pass|skipping) ;; *) missing="${missing} ${name}" ;; esac
    done <<< "$expected"
    if [ -z "$missing" ]; then
      echo "CI_WAIT: OK"
      return 0
    fi
    echo "  待ち${missing:+（未完了:${missing}）}... ${elapsed}s / ${timeout_s}s"
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

# ---- I197 §4.8: 基本レビューの台帳（やり直しは差分と台帳だけを見て、合否は台帳から決定論で出す） ----
# 台帳の行（スクリプトが書く）: `LEDGER: F<n> SEV=… STATUS=<open|resolved> SCOPE=<delta|outside> KIND=<app|harness|guard> STOP=<…> REPRO=<yes|no> SECURITY=<yes|no> | 要約`
# レビュー役の行（code-reviewer が書く・I205）:
#   `FINDING: F<n> SEV=… STATUS=… FILE=<パス|-> LINE=<n|n-m|-> SECURITY=… STOP=<flow|leak|github|ac:<番号>|-> | 要約 | 再現: …`
# SCOPE（行で決める）と KIND（FILE のパスで決める）はレビュー役に書かせず、スクリプトが決める。止めるかは blocking()（I205: 変更の種類ごと）。
# 台帳は最新の記録に累積で全部書く

# LEDGER_ROUND: のある（＝レビュー役が正常に終わった）コードレビュー記録を、ファイル名の時刻順に出す
ledger_records() {   # $1=I###
  local f
  while IFS= read -r f; do
    grep -qE '^LEDGER_ROUND:[[:space:]]*[0-9]+[[:space:]]*$' "$f" && printf '%s\n' "$f"
  done < <(find docs/reviews -maxdepth 2 -type f -name "${1}_code_review_*.md" 2>/dev/null \
             | awk -F/ '{ print $NF "\t" $0 }' | LC_ALL=C sort | cut -f2)
  return 0
}

# 全体か差分か: "full<TAB>1<TAB><TAB>" か "delta<TAB><n><TAB><起点の SHA><TAB><前の記録>"。
# 差分にするのは、台帳のある最新の記録の REVIEWED_COMMIT が今の HEAD の祖先のときだけ（rebase などで祖先でなければ全体）
review_mode() {   # $1=I###
  local last n sha
  last=$(ledger_records "$1" | tail -1)
  if [ -n "$last" ]; then
    n=$(grep -oE '^LEDGER_ROUND:[[:space:]]*[0-9]+[[:space:]]*$' "$last" | tail -1 | grep -oE '[0-9]+' || true)
    sha=$(grep -oE '^REVIEWED_COMMIT:[[:space:]]*[0-9a-f]{7,40}[[:space:]]*$' "$last" | tail -1 | grep -oE '[0-9a-f]{7,40}' || true)
    if [ -n "$n" ] && [ -n "$sha" ] && git merge-base --is-ancestor "$sha" HEAD 2>/dev/null; then
      printf 'delta\t%s\t%s\t%s\n' "$(( n + 1 ))" "$sha" "$last"; return 0
    fi
  fi
  printf 'full\t1\t\t\n'
}

# 差分のレビューの範囲: ブランチ自身が変えたファイル（比べる相手との merge-base から HEAD）のうち、起点から HEAD までに
# 変わったもの（記録の場所を除く）。develop の取り込みで入った develop 側だけの変更は含めない
delta_files() {   # $1=比べる相手 $2=起点の SHA
  local own
  own=$(branch_own_files "$1") || return 2
  LC_ALL=C comm -12 <(printf '%s\n' "$own" | LC_ALL=C sort) \
    <(git -c core.quotePath=false diff --name-only --no-renames "$2" HEAD | LC_ALL=C sort) | grep -v '^$' || true
  return 0
}

# I205: ブランチ自身が変えたファイル（比べる相手との merge-base から HEAD・記録の場所を除く）。delta_files の土台
branch_own_files() {   # $1=比べる相手
  local mb f
  mb=$(git merge-base "$1" HEAD) || return 2
  while IFS= read -r f; do
    [ -n "$f" ] && ! is_record_path "$f" && printf '%s\n' "$f"
  done < <(git -c core.quotePath=false diff --name-only --no-renames "$mb" HEAD)
  return 0
}

# I205: 差分の中かどうかを行で決めるための、行の塊「<パス>\t<始め>\t<終わり>」（HEAD の行番号）。
# 全体のレビュー（起点が空）: ブランチが変えた行（merge-base から HEAD）。
# 差分のレビュー: 起点から HEAD までに変わった行のうち、ブランチが変えた行（develop の取り込みで入った行は入れない）。
# 消しただけの塊は消した位置の 1 行、塊の無い変更（バイナリなど）はファイル全体。
# 読み取りが崩れても見逃し側に倒れないよう（I205 計画 4.11）: git の設定（接頭辞・外部 diff・相対パス）に左右されない
# オプションで取り、対象のファイルのうち diff に出てこなかったものはファイル全体にする。git が失敗したら 2（本体は止める）
delta_hunks() {   # $1=比べる相手 $2=起点の SHA（空なら全体のレビュー）
  local mb files a b l rc
  mb=$(git merge-base "$1" HEAD) || return 2
  if [ -n "$2" ]; then files=$(delta_files "$1" "$2") || return 2; else files=$(branch_own_files "$1") || return 2; fi
  [ -n "$files" ] || return 0
  a=$(mktemp); b=$(mktemp); l=$(mktemp)
  printf '%s\n' "$files" > "$l"
  xargs -d '\n' git -c core.quotePath=false diff -U0 --no-renames --no-color --no-ext-diff --no-textconv --no-relative \
    --src-prefix=a/ --dst-prefix=b/ "$mb" HEAD -- < "$l" > "$a" || { rm -f "$a" "$b" "$l"; return 2; }
  if [ -n "$2" ]; then
    # 起点からの塊と、ブランチ自身の塊（merge-base から）の重なりだけ
    xargs -d '\n' git -c core.quotePath=false diff -U0 --no-renames --no-color --no-ext-diff --no-textconv --no-relative \
      --src-prefix=a/ --dst-prefix=b/ "$2" HEAD -- < "$l" > "$b" || { rm -f "$a" "$b" "$l"; return 2; }
    hunks_from_diff "$l" "$a" "$b"
  else
    hunks_from_diff "$l" "$a"
  fi
  rc=$?; rm -f "$a" "$b" "$l"; return "$rc"
}
# diff（-U0）から行の塊を出す: <対象のファイルの一覧> <diff A> [<diff B>（あれば A と重なる行だけ）]
hunks_from_diff() { python3 -I -c "$_HUNKS_PY" "$@"; }

_HUNKS_PY='
import re, sys
HUNK = re.compile(r"@@ -[0-9]+(?:,[0-9]+)? \+([0-9]+)(?:,([0-9]+))? @@")
WHOLE = [(1, 999999999)]
def hunks(path):
    out, cur, head = {}, None, False
    for line in open(path, encoding="utf-8", errors="replace").read().split("\n"):
        if line.startswith("diff --git "):
            cur = line[len("diff --git "):].rsplit(" b/", 1)[-1]
            out.setdefault(cur, []); head = True
        elif head and line.startswith("+++ "):
            # 見出しとして読むのは diff --git の後、最初の @@ までだけ（追加した行の中身「++ …」と取り違えない）
            if line.startswith("+++ b/"):
                cur = line[len("+++ b/"):]; out.setdefault(cur, [])
        elif cur is not None and line.startswith("@@ "):
            head = False
            m = HUNK.match(line)
            if m:
                c, d = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
                out[cur].append((max(c, 1), max(c, 1)) if d == 0 else (c, c + d - 1))
    # 塊の無い変更（バイナリ・モード）はファイル全体
    return {p: (r or WHOLE) for p, r in out.items()}
expected = [l for l in open(sys.argv[1], encoding="utf-8").read().split("\n") if l]
a = hunks(sys.argv[2])
b = hunks(sys.argv[3]) if len(sys.argv) > 3 else a
# 対象のファイルなのに diff に出てこなかった（読み取りが崩れた）ものは、ファイル全体（止める側）
for p in expected:
    if p not in a or p not in b:
        a[p] = b[p] = WHOLE
if b is a:   # 全体のレビュー: そのまま出す
    for p in sorted(a):
        for s, e in a[p]:
            print(f"{p}\t{s}\t{e}")
    sys.exit(0)
for p in sorted(set(a) & set(b)):
    for s1, e1 in a[p]:
        for s2, e2 in b[p]:
            s, e = max(s1, s2), min(e1, e2)
            if s <= e:
                print(f"{p}\t{s}\t{e}")
'

_LEDGER_PY='
import os, re, sys
FIND = re.compile(r"FINDING: (F[0-9]+) SEV=(Blocker|High|Medium|Low) STATUS=(open|resolved) FILE=(\S+) LINE=(\S+) SECURITY=(yes|no) STOP=(\S+)(?: \| (.*))?")
# 前の形（I197・KIND などの欄なし）の行も読む。足りない欄は止める側の既定値（app・STOP=-・REPRO=yes）
LEDG = re.compile(r"LEDGER: (F[0-9]+) SEV=(Blocker|High|Medium|Low) STATUS=(open|resolved) SCOPE=(delta|outside)(?: KIND=(app|harness|guard) STOP=(\S+) REPRO=(yes|no))? SECURITY=(yes|no)(?: \| (.*))?")
RANK = {"Low": 0, "Medium": 1, "High": 2, "Blocker": 3}
# ハーネスの止める条件の一覧（I205）: ① flow 流れが動かなくなる ② leak 秘密情報・個人情報が外に出る
# ③ github develop・main を直接壊す／GitHub から戻せない設定を壊す ④ ac:<番号> 受け入れ条件の未達
STOP_RE = re.compile(r"flow|leak|github|ac:[0-9]+")
LINE_RE = re.compile(r"([0-9]+)(?:-([0-9]+))?")
REPRO_RE = re.compile(r"(?:^|\s*\|)\s*再現:(.*)$")   # 要約の後ろの「| 再現: …」（中身があれば再現あり）
HUNK_MARGIN = 3   # 塊の前後の行数（git の既定の前後の行数と同じ）
# 変更の種類（I205）。guard は path_risk_trigger() と同じ集合（テスト R-K2 で一致を固定）。どれでもないものは app（厳しい側）
GUARD_PREFIX = (".github/",)
GUARD_FILES = {".pre-commit-config.yaml", ".secrets.baseline", "scripts/claude/hooks/pretooluse_guard.py",
               ".claude/settings.json", ".claude/settings.local.json"}
HARNESS_PREFIX = (".claude/", "scripts/claude/", "docs/", "rules/")
HARNESS_FILES = {"CLAUDE.md", ".mcp.json", ".worktreeinclude"}

def norm_path(path):
    # 表記の形を列挙せず、:行番号 を除いてリポジトリのルート（cwd）からの相対パスに揃える
    return os.path.relpath(os.path.normpath(os.path.abspath(path.split(":", 1)[0])))

def kind_of(path):
    if path in GUARD_FILES or path.startswith(GUARD_PREFIX):
        return "guard"
    if path in HARNESS_FILES or path.startswith(HARNESS_PREFIX):
        return "harness"
    return "app"

def branch_kind(paths):
    # FILE=- の指摘の種類: ブランチが変えたファイルに guard があれば guard、無くて app があれば app、どちらも無ければ harness
    ks = set(kind_of(p) for p in paths)
    return "guard" if "guard" in ks else "app" if ("app" in ks or not paths) else "harness"

def read_lines(path):
    return [l for l in open(path, encoding="utf-8", errors="replace").read().split("\n") if l] if path else []

def read_findings(path):
    out = []
    for line in open(path, encoding="utf-8", errors="replace").read().split("\n"):
        if not line.startswith("FINDING:"):
            continue
        m = FIND.fullmatch(line.rstrip())
        if not m:
            print("形の崩れた FINDING 行: " + line[:120], file=sys.stderr)
            sys.exit(2)
        out.append(m.groups())
    return out

def read_ledger(path):
    led = {}
    if path:
        for line in open(path, encoding="utf-8", errors="replace").read().split("\n"):
            m = LEDG.fullmatch(line.rstrip())
            if m:
                fid, sev, st, scope, kind, stop, repro, sec, title = m.groups()
                led[fid] = [sev, st, scope, kind or "app", stop or "-", repro or "yes", sec, title or ""]
    return led

def ledger_line(fid, e):
    sev, st, scope, kind, stop, repro, sec, title = e
    return f"LEDGER: {fid} SEV={sev} STATUS={st} SCOPE={scope} KIND={kind} STOP={stop} REPRO={repro} SECURITY={sec}" + (f" | {title}" if title else "")

def blocking(e):
    sev, st, scope, kind, stop, repro, sec = e[:7]
    if st != "open":
        return False
    sec_blocker = sev == "Blocker" and sec == "yes"
    if kind == "guard":           # GitHub から復旧できない例外: I197 のまま（再現は問わない）
        return RANK[sev] >= 2 and (scope == "delta" or sec_blocker)
    if repro != "yes":            # 再現の無い指摘は止めない（アプリ本体・ハーネス共通）
        return False
    if sec_blocker:               # 差分の外でもセキュリティの Blocker は止める（共通）
        return True
    if scope != "delta":
        return False
    if kind == "app":             # アプリ本体: Blocker・High・Medium。受け入れ条件の未達（ac:<番号>）は重大度に関係なく止める
        return RANK[sev] >= 1 or stop.startswith("ac:")
    return bool(STOP_RE.fullmatch(stop))   # それ以外のハーネス: 止める条件の一覧に当たるものだけ（重大度は見ない）

mode = sys.argv[1]
if mode == "parse":
    for g in read_findings(sys.argv[2]):
        print("\t".join(x or "" for x in g))
elif mode == "kinds":
    # kinds <パスの一覧>: 「種類\tパス」を出す（レビュー役の入力の「変更の種類」の節）
    for p in read_lines(sys.argv[2]):
        print(f"{kind_of(p)}\t{p}")
elif mode == "update":
    # update <full|delta> <前の記録|""> <今回のレビュー> <行の塊の一覧（delta_hunks）> [<ブランチが変えたファイルの一覧>]
    review_kind, prev, cur, hunk_file = sys.argv[2:6]
    branch_files = read_lines(sys.argv[6]) if len(sys.argv) > 6 else []
    led = read_ledger(prev) if review_kind == "delta" else {}
    shown = set(k for k, e in led.items() if blocking(e))   # 差分のレビューの入力に見せた（止める）指摘
    hunks = {}
    for l in read_lines(hunk_file):
        p, s, e = l.split("\t")
        hunks.setdefault(p.casefold(), []).append((int(s), int(e)))
    next_id = max([int(k[1:]) for k in led] or [0]) + 1
    def scope_of(path, line, stop):
        # delta（止める側）: 受け入れ条件の未達・FILE=-・行が読めない・リポジトリの外・実在しないファイル・塊と重なる行。
        # outside にするのは「リポジトリの中の実在のファイルで、どの塊（前後 HUNK_MARGIN 行）とも重ならない行」だけ
        if stop.startswith("ac:") or path == "-":
            return "delta"
        m = LINE_RE.fullmatch(line)
        if not m:
            return "delta"
        norm = norm_path(path)
        if norm.startswith("..") or not os.path.isfile(norm):
            return "delta"
        a = int(m.group(1)); b = int(m.group(2) or a)
        a, b = min(a, b), max(a, b)
        # 大文字・小文字を区別しないファイルシステムでの表記違いも同じファイルとして比べる（I202 F16）
        for s, e in hunks.get(norm.casefold(), []):
            if a <= e + HUNK_MARGIN and b >= s - HUNK_MARGIN:
                return "delta"
        return "outside"
    for fid, sev, st, path, line, sec, stop, rest in read_findings(cur):
        rest = rest or ""
        stop = stop if STOP_RE.fullmatch(stop) else "-"
        m = REPRO_RE.search(rest)
        repro = "yes" if m and m.group(1).strip() else "no"
        title = (rest[:m.start()] if m else rest).strip()
        if fid in led and fid not in shown:
            # 入力に見せていない既存の番号（止めない指摘・直った指摘）を使った行は、新しい指摘として振り直す
            fid = f"F{next_id}"
            next_id += 1
        if fid in led:
            o = led[fid]
            # 既にある指摘: SCOPE・KIND は前のまま（今回の範囲で決め直すと、触っていない行の未解決の指摘が消える）。
            # 止める側の値は残す（重大度は下げない・SECURITY・REPRO は yes が残る・一覧に当たる STOP は残る）
            led[fid] = [sev if RANK[sev] > RANK[o[0]] else o[0], st, o[2], o[3],
                        o[4] if STOP_RE.fullmatch(o[4]) else stop, "yes" if "yes" in (repro, o[5]) else "no",
                        "yes" if "yes" in (sec, o[6]) else "no", title or o[7]]
        else:
            k = branch_kind(branch_files) if path == "-" else kind_of(norm_path(path))
            led[fid] = [sev, st, scope_of(path, line, stop), k, stop, repro, sec, title]
            next_id = max(next_id, int(fid[1:]) + 1)
    for fid in sorted(led, key=lambda x: int(x[1:])):
        print(ledger_line(fid, led[fid]))
elif mode == "blocking":
    # 止める指摘の LEDGER 行だけを出す（差分のレビューの入力・記録の「止める指摘」の節。合否と同じ blocking() で選ぶ）
    led = read_ledger(sys.argv[2])
    for fid in sorted(led, key=lambda x: int(x[1:])):
        if blocking(led[fid]):
            print(ledger_line(fid, led[fid]))
elif mode == "verdict":
    stops = [e for e in read_ledger(sys.argv[2]).values() if blocking(e)]
    print("BLOCKER" if any(e[0] == "Blocker" for e in stops) else "HIGH" if stops else "OK")
'
# FINDING 行を「id\tSEV\tSTATUS\tFILE\tLINE\tSECURITY\tSTOP\t要約（と再現）」で出す。形の崩れた FINDING 行があれば 2
parse_findings() { python3 -I -c "$_LEDGER_PY" parse "$1"; }
# パスの一覧（ファイル）の各行を「種類\tパス」で出す（I205: app / harness / guard）
ledger_kinds() { python3 -I -c "$_LEDGER_PY" kinds "$1"; }
# 累積の台帳（LEDGER 行）を出す: <full|delta> <前の記録|""> <今回のレビュー> <行の塊の一覧> [<ブランチが変えたファイルの一覧>]。
# 形の崩れた FINDING 行があれば 2
ledger_update() { python3 -I -c "$_LEDGER_PY" update "$@"; }
# 台帳の合否: 止める指摘（blocking()・変更の種類ごと）に Blocker があれば BLOCKER、ほかの止める指摘があれば HIGH、無ければ OK
ledger_verdict() { python3 -I -c "$_LEDGER_PY" verdict "$1"; }
# 止める指摘（合否と同じ規則）の LEDGER 行だけを出す
ledger_blocking() { python3 -I -c "$_LEDGER_PY" blocking "$1"; }

# 高リスクの判定（計画の段階で決める・周ごとに変えない）: 最新の計画レビュー記録の「## 高リスク判定」の `判定: Yes|No`。
# 読めない・記録が無いときは YES（止まる側）
plan_risk() {   # $1=I###
  local f v
  # set -euo pipefail の下でも、見つからないときに止まらず空になるよう || true を付ける
  f=$(find docs/reviews -maxdepth 2 -type f -name "${1}_plan_review_*.md" 2>/dev/null | awk -F/ '{ print $NF "\t" $0 }' | LC_ALL=C sort | tail -1 | cut -f2 || true)
  [ -n "$f" ] || { echo YES; return; }
  # 読み方は plan-issue-review.sh の detect_plan_verdict の保険と同じ（大文字・小文字を区別しない・行末まで Yes か No だけ）
  v=$(awk '/^## 高リスク判定/ { s=1; next } s && /^## / { s=0 } s && /^判定:/ { print toupper($0); exit }' "$f" \
        | grep -oE '^判定:[[:space:]]*(YES|NO)[[:space:]]*$' | grep -oE '(YES|NO)' || true)
  if [ "$v" = "NO" ]; then echo NO; else echo YES; fi
}

# 記録の RISK 行を 1 行にして、最後の VERDICT 行の直前に置く（code-reviewer の RISK 行は使わず、スクリプトの判定で書き直す）
set_risk_line() {   # $1=ファイル $2=YES|NO
  local tmp; tmp=$(mktemp)
  awk -v r="$2" '
    NR == FNR { if ($0 ~ /^RISK:/) next; n++; line[n] = $0; if ($0 ~ /^VERDICT:/) last = n; next }
    END { for (i = 1; i <= n; i++) { if (i == last) print "RISK: " r; print line[i] } if (last == 0) print "RISK: " r }
  ' "$1" /dev/null > "$tmp"
  mv "$tmp" "$1"
}

# テストから関数のみを source するためのガード（本体は実行しない）
if [ "${REVIEW_LIB_SOURCE_ONLY:-}" = "1" ]; then return 0; fi

# I197: 別プロセスのレビュー役を「時間上限つき・承認なし・途中の出力を残す」で起動し、記録を読む関数
# （関数だけを読み込む使い方〔gate-check・テストの写し〕には要らないので、本体でだけ読む）
# shellcheck source=scripts/claude/review-process-lib.sh disable=SC1091  # -x なしの単体の検査（TC-C1）でもたどらない。ライブラリは別に検査される
. "$(dirname "${BASH_SOURCE[0]}")/review-process-lib.sh"

ISSUE="${1:?Usage: $0 I###}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

TIMESTAMP=$(date +%Y%m%d_%H%M)
REVIEW_FILE="docs/reviews/${ISSUE}_code_review_${TIMESTAMP}.md"
# I197: 同じ分のうちにもう一度流しても前の記録を上書きしない（台帳の前の周が消えるため）
n=1; while [ -e "$REVIEW_FILE" ]; do n=$(( n + 1 )); REVIEW_FILE="docs/reviews/${ISSUE}_code_review_${TIMESTAMP}_${n}.md"; done
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

# I197 §4.8: 全体のレビューか差分のレビューか（台帳のある最新の記録の REVIEWED_COMMIT が HEAD の祖先なら差分）
IFS=$'\t' read -r REVIEW_KIND LEDGER_N SINCE PREV_LEDGER_REC <<< "$(review_mode "$ISSUE")"
SCOPE_FILE=$(mktemp)
# 前の周の台帳は、始めた時点で写しておく（以後に記録が変わっても、読んだ台帳を使う）
PREV_LEDGER_FILE=""
if [ -n "$PREV_LEDGER_REC" ]; then PREV_LEDGER_FILE=$(mktemp); grep -E '^LEDGER: ' "$PREV_LEDGER_REC" > "$PREV_LEDGER_FILE" || true; fi
if [ "$REVIEW_KIND" = "delta" ]; then
  delta_files origin/develop "$SINCE" > "$SCOPE_FILE" || { echo "⛔ 差分のレビューの範囲を取れません（起点 ${SINCE}）"; exit 1; }
  REVIEW_RANGE="${SINCE}...HEAD"
  echo "差分のレビュー（台帳の ${LEDGER_N} 周目・起点 ${SINCE}・範囲のファイル $(grep -c . "$SCOPE_FILE") 本）"
else
  REVIEW_RANGE="origin/develop...HEAD"
  echo "全体のレビュー（台帳の 1 周目）"
fi
# I205: 差分の中かどうかを行で決める（全体のレビューでもブランチが変えた行だけ）。FILE=- の種類にブランチが変えたファイルを使う
HUNKS_FILE=$(mktemp); BRANCH_OWN_FILE=$(mktemp)
delta_hunks origin/develop "$SINCE" > "$HUNKS_FILE" || { echo "⛔ 差分の行の塊を取れません（起点 ${SINCE:-merge-base}）"; exit 1; }
branch_own_files origin/develop > "$BRANCH_OWN_FILE" || { echo "⛔ ブランチが変えたファイルを取れません"; exit 1; }

# git 情報取得（最大 100KB、|| true で SIGPIPE による pipefail を抑制）。差分のレビューは範囲のファイルの起点からの差分だけ
if [ "$REVIEW_KIND" = "delta" ]; then
  if [ -s "$SCOPE_FILE" ]; then
    GIT_DIFF=$(xargs -d '\n' git diff "$SINCE" HEAD -- < "$SCOPE_FILE" | head -c 102400 || true)
  else
    GIT_DIFF="(起点の後に、記録の場所の外でブランチが変えたファイルは無い)"
  fi
else
  GIT_DIFF=$(git diff origin/develop...HEAD | head -c 102400 || true)
fi
GIT_LOG=$(git log "$REVIEW_RANGE" --oneline)
# I086 敵対レビュー H3 対応: core.quotePath=false で取得する。git 既定（true）は非 ASCII を含む
# パスを "..."（八進エスケープ）で丸ごとクォートし、path_risk_trigger の先頭リテラル glob が
# 不一致になって監視パスを NO に落とす（日本語ファイル名で安全網が fail-open する）ため。
# I181: --no-renames で名前変更を「元の場所の削除＋新しい場所の追加」として両方出す（既定は新しい名前だけで、
# 監視しているファイルを外へ移す変更が path_risk_trigger をすり抜けるため）。
GIT_FILES=$(git -c core.quotePath=false diff origin/develop...HEAD --name-only --no-renames)

# I193: 組み込みのレビュー（公式）を背景で同時に走らせ、CI 待ちと重ねる（互いに依存しないため）。
# パス判定（決定論）が YES のときは組み込みの /security-review も走らせる。結果は自作のレビュー役に渡す。
RISK_PATH=$(path_risk_trigger "$GIT_FILES")
# I197 §4.8: 高リスクは計画の段階（計画レビューの判定）とパスの判定で決める（周ごとの code-reviewer の判定は使わない）
RISK_PLAN=$(plan_risk "$ISSUE")
RISK_FINAL=$(combine_risk "$RISK_PLAN" "$RISK_PATH")
OFFICIAL_DIR=$(mktemp -d)
OFFICIAL_PIDS=()
cleanup_official() {
  local p
  for p in "${OFFICIAL_PIDS[@]}"; do kill_tree "$p"; done   # 子の timeout・claude まで止める（I193 F5）
  rm -rf "$OFFICIAL_DIR"
}
trap cleanup_official EXIT
echo "組み込みの /code-review を背景で実行しています..."
run_official_review "/code-review medium ${REVIEW_RANGE}" > "$OFFICIAL_DIR/code" &
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

# CI 待機（I193: 時間切れは exit 3・失敗は exit 1。打ち切った後に先へ進まない）。
# PR を取れない（gh の失敗）・PR が無いときも、CI を確かめられないので止める（I193 4 回目 H1。新しい流れでは
# /plan-issue が Draft PR を作るので、PR が無いのは異常。前は PR を取れないと CI 待ちを丸ごと飛ばしていた）
PR_RC=0
PR_NUM=$(find_pr_num) || PR_RC=$?
if [ "$PR_RC" -ne 0 ]; then
  if [ "$PR_RC" -eq 2 ]; then
    echo "⛔ ブランチ $(git rev-parse --abbrev-ref HEAD) の開いている PR がありません。CI を確かめられないので止めます。"
  else
    echo "⛔ PR を調べられませんでした（gh の失敗。認証・ネットワークを確かめてください）。CI を確かめられないので止めます。"
  fi
  echo "CI_WAIT: NO_PR"
  exit 1
fi
echo "CI を確認しています (PR #${PR_NUM})..."
CI_RC=0
wait_ci "$PR_NUM" || CI_RC=$?
if [ "$CI_RC" -eq 3 ]; then
  echo "⛔ CI が ${CI_WAIT_TIMEOUT:-1200} 秒で終わりませんでした。"
  exit 3
fi
if [ "$CI_RC" -ne 0 ]; then
  echo "⛔ CI が失敗しています。"
  exit 1
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
SECURITY_VERDICT=$(official_security_verdict "$RISK_PATH" "$OFFICIAL_SECURITY")
if [ "$SECURITY_VERDICT" != "OK" ]; then
  echo "⛔ 高リスクの変更で、組み込みの /security-review が動きませんでした（実行できず・読めていない）。HIGH として記録します。"
  echo "OFFICIAL_SECURITY: FAILED"
  GATE_EVIDENCE+="- ⛔ 高リスク（パス判定 YES）で組み込みの /security-review が動かなかった（HIGH。直すものは無いので review-gate が 1 回だけ実行し直す）"$'\n'
fi

# コンテキスト組み立て（条件で空になる語は先に変数にする。$( [ … ] && … ) は偽で 1 を返し set -e で止まるため）
FILES_NOTE=""; [ "$REVIEW_KIND" = "delta" ] && FILES_NOTE="（差分のレビューの範囲）"
CONTEXT="イシュー番号: ${ISSUE}

### イシューファイル
$(cat "$ISSUE_FILE")

### 計画書
$([ -n "$PLAN_FILE" ] && cat "$PLAN_FILE" || echo "(計画書なし)")

### レビューの種類（I197 §4.8）
$(if [ "$REVIEW_KIND" = "delta" ]; then
  printf '差分のレビュー（台帳の %s 周目）。見るのは下の「git diff」（起点 %s から HEAD までの、直した差分）と、次の「止める指摘（前の周まで）」が直ったかだけ。\n' "$LEDGER_N" "$SINCE"
  printf '下の止める指摘のすべてについて、FINDING 行を同じ id で書き直す（STATUS=resolved か open）。新しい指摘は続きの番号で書く（差分の外で見つけたものも書いてよいが、止めるかどうかはスクリプトが FILE・LINE・STOP・再現の欄と変更の種類から決める）。\n'
  printf '\n台帳の最大の番号: F%s（新しい指摘はこの次から）\n' "$(grep -oE '^LEDGER: F[0-9]+' "$PREV_LEDGER_FILE" | grep -oE '[0-9]+' | sort -n | tail -1 || true)"
  printf '\n#### 止める指摘（前の周まで）\n'
  ledger_blocking "$PREV_LEDGER_FILE" || true
  printf '\n#### 差分のレビューの範囲のファイル\n'; cat "$SCOPE_FILE"
else
  printf '全体のレビュー（台帳の 1 周目）。ブランチ全体を見て、指摘ごとに FINDING 行を書く（止めるかどうかはスクリプトが FILE・LINE・STOP・再現の欄と変更の種類から決める。ブランチで触っていない行の指摘は止めない）。\n'
fi)

### 変更の種類（I205・スクリプトが決めた。種類ごとの止め方は code-reviewer の定義の「止める指摘の書き方」）
$(if [ "$REVIEW_KIND" = "delta" ]; then ledger_kinds "$SCOPE_FILE"; else ledger_kinds "$BRANCH_OWN_FILE"; fi)

### 決定論ゲート実行結果（スクリプト実走済み・実 exit code／読解で上書きしないこと）
${GATE_EVIDENCE}
omission-lint: ${OMISSION_VERDICT}

### git log (${REVIEW_RANGE})
${GIT_LOG}

### 変更ファイル一覧${FILES_NOTE}
$(if [ "$REVIEW_KIND" = "delta" ]; then cat "$SCOPE_FILE"; else printf '%s' "$GIT_FILES"; fi)

### git diff (${REVIEW_RANGE}, max 100KB)
\`\`\`diff
${GIT_DIFF}
\`\`\`

### 組み込み /code-review の指摘（公式・plan モード。file・line・summary・failure_scenario）
${OFFICIAL_CODE}

### 組み込み /security-review の指摘（公式・plan モード。パス判定 YES のときだけ実行）
${OFFICIAL_SECURITY}"

# claude -p でレビュー実行（I193: 公式のサブエージェント定義を --agent で呼ぶ。読み取り専用は定義の tools で効かせる）
# 時間上限 REVIEW_TIMEOUT（既定 900 秒）。時間切れ・失敗・空は、その旨の記録を残して BLOCKER にする（fail-closed）
# I197: 承認なし（--permission-prompts none）・途中の出力を残す形で起動し、本文は記録の result から受け取る
REVIEW_RC=0
REVIEW_IN="$OFFICIAL_DIR/reviewer_in.txt"; REVIEW_LOG="$OFFICIAL_DIR/reviewer.jsonl"
printf '%s' "$CONTEXT" > "$REVIEW_IN"
run_claude_logged "${REVIEW_TIMEOUT:-900}" "$REVIEW_LOG" "$REVIEW_IN" \
  --agent "$REVIEWER_AGENT" --tools "Read,Grep,Glob" --permission-prompts none || REVIEW_RC=$?
REVIEW=$(claude_log_result "$REVIEW_LOG" 2>/dev/null) || REVIEW=""
REVIEW_OK=1
if [ "$REVIEW_RC" -ne 0 ] || [ -z "$REVIEW" ]; then
  REVIEW_OK=0
  echo "⚠️ レビュー役が終わりませんでした（claude -p exit=${REVIEW_RC}。124 は時間切れ）。BLOCKER として記録します。"
  REVIEW=$(reviewer_failure_record "$ISSUE" "$REVIEW_RC" "$REVIEW_LOG")
fi

# I193: レビューの間に、記録の場所の外のファイルが動いたら（組み込みのレビューと記録の REVIEWED_COMMIT の
# 対象がずれるので）決定論で BLOCKER にする。記録だけのコミット（敵対的レビューの記録など）は数えない（gate-check と同じ）
if DRIFT_FILES=$(changed_outside_records "$REVIEWED_HEAD" HEAD); then
  :
else
  echo "⛔ レビューを始めた後に、記録の場所の外のファイルが変わりました。BLOCKER として記録します（動かしてから review-gate をやり直してください）:"
  printf '%s' "$DRIFT_FILES"
  GATE_EVIDENCE+="- ⛔ レビューを始めた後に HEAD が ${REVIEWED_HEAD} から $(git rev-parse HEAD) に動き、記録の場所の外が変わった（BLOCKER）"$'\n'
  GATE_VERDICT=BLOCKER
fi

# 出力正規化
REVIEW_CLEAN=$(printf '%s\n' "$REVIEW" | sed -E 's/[[:space:]]*$//; s/^([[:space:]]*)(LEDGER|LEDGER_ROUND):/\1> \2:/')

# ファイル保存。判定（RISK・VERDICT）は自作のレビュー役の本文だけで行い、組み込みのレビューの出力は判定の後に足す
# （組み込みの出力の中の表の「| High |」などを、VERDICT 行が無いときの代わりの判定が拾わないように。I193 M6）
mkdir -p "$(dirname "$REVIEW_FILE")"
printf '%s\n' "$REVIEW_CLEAN" > "$REVIEW_FILE"

# I197 §4.8: 高リスク判定は計画レビューとパス（code-reviewer は判定しない）。証跡は注入セクションに残す
GATE_EVIDENCE+="- 高リスク判定: ${RISK_FINAL}（計画レビュー=${RISK_PLAN} / path=${RISK_PATH}）"$'\n'

# I197 §4.8: 台帳（累積）と合否。レビュー役が正常に終わり FINDING 行を読めたときだけ台帳の周に数える
LEDGER_FILE=$(mktemp)
if [ "$REVIEW_OK" = "1" ] && ledger_update "$REVIEW_KIND" "${PREV_LEDGER_FILE:-}" "$REVIEW_FILE" "$HUNKS_FILE" "$BRANCH_OWN_FILE" > "$LEDGER_FILE"; then
  LEDGER_VERDICT=$(ledger_verdict "$LEDGER_FILE")
  # 累積の台帳と台帳の周を本文の後ろに足す（正常に終わった周だけ。失敗した周は台帳に入れない）。
  # I205: 止める指摘（スクリプトが決めた）も書く。fix-loop が直すのはこの節の指摘だけ
  { printf '\n## 台帳（累積・スクリプトが書く）\n'; cat "$LEDGER_FILE"; printf 'LEDGER_ROUND: %s\n' "$LEDGER_N"
    printf '\n## 止める指摘（スクリプトが決めた・fix-loop が直すのはこれだけ）\n'
    ledger_blocking "$LEDGER_FILE" | sed 's/^LEDGER: /- /'; } >> "$REVIEW_FILE"
else
  [ "$REVIEW_OK" = "1" ] && GATE_EVIDENCE+="- ⛔ code-reviewer の FINDING 行の形が崩れている（BLOCKER・台帳の周に数えない）"$'\n'
  REVIEW_OK=0; : > "$LEDGER_FILE"; LEDGER_VERDICT=BLOCKER
fi
LLM_VERDICT=$(detect_code_verdict "$REVIEW_FILE")
# I205: code-reviewer の VERDICT 行は、全体のレビューでも差分のレビューでも合否に使わない（止めるかはスクリプトが FINDING 行の欄から決める）。
# VERDICT 行が無い＝出力が壊れているときだけ止める
grep -qE '^VERDICT:[[:space:]]*(BLOCKER|HIGH|OK)[[:space:]]*$' "$REVIEW_FILE" && REVIEWER_VERDICT=OK || REVIEWER_VERDICT=BLOCKER
# レビュー役が止めると言うのに、読める FINDING 行が 1 行も無い（表の中・箇条書きなどで書いた）→ 食い違いは止める側
if [ "$LLM_VERDICT" != "OK" ] && ! grep -qE '^FINDING: ' "$REVIEW_FILE"; then
  REVIEWER_VERDICT=BLOCKER
  GATE_EVIDENCE+="- ⛔ code-reviewer の VERDICT は ${LLM_VERDICT} なのに、読める FINDING 行が無い（BLOCKER）"$'\n'
fi
GATE_EVIDENCE+="- 台帳（${REVIEW_KIND}・${LEDGER_N} 周目）: ${LEDGER_VERDICT}（code-reviewer の VERDICT=${LLM_VERDICT}・合否に使わない）"$'\n'

# I084: 決定論ゲート結果で VERDICT を決定論的に上書きする（LLM 出力非依存）。
# FINAL = max(gate, omission, 台帳, code-reviewer の出力の壊れ, 組み込みのセキュリティ)。証跡を記録先頭へ注入し末尾 VERDICT 行を FINAL に書換え。
FINAL_VERDICT=$(combine_verdict "$GATE_VERDICT" "$OMISSION_VERDICT" "$LEDGER_VERDICT" "$REVIEWER_VERDICT" "$SECURITY_VERDICT")
inject_gate_result "$REVIEW_FILE" "$GATE_EVIDENCE" "$OMISSION_VERDICT" "$FINAL_VERDICT"
# 記録の RISK 行はスクリプトの判定で書き直す（gate-check はこの行とパスの判定を読む）
set_risk_line "$REVIEW_FILE" "$RISK_FINAL"
# I193（L13）: このレビューが見た HEAD を記録する（gate-check.sh が読む）
add_reviewed_commit "$REVIEW_FILE" "$REVIEWED_HEAD"
rm -f "$LEDGER_FILE" "$SCOPE_FILE" "$HUNKS_FILE" "$BRANCH_OWN_FILE" "${PREV_LEDGER_FILE:-}"
# 判定の後に、組み込みのレビューの出力を参考として足す（機械が読む行は neutralize_machine_lines で無効にしてある）
printf '\n## 組み込みのレビューの出力（公式・参考）\n\n### 組み込み /code-review の指摘\n\n%s\n\n### 組み込み /security-review の指摘\n\n%s\n' \
  "$OFFICIAL_CODE" "$OFFICIAL_SECURITY" >> "$REVIEW_FILE"

# 案A(I069): 生産物（レビュー記録）を生産者がコミットする（feature ブランチ時のみ・path-scoped）。
commit_review_artifact "$REVIEW_FILE" "$ISSUE" "code-review"

# PR コメント投稿（GitHub のコメントの上限 65,536 文字を超えるときは、組み込みのレビューの出力の前までと記録への参照だけにする。I193 L2）
if [ -n "$PR_NUM" ]; then
  PR_BODY=$(cat "$REVIEW_FILE")
  if [ "${#PR_BODY}" -gt 60000 ]; then
    PR_BODY="$(sed '/^## 組み込みのレビューの出力（公式・参考）/,$d' "$REVIEW_FILE" | head -c 58000)

（長いため一部だけを載せた。全文は ${REVIEW_FILE}）"
  fi
  gh pr review "$PR_NUM" --comment --body "$PR_BODY" \
    || echo "⚠️ PR コメント投稿失敗。手動で実行: gh pr review $PR_NUM --comment --body-file $REVIEW_FILE"
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
