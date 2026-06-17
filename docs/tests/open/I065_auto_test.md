# I065 自動テスト

- **関連イシュー**: #131
- **計画書**: docs/plans/open/plan_I065.md
- **対象**: `.claude/skills/close/SKILL.md` / `docs/runbooks/review-rules.md` / 既存 timestamped 監査記録の遡及整理（I054〜I064）
- **テスト戦略**: ① grep/静的存在確認（手順・記述・スクリプト不変）、② sandbox での回収＋リンク更新ロジックの振る舞いスモーク、③ 遡及整理後の件数保存・リンク健全性の機械検証。

## 実行方法（重要）
シェルロジックを含む TC は**スクリプトファイルとして `bash` 実行**する。

> ⚠️ 対話シェルへ直接コマンドを貼り付けないこと。Claude Code の対話シェルでは `grep` が同梱 `ugrep` ラッパーに上書きされ `-E`/`-o` パイプが誤動作する。`bash script.sh` のサブプロセスでは実 GNU grep が使われる。各 TC の期待終了コード: **0**。

---

## 1. 静的/grep 存在確認（実装後）

| TC | 対象 | 期待（ヒットする趣旨／値） | 実施者 | 実結果 |
|---:|------|----------------------------|--------|--------|
| TC-01 | `.claude/skills/close/SKILL.md` | step 1 に「直下 timestamped 監査記録を `closed/` へ `git mv` する」回収手順と、対応 plan の `## レビュー結果` リンクを `../../reviews/closed/` 向きに `sed` 更新する手順が存在する（glob `I${ISSUE_NUM}_*_review_*.md` を含む） | Claude | 未実行 |
| TC-02 | `docs/runbooks/review-rules.md` | `:27-29` の監査記録3行の備考が「移動しない」ではなく「`/close` が当該 issue 分を `closed/` へ回収（I065）」相当のライフサイクル記述になっている | Claude | 未実行 |
| TC-03 | `docs/runbooks/review-rules.md` | `:38` 相当の文が「直下に蓄積し `/close` が `closed/` へ回収」に更新され、「移動しない」と断定する旧文言が残っていない | Claude | 未実行 |
| TC-07 | `scripts/claude/{code-review,plan-issue-review,issue-review}.sh` | `REVIEW_FILE=` が `docs/reviews/${ISSUE}_..._review_${TIMESTAMP}.md`（直下）のまま**不変**。`docs/reviews/closed/` や `open/` へ保存先変更していない（案A・I062 非衝突） | Claude | 未実行 |

検証スクリプト例（`/tmp/i065_static.sh`）:
```bash
#!/usr/bin/env bash
set -u; cd /mnt/c/app/study-app-multitenant; fail=0
# TC-01
grep -qE 'I\$\{ISSUE_NUM\}_\*_review_\*\.md' .claude/skills/close/SKILL.md && \
  grep -q 'reviews/closed/' .claude/skills/close/SKILL.md || { echo "TC-01 NG"; fail=1; }
# TC-02/03: 旧断定文言「移動しない」が監査記録の文脈から消えていること
if grep -nE 'timestamped|監査記録' docs/runbooks/review-rules.md | grep -q '移動しない'; then
  echo "TC-02/03 NG（旧『移動しない』記述が残存）"; fail=1; fi
grep -q '回収' docs/runbooks/review-rules.md || { echo "TC-02/03 NG（回収記述なし）"; fail=1; }
# TC-07: スクリプト保存先不変
for s in code-review plan-issue-review issue-review; do
  grep -qE 'REVIEW_FILE="docs/reviews/\$\{ISSUE\}_.*review_\$\{TIMESTAMP\}\.md"' "scripts/claude/${s}.sh" \
    || { echo "TC-07 NG: ${s}.sh 保存先変化"; fail=1; }
done
[ "$fail" = 0 ] && echo "STATIC PASS" || exit 1
```

---

## 2. 振る舞いスモーク（sandbox）

| TC | シナリオ | 期待 | 実施者 | 実結果 |
|---:|----------|------|--------|--------|
| TC-S1 | 一時ディレクトリに擬似 `docs/reviews/I999_code_review_20260101_0000.md`（timestamped）・`docs/reviews/I999_review.md`（lifecycle）・`docs/plans/closed/plan_I999.md`（`](../../reviews/I999_code_review_20260101_0000.md)` リンク入り）を作り、`/close` 回収ロジックと同型のコードを実走する。期待: ① timestamped 記録が `docs/reviews/closed/` へ移動、② plan リンクが `../../reviews/closed/I999_code_review_20260101_0000.md` に更新、③ `I999_review.md`（lifecycle）は**移動されず**直下に残る（glob 非マッチ）。終了コード 0 | Claude | 未実行 |

