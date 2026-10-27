#!/usr/bin/env bash
# adversarial-review.sh I###: 高リスク変更の敵対的レビューを 1 周行う（I197）。
# 呼び出し元: .claude/skills/review-gate/SKILL.md §3（Bash ツールの run_in_background で 1 回呼ぶ）
#
# 1 周の流れ（人の応答を一度も待たない・締め切り ADV_DEADLINE 秒）:
#   1. 計画書の「## 必ず確かめる項目」の一覧を読む（無い・形が違う → exit 2）
#   2. 読むだけのレビュー役（.claude/agents/adversarial-reviewer.md）を 3 観点で並列に、別プロセスの claude -p で起動する
#   3. レビュー役が返した実験案を、実験役（別プロセス・auto＋承認なし・Bash だけ）が変えずに実行し、結果を --resume で返す
#   4. 判定は一覧からこのスクリプトが決定論で出す（レビュー役の「実験した」は実験役の記録で確かめる）。
#      未検証・報告なし・時間切れ・拒否・作業ツリーの変更は合格にしない
#   5. 記録 docs/reviews/I###_adversarial_review_<ts>.md を書いてコミットする（gate-check が最後の VERDICT・REVIEWED_COMMIT を読む）
# 終了コード: 0=OK / 1=HIGH・BLOCKER（3 観点とも報告あり）/ 3=報告の無い観点がある（ROUNDS: 0）/ 4=周回の上限 / 2=実行できない
# 環境変数: ADV_DEADLINE（既定 600）・ADV_STEP_TIMEOUT（300）・ADV_MIN_STEP（60）・ADV_EXPERIMENT_ROUNDS（2）・
#           ADV_ROUND_LIMIT（2。ユーザーが延長を承認したときだけ 3）・ADV_REVIEW_BUDGET（2）・ADV_EXEC_BUDGET（0.5）・
#           ADV_BASE（比べる相手。既定 origin/develop）・CLAUDE_BIN（テスト用）
# 計画: docs/plans/open/plan_I197.md §4.3
set -uo pipefail

ADV_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 記録の場所・無害化・記録のコミットは code-review.sh と同じ関数を使う（同じ規則を 2 か所に書かない）
# shellcheck source=scripts/claude/code-review.sh disable=SC1091  # -x なしの単体の検査でもたどらない（読み込み先は別に検査される）
REVIEW_LIB_SOURCE_ONLY=1 . "$ADV_SCRIPT_DIR/code-review.sh" || { echo "⛔ code-review.sh を読み込めません"; exit 2; }
set +e
# shellcheck source=scripts/claude/review-process-lib.sh disable=SC1091
. "$ADV_SCRIPT_DIR/review-process-lib.sh" || { echo "⛔ review-process-lib.sh を読み込めません"; exit 2; }

# 既定値はここで 1 回だけ決める（記録に書く値と実際に効く値をそろえる）
: "${ADV_DEADLINE:=600}" "${ADV_STEP_TIMEOUT:=300}" "${ADV_MIN_STEP:=60}" "${ADV_EXPERIMENT_ROUNDS:=2}" \
  "${ADV_ROUND_LIMIT:=2}" "${ADV_REVIEW_BUDGET:=2}" "${ADV_EXEC_BUDGET:=0.5}" "${ADV_BASE:=origin/develop}"

PERSPECTIVE_NAMES=(
  ""
  "ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）"
  "テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）"
  "要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）"
)

