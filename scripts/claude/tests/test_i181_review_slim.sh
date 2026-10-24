#!/usr/bin/env bash
# I181（plan_I181.md 4-2〜4-7・4-9）: 敵対的レビューの対象・上限・守る範囲・上限到達時の扱い・
# 計画レビューのやり直しの条件・新しい安全装置を足す前の確認が、指示ファイルと runbook に書かれ、
# パス判定と LLM の条件（code-reviewer.md・plan-reviewer.md）の例外の集合が一致することを決定論検証する。
# 実行: bash scripts/claude/tests/test_i181_review_slim.sh
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || exit 1
TMP="$(mktemp -d)"
trap 'rm -r "$TMP"' EXIT
SK=.claude/skills/code-review/SKILL.md; RR=docs/runbooks/review-rules.md
AR=.claude/review-agents/adversarial-reviewer.md; CR=.claude/review-agents/code-reviewer.md
PR=.claude/review-agents/plan-reviewer.md; FL=.claude/skills/fix-loop/SKILL.md
CRS=scripts/claude/code-review.sh

# 判定本体: sec <ファイル> <開始行の前方一致> <終了行の正規表現> <必須の語...>
#   開始行から、終了行の正規表現に一致する行の手前までを「節」とし、必須の語が全部あれば exit 0
cat > "$TMP/sec.py" <<'PY'
import re, sys
path, head, end_re, *words = sys.argv[1:]
lines = open(path, encoding="utf-8").read().split("\n")
start = next((i for i, l in enumerate(lines) if l.startswith(head)), None)
if start is None:
    print(f"開始行が無い: {head}"); sys.exit(1)
end = next((i for i in range(start + 1, len(lines)) if re.match(end_re, lines[i])), len(lines))
body = "\n".join(lines[start:end])
miss = [w for w in words if w not in body]
if miss:
    print(f"節に無い語: {miss}"); sys.exit(1)
PY
# 節の中のバッククォートのパス（`/` を含むもの。<…>・*・{・空白・: を含むもの、`/` で始まるスラッシュコマンド、
# `origin/` で始まる git の参照は除く）が実在するか
cat > "$TMP/paths.py" <<'PY'
import os, re, sys
path, head, end_re = sys.argv[1:4]
lines = open(path, encoding="utf-8").read().split("\n")
start = next((i for i, l in enumerate(lines) if l.startswith(head)), None)
if start is None:
    print(f"開始行が無い: {head}"); sys.exit(1)
end = next((i for i in range(start + 1, len(lines)) if re.match(end_re, lines[i])), len(lines))
bad = []
for p in re.findall(r"`([^`]+)`", "\n".join(lines[start:end])):
    if any(c in p for c in "<>*{ :") or "/" not in p or p.startswith(("http", "-", "/", "origin/")):
        continue
    if not os.path.exists(p.rstrip("/")):
        bad.append(p)
if bad:
    print(f"実在しないパス: {bad}"); sys.exit(1)
PY
# 集合の一致: path_risk_trigger の case 行 ＝ code-reviewer.md ＝ plan-reviewer.md の例外の行
cat > "$TMP/sets.py" <<'PY'
import re, sys
crs, cr, pr = sys.argv[1:4]
src = open(crs, encoding="utf-8").read().split("\n")
case = [l for l in src if re.match(r"^\s+\.github/\*\|", l)]
if len(case) != 1:
    print(f"case 行が 1 行でない: {len(case)}"); sys.exit(1)
path_set = set(case[0].strip().split(")")[0].split("|"))
def md_set(f):
    rows = [l for l in open(f, encoding="utf-8").read().split("\n")
            if l.startswith("- 【harness 固有】GitHub から復旧できない例外")]
    if len(rows) != 1:
        print(f"{f}: 例外の行が 1 行でない: {len(rows)}"); sys.exit(1)
    return set(re.findall(r"`([^`]+)`", rows[0].split("（正は")[0]))
a, b = md_set(cr), md_set(pr)
if not (path_set == a == b):
    print(f"不一致: path={sorted(path_set)} code-reviewer={sorted(a)} plan-reviewer={sorted(b)}"); sys.exit(1)
PY
sec() { python3 "$TMP/sec.py" "$@" >/dev/null 2>&1; echo $?; }
paths() { python3 "$TMP/paths.py" "$@" >/dev/null 2>&1; echo $?; }
sets() { python3 "$TMP/sets.py" "$@" >/dev/null 2>&1; echo $?; }
absent() { # absent <ファイル...> -- <語...> : どのファイルにもどの語も無ければ 0
  local files=() w f
  while [ "$1" != "--" ]; do files+=("$1"); shift; done; shift
  for w in "$@"; do for f in "${files[@]}"; do grep -qF -- "$w" "$f" && { echo 1; return; }; done; done
  echo 0
}

pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'PASS %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL %s expected=%s got=%s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

