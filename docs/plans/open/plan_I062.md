# plan_I062: レビュースクリプトの判定堅牢化（太字Blocker誤判定・出力契約・plan命名対応）

## 基本情報
- **計画書ID**: plan_I062
- **関連イシュー**: #128
- **Draft PR**: #（作成後に追記）
- **作成根拠資料**: docs/issues/open/I062.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I062_review.md
- **作成日**: 2026-06-15

---

## 1. 背景/目的

### 原因の概要（平易な説明）
レビュー結果ファイルに「Blocker（重大な差し戻し事由）」が書かれていても、判定スクリプトがそれを取りこぼして「✅ 完了」と誤表示することがある。原因は、レビュー結果を生成する側（レビューエージェント）が重大度を **Markdown 太字**（`| **Blocker** |`）で出力するのに対し、判定する側のスクリプトがプレーン文字列（`| Blocker |`）だけを前提にした `grep` をしているため。生成側と判定側の「表記の約束」がずれている。あわせて、計画書の再作成サフィックス（`plan_I###_2.md`）をスクリプトが探さないため、改訂版の計画書がレビュー対象から外れる。

### 詳細な原因分析
1. **太字 Blocker/High の取りこぼし（誤 `✅`）**
   - `scripts/claude/code-review.sh` の最終判定が `grep -qE "^\| Blocker \|"`（99行目）/ `grep -qE "^\| High \|"`（102行目）。これはセル両端に半角スペースのあるプレーン表記のみ一致する。
   - 一方 `.claude/review-agents/code-reviewer.md` の重大度定義・出力例は `| **Blocker** |` / `| **High** |` の**太字**。grep が非マッチ（exit 1）になり、Blocker 残存でも `else` 節の `✅ コードレビュー完了` に落ちる。
   - **本リポジトリ内に実証サンプルあり**: `docs/reviews/I060_code_review_20260612_0045.md` の 21・22 行目に `| **Blocker** |` 行が存在。現行 grep は非マッチ＝バグ再現（調査結果セクションに実測ログ）。
2. **計画書の再作成サフィックス（`plan_I###_N.md`）を読まない**
   - `code-review.sh` / `plan-issue-review.sh` の `find_file` は `plan_I###.md` 固定パターン。`plan-writing-rules.md` が定める再作成命名 `plan_I###_2.md` 等を拾えず、改訂計画がレビュー対象から外れる（I060 で実害）。

### 根本原因
- レビュー結果の**機械判定（verdict 検出）が、生成側（review-agent）の出力装飾に対して頑健でない**。フォーマット契約も表記揺れ許容も無い。
- **ファイル命名規約（`plan_I###_N.md`）とそれを読むスクリプトの探索パターンが不整合**。

### 目的
判定を「機械可読な固定判定行（`VERDICT:`）を一次・装飾許容 grep を保険」の二段構えに堅牢化し、`plan_I###_N.md` を連番数値順で正しく選ぶ。命名規約ドキュメント自体は変更しない（I064 の担当）。

### 調査結果（実装前に実測・検証済み）
> 本イシューは CI/lint/テスト・コード品質ツール系ではなくシェルスクリプト/エージェント定義の修正のため、pytest/eslint ベースライン計測は非該当。代わりに**判定ロジックのプロトタイプ検証を実装前に実施**した（未知リスク先行原則）。