検証スクリプト例（`/tmp/i065_smoke.sh`）— sandbox は git 不要のため `mv` で同型検証:
```bash
#!/usr/bin/env bash
set -eu
T="$(mktemp -d)"; mkdir -p "$T/docs/reviews/closed" "$T/docs/plans/closed"
touch "$T/docs/reviews/I999_code_review_20260101_0000.md"
touch "$T/docs/reviews/I999_review.md"   # lifecycle: 移動されてはならない
printf '## レビュー結果\n- [20260101_0000 ✅](../../reviews/I999_code_review_20260101_0000.md)\n' \
  > "$T/docs/plans/closed/plan_I999.md"
cd "$T"; ISSUE_NUM=999
for f in docs/reviews/I${ISSUE_NUM}_*_review_*.md; do
  [ -f "$f" ] || continue
  base="$(basename "$f")"
  mv "$f" docs/reviews/closed/
  PLAN="docs/plans/closed/plan_I${ISSUE_NUM}.md"
  [ -f "$PLAN" ] && sed -i "s#(\.\./\.\./reviews/${base})#(../../reviews/closed/${base})#g" "$PLAN"
done
# 検証
[ -f docs/reviews/closed/I999_code_review_20260101_0000.md ] || { echo "TC-S1 NG: 未移動"; exit 1; }
[ -f docs/reviews/I999_review.md ] || { echo "TC-S1 NG: lifecycle が消えた"; exit 1; }
[ ! -f docs/reviews/closed/I999_review.md ] || { echo "TC-S1 NG: lifecycle を誤回収"; exit 1; }
grep -q 'reviews/closed/I999_code_review_20260101_0000.md' docs/plans/closed/plan_I999.md \
  || { echo "TC-S1 NG: リンク未更新"; exit 1; }
echo "TC-S1 PASS"; rm -rf "$T"
```

---

## 3. 遡及整理の事後検証（実装後・実 repo）

| TC | 期待値 | 実施者 | 実結果 |
|---:|--------|--------|--------|
| TC-04 | 遡及移動後、不変量を機械検証: ① 直下（`docs/reviews/*.md`）に残るのは **open issue（`docs/issues/open/` に存在する番号）の記録のみ**。② 総数（直下+`closed/`）が移動前後で**保存**。参考値（2026-06-17 develop ベース）: 直下 64→**3**、`closed/` 53→**114**、総数 **117** で一定。**実装直前に `wc -l` で基準値（BEFORE_ROOT/BEFORE_CLOSED）を再取得し、他イシューの close/レビュー実行で増減があれば期待値を再算出する** | Claude | 未実行 |
| TC-05 | 移動後、I054〜I064 の `docs/plans/closed/plan_I###.md` 内 `](../../reviews/I###_..._review_<ts>.md)` リンクがすべて `](../../reviews/closed/...)` を指し、リンク先実ファイルが `test -f` で存在（デッドリンクゼロ） | Claude | 未実行 |
| TC-06 | 遡及 `git mv` 時、移動先 `docs/reviews/closed/` に同名ファイルが既存せず衝突ゼロ（移動が61件すべて成功） | Claude | 未実行 |

> **基準値の再取得（必須）**: TC-04 の参考値（3 / 114 / 117）は固定値ではない。**遡及移動の直前**に
> `BEFORE_ROOT=$(ls docs/reviews/*.md | wc -l)` / `BEFORE_CLOSED=$(ls docs/reviews/closed/*.md | wc -l)` を控え、
> 「総数 = `BEFORE_ROOT + BEFORE_CLOSED` が移動後も一定」かつ「直下に残るのは open issue 記録のみ」を不変量として検証する。
> open issue 集合・期待件数はハードコードせず `docs/issues/open/` から動的に導出する。

検証スクリプト例（`/tmp/i065_retro_verify.sh`・**実装後**実行。移動前の総数 `$EXPECTED_TOTAL` を引数で渡す）:
```bash
#!/usr/bin/env bash
set -u; cd /mnt/c/app/study-app-multitenant; fail=0
EXPECTED_TOTAL="${1:-117}"   # 移動直前に控えた BEFORE_ROOT+BEFORE_CLOSED を渡す（既定は参考値117）
root=$(ls docs/reviews/*.md 2>/dev/null | wc -l)
closed=$(ls docs/reviews/closed/*.md 2>/dev/null | wc -l)
# TC-04-①: 総数保存（記録の消失なし）
[ "$((root + closed))" = "$EXPECTED_TOTAL" ] || { echo "TC-04 NG: 総数=$((root+closed))（期待$EXPECTED_TOTAL）"; fail=1; }
# TC-04-②: 直下に残るのは open issue（issues/open）の記録のみ（番号を動的導出）
OPEN_RE="$(ls docs/issues/open/ | grep -oE 'I[0-9]{3}' | sort -u | paste -sd'|' -)"
for f in docs/reviews/*.md; do
  n="$(basename "$f" | grep -oE 'I[0-9]{3}')"
  echo "$n" | grep -qE "^(${OPEN_RE})$" || { echo "TC-04 NG: 直下に非-open 記録が残存: $f"; fail=1; }
done
# TC-05: closed plan の reviews リンク先がすべて実在
for p in docs/plans/closed/plan_I054.md docs/plans/closed/plan_I055.md docs/plans/closed/plan_I057.md \
         docs/plans/closed/plan_I058.md docs/plans/closed/plan_I059.md docs/plans/closed/plan_I060.md \
         docs/plans/closed/plan_I061.md docs/plans/closed/plan_I062.md docs/plans/closed/plan_I063.md \
         docs/plans/closed/plan_I064.md; do
  while read -r rel; do
    tgt="docs/plans/closed/$rel"; norm="$(cd "$(dirname "$tgt")" && pwd)/$(basename "$rel")"
    [ -f "$norm" ] || { echo "TC-05 NG: デッドリンク $p -> $rel"; fail=1; }
  done < <(grep -oE '\.\./\.\./reviews/[A-Za-z0-9_/.]+_review_[0-9_]+\.md' "$p")
done
[ "$fail" = 0 ] && echo "RETRO PASS" || exit 1
```

> TC-05 のリンク解決は `../../reviews/closed/...` を含む形で `test -f` する。移動漏れ（`closed/` 無しの旧リンク）があれば実ファイル不在で NG。

---

## 実行結果（実装後に追記）
- （未実行）