H_SK="## 3."; E_H2='^## '
H_RR="## 高リスク変更の敵対的レビューステージ"
H_AR_SCOPE="## 守る範囲"; H_AR_TOOL="## ツール境界"
H_CR="## 高リスク判定の条件"; E_CR='^(## |---)'
H_P8="### P8."; E_H3='^(### |## |---)'
H_FL="3) 対応方法"; E_FL='^3\.5\)'

D1_WORDS=('15 分' '攻め筋は 1 体 3 本' '1 周 3 体' 'イシュー全体で 2 周' 'REVIEWED_COMMIT' 'ROUNDS:' '{REVIEW_BASE}'
          'run_in_background' 'sleep 900' 'TaskStop' 'task_id' '時間切れ' '行が無い記録')
OLD_WORDS=('最大 3 周' '総数 15' 'loop-until-dry' '動的観点' '最大 5 エージェント')
D3_WORDS=('種類ごと' '止める場所・方式の見直し')
D4_WORDS=('{REVIEW_BASE}' '攻め筋は最大 3 本' '12 分' '15 分' 'ulimit -v' 'timeout 60' '処理量の欠陥')
D4_SCOPE_WORDS=('普通の書き方による事故' 'わざと回避する書き方' 'Low' '件数に数えない' 'danger-ops.md')
D5_WORDS=('GitHub が最後の守り' 'danger-ops.md' 'path_risk_trigger' '.github/*' '.pre-commit-config.yaml' '.secrets.baseline'
          'scripts/claude/hooks/pretooluse_guard.py' '.claude/settings.json' '.claude/settings.local.json')
D7_WORDS=('新しい安全装置' '復旧' '最後の守り' 'danger-ops.md' 'I179 retro P1')
D9_WORDS=('認証・認可・ロール変更' 'マルチテナント境界変更' '管理画面追加・変更' 'ファイルアップロード/ダウンロード'
          '外部公開API追加・変更' 'Webhook・外部API連携' '個人情報・機微情報の新規取り扱い'
          '未成年データ・個人情報のテナント越境・目的外利用' 'DBスキーマ重要変更' '既存事故の再発リスクが高い変更'
          '画面制御していてもAPI直叩きで事故りうる変更' '【harness 固有・Yes にしない】')
D10_PHRASE='計画レビューのやり直しは、計画の方式・範囲・受け入れ条件を変えたときだけ'

ck "D1 SKILL §3 に上限・止め方・周回の数え方" 0 "$(sec "$SK" "$H_SK" "$E_H2" "${D1_WORDS[@]}")"
ck "D2 SKILL・review-rules に旧上限の語が無い" 0 "$(absent "$SK" "$RR" -- "${OLD_WORDS[@]}")"
ck "D3 SKILL §3 に種類別集計と方式見直し" 0 "$(sec "$SK" "$H_SK" "$E_H2" "${D3_WORDS[@]}")"
ck "D3 review-rules に種類別集計と方式見直し" 0 "$(sec "$RR" "$H_RR" "$E_H2" "${D3_WORDS[@]}")"
if r=0; for w in "${D4_WORDS[@]}"; do grep -qF -- "$w" "$AR" || r=1; done; [ "$r" -eq 0 ]; then d4=0; else d4=1; fi
ck "D4 adversarial-reviewer に上限・資源の上限" 0 "$d4"
ck "D4 adversarial-reviewer に守る範囲（A10）" 0 "$(sec "$AR" "$H_AR_SCOPE" "$E_H2" "${D4_SCOPE_WORDS[@]}")"
ck "D5 review-rules に前提・例外の一覧" 0 "$(sec "$RR" "$H_RR" "$E_H2" "${D5_WORDS[@]}")"
ck "D6 例外の集合が 3 か所で一致" 0 "$(sets "$CRS" "$CR" "$PR")"
ck "D7 fix-loop 手順 3 に安全装置を足す前の確認" 0 "$(sec "$FL" "$H_FL" "$E_FL" "${D7_WORDS[@]}")"
ck "D7 plan-reviewer P8 に安全装置を足す前の確認" 0 "$(sec "$PR" "$H_P8" "$E_H3" "${D7_WORDS[@]}")"
ck "D8 新しい節のパスが実在（SKILL §3）" 0 "$(paths "$SK" "$H_SK" "$E_H2")"
ck "D8 新しい節のパスが実在（review-rules）" 0 "$(paths "$RR" "$H_RR" "$E_H2")"
ck "D8 新しい節のパスが実在（adversarial 守る範囲）" 0 "$(paths "$AR" "$H_AR_SCOPE" "$E_H2")"
ck "D8 新しい節のパスが実在（adversarial ツール境界）" 0 "$(paths "$AR" "$H_AR_TOOL" "$E_H2")"
ck "D9 code-reviewer のアプリ条件が残り・Yes にしない行がある" 0 "$(sec "$CR" "$H_CR" "$E_CR" "${D9_WORDS[@]}")"
ck "D9 code-reviewer に旧 harness 条件が無い" 0 "$(absent "$CR" -- '【harness 固有】hooks・ガード・権限設定・レビュー基盤' '【harness 固有】指示階層')"
ck "D10 review-rules に計画レビューのやり直しの条件" 0 "$(sec "$RR" "$H_RR" "$E_H2" "$D10_PHRASE")"