- **環境前提**: `bash`（`#!/usr/bin/env bash`、`[[ =~ ]]`/`BASH_REMATCH` 使用可）、`grep` は **GNU grep 3.11**（`/usr/bin/grep`、`-E`・`-o`・`\s`・`\b` 対応を実測確認）。
- **バグ再現（実測）**: `grep -qE "^\| Blocker \|" docs/reviews/I060_code_review_20260612_0045.md` → **非マッチ（exit 1）= 誤 `✅` を再現**。
- **修正案の有効性（実測）**: 装飾許容 grep `^\|\s*\*{0,2}Blocker\b` → 同ファイルに**マッチ（fix 成立）**。
- **find_plan_file プロトタイプ**: 連番数値順（`_10 > _9 > _2 > 無印`、open/closed 横断、最大選択、無存在→空）を 5 ケース実測 **5/5 PASS**。
- **verdict 検出プロトタイプ**: 一次（`VERDICT:` 行）＋保険（装飾許容/プレーン）を code/plan 両系統・太字回帰サンプル含む 14 ケース実測 **14/14 PASS**。
- **テスト実行時の注意（重要）**: Claude Code の対話シェルでは `grep` が同梱 `ugrep` ラッパー（`exec -a ugrep ... -G`）に上書きされており、対話シェルへ直接貼り付けた検証は `-E`/`-o` パイプで誤動作する。**実スクリプトは `bash script.sh` のサブプロセスで実行され、そこでは実 GNU grep が使われる**（`bash -c 'type -t grep'` → `file` を実測確認）。よって自動テストは**スクリプトファイルとして `bash` 実行**する（対話シェルへ貼らない）。本注意は auto_test 文書にも明記。

---

## 2. 受け入れ条件（Acceptance Criteria）
- [ ] `code-reviewer.md` / `plan-reviewer.md` が出力末尾に機械可読な固定判定行（`VERDICT: ...`）を出す
- [ ] `code-review.sh` / `plan-issue-review.sh` が固定判定行を一次判定に使い、レビュー結果に太字 `| **Blocker** |` / `| **High** |` が含まれても誤って `✅` を出さない
- [ ] 後方互換: 固定判定行が無い旧レビュー出力でも、装飾許容 grep（`code-review.sh`）/ 既存プレーン判定（`plan-issue-review.sh`）で従来どおり検出される
- [ ] `plan_I###_2.md`（再作成サフィックス）が存在する場合、両スクリプトが連番数値順で最新の計画書を読む（`_10` > `_9` の数値ソート、無印を最古）
- [ ] `find_file` の `_N` 対応が issues/tests/reviews の通常ルックアップを壊さない（回帰確認）
- [ ] 既存の正常系（OK 判定）が壊れていないこと
- [ ] P1 gate 観点（規約是正イシューの消費箇所取りこぼし検証）が `plan-reviewer.md` / `code-reviewer.md` に追加されている

---

## 3. 影響範囲
- **Backend**: なし
- **Frontend**: なし（**P6 影響なし**: UI・性能・データ量・外部API懸念なし）
- **DB**: なし（**P3 影響なし**: DB/マイグレーション変更なし）
- **外部API・非同期・バッチ**: なし（**P5 影響なし**）
- **新規インフラ・外部サービス**: なし（**P8 影響なし**）
- **依存ライブラリ**: 追加・更新なし（requirements*.txt / package*.json 不変 → Dockerfile / docker-compose への波及なし）
- **Config/Infra（本イシューの対象）**:
  - `scripts/claude/code-review.sh`（レビュー自動化・判定ロジック）
  - `scripts/claude/plan-issue-review.sh`（同上）
  - `.claude/review-agents/code-reviewer.md`（レビュー出力契約）
  - `.claude/review-agents/plan-reviewer.md`（同上）
  - `scripts/claude/tests/test_review_verdict.sh`（**新規・回帰テスト資産**。実装関数を source して検証）
  - ワークフロー判定ロジックに関わるため、変更後は実レビュー1件で誤判定なしを確認（手動 TC）

### セキュリティ影響
**セキュリティ影響なし（新規攻撃面なし）**。スクリプト/エージェント定義のみで、新規依存・新規エンドポイント・認証認可変更なし。判定対象は自前生成のレビュー結果ファイルを `grep -f`/位置引数として渡すのみ（`eval` 不使用）。grep パターンは固定リテラル。むしろ **Blocker 見落とし防止**でプロセス安全性は向上（安全側の変更）。

---

## 4. 変更点一覧（ファイル/関数）

### 4-1. `.claude/review-agents/code-reviewer.md`
- **修正方針**: 出力末尾に機械可読な固定判定行を1行だけ出すよう契約を追加。既存の「出力フォーマット（このフォーマットのみ出力）」と矛盾しないよう、出力テンプレート末尾に組み込む。
- 追加内容（出力フォーマットの最終行・必須）:
  ```
  VERDICT: BLOCKER   # Blocker を1件以上検出
  VERDICT: HIGH      # Blocker 0 かつ High を1件以上検出
  VERDICT: OK        # Blocker・High なし
  ```
  上記のうち**該当する1行だけ**を出力の最終行に置く（装飾・前後の語を付けない）。