# 計画書の一覧を「V<n>\t<観点>\t<確かめ方>\t<内容>」で出す。節が無い・0 行・形の違う行・重複 → 2。
# 節の見出しは、コードブロックの外の「## 必ず確かめる項目」か、その直後に全角の「（」が続く行だけ（階層・文言の違いは認めない）
read_checklist() {
  awk -v FS='|' '
    /^```/ || /^~~~/ { fence = !fence; next }
    fence { next }
    /^## / {
      insec = ($0 == "## 必ず確かめる項目" || index($0, "## 必ず確かめる項目（") == 1)
      if (insec) found = 1
      next
    }
    !insec { next }
    /^\|/ {
      if ($0 ~ /^\|[-:| ]+\|[[:space:]]*$/) next
      id = $2; p = $3; m = $4; gsub(/^[[:space:]]+|[[:space:]]+$/, "", id); gsub(/^[[:space:]]+|[[:space:]]+$/, "", p); gsub(/^[[:space:]]+|[[:space:]]+$/, "", m)
      if (id == "項目") next
      c = ""; for (i = 5; i < NF; i++) c = c (i > 5 ? "|" : "") $i
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", c)
      if (id !~ /^V[0-9]+$/ || p !~ /^[123]$/ || (m != "実験必須" && m != "読んで可") || c == "") { bad = bad "\n  " $0; next }
      if (seen[id]++) { bad = bad "\n  （重複）" $0; next }
      n++; printf "%s\t%s\t%s\t%s\n", id, p, m, c
    }
    END {
      if (!found) { print "一覧の節（## 必ず確かめる項目）がありません" > "/dev/stderr"; exit 2 }
      if (bad != "") { print "形の違う行があります:" bad > "/dev/stderr"; exit 2 }
      if (n == 0) { print "一覧の表に行がありません" > "/dev/stderr"; exit 2 }
    }
  ' "$1"
}

# 過去の記録（docs/reviews/[closed/]I###_adversarial_review_*.md）をファイル名の時刻順に出す（code-review.sh の review_records）
adversarial_records() { review_records "$ISSUE" adversarial_review; }

# 周回の合計（記録ごとの最後の ROUNDS: 行。行が無い記録は 1）
count_rounds() {
  local f r total=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    r=$(grep -oE '^ROUNDS:[[:space:]]*[0-9]+[[:space:]]*$' "$f" | tail -1 | grep -oE '[0-9]+')
    total=$(( total + ${r:-1} ))
  done < <(adversarial_records)
  echo "$total"
}

# 周に数えた記録（ROUNDS: 1 以上。行が無い古い記録は 1）を時刻順に出す。ROUNDS: 0 の記録（報告の無い周・
# 受け入れの記録）は「周として成立していない」ので、見る範囲の起点にも既知 findings にも使わない
# （起点に使うと、やり直しの周が空の差分を見て OK を出す。既知に使うと、未修正の指摘が再報告されずに消える）
counted_records() {
  local f r
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    r=$(grep -oE '^ROUNDS:[[:space:]]*[0-9]+[[:space:]]*$' "$f" | tail -1 | grep -oE '[0-9]+')
    [ "${r:-1}" -ge 1 ] && printf '%s\n' "$f"
  done < <(adversarial_records)
  return 0
}

# 見る範囲の起点: 周に数えた最新の記録の REVIEWED_COMMIT。無い・HEAD の祖先でない（rebase の後など）ときは
# 比べる相手（origin/develop）。祖先でないコミットとの差分は HEAD の歴史と食い違うので、広い側で見る（I202 F7）
review_base() {
  local last sha
  last=$(counted_records | tail -1)
  if [ -n "$last" ]; then
    sha=$(record_reviewed_commit "$last")
    if [ -n "$sha" ] && git merge-base --is-ancestor "$sha" HEAD 2>/dev/null; then echo "$sha"; return; fi
  fi
  echo "${ADV_BASE}"
}

# 記録の場所の外の、コミットしていない変更（未追跡を含む）の一覧
dirty_outside_records() {
  local entry p
  while IFS= read -r -d '' entry; do
    p="${entry:3}"
    is_record_path "$p" || printf '%s\n' "$p"
  done < <(git status --porcelain=v1 -z --untracked-files=all --no-renames)
}

# 作業ツリーの状態: status の各行と、そのファイルの中身のハッシュ（消えたものは -）。記録の場所も含める
# （起動前から変更済み・未追跡のファイル〔作業中の計画書・記録〕を実験がさらに書き換えても、ハッシュの違いで捕まえる）
worktree_state() {
  local entry p h
  while IFS= read -r -d '' entry; do
    p="${entry:3}"
    h="-"; [ -f "$p" ] && h=$(git hash-object -- "$p" 2>/dev/null)
    printf '%s\t%s\n' "$entry" "$h"
  done < <(git status --porcelain=v1 -z --untracked-files=all --no-renames)
}

# 実験が作業ツリーを変えたか（起動時の状態〔$RUN/state0〕・HEAD・ブランチと比べる）。変えていたら周全体のフラグ $RUN/dirty に足す。
# 実験中はこのスクリプトもリポジトリに書かないので、記録の場所を含むどのファイルの変化も実験のせいとみなす。
# 実験は同じ作業ツリーで並列に動くので、どの観点が変えたかは決めず、周全体の実験を無効にする（消さない・戻さない）
check_worktree() {
  local head branch changed
  head=$(git rev-parse HEAD 2>/dev/null)
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  changed=$(worktree_state | diff "$RUN/state0" - | sed -nE 's/^[<>] ...([^	]*)	.*$/\1/p' | sort -u)
  [ -n "$changed" ] && printf '%s\n' "$changed" >> "$RUN/dirty"
  [ "$head" = "$REVIEWED_HEAD" ] || printf 'HEAD が %s から %s に動いた\n' "$REVIEWED_HEAD" "${head:-不明}" >> "$RUN/dirty"
  [ "$branch" = "$REVIEWED_BRANCH" ] || printf 'ブランチが %s から %s に変わった\n' "$REVIEWED_BRANCH" "${branch:-不明}" >> "$RUN/dirty"
  return 0
}

remaining() { echo $(( ADV_START + ADV_DEADLINE - $(date +%s) )); }
step_timeout() { local r; r=$(remaining); local s="${ADV_STEP_TIMEOUT}"; [ "$r" -lt "$s" ] && s="$r"; echo "$s"; }

# 締め切りまでの残りで 1 回呼ぶ: <入力> <ログ> <claude の引数…>（残りが無ければ呼ばずに 124）
run_step() {
  local input="$1" log="$2" t
  shift 2
  t=$(step_timeout)
  if [ "$t" -le 0 ]; then echo '0	{"type":"__log_closed__"}' > "$log"; return 124; fi
  run_claude_logged "$t" "$log" "$input" "$@"
}

# レビュー役の 1 回の呼び出し: <入力> <ログ> [<session_id>]
run_reviewer() {
  local sid="${3:-}"
  run_step "$1" "$2" \
    --agent adversarial-reviewer --tools "Read,Grep,Glob" \
    --permission-mode manual --permission-prompts none \
    --max-budget-usd "${ADV_REVIEW_BUDGET}" ${sid:+--resume "$sid"}
}

# 実験役の 1 回の呼び出し: <入力> <ログ>
run_experiment_agent() {
  run_step "$1" "$2" \
    --model haiku --tools "Bash" \
    --permission-mode auto --permission-prompts none \
    --setting-sources user --settings .claude/settings.json \
    --strict-mcp-config --no-session-persistence \
    --max-budget-usd "${ADV_EXEC_BUDGET}"
}

# 本文から実験案を取り出し、<出力先>/<id>.cmd に書いて id を 1 行ずつ出す（EXPERIMENT_BEGIN <id> 〜 EXPERIMENT_END <id>）。
# 既に .cmd がある id（扱い済み）は書き直さず出さない（記録のコマンドと実行したコマンドを食い違わせない）
extract_experiments() {   # $1=本文のファイル $2=出力先
  python3 -I - "$1" "$2" <<'PY'
import re, sys, os
body, out = sys.argv[1], sys.argv[2]
cur, buf, seen = None, [], set()
for line in open(body, encoding="utf-8", errors="replace").read().split("\n"):
    m = re.fullmatch(r"EXPERIMENT_BEGIN ([A-Za-z0-9_-]+)\s*", line)
    if cur is None and m:
        cur, buf = m.group(1), []
        continue
    if cur is not None and re.fullmatch(r"EXPERIMENT_END " + re.escape(cur) + r"\s*", line):
        while buf and not buf[0].strip():
            buf.pop(0)
        while buf and not buf[-1].strip():
            buf.pop()
        path = os.path.join(out, cur + ".cmd")
        if cur not in seen and buf and not os.path.exists(path):
            seen.add(cur)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(buf))
            print(cur)
        cur = None
        continue
    if cur is not None:
        buf.append(line)
PY
}

# 報告の項目の行（最後のもの）: <本文> <id> → "<result>\t<exp,exp>"（無ければ空）
item_line() {
  grep -E "^ITEM: $2 RESULT=(experiment|read|not_done)( EXP=[A-Za-z0-9_,-]+)?[[:space:]]*$" "$1" | tail -1 \
    | sed -E 's/^ITEM: [^ ]+ RESULT=([a-z_]+)( EXP=([A-Za-z0-9_,-]+))?.*$/\1\t\3/'
}
# NEW_CRITICAL / NEW_HIGH の数（最後の行。無ければ空）
new_count() { grep -oE "^$2:[[:space:]]*[0-9]+[[:space:]]*\$" "$1" | tail -1 | grep -oE '[0-9]+'; }

# 1 観点を通しで行う（background で呼ぶ）。結果は $RUN/p<n>/ に書く
run_perspective() {
  local p="$1" d="$RUN/p$1" r=0 log rc sid ids id st out next_in reason
  mkdir -p "$d/exp"
  local t0; t0=$(date +%s)
  {
    printf '対象イシュー: %s\nあなたの観点: %s. %s\n' "$ISSUE" "$p" "${PERSPECTIVE_NAMES[$p]}"
    printf '見る範囲（REVIEW_BASE）: %s...HEAD（下に変更ファイルの一覧と差分）\n' "$REVIEW_BASE"
    printf 'イシューファイル: %s\n計画書: %s（どちらも Read で読む）\n' "$ISSUE_FILE" "$PLAN_FILE"
    printf '既知 findings（再報告しない。Read で読む）: %s\n\n' "${PREV_RECORDS:-なし}"
    printf '## あなたが判定を持つ項目（すべてに ITEM 行を書く）\n'
    awk -F'\t' -v p="$p" '$2 == p { printf "- %s（%s）: %s\n", $1, $3, $4 }' "$RUN/checklist.tsv"
    printf '\n## 全項目（参考。ほかの観点の項目の ITEM 行は判定に使われない）\n'
    awk -F'\t' '{ printf "- %s（観点 %s・%s）: %s\n", $1, $2, $3, $4 }' "$RUN/checklist.tsv"
    printf '\n## 実験の約束\n実験は自分で実行せず EXPERIMENT_BEGIN P%s-E<n> 〜 EXPERIMENT_END P%s-E<n> で返す。実験役が変えずに実行し、結果が次の入力で返る（往復は %s 回まで・1 周 %s 秒で締め切り）。作業ツリーに書く実験は無効になる（/tmp に書く）。\n' \
      "$p" "$p" "${ADV_EXPERIMENT_ROUNDS}" "${ADV_DEADLINE}"
    printf '\n## 変更ファイルの一覧\n'; cat "$RUN/files.txt"
    printf '\n## 差分\n'; cat "$RUN/diff.txt"
  } > "$d/in0.txt"
  log="$d/log0.jsonl"
  run_reviewer "$d/in0.txt" "$log"; rc=$?
  sid=$(claude_log_session "$log" 2>/dev/null)
  # 判定に使うのは、最後に成功した呼び出しの本文（続きの呼び出しが時間切れ・失敗しても、前の報告を消さない）
  local good_log="" note="" last_ids=""
  : > "$d/body.txt"
  local sub why
  while :; do
    # 成功＝exit 0 かつ result が success（exit 0 でも success でなければ失敗として、前の成功した報告を消さない）
    sub=$(claude_log_subtype "$log" 2>/dev/null)
    if [ "$rc" -ne 0 ] || [ "$sub" != "success" ]; then
      if [ "$rc" -ne 0 ]; then why="exit=${rc}"; else why="result が success でない（${sub:-なし}）"; fi
      if [ -n "$good_log" ]; then
        note="続きの呼び出しが終わらなかった（${why}）ため、前の報告で判定（その後の実験の結果は読まれていない）"
        # 結果をレビュー役が読んでいない実験は「実行した」に数えない（exp_status は最後の行を採る）
        for id in $last_ids; do printf '%s\t%s\n' "$id" "unread" >> "$d/exp_status"; done
      fi
      break
    fi
    claude_log_result "$log" > "$d/body.txt" 2>/dev/null || : > "$d/body.txt"
    good_log="$log"
    # まだ扱っていない実験案（exp_status の 1 列目にない id）だけを実行する
    ids=$(extract_experiments "$d/body.txt" "$d/exp" | while IFS= read -r id; do cut -f1 "$d/exp_status" 2>/dev/null | grep -qxF -- "$id" || echo "$id"; done)
    [ -n "$ids" ] || break
    reason=""
    if [ "$r" -ge "${ADV_EXPERIMENT_ROUNDS}" ] || [ -z "$sid" ]; then reason=limit
    # 往復を始めるのは、実験役と続きの 2 回分（2 × ADV_MIN_STEP）の時間が残っているときだけ
    elif [ "$(remaining)" -lt $(( 2 * ADV_MIN_STEP )) ]; then reason=deadline; fi
    if [ -n "$reason" ]; then
      for id in $ids; do printf '%s\t%s\n' "$id" "$reason" >> "$d/exp_status"; done
      break
    fi
    r=$(( r + 1 ))
    {
      printf '次の実験を、書かれたコマンドを一字も変えずに、Bash ツールで 1 つずつ 1 回だけ実行せよ。ほかの道具は使わない。拒否されたら再試行せず次へ進む。全部終わったら DONE とだけ答えよ。\n'
      for id in $ids; do printf '\n<<<COMMAND %s\n%s\nCOMMAND>>>\n' "$id" "$(cat "$d/exp/$id.cmd")"; done
    } > "$d/exec_in$r.txt"
    # 実験役は観点をまたいで同時に 1 本だけ（同じ作業ツリーで「壊して戻す」実験が重ならないように・I202 F6）。
    # 待った後に締め切りが迫っていれば、呼ばずに締め切りとして扱う（未検証）
    local waited_out=0
    # 鍵を取った後も、鍵の前と同じく実験役と続きの 2 回分の時間で比べる（I206 F5）。
    # 実験役の後の作業ツリーの比較（ファイル・HEAD・ブランチ）も鍵を持ったまま行う（ほかの観点の実験の途中を拾わない・I206 F3）
    {
      flock 9
      if [ "$(remaining)" -lt $(( 2 * ADV_MIN_STEP )) ]; then waited_out=1
      else run_experiment_agent "$d/exec_in$r.txt" "$d/exec$r.jsonl"
        check_worktree; fi
    } 9>"$RUN/exp.lock"
    if [ "$waited_out" -eq 1 ]; then
      for id in $ids; do printf '%s\t%s\n' "$id" deadline >> "$d/exp_status"; done
      r=$(( r - 1 ))   # 往復は始めていない
      break
    fi
    local mode; mode=$(claude_log_mode "$d/exec$r.jsonl")
    next_in="$d/in$r.txt"
    printf '## 実験の結果（往復 %s）\n' "$r" > "$next_in"
    for id in $ids; do
      if [ "$mode" != "auto" ]; then
        st="mode"; out="実験役のモードが auto ではない（${mode:-不明}）ため実行していない"
      else
        out=$(claude_log_ran "$d/exec$r.jsonl" "$d/exp/$id.cmd"); case $? in 0) st=ran ;; 10) st=denied ;; 1) st=notcalled ;; *) st=unreadable ;; esac
      fi
      printf '%s\t%s\n' "$id" "$st" >> "$d/exp_status"
      printf '%s\n' "$out" > "$d/exp/$id.out"
      printf '\n### %s: %s\n~~~\n%s\n~~~\n' "$id" "$st" "$out" >> "$next_in"
    done
    last_ids="$ids"
    printf '\n上の結果を踏まえ、最終報告を出力の形どおりに全部書き直せ（担当の項目すべてに ITEM 行を書く）。まだ実験が要るなら EXPERIMENT 行で出せ（残りの往復: %s）。\n' \
      "$(( ADV_EXPERIMENT_ROUNDS - r ))" >> "$next_in"
    log="$d/log$r.jsonl"
    run_reviewer "$next_in" "$log" "$sid"; rc=$?
  done
  # 終わり方: 報告あり = 最後に成功した呼び出しの result が success・本文に NEW_CRITICAL と NEW_HIGH の行
  local state
  if [ -z "$good_log" ]; then
    if [ "$rc" -eq 124 ]; then state="時間切れ"; else state="失敗（${why:-exit=${rc}}）"; fi
  elif [ -z "$(new_count "$d/body.txt" NEW_CRITICAL)" ] || [ -z "$(new_count "$d/body.txt" NEW_HIGH)" ]; then state="報告なし（NEW_CRITICAL・NEW_HIGH の行が無い）"
  else state="報告あり"; fi
  printf '%s\n' "$state" > "$d/state"
  printf '%s' "$note" > "$d/note"   # 空なら空のファイル（改行だけで「報告あり（）」と出さない）
  printf '%s\n' "$(( $(date +%s) - t0 ))" > "$d/secs"
  printf '%s\n' "$r" > "$d/rounds"
  claude_log_last_tool "$log" > "$d/last_tool" 2>/dev/null
  # 拒否の件数と費用（total_cost_usd）の合計。費用は既定の予算を見直す材料（plan_I197.md 手動 No.1）
  # 拒否の一覧を読めないログが 1 つでもあれば印のファイル denials_unreadable を作る（黙って 0 件にしない・I202 F8。判定は合格にしない）
  local n=0 cost=0 f c ds; for f in "$d"/log*.jsonl "$d"/exec*.jsonl; do
    [ -f "$f" ] || continue
    if ds=$(claude_log_denials "$f" 2>/dev/null); then n=$(( n + $(printf '%s' "$ds" | grep -c .) ))
    else : > "$d/denials_unreadable"; fi
    c=$(claude_log_cost "$f"); cost=$(awk -v a="$cost" -v b="${c:-0}" 'BEGIN { printf "%.4f", a + b }')
  done
  printf '%s\n' "$n" > "$d/denials"
  printf '%s\n' "$cost" > "$d/cost"
}

# 項目の判定: <id> <観点> <確かめ方> → "<報告>\t<実験>\t<判定>"（判定は「確認済み（実験）」「確認済み（読んで）」「未検証（理由）」）
item_verdict() {
  local id="$1" p="$2" m="$3" d="$RUN/p$2" line res exps e ok=0 shown=""
  if [ "$(cat "$d/state")" != "報告あり" ]; then printf '―\t―\t未検証（観点 %s の報告なし）\n' "$p"; return; fi
  line=$(item_line "$d/body.txt" "$id")
  if [ -z "$line" ]; then printf '―\t―\t未検証（ITEM 行が無い）\n'; return; fi
  res="${line%%$'\t'*}"; exps="${line#*$'\t'}"
  if [ "$res" = "experiment" ]; then
    for e in ${exps//,/ }; do
      local st; st=$(awk -F'\t' -v e="$e" '$1 == e { s = $2 } END { print s }' "$d/exp_status" 2>/dev/null)
      shown+="${e}=${st:-なし} "
      [ "$st" = "ran" ] && [ ! -s "$RUN/dirty" ] && ok=1
    done
    if [ "$ok" -eq 1 ]; then printf '実験で確認\t%s\t確認済み（実験）\n' "$shown"
    else printf '実験で確認\t%s\t未検証（実験が実行されていない・無効）\n' "${shown:-EXP なし}"; fi
    return
  fi
  if [ "$res" = "read" ]; then
    if [ "$m" = "読んで可" ]; then printf '読んで確認\t―\t確認済み（読んで）\n'
    else printf '読んで確認\t―\t未検証（実験必須を読んで確認しただけ）\n'; fi
    return
  fi
  printf '未実施\t―\t未検証（未実施）\n'
}

# 表の 1 マスに入れる（改行を空白に・| を全角に。tr は多バイト文字を扱えないので sed で置き換える）
cell() { sed -e 's/|/／/g' | tr '\n' ' '; }

# ---- テストは REVIEW_LIB_SOURCE_ONLY=1 で関数だけを読み込む ----
if [ "${REVIEW_LIB_SOURCE_ONLY:-}" = "1" ]; then return 0; fi

ISSUE="${1:-}"
if ! [[ "$ISSUE" =~ ^I[0-9]{3}$ ]]; then echo "⛔ 使い方: $0 I###（受け取った値: '${ISSUE}'）"; echo "ADVERSARIAL_ERROR: USAGE"; exit 2; fi
# 実験役を観点をまたいで 1 本ずつにする flock が無ければ実行できない（黙って鍵なしで走らせない・I206 F10）
if ! command -v flock >/dev/null 2>&1; then echo "⛔ flock がありません（実験役を 1 本ずつにできない）。util-linux を入れてください。"; echo "ADVERSARIAL_ERROR: FLOCK"; exit 2; fi
REPO_ROOT="$(git rev-parse --show-toplevel)" || { echo "⛔ git リポジトリの中で実行してください"; exit 2; }
cd "$REPO_ROOT" || exit 2
ADV_START=$(date +%s)

# 周回の上限（今の周を始める前に数える）
USED=$(count_rounds)
if [ "$USED" -ge "${ADV_ROUND_LIMIT}" ]; then
  echo "⛔ 敵対的レビューの周回の上限に達しています（通算 ${USED} 周・上限 ${ADV_ROUND_LIMIT}）。起動しません。"
  echo "ADVERSARIAL_ROUNDS_USED: ${USED}"
  echo "ADVERSARIAL_VERDICT: LIMIT"
  exit 4
fi

ISSUE_FILE=$(find_file "issues" "${ISSUE}.md")
PLAN_FILE=$(find_plan_file "$ISSUE")
if [ -z "$ISSUE_FILE" ] || [ -z "$PLAN_FILE" ]; then echo "⛔ イシューファイルか計画書がありません"; echo "ADVERSARIAL_ERROR: FILES"; exit 2; fi

RUN=$(mktemp -d)
PIDS=()
# 止められたときも、背景の観点と子プロセス（claude・実験役の Bash）を止めてから一時フォルダを消す（code-review.sh の kill_tree）
# shellcheck disable=SC2317  # trap から呼ぶ
cleanup_adv() { local q; for q in "${PIDS[@]}"; do kill_tree "$q"; done; rm -rf "$RUN"; }
trap cleanup_adv EXIT
trap 'exit 130' INT TERM
if ! read_checklist "$PLAN_FILE" > "$RUN/checklist.tsv"; then
  echo "⛔ ${PLAN_FILE} の「## 必ず確かめる項目」を読めません（上の理由）。一覧を直してからやり直してください。"
  echo "ADVERSARIAL_ERROR: CHECKLIST"
  exit 2
fi
DIRTY0=$(dirty_outside_records)
if [ -n "$DIRTY0" ]; then
  echo "⛔ 記録の場所の外に、コミットしていない変更があります（実験が作業ツリーを変えたかを比べられません）:"
  printf '%s\n' "$DIRTY0"
  echo "ADVERSARIAL_ERROR: DIRTY"
  exit 2
fi

REVIEW_BASE=$(review_base)
REVIEW_BASE_NOTE=""
if [ "$REVIEW_BASE" = "$ADV_BASE" ] && [ -n "$(counted_records | tail -1)" ]; then
  REVIEW_BASE_NOTE="前の記録の REVIEWED_COMMIT が無い・HEAD の祖先ではないため、比べる相手（${ADV_BASE}）から見た"
fi
REVIEWED_HEAD=$(git rev-parse HEAD)
REVIEWED_BRANCH=$(git rev-parse --abbrev-ref HEAD)
worktree_state > "$RUN/state0"
PREV_RECORDS=$(counted_records | paste -sd' ' -)
if ! git -c core.quotePath=false diff --name-status --no-renames "${REVIEW_BASE}...HEAD" > "$RUN/files.txt" \
   || ! git diff "${REVIEW_BASE}...HEAD" > "$RUN/diff_full.txt"; then
  echo "⛔ 見る範囲 ${REVIEW_BASE}...HEAD の差分を取れません（比べる相手が無い・REVIEWED_COMMIT が無い）。"
  echo "ADVERSARIAL_ERROR: DIFF"
  exit 2
fi
head -c 102400 "$RUN/diff_full.txt" > "$RUN/diff.txt"
if [ "$(wc -c < "$RUN/diff_full.txt")" -gt 102400 ]; then
  printf '\n（差分は 100KB で切った。続きは一覧のファイルを Read で読む）\n' >> "$RUN/diff.txt"
fi

echo "敵対的レビューを 3 観点で起動しました（締め切り ${ADV_DEADLINE} 秒・見る範囲 ${REVIEW_BASE}...HEAD）..."
for p in 1 2 3; do run_perspective "$p" & PIDS+=("$!"); done
wait "${PIDS[@]}"
PIDS=()
check_worktree   # 全観点が終わった後にもう一度比べる
ELAPSED=$(( $(date +%s) - ADV_START ))

# ---- 判定（決定論） ----
UNVERIFIED=0; CRIT=0; HIGHN=0; UNREPORTED=0; DIRTY_ANY=0; DENIALS=0; DENIALS_UNREADABLE=0
ITEM_ROWS=""
while IFS=$'\t' read -r id p m c; do
  IFS=$'\t' read -r rep exps ver <<< "$(item_verdict "$id" "$p" "$m")"
  case "$ver" in 未検証*) UNVERIFIED=$(( UNVERIFIED + 1 )) ;; esac
  ITEM_ROWS+="| ${id} | ${p} | ${m} | ${rep} | $(printf '%s' "$exps" | cell) | ${ver} |"$'\n'
done < "$RUN/checklist.tsv"
PERSP_ROWS=""
for p in 1 2 3; do
  d="$RUN/p$p"; st=$(cat "$d/state")
  if [ "$st" = "報告あり" ]; then
    CRIT=$(( CRIT + $(new_count "$d/body.txt" NEW_CRITICAL) )); HIGHN=$(( HIGHN + $(new_count "$d/body.txt" NEW_HIGH) ))
    lt="―"; lr="―"; le="―"
  else
    UNREPORTED=$(( UNREPORTED + 1 ))
    lt=$(cut -f1,2 "$d/last_tool" | tr '\t' ' ' | cell); lr=$(cut -f3 "$d/last_tool" | cell); le="$(cut -f4 "$d/last_tool") 秒"
  fi
  DENIALS=$(( DENIALS + $(cat "$d/denials") ))
  dn="$(cat "$d/denials")"
  if [ -e "$d/denials_unreadable" ]; then DENIALS_UNREADABLE=1; dn="${dn}（読めない記録あり）"; fi
  [ -s "$d/note" ] && st+="（$(cat "$d/note")）"
  PERSP_ROWS+="| ${p} | ${st} | $(cat "$d/secs") 秒 | $(cat "$d/rounds") | ${dn} | \$$(cat "$d/cost") | ${lt} | ${lr} | ${le} |"$'\n'
done

[ -s "$RUN/dirty" ] && DIRTY_ANY=1
if [ "$CRIT" -gt 0 ]; then VERDICT=BLOCKER
elif [ "$HIGHN" -gt 0 ] || [ "$UNVERIFIED" -gt 0 ] || [ "$UNREPORTED" -gt 0 ] || [ "$DIRTY_ANY" -eq 1 ] || [ "$DENIALS_UNREADABLE" -eq 1 ]; then VERDICT=HIGH
else VERDICT=OK; fi
if [ "$UNREPORTED" -gt 0 ]; then ROUNDS=0; else ROUNDS=1; fi

# ---- 記録 ----
TS=$(date +%Y%m%d_%H%M)
RECORD="docs/reviews/${ISSUE}_adversarial_review_${TS}.md"
n=1; while [ -e "$RECORD" ]; do n=$(( n + 1 )); RECORD="docs/reviews/${ISSUE}_adversarial_review_${TS}_${n}.md"; done
{
  printf '# 敵対的レビュー [%s]（別プロセス・%s）\n\n' "$ISSUE" "$(date '+%Y-%m-%d %H:%M')"
  printf -- '- 見た範囲: %s...%s\n' "$REVIEW_BASE" "$REVIEWED_HEAD"
  printf -- '- 所要時間: %s 秒（上限 %s）\n' "$ELAPSED" "${ADV_DEADLINE}"
  printf -- '- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 %s 件は下の表）\n' "$DENIALS"
  [ "$DENIALS_UNREADABLE" -eq 1 ] && printf -- '- ⛔ 拒否の一覧を読めない記録がある（承認が要る操作で止まったかを確かめられないので、この周は合格にしない）\n'
  [ -n "$REVIEW_BASE_NOTE" ] && printf -- '- %s\n' "$REVIEW_BASE_NOTE"
  printf -- '- 一覧: %s の「## 必ず確かめる項目」（%s 項目）\n' "$PLAN_FILE" "$(grep -c . "$RUN/checklist.tsv")"
  [ "$UNREPORTED" -gt 0 ] && printf -- '- 報告の無い観点が %s 件ある（この周は ROUNDS: 0。review-gate が 1 回だけやり直す）\n' "$UNREPORTED"
  printf '\n## 確かめる項目の結果\n| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |\n|---|---|---|---|---|---|\n%s' "$ITEM_ROWS"
  printf '\n## 観点ごとの実行\n| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |\n|---|---|---|---|---|---|---|---|---|\n%s' "$PERSP_ROWS"
  printf '\n## 実験\n'
  if [ -s "$RUN/dirty" ]; then printf -- '- ⛔ 実験の後に作業ツリーが変わった（この周の実験はすべて無効。ファイルは消していない・戻していない）: %s\n' "$(sort -u "$RUN/dirty" | paste -sd' ' -)"; fi
  for p in 1 2 3; do
    d="$RUN/p$p"
    [ -s "$d/exp_status" ] || continue
    printf '\n### 観点 %s\n' "$p"
    while IFS=$'\t' read -r id st; do
      case "$st" in ran) label="実行した" ;; unread) label="実行した（続きの呼び出しが終わらず、結果は読まれていない）" ;; denied) label="拒否された" ;; notcalled) label="呼ばれなかった（同じコマンドの実行が無い）" ;; mode) label="実行していない（実験役のモードが auto でない）" ;; deadline) label="実行していない（締め切り）" ;; limit) label="実行していない（往復の上限）" ;; *) label="判定できない（実験役の記録を読めない）" ;; esac
      printf '\n#### %s: %s\n~~~\n%s\n~~~\n' "$id" "$label" "$(neutralize_machine_lines < "$d/exp/$id.cmd" 2>/dev/null)"
      [ -s "$d/exp/$id.out" ] && printf '出力の先頭:\n~~~\n%s\n~~~\n' "$(neutralize_machine_lines < "$d/exp/$id.out")"
    done < "$d/exp_status"
  done
  printf '\n## 各観点の報告（本文。機械が読む行は無害化した）\n'
  for p in 1 2 3; do
    printf '\n### 観点 %s: %s\n\n' "$p" "${PERSPECTIVE_NAMES[$p]}"
    if [ -s "$RUN/p$p/body.txt" ]; then neutralize_machine_lines < "$RUN/p$p/body.txt"; printf '\n'; else printf '（本文なし）\n'; fi
  done
  printf '\nNEW_CRITICAL_TOTAL: %s\nNEW_HIGH_TOTAL: %s\nUNVERIFIED: %s\nREVIEWED_COMMIT: %s\nROUNDS: %s\nVERDICT: %s\n' \
    "$CRIT" "$HIGHN" "$UNVERIFIED" "$REVIEWED_HEAD" "$ROUNDS" "$VERDICT"
} | sed 's/[[:space:]]*$//' > "$RECORD"   # 行末の空白を落とす（pre-commit の trailing-whitespace でコミットが失敗しないように）
commit_review_artifact "$RECORD" "$ISSUE" "adversarial-review"

echo "ADVERSARIAL_RECORD: ${RECORD}"
echo "UNVERIFIED: ${UNVERIFIED}"
echo "NEW_CRITICAL: ${CRIT}"
echo "NEW_HIGH: ${HIGHN}"
echo "ADVERSARIAL_VERDICT: ${VERDICT}"
if [ "$UNREPORTED" -gt 0 ]; then exit 3; fi
[ "$VERDICT" = "OK" ] && exit 0
exit 1