# ---- 偽合格の防止（複製に注入して当てる） ----
inject() { # inject <src> <dst> <python の置換式: s を書き換える>
  python3 - "$1" "$2" "$3" <<'PY'
import sys
src, dst, expr = sys.argv[1:4]
s = open(src, encoding="utf-8").read()
t = eval(expr, {"s": s})
if t == s:
    sys.exit(3)   # 注入が起きなかった＝FG 自体が無効
open(dst, "w", encoding="utf-8").write(t)
PY
}
fg() { # fg <name> <src> <dst> <expr> <検査コマンド...> : 注入が起き、検査が非ゼロなら PASS
  local name="$1" src="$2" dst="$3" expr="$4"; shift 4
  if ! inject "$src" "$dst" "$expr"; then ck "$name（注入が起きた）" ok ng; return; fi
  ck "$name" 1 "$("$@")"
}
fg "FG-D1 sleep 900 を消すと D1 不合格" "$SK" "$TMP/sk1.md" 's.replace("sleep 900", "")' \
   sec "$TMP/sk1.md" "$H_SK" "$E_H2" "${D1_WORDS[@]}"
fg "FG-D2 最大 3 周 を足すと D2 不合格" "$RR" "$TMP/rr2.md" 's + "\n最大 3 周\n"' \
   absent "$SK" "$TMP/rr2.md" -- "${OLD_WORDS[@]}"
fg "FG-D3 方式見直しを消すと D3 不合格" "$RR" "$TMP/rr3.md" 's.replace("止める場所・方式の見直し", "")' \
   sec "$TMP/rr3.md" "$H_RR" "$E_H2" "${D3_WORDS[@]}"
fg "FG-D4 件数に数えない を消すと D4 不合格" "$AR" "$TMP/ar4.md" 's.replace("件数に数えない", "")' \
   sec "$TMP/ar4.md" "$H_AR_SCOPE" "$E_H2" "${D4_SCOPE_WORDS[@]}"
if inject "$AR" "$TMP/ar4b.md" 's.replace("ulimit -v", "")'; then
  if r=0; for w in "${D4_WORDS[@]}"; do grep -qF -- "$w" "$TMP/ar4b.md" || r=1; done; [ "$r" -eq 0 ]; then g=0; else g=1; fi
  ck "FG-D4 ulimit -v を消すと D4 不合格" 1 "$g"
else ck "FG-D4 ulimit -v を消すと D4 不合格（注入が起きた）" ok ng; fi
fg "FG-D5 .secrets.baseline を消すと D5 不合格" "$RR" "$TMP/rr5.md" 's.replace(".secrets.baseline", "")' \
   sec "$TMP/rr5.md" "$H_RR" "$E_H2" "${D5_WORDS[@]}"
# shellcheck disable=SC2016  # 置換式のバッククォートはリテラル（展開させない）
fg "FG-D6 code-reviewer の例外から .github/* を消すと D6 不合格" "$CR" "$TMP/cr6.md" \
   's.replace("`.github/*`・", "", 1)' sets "$CRS" "$TMP/cr6.md" "$PR"
# shellcheck disable=SC2016
fg "FG-D6 plan-reviewer の例外に CLAUDE.md を足すと D6 不合格" "$PR" "$TMP/pr6.md" \
   's.replace("`.claude/settings.local.json`（正は", "`.claude/settings.local.json`・`CLAUDE.md`（正は", 1)' \
   sets "$CRS" "$CR" "$TMP/pr6.md"
fg "FG-D7 fix-loop の追加項目を消すと D7 不合格" "$FL" "$TMP/fl7.md" 's.replace("I179 retro P1", "")' \
   sec "$TMP/fl7.md" "$H_FL" "$E_FL" "${D7_WORDS[@]}"
# shellcheck disable=SC2016
fg "FG-D8 存在しないパスを足すと D8 不合格" "$SK" "$TMP/sk8.md" \
   's.replace("## 3.", "## 3.\n\n`docs/runbooks/no_such_file.md`\n", 1)' paths "$TMP/sk8.md" "$H_SK" "$E_H2"
fg "FG-D9 マルチテナント境界変更を消すと D9 不合格" "$CR" "$TMP/cr9.md" 's.replace("マルチテナント境界変更", "")' \
   sec "$TMP/cr9.md" "$H_CR" "$E_CR" "${D9_WORDS[@]}"
fg "FG-D10 やり直しの条件を消すと D10 不合格" "$RR" "$TMP/rr10.md" "s.replace('$D10_PHRASE', '')" \
   sec "$TMP/rr10.md" "$H_RR" "$E_H2" "$D10_PHRASE"

printf -- '---\npass=%s fail=%s\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