- **P1 gate 観点の追加**（「ベストプラクティス」観点に1項目）:
  - 「**規約・命名・フォーマット是正の網羅性**: 命名規則・フォーマット・規約を是正する変更で、宣言箇所のみを修正し消費箇所（グロブパターン・参照・スクリプト・ドキュメント）への反映を取りこぼしていないか。宣言箇所のみ修正＝該当時 High。」

### 4-2. `.claude/review-agents/plan-reviewer.md`
- **修正方針**: 同様に固定判定行を追加（3値）。
- 追加内容（出力フォーマットの最終行・必須）:
  ```
  VERDICT: BLOCKER   # 差し戻し（Blocker 1件以上）
  VERDICT: HIGHRISK  # 完了 かつ 高リスク: Yes
  VERDICT: OK        # 完了 かつ 高リスク: No
  ```
- **P1 gate 観点の追加**（「ベストプラクティス」観点に1項目）:
  - 「**規約・命名・フォーマット是正の網羅性**: 命名規則・フォーマット・規約を是正する計画で、宣言箇所だけでなく消費箇所（グロブパターン・参照・スクリプト・ドキュメント）の是正が影響範囲に列挙されているか。消費箇所が未列挙なら Blocker、列挙はあるが不完全なら Warning。」

### 4-3. `scripts/claude/code-review.sh`
- **構造変更**: 関数定義をファイル冒頭（`set -euo pipefail` 直後）へ移動し、source 専用ガードを追加。これによりテストが本体（CI 待機・`claude -p`）を実行せず関数だけを利用できる。
- 追加/変更関数:
  - `find_file()`（既存・**変更なし**。冒頭へ移動のみ。issues/tests/reviews/plans 単一パターン用）
  - `find_plan_file()`（**新規**）: `docs/plans/{open,closed}/plan_I###*.md` から連番を**数値ソート**し最大を選ぶ（無印=最古=0、`_N`=N）。同値は open 優先。該当なしは空文字。
    ```bash
    find_plan_file() {
      local issue="$1" f n best="" best_n=-1
      for f in "docs/plans/open/plan_${issue}.md" docs/plans/open/plan_${issue}_*.md \
               "docs/plans/closed/plan_${issue}.md" docs/plans/closed/plan_${issue}_*.md; do
        [ -f "$f" ] || continue
        if [[ "$f" =~ plan_${issue}_([0-9]+)\.md$ ]]; then n="${BASH_REMATCH[1]}"; else n=0; fi
        if [ "$n" -gt "$best_n" ]; then best_n="$n"; best="$f"; fi
      done
      echo "$best"
    }
    ```
  - `detect_code_verdict()`（**新規**）: 一次=`^VERDICT:` 行（`BLOCKER|HIGH|OK`、最終一致を採用）、無ければ保険=装飾許容 grep。
    ```bash
    detect_code_verdict() {
      local file="$1" v
      v=$(grep -oE '^VERDICT:[[:space:]]*(BLOCKER|HIGH|OK)' "$file" 2>/dev/null | tail -1 | grep -oE '(BLOCKER|HIGH|OK)' || true)
      if [ -n "$v" ]; then echo "$v"; return; fi
      if grep -qE '^\|\s*\*{0,2}Blocker\b' "$file"; then echo "BLOCKER"; return; fi
      if grep -qE '^\|\s*\*{0,2}High\b'    "$file"; then echo "HIGH"; return; fi
      echo "OK"
    }
    ```
- source 専用ガード（関数定義群の直後）:
  ```bash
  if [ "${REVIEW_LIB_SOURCE_ONLY:-}" = "1" ]; then return 0; fi
  ```
