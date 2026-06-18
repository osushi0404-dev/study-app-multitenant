# plan_I066: レビュー自動化の高リスク判定多行対応・計画書追記の冪等化

## 基本情報
- **計画書ID**: plan_I066
- **関連イシュー**: #134
- **Draft PR**: #138
- **作成根拠資料**: docs/issues/open/I066.md（起点イシュー・2026-06-18 再スコープ済み）
- **実装後評価**: docs/reviews/open/I066_review.md
- **作成日**: 2026-06-18

---

## 1. 背景/目的

`plan-issue-review.sh`（プランレビュー自動化スクリプト）に、一度もテストで守られていなかったために silent に機能不全を起こしている分岐が 2 つ残っている。I062 が VERDICT 一次判定を導入し、I065 が dated review のアーカイブを案A（`closed/` 回収）で解決した今、本イシューは**残された 2 つの分岐（#1・#3）を補修し、ユニットテストで固定**する。

### 再スコープの経緯（重要）
- 起票時（grill-me 含む）は I065 より前で、問題 #2（dated review のアーカイブ整合）を本イシューで案C（`docs/reviews/runs/` 集約）で解決する前提だった。
- しかし **I065（PR #137）が 2026-06-17 にマージ済み**で、#2 を **案A（`/close` が issue 単位で `docs/reviews/closed/` へ回収）** で既に解決している（I065 は grill-me で案B/案C を明示的に却下）。
- → **grill-me メモ Q1/Q2（案C=runs/）は古いため破棄**。#2 は本イシュー対象外（I065 達成済み）。Q3（追記冪等化）は #2 と独立で有効。
- 本イシューの実スコープ = **#1（高リスク保険の多行対応）・#3（計画書追記の冪等化）・#4（テスト固定）**。

### 対象の問題
1. **#1 高リスク保険判定の空振り（silent・最も危険）**
   - `detect_plan_verdict()`（`plan-issue-review.sh:34`）の保険経路 `grep -qiE "高リスク判定.*Yes"` は**行単位**マッチ。実レビュー出力は `## 高リスク判定`（見出し行）と `判定: Yes`/`No`（次行）が**別行**のため、保険経路は常に空振り。
   - I062 の VERDICT 一次判定（`VERDICT: HIGHRISK` 行）で新形式は救済済みだが、**VERDICT 行を持たない旧形式**では `/security-review` 案内が出ず `/implement` 直行する。
3. **#3 計画書追記の非冪等性**
   - `plan-issue-review.sh:99-103` は実行ごとに `## レビュー結果` 見出し＋リンク行を**新規追記**するため、同一イシューで再実行すると見出しが重複する（例: `plan_I062.md` に 3 重複が実在）。

---

## 2. 調査結果

### 環境前提確認
- `bash` `/usr/bin/bash`、`awk` = **GNU Awk 5.2.1**、`grep` `/usr/bin/grep`、`git`、`gh` いずれも存在。新規インストール不要。
- 検証は **bash でスクリプトをファイル実行**して行う（対話シェルの `grep` は同梱 ugrep ラッパーで `-E/-o` が誤動作するため。`reference_interactive_shell_grep_wrapper` 既知事項）。

### 既存テストのベースライン（分岐元 develop = I065 込み）
```
bash scripts/claude/tests/test_review_verdict.sh
→ PASS=44 FAIL=1
→ FAIL TC-05  expected[BLOCKER] got[OK]
```
- **TC-05 が現在 FAIL**。原因 = `test_review_verdict.sh:19` の `REAL_BOLD_BLOCKER="docs/reviews/I060_code_review_20260612_0045.md"` がハードコードした flat パスを、**I065 の遡及移動（commit `07dfa91`）が `docs/reviews/closed/` へ動かした**ため。`detect_code_verdict` が存在しないファイルに対し空文字→`OK` を返し BLOCKER と不一致。
- TC-12（`ck_false`）は「存在しないファイルに grep 非マッチ」で**偶然 PASS している**（理由が誤り）。fixture 解決で両者を是正する。
- → I062 の `find_*`/判定系・I065 の close 回収には**機能的回帰なし**。FAIL は fixture パスのみ。