- 既存 `PLAN_FILE=$(find_file "plans" "plan_${ISSUE}.md")` → `PLAN_FILE=$(find_plan_file "$ISSUE")` に変更（48行目相当）。
- 最終判定ブロック（99〜108行目相当）を `detect_code_verdict` 主導の `case` に置換（メッセージ文面は現行維持）:
  ```bash
  case "$(detect_code_verdict "$REVIEW_FILE")" in
    BLOCKER) printf '\n⛔ Blocker が残っています。`/fix-loop %s` で修正後、`/code-review %s` を再実行してください。\n' "$ISSUE" "$ISSUE" ;;
    HIGH)    printf '\n❌ レビュー NG。`/fix-loop %s` を実行してください。fix-loop 完了後は `/code-review %s` に戻ってください。\n' "$ISSUE" "$ISSUE" ;;
    *)       printf '\n✅ コードレビュー完了。`/test %s` を実行してください。\n' "$ISSUE" ;;
  esac
  ```

### 4-4. `scripts/claude/plan-issue-review.sh`
- **構造変更**: 同様に関数を冒頭へ移動＋source 専用ガード追加。
- 追加/変更関数:
  - `find_file()`（既存・変更なし・冒頭へ移動）
  - `find_plan_file()`（**新規**・4-3 と同一実装）
  - `detect_plan_verdict()`（**新規**）: 一次=`^VERDICT:`（`BLOCKER|HIGHRISK|OK`）、無ければ保険=既存プレーン判定（`判定:.*差し戻し` / `高リスク判定.*Yes`、後方互換のため残置）。
    ```bash
    detect_plan_verdict() {
      local file="$1" v
      v=$(grep -oE '^VERDICT:[[:space:]]*(BLOCKER|HIGHRISK|OK)' "$file" 2>/dev/null | tail -1 | grep -oE '(BLOCKER|HIGHRISK|OK)' || true)
      if [ -n "$v" ]; then echo "$v"; return; fi
      if grep -qE "判定:.*差し戻し" "$file"; then echo "BLOCKER"; return; fi
      if grep -qiE "高リスク判定.*Yes" "$file"; then echo "HIGHRISK"; return; fi
      echo "OK"
    }
    ```
- source 専用ガード（関数定義群の直後）追加。
- 既存 `PLAN_FILE=$(find_file "plans" "plan_${ISSUE}.md")` → `PLAN_FILE=$(find_plan_file "$ISSUE")`（22行目相当）。
- 最終判定ブロック（78〜87行目相当）を `detect_plan_verdict` 主導の `case` に置換（メッセージ文面・遷移先は現行維持）:
  ```bash
  case "$(detect_plan_verdict "$REVIEW_FILE")" in
    BLOCKER)  printf '\n⛔ Blocker が残っています。修正後に `/plan-issue-review %s` を再実行してください。\n' "$ISSUE" ;;
    HIGHRISK) printf '\n✅ プランレビュー完了。`/security-review %s` を実行してから `/implement %s` へ進んでください。\n' "$ISSUE" "$ISSUE" ;;
    *)        printf '\n✅ プランレビュー完了。`/implement %s` を実行してください。\n' "$ISSUE" ;;
  esac
  ```
- 計画書リンク追記（71〜75行目）の `VERDICT=$(grep -o '判定:.*' ...)` は**マークダウンリンクのラベル用**であり判定ロジックではないため**変更しない**（`## 判定:` 行に一致し従来どおり機能）。
  - 補足: 既存の `高リスク判定.*Yes`（行単位 grep）は出力フォーマット上「`## 高リスク判定`」見出しと「`判定: Yes`」本文が別行のため実質マッチしない既知の弱点があるが、本イシューでは**一次判定を `VERDICT: HIGHRISK` に置く**ことでこの経路が正しく機能するようになる（保険側は後方互換として現状のまま残置）。

### 4-5. `scripts/claude/tests/test_review_verdict.sh`（新規・回帰テスト資産）
- 両スクリプトを `REVIEW_LIB_SOURCE_ONLY=1` で source し、`find_plan_file` / `detect_code_verdict` / `detect_plan_verdict` を直接アサート（実関数を検証＝ドリフトなし）。
- エージェント `.md` 2ファイルに `VERDICT` 契約・P1 gate 観点が含まれることを grep でアサート。
- いずれか失敗で非ゼロ終了。`bash scripts/claude/tests/test_review_verdict.sh` で実行（対話シェルへ貼らない）。
- 詳細 TC は `docs/tests/open/I062_auto_test.md` 参照。

---

## 5. 実装手順（ステップ）

> 各原則の読み替え: 本イシューは Django/React レイヤーを持たないツール変更のため、「垂直スライス」=「生成側（review-agent 契約）→判定側（スクリプト）→検証（テスト）」を1経路ずつ縦に貫通する単位で切る。**未知リスク（regex 堅牢性・grep ラッパー差異・連番数値ソート）は調査フェーズで実測済み**（調査結果セクション）。各ステップの検証は自動テスト文書の TC を参照（本文に検証コマンドは書かない）。

- **ステップ1: code-review 経路（生成→判定）を貫通**
  - `.claude/review-agents/code-reviewer.md` に `VERDICT: BLOCKER|HIGH|OK` 固定行契約を追加。
  - `scripts/claude/code-review.sh` に関数群（`find_file` 移動＋`find_plan_file`＋`detect_code_verdict`）と source ガードを追加、`PLAN_FILE` と最終判定 `case` を差し替え。
  - → TC-01〜TC-12 参照。

- **ステップ2: plan-review 経路（生成→判定）を貫通**（ステップ1と独立・並行実施可能）
  - `.claude/review-agents/plan-reviewer.md` に `VERDICT: BLOCKER|HIGHRISK|OK` 固定行契約を追加。
  - `scripts/claude/plan-issue-review.sh` に関数群と source ガードを追加、`PLAN_FILE` と最終判定 `case` を差し替え。
  - → TC-13〜TC-17 参照。

- **ステップ3: P1 gate 観点の追加**（ステップ1・2の `.md` 編集に同梱可能）
  - `code-reviewer.md` / `plan-reviewer.md` の「ベストプラクティス」観点に消費箇所取りこぼし検証を1項目ずつ追加。
  - → TC-18 参照。

- **ステップ4: 回帰テスト資産の作成と実行**（ステップ1〜3完了が前提）
  - `scripts/claude/tests/test_review_verdict.sh` を作成し、全 TC を実行・記録。
  - 構文チェック（`bash -n`）を両スクリプトに実施。
  - → TC-19・TC-20 参照。

**依存関係**: ステップ1・2は並行実施可能。ステップ3はステップ1・2の `.md` 編集に同梱。ステップ4はステップ1〜3完了が前提。

---

## 6. テスト計画（自動/手動）
- **テストレベルの選択**: スクリプト関数のユニットテスト（`find_plan_file` / `detect_*` を source して直接アサート）＋ 文字列契約の grep アサート＋ 実レビュー1件のスモーク（手動）。E2E（`claude -p` 込みの全経路）は非決定的・コスト高のため手動スモーク1件に留める。
- **認可・テナント境界テスト**: 本イシューに認証認可変更なし → 非該当。
- **再発防止テスト**: バグ修正イシューのため、太字 Blocker サンプル（実ファイル `I060_code_review_20260612_0045.md`）での誤 `✅` 非発生を TC-05 として固定化。
- 自動: `docs/tests/open/I062_auto_test.md`（TC-01〜TC-20）
- 手動: `docs/tests/open/I062_manual_test.md`

---

## 7. ロールバック
- 変更は4ファイル＋新規テスト1ファイルに限定。`git revert`（PR 単位）または各ファイルを develop 版へ戻すだけで原状復帰可能。
- DB・マイグレーション・外部状態を持たないため、切り戻しに副作用なし。
- 万一新判定が誤動作した場合でも、保険 grep / 後方互換判定が残るため旧挙動以上の退行は発生しない設計。

---