### 修正アプローチの事前検証（実行済み・全 PASS=8）
`/tmp/i066_validate.sh` を bash 実行し、修正ロジックを実証した（結果は `I066_auto_test.md` 調査結果欄に記録）:
- **#1**: 旧 `grep -qiE "高リスク判定.*Yes"` は多行 fixture（`## 高リスク判定`＋次行 `判定: Yes`）に**空振り（非ゼロ）= バグ確認**。新 `awk` 範囲検出は Yes→検出 / No→非検出 / 別セクションの `判定: Yes`→非検出（アンカリング）。
- **#3**: 旧追記を 2 回で `## レビュー結果` 見出し**2 個（バグ確認）**。新冪等追記は 2〜3 回でも見出し**1 個維持・リンク行は履歴保持**。
- **fixture**: TC-05/TC-12 を合成太字 fixture（`| **Blocker** | ... |`・VERDICT 行なし）に置換すると `detect_code_verdict=BLOCKER`・旧プレーン grep `^\| Blocker \|` 非マッチを hermetic に固定できる（`bash /tmp/i066_fixture_ideal.sh` で **PASS=2** 実証済み）。実ファイル依存を撤去して移動破損を根治。

### レビュー出力の実書式（plan-reviewer 契約）
`.claude/review-agents/plan-reviewer.md`（215-216 行）および実出力（`docs/reviews/closed/I062_plan_review_*.md`）で確認:
```
## 高リスク判定
判定: Yes / No
該当条件: ...
```
- 見出しと判定行は別行。BLOCKER 用の `## 判定: 差し戻し / ✅ 完了` 見出しは別セクション（高リスク判定ブロック外）。

### 参照先実在性
- 本イシューが触るパスは `plan-issue-review.sh` / `test_review_verdict.sh` の 2 ファイルのみ（実在確認済み）。TC-05 fixture の不在参照は上記の通り是正対象。

---

## 3. 影響範囲
- **Backend**: なし
- **Frontend**: なし
- **DB**: なし
- **Config/Infra**: `scripts/claude/plan-issue-review.sh`（#1 判定・#3 追記）/ `scripts/claude/tests/test_review_verdict.sh`（#4 TC・fixture 是正）の 2 ファイルのみ。
- **依存関係ファイル**: requirements/package 変更なし → Dockerfile / docker-compose への波及なし。
- **非対象（再スコープで除外）**: `code-review.sh` / `.claude/skills/close/SKILL.md` / `docs/reviews/` の移動（I065 達成済み・案C 破棄）。

---

## 4. 変更点一覧

### 4-1. `scripts/claude/plan-issue-review.sh`

**(#1) `detect_plan_verdict()` の保険経路を多行対応にする（34 行目）**

修正方針: VERDICT 一次判定（31-32 行）と差し戻し判定（33 行）は**そのまま維持**。保険経路（34 行）の行単位 grep を、`## 高リスク判定` 見出しから次の `## ` 見出しまでのブロック内で `判定: Yes`（末尾アンカー）を検出する `awk` 範囲指定に置換する。

```bash
# 変更前（34 行目・行単位 grep で多行に空振り）
if grep -qiE "高リスク判定.*Yes" "$file"; then echo "HIGHRISK"; return; fi

# 変更後（## 高リスク判定 ブロック内の「判定: Yes」を範囲検出）
if awk '
  /^## 高リスク判定/ { inblock=1; next }
  /^## /            { inblock=0 }
  inblock && /^判定:[[:space:]]*Yes[[:space:]]*$/ { found=1 }
  END { exit(found?0:1) }
' "$file"; then echo "HIGHRISK"; return; fi
```
- 判定の優先順位は不変: `VERDICT 行` > `差し戻し（BLOCKER）` > `高リスク（HIGHRISK）` > `OK`。
- アンカー `^判定:[[:space:]]*Yes[[:space:]]*$` で `判定: No` や他セクションの `判定: Yes` を誤検出しない（`reference_string_token_match_anchoring` 準拠）。
- 高リスク判定が最終セクションでも、次の `## ` が無いため EOF まで `inblock=1` を維持し検出可。

**(#3) 計画書追記を `append_review_link()` 関数へ抽出し冪等化（99-103 行目）**

修正方針: source ガード（39 行）より**前**に `append_review_link()` を定義（既存 `detect_*`/`find_*` と同じテスト可能パターン）。既存の `## レビュー結果` セクションがあれば**リンク行のみ**を見出し直後に挿入（単一セクション維持・履歴保持＝grill-me Q3）、無ければ見出し＋リンク行を新規追記する。本体（99-103 行）は同関数呼び出しに置換する。

```bash
# source ガード前に追加（関数定義）
# 計画書の「## レビュー結果」へリンク行を冪等追記（重複見出しを作らない・履歴保持）
append_review_link() {
  local plan="$1" ts="$2" verdict="$3" base="$4"
  local line="- [${ts} ${verdict}](../../reviews/${base})"
  if grep -q '^## レビュー結果$' "$plan"; then
    local tmp="${plan}.tmp"
    # LINE を環境変数で渡し ENVIRON で読む（awk -v のバックスラッシュ エスケープ解釈を回避）
    if LINE="$line" awk 'BEGIN{l=ENVIRON["LINE"]} {print} /^## レビュー結果$/ && !d {print l; d=1}' \
         "$plan" > "$tmp"; then
      mv "$tmp" "$plan"
    else
      rm -f "$tmp"; return 1   # awk 失敗時は一時ファイルを残さない
    fi
  else
    printf '\n## レビュー結果\n%s\n' "$line" >> "$plan"
  fi
}
```
> plan-review 反映: `awk -v` は値中の `\` をエスケープ解釈するため、`VERDICT`（`grep -o '判定:.*'` 由来）に `\` が混入すると link 行が壊れうる（Warning/BP）。`ENVIRON["LINE"]` 経由で受け取りエスケープ解釈を排除（`bash /tmp/i066_environ.sh` で `\textbf` 保持を実証）。awk 失敗時は `rm -f` で一時ファイル残留を防ぐ（Info/BP）。
```bash
# 変更後の本体（99-103 行）
if [ -f "$PLAN_FILE" ]; then
  VERDICT=$(grep -o '判定:.*' "$REVIEW_FILE" | head -1 || echo "完了")
  append_review_link "$PLAN_FILE" "$TIMESTAMP" "$VERDICT" "$(basename "$REVIEW_FILE")"
fi
```
- 生成するリンク形式 `../../reviews/<basename>` は不変 → I065 の `/close` が行う `closed/` 向けリンク書き換え（`sed`）と非衝突。

### 4-2. `scripts/claude/tests/test_review_verdict.sh`

**(TC-05/TC-12 fixture 是正・19/79/85 行目)** 外部の実ファイル依存（`REAL_BOLD_BLOCKER`）を**撤去**し、合成 hermetic fixture に置換する。I065 のようなファイル移動・削除・編集に不変化し、今回 FAIL の根本（外部ファイル依存）を根治する。既存 `TC-04c`/`TC-09` と同じ合成太字 fixture 様式に統一:
```bash
# 撤去（19 行目）: 実ファイルへのハードコード依存
# REAL_BOLD_BLOCKER="docs/reviews/I060_code_review_20260612_0045.md"

# TC-05（合成・VERDICT 行なしの太字 Blocker → 保険経路で BLOCKER 検出）
printf '| **Blocker** | 説明 |\n指摘あり\n' > "$TMP/c5"
ck TC-05 BLOCKER "$(detect_code_verdict "$TMP/c5")"
# TC-12（バグ固定・旧プレーン grep が太字 Blocker に非マッチ）
ck_false TC-12-old-grep-nonmatch grep -qE '^\| Blocker \|' "$TMP/c5"
```

**(#1 TC 追加)** 多行高リスク保険判定の回帰（detect_plan_verdict は VERDICT 行が無い fixture を使用）:
- TC-24: `## 高リスク判定`＋次行 `判定: Yes`（VERDICT 無し）→ `HIGHRISK`
- TC-25: 同形式で `判定: No` → `OK`
- TC-26: アンカリング — 高リスク判定ブロックは `判定: No`、別セクション `## その他` に `判定: Yes` → `OK`（誤検出しない）
- TC-27: バグ固定 — 旧 `grep -qiE "高リスク判定.*Yes"` が多行 Yes fixture に**非マッチ**（`ck_false`）

**(#3 TC 追加)** 冪等追記の回帰（`append_review_link` を source して検証）:
- TC-28: `declare -F append_review_link`（関数定義の存在）
- TC-29: `## レビュー結果` を含まない plan に **2 回**追記 → 見出しは**1 個**
- TC-30: TC-29 と同一 fixture（2 回呼び出し後）→ リンク行（`^- \[`）は**2 個**（履歴保持）
- TC-31: 見出しが無い plan への**初回（1 回）**追記 → 見出し＋リンク行が 1 組生成（TC-29 との差分は呼び出し回数のみ）

> 注: TC 番号は既存（TC-01〜TC-23）に継続。`append_review_link` は `PLAN_REVIEW` の source（既存 42 行）で取り込まれる。

---

## 5. 実装手順（ステップ）

各ステップは「ロジック修正＋それを固定する TC」を縦に貫通する垂直スライス。検証は各 TC で行い、本文には検証コマンドを書かない（→ 該当 TC 参照）。

- **ステップ 1: テスト基盤の回復（TC-05/TC-12 の hermetic 化）**
  - `test_review_verdict.sh` の `REAL_BOLD_BLOCKER` 実ファイル依存（19 行）を撤去し、TC-05/TC-12 を合成太字 fixture（VERDICT 行なし）に置換（4-2）。外部ファイル移動に不変化し、現在の FAIL を根治する。後続 TC 追加の土台。
  - 依存: なし（最初に実施）。
  - → TC-05 / TC-12 参照。

- **ステップ 2: #1 高リスク保険判定の多行対応**
  - `plan-issue-review.sh` の `detect_plan_verdict()` 34 行を `awk` 範囲検出に置換（4-1 #1）。
  - 同時に `test_review_verdict.sh` へ TC-24〜TC-27 を追加。
  - 依存: ステップ 1 完了後（クリーンなベースライン上で追加）。
  - → TC-24 / TC-25 / TC-26 / TC-27 参照。

- **ステップ 3: #3 計画書追記の冪等化**
  - `plan-issue-review.sh` に `append_review_link()` を source ガード前へ追加し、本体 99-103 行を関数呼び出しへ置換（4-1 #3）。
  - 同時に `test_review_verdict.sh` へ TC-28〜TC-31 を追加。
  - 依存: ステップ 1 完了後（ステップ 2 とは独立・並行可）。
  - → TC-28 / TC-29 / TC-30 / TC-31 参照。

- **ステップ 4: 全回帰とスクリプト健全性**
  - 全 TC（既存 + 新規）の総合実行とスクリプト構文の健全性を担保する。
  - 依存: ステップ 1〜3 完了が前提。
  - → TC-20（bash -n）/ 自動テスト文書「全体（FAIL=0）」参照。

---

## 6. テスト計画（自動/手動）
- **自動**: `docs/tests/open/I066_auto_test.md`。`test_review_verdict.sh` をユニットテストレベルで使用（関数 source 方式）。新規 TC-24〜TC-31 + 既存 TC-05/TC-12 是正 + 全回帰。認証/認可/テナント境界に関わる変更は無し（テスト不要）。
- **手動**: `docs/tests/open/I066_manual_test.md`。ファイル/コマンド確認は Claude 実行。実際の `/plan-issue-review` ライブ実走による end-to-end 確認は任意（LLM 実行コストを伴うため Human 判断）。
- **再発防止**: #1/#3 は本イシューで初めてユニットテストに載る（バグ固定 TC-27・冪等 TC-29/30 を含む）。

---

## 7. ロールバック
- 影響は bash スクリプト 2 ファイルのみ。`git revert` で PR 単位に戻せる。DB マイグレーション・データ変更・外部連携なし。
- 既存挙動への後方互換: VERDICT 一次判定・差し戻し・既存 TC は不変。追記リンク形式 `../../reviews/<base>` も不変（close の sed と非衝突）。

---

## 8. Risk & 回避策
- **R1: awk の `inblock` クリア漏れ**（高リスク判定が最終セクション/別の `## ` 見出し直後）。→ TC-24（最終想定）・TC-26（後続 `## ` でクリア）で固定。
- **R2: `append_review_link` の awk 値にメタ文字混入**。入力は全てスクリプト生成値（`TIMESTAMP`=date、`basename`=自前 REVIEW_FILE、`VERDICT`=自前エージェント出力の `判定:` 行）だが、`VERDICT` は LLM 出力由来のため `\` 混入はゼロではない。→ plan-review Warning を受け **`ENVIRON["LINE"]` 経由でエスケープ解釈を排除**（`-v` 不使用）。実証済み（`\textbf` 保持）。awk 失敗時は `rm -f` で一時ファイル残留を防止。
- **R3: 対話シェル grep ラッパーによる誤検証**。→ テストは必ず `bash scripts/claude/tests/test_review_verdict.sh` でファイル実行（既存 TC-23/runbook 既出の注意）。
- **R4: テストの外部ファイル依存による破損（今回 FAIL の根本）**。→ TC-05/TC-12 を合成 hermetic fixture に置換し、外部ファイルの移動・削除・編集に不変化する（既存 TC-04c/09 と同様式）。

---

## 9. セキュリティ・データ整合性・性能（該当性メモ）
- **セキュリティ影響**: 限定的。Backend/Frontend のコード変更なし。入力は全てスクリプト内部生成値で外部入力境界の追加なし（R2 参照）。OWASP/認証認可/機密データの新規取り扱いなし。shellcheck は pre-commit で実行（既存運用）。
- **P3（データ整合性）影響なし**: DB 変更なし。
- **P5（運用設計）影響なし**: 外部 API・非同期・バッチなし。
- **P6（性能・UX）影響なし**: UI なし・大量データ/外部 API 連携なし。
- **P8（コスト）影響なし**: 新規インフラ・外部サービス・依存追加なし。

---

## 設計判断の明示（イシュー明記 / 仮定の区別）
| 判断 | 区分 | 根拠 |
|------|------|------|
| #2（アーカイブ）は対象外・案C 破棄 | **ユーザー承認済み**（本会話で再スコープ合意） | I065 案A=closed/ がマージ済み・案B/C を I065 が明示却下 |
| #1 は VERDICT 一次を維持し保険のみ多行対応 | イシュー明記 | I066「VERDICT 一次経路は I062 実装済みのため保険のみ補修」 |
| #1 を `awk` 範囲検出で実装 | イシュー明記 | grill-me 補足「`awk` 範囲指定 / `grep -A` で検出」を awk で確定 |
| #3 は単一セクション維持・リンク行のみ追記 | イシュー明記 | grill-me Q3「(i) 単一セクション維持・リンク行のみ追記（履歴保持）」 |
| #3 を `append_review_link` 関数へ抽出 | **ユーザー承認済み** | 冪等ロジックを決定論ゲート（TC-29/30/31）で固定するため関数化（実行時挙動はインラインと同一） |
| TC-05/TC-12 を合成 hermetic fixture に置換（実ファイル依存撤去） | **ユーザー承認済み**（理想基準で再検討・確定） | 外部ファイル移動が FAIL の根本。合成化で根治し既存 TC-04c/09 と統一 |

---

## 承認ポイント（このチェックリストに OK で実装開始）
- [ ] 再スコープ（#2=案C 破棄・I065 案A 維持、本イシューは #1/#3/#4 に集中）で良い
- [ ] #1: `detect_plan_verdict` の保険経路を `awk` 範囲検出（4-1 #1）で多行対応する方針で良い（VERDICT 一次・差し戻し判定は不変）
- [ ] #3: `append_review_link` 関数へ抽出し、単一 `## レビュー結果` セクション維持・リンク行のみ追記（履歴は newest-first で残す）で良い
- [x] #4 + fixture 是正: `test_review_verdict.sh` に TC-24〜TC-31 追加・TC-05/TC-12 を合成 hermetic fixture に置換（実ファイル依存撤去）
- [ ] 影響範囲は `plan-issue-review.sh` / `test_review_verdict.sh` の 2 ファイルのみ・Danger Ops 無し・セキュリティ/P3/P5/P6/P8 影響なし、で良い
- [x] 設計判断 2 項目（`append_review_link` 関数抽出 / fixture の合成 hermetic 化）はユーザー承認済み

## レビュー結果
- [20260618_1637 判定: ✅ 完了](../../reviews/I066_plan_review_20260618_1637.md)