## 8. Risk & 回避策
| Risk | 回避策 |
|------|--------|
| `VERDICT` 行と本文の重大度が食い違う（エージェント不整合） | 一次判定は `VERDICT` を正本とする（Q1=c の設計）。エージェント側契約で「該当1行のみ」を明示。`VERDICT` が無い旧出力のみ保険 grep に委ねる |
| 連番数値ソートの取りこぼし（`_10` を `_9` 扱い等） | `[[ =~ ([0-9]+) ]]` で数値抽出し整数比較。プロト実測 5/5 PASS |
| 関数冒頭移動による本体挙動変化（CWD・`set -e`・`PIPESTATUS`） | 本体ロジックは順序・内容を保持し関数を前出しするのみ。`cd "$REPO_ROOT"` は本体内に残す。source ガードは `if` 文で `set -e` を誘発しない |
| テスト実行時の grep ラッパー差異で誤検出 | 自動テストは**スクリプトファイルとして `bash` 実行**（実 GNU grep）。auto_test に明記。`bash -c` サブプロセスで実 grep を実測確認済み |
| `plan_I###_*.md` グロブが無マッチ時に literal 残留 | `[ -f "$f" ] || continue` で literal をスキップ。プロト実測で確認 |
| スコープ拡張（P1 gate・テスト資産追加） | 承認ポイントで明示。命名規約ドキュメント（plan-writing-rules.md 等）は不変（I064 棲み分け維持） |

---

## 9. 承認ポイント（ユーザーが OK を返すチェックリスト）

### 設計判断の明示（イシュー明記 / 仮定で決めた の区別）
| 設計判断 | 区分 | 補足 |
|---------|------|------|
| `VERDICT:` 固定行を一次・装飾許容 grep を保険（二段構え） | **イシュー明記**（Q1=c） | code/plan 両系統に統一適用（Q4） |
| `find_plan_file` は連番数値順・最大選択・mtime 不使用 | **イシュー明記**（Q2） | 無印=最古、`_10`>`_9` |
| 命名規約ドキュメントは触らない（I064 棲み分け） | **イシュー明記**（Q3） | スクリプトを既存規約に「合わせる」だけ |
| P1 gate 観点を **plan-reviewer.md と code-reviewer.md の両方**に追加 | **仮定→ユーザー確認済み**（本セッションで「両方追加」を選択） | `rules/` は触らない |
| `VERDICT` の plan 側を3値（BLOCKER/HIGHRISK/OK）で表現 | 仮定（設計上の最小表現） | 既存3分岐（差し戻し/高リスク/通常）に対応 |
| `find_plan_file` を両スクリプトに**インライン重複**（共有 lib 化しない） | 仮定 | 既存 `find_file` も両スクリプトで重複しており**既存パターンに一貫**。スコープを4ファイル＋テストに限定 |
| source 専用ガード（`REVIEW_LIB_SOURCE_ONLY=1`）で関数をテスト可能化 | 仮定 | 標準的な bash ユニットテストパターン。本体挙動は不変 |
| 回帰テストを `scripts/claude/tests/test_review_verdict.sh` として**新規コミット** | 仮定 | 受け入れ条件の検証を再現可能化（理想状態）。影響範囲に明記 |

### セキュリティ・ベストプラクティスチェック結果
- 入力バリデーション: 判定対象は自前生成ファイル。`eval` 不使用、固定 grep パターン → **新規リスクなし**
- 認証・認可変更: **なし**
- 機密データ: **扱わない**
- OWASP Top 10: スクリプト/ドキュメント変更のため**非該当**
- 依存ライブラリ追加: **なし**（pip-audit/npm audit 非該当）
- セキュリティスキャン基準: コード変更が Python/JS でないため bandit/npm audit 非該当。shellcheck 相当として `bash -n` 構文チェックを TC-20 に設定

### テスト計画チェック結果
- 再発防止テスト: **あり**（TC-05 太字 Blocker 実ファイル回帰）
- テストレベル選択: **明示済み**（セクション6）
- 認可・テナント境界テスト: 認可変更なしのため**非該当**

### データ整合性・運用性・コスト設計
- **P3/P5/P8 影響なし**（DB・外部API/非同期/バッチ・新規インフラいずれも無し）

### 性能・UX設計
- **P6 影響なし**（フロントエンド・性能・データ量・外部API懸念なし）

---

## 承認待ち宣言
この計画書の内容（特に **P1 gate 観点を両エージェントに追加**・**回帰テスト資産を新規コミット**・**スクリプトの関数前出し＋source ガード**という3つのスコープ要素）で実装を進めてよいかご確認ください。
