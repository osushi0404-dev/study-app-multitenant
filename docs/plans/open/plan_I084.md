# I084 計画書: code-review の決定論ゲートを実走化（実 exit code を VERDICT に注入・推論 PASS を排除）

## 基本情報
- **計画書ID**: plan_I084
- **関連イシュー**: #167
- **Draft PR**: #174
- **作成根拠資料**: docs/issues/open/I084.md（起点イシュー・grill-me で設計確定済み）
- **実装後評価**: docs/reviews/open/I084_review.md
- **作成日**: 2026-07-01

---

## 1. 背景/目的

### 原因の概要（平易）
`/code-review`（`scripts/claude/code-review.sh`）は単発の `claude -p`（tools=`Read,Grep,Glob`）でレビューする。決定論で判定できるゲート（`auto_test.md` が指定するテストスクリプト・doc-sync grep 等）まで、スクリプトが**実走せず LLM の読解に委ねている**ため、実行していないのに「PASS」と断定し得る（false-green）。

### 詳細な原因分析（I080 実証）
code-review 記録 `docs/reviews/I080_code_review_20260629_0101.md` は AC#11 で「TC-DOC1〜3 PASS」と記載したが、実際には **TC-DOC3 が FAIL**（`claude-code-structure.md` の限界注記にイシュー番号 `I083` を混入・規約違反）していた。次工程 `/test` が当該 grep を**実走して初めて検出**（`2c85f27` で修正）。レビューが決定論ゲートを実走していれば code-review 段階で捕捉できた。

### 根本原因
レビュー自動化が**決定論で判定可能な結果を、実行でなく推論で報告**している。検証階層（①手続き＜②決定論ゲート＜③敵対的検証）のうち **② を ① に退化**させている。本イシューは ② を実走で締める最初の施策（retro I080 の根本 A）。

### 目的
`code-review.sh` が `auto_test.md` の決定論ゲートを**スクリプト自身で実走**し、実 exit code を証跡としてレビュー文脈へ注入、FAIL/実行不能があれば VERDICT を決定論的に BLOCKER へ倒す。

---

## 2. 受け入れ条件
（イシュー AC を継承。実装・テストで固定する。）
- [ ] AC1: `/code-review` 実行時、`auto_test.md` の『決定論ゲート（自動実走）』宣言セクションのゲート（テストスクリプト・doc-sync grep 等）が**実走**され、実 exit code が記録に証跡として残る
- [ ] AC2: 決定論ゲートに FAIL がある場合、`code-review.sh` が最終 VERDICT を **BLOCKER** に決定論的に上書きする（LLM 出力非依存）ことを単体テストで固定
- [ ] AC3: 決定論ゲートが**実行不能**（宣言スクリプト不在・インタプリタ未検出・timeout 超過）の場合も fail-closed で VERDICT を BLOCKER に倒すことを単体テストで固定
- [ ] AC4: I080 の「TC-DOC3 FAIL を PASS と誤記」相当のケースが本改修後は実走で検出されることを回帰テストで固定（false-green 注入）
- [ ] AC5: `.claude/review-agents/code-reviewer.md` に「決定論ゲートは注入済み実結果を使い読解で PASS 断定しない」が明記
- [ ] AC6: 既存 code-review フロー（claude -p 実行・PR コメント投稿・記録の path-scoped コミット・ブランチガード）が無回帰（`test_review_verdict.sh` PASS 維持）
- [ ] AC7: 抽出方式がハイブリッド（(a) 宣言セクション `## 決定論ゲート（自動実走）` のみ実走 ＋ (b) omission-lint）で実装と一致し、`auto_test_template.md` に当該セクション規約が追加されている
- [ ] AC8: omission-lint が宣言セクション**外**の副作用なし allowlist ゲートパターン行を検出時に **HIGH** で VERDICT 反映し、**heavy/deferred（pytest/Jest/E2E・docker・npm）のみのブロックや散文裸語は非検出**であることを単体テストで固定
- [ ] AC9: I084 自身の `auto_test.md` が `## 決定論ゲート（自動実走）` で決定論ゲートを宣言している（ドッグフーディング）
- [ ] AC10: 実走対象は副作用のない読み取り系 allowlist ∩ 宣言分に限り、破壊的コマンド・heavy は実走しない（heavy は「/test 委譲」記録）ことを単体テストで固定（安全境界）

---

## 3. 影響範囲
- **Backend**: なし（Django/DRF コード変更なし）
- **Frontend**: なし（React コード変更なし）
- **DB**: なし（マイグレーション・モデル変更なし）
- **Config/Infra**:
  - `scripts/claude/code-review.sh`（決定論ゲート抽出・実走・VERDICT 上書き・omission-lint 追加）
  - `.claude/review-agents/code-reviewer.md`（レビューア指示追記）
  - `docs/tests/templates/auto_test_template.md`（`## 決定論ゲート（自動実走）` セクション規約追加・template-sync 対象）
  - `scripts/claude/tests/test_review_gates.sh`（新規・source-only 単体テスト）
- **実走参照（非改変）**: `scripts/claude/tests/*.sh`（宣言ゲートとして allowlist 実走される既存テスト群）

**セキュリティ影響（要記載・コマンド実行面）**: 本改修で `code-review.sh` は `auto_test.md`（repo 内文書）の宣言セクションから抽出したコマンドを**ローカル dev 環境で実行**する新たな実行面を持つ。緩和策＝**positive allowlist**（`bash scripts/claude/tests/*.sh`・`grep`・`python3 -m json.tool`・`bash -n`・`python3 -m py_compile` のみ実走。チェーン系メタ文字 `; && || | \` $( >` を含む行は実走せず、pytest/docker/npm 等 heavy は /test 委譲）。auto_test.md は計画工程でレビュー済みの信頼文書だが、allowlist で万一の破壊的コマンド混入を実行しない多層防御とする。§4・§5・§8・auto_test TC で固定。

---

## 4. 変更点一覧（具体）

### 4-1. `scripts/claude/code-review.sh` — 新規 helper 関数（`REVIEW_LIB_SOURCE_ONLY=1` ガードより前に置き source 可能に）

| 関数 | 責務 |
|------|------|
| `extract_gate_commands <auto_test_file>` | 見出し `## 決定論ゲート（自動実走）` 配下の単一 fenced ```bash ブロックから、非空・非コメント行を 1 行 1 コマンドで抽出。見出し不在なら空 |
| `classify_gate <cmd>` | `ALLOW`（副作用なし＝実走）/ `HEAVY`（/test 委譲・実走しない）/ `UNSAFE`（allowlist 不一致・チェーン系＝実走せず fail-closed）を返す |
| `run_one_gate <cmd>` | `timeout "${GATE_TIMEOUT:-120}" bash -c "$cmd"` で実走し exit code を返す（command not found / timeout も非ゼロ＝fail-closed）。`GATE_TIMEOUT` は**テスト用に上書き可能**（例 `GATE_TIMEOUT=1`）。**`! grep …` 不在検証は特別扱い**: 生 `!` は grep のエラー(exit≥2・ファイル不在等)まで 0 に反転し **false-PASS** になるため、内側 grep の exit を見て「一致なし(1)＝pass / それ以外(0=一致あり・≥2=エラー)＝fail-closed」に正す（code-review Medium 対応・TC-DOC5/RUN10） |
| `run_declared_gates <auto_test_file>` | 宣言ゲートを分類・実走し、**グローバル変数 `GATE_EVIDENCE`（証跡 markdown）・`GATE_VERDICT`（OK/BLOCKER）を設定**する。**コマンド置換 `$()` で呼ばない**（サブシェルだとグローバル設定が呼び出し元へ伝播しない・W1）。呼び出しは `run_declared_gates "$f"` 直呼び |
| `omission_lint <auto_test_file>` | 宣言セクション**外**の **fenced ```bash/```sh ブロック**に allowlist ゲートパターンがあれば `HIGH`、なければ `OK`。**インライン backtick・Markdown テーブルセル・散文・heavy のみブロックは非検出**（TC 記述文中のコマンド文字列で自傷 HIGH しない・W4） |
| `verdict_rank <v>` / `combine_verdict <v...>` | `BLOCKER>HIGH>OK` の順位で最大の VERDICT を返す |

**classify_gate 判定順（重要・分岐順で挙動が変わる。HEAVY は先頭コマンド anchored＝部分一致にしない）**:
1. **HEAVY（先頭コマンド anchored）**: 先頭トークンが heavy ツール（`docker` / `docker-compose` / `npm` / `npx` / `pytest` / `python -m pytest` / `python3 -m pytest` / `jest` / `playwright`）または `manage.py test` を含む invocation → `HEAVY`（実走しないのでチェーン有無は不問）。
   - **anchored の理由**: 部分一致にすると `grep -q "npm test done" build.log`（引数に heavy 語を含む正当な grep ゲート）が HEAVY 誤判定で**実走されず沈黙スキップ＝false-negative（gate 取りこぼし）**になる。先頭コマンドで判定してこれを防ぐ。
2. **allowlist 前方一致 ＋ チェーンメタ文字なし** → `ALLOW`。allowlist＝`bash scripts/claude/tests/*.sh` / `grep ` / `! grep `（不在検証） / `python3 -m json.tool` / `bash -n ` / `python3 -m py_compile `。チェーン系メタ文字（`;` `&&` `||` `|` `` ` `` `$(` `>`）を含む場合は ALLOW にせず 3 へ（**実行する ALLOW のみメタ文字ガードを課す＝安全境界**）。
2.5. **パストラバーサル拒否**: `case` glob の `*` は `/` にもマッチするため、`../` を含む行は `UNSAFE`（`bash scripts/claude/tests/*.sh` 経由で `.../../evil.sh` を実走させない安全境界・code-review Medium 対応・TC-CL15）。
3. 上記いずれにも該当しない（破壊系・チェーン付き・未知）→ `UNSAFE`（実走しない）。

> doc-sync ゲートは grep で表現する: **存在**=`grep -q 文言 file`（exit0=合格）、**不在**=`! grep -q 文言 file`（file が文言を含まないとき grep exit1→`!`で exit0=合格・含むと exit0→`!`で exit1＝I080 型の混入を捕捉）。allowlist に `! grep …` を含める（`!` は grep の否定のみで安全）。
> - **ファイル不在の false-PASS 対策（必須）**: `! grep -q pat missing_file` は grep exit2 を `!` が 0 化し「不在＝合格」と誤判定する。`run_one_gate` が `! grep` を特別扱いし **grep exit1 のみ pass・exit≥2(エラー)は fail-closed** に正す。よって auto_test 側は素直に `! grep -q pat file` と書けばよい（`[ -f file ] && …` のようなチェーンは不要かつ allowlist 不一致で書けない）。
> - ※ `grep -L` は exit status が「pattern が見つかったか」に従い**不在検証には使えない**ため採用しない（実測で確認済み）。

> **omission_lint の走査スコープ（W4 対策・自傷回避）**: 対象は宣言セクション外の **fenced ```bash/```sh コードブロック内の行のみ**。Markdown テーブルセルやインライン backtick（TC 記述中の `` `bash scripts/…` `` 等の文字列）・散文は**走査しない**。これにより本 auto_test.md 自身（TC テーブルにコマンド文字列を多数含む）がドッグフーディング実走時に自傷 HIGH しない。実装は「宣言セクション除外 → 残りから ``` フェンス内行のみ抽出 → allowlist パターン grep」。

**run_declared_gates の verdict 集約**:
- `ALLOW` を実走し exit≠0 が 1 件でもあれば `GATE_VERDICT=BLOCKER`（fail-closed）
- `UNSAFE`（宣言ゲートなのに実走できない）も `GATE_VERDICT=BLOCKER`（検証できない＝OK にしない・安全境界警告）
- `HEAVY` は「/test 委譲」を証跡記録するのみ（FAIL ではない・別バケット）

### 4-2. `scripts/claude/code-review.sh` — 本体フローへの配線
`claude -p` 実行（現行 L128）**前**に:
```bash
AUTO_TEST_FILE=$(find_file "tests" "${ISSUE}_auto_test.md")
GATE_VERDICT=OK; OMISSION_VERDICT=OK; GATE_EVIDENCE="(決定論ゲート宣言なし)"
if [ -n "$AUTO_TEST_FILE" ]; then
  # 直呼び（$() を使わない）: run_declared_gates が GATE_EVIDENCE / GATE_VERDICT をグローバル設定（W1）
  run_declared_gates "$AUTO_TEST_FILE"
  OMISSION_VERDICT=$(omission_lint "$AUTO_TEST_FILE")   # omission_lint は HIGH/OK を stdout 返しなので $() 可
fi
```
`CONTEXT` に証跡セクションを追加（LLM 文脈への事前注入・叙述整合）:
```
### 決定論ゲート実行結果（実 exit code・スクリプト実走済み／読解で上書きしないこと）
${GATE_EVIDENCE}
omission-lint: ${OMISSION_VERDICT}
```
`claude -p` 保存後（現行 L140 の後）、**VERDICT 決定論的上書き**:
```bash
LLM_VERDICT=$(detect_code_verdict "$REVIEW_FILE")
FINAL_VERDICT=$(combine_verdict "$GATE_VERDICT" "$OMISSION_VERDICT" "$LLM_VERDICT")
# 記録先頭へ証跡セクションを prepend し、末尾 VERDICT 行を FINAL へ書換え
inject_gate_result "$REVIEW_FILE" "$GATE_EVIDENCE" "$OMISSION_VERDICT" "$FINAL_VERDICT"
```
→ 以降の `commit_review_artifact` / PR コメント / `case "$(detect_code_verdict ...)"`（現行 L152）は**書換え後の FINAL を読む**ため、routing が決定論的に BLOCKER へ倒れる。`inject_gate_result` は「最終行の `^VERDICT:` を FINAL に置換」＋「先頭に証跡見出しを挿入」を行う小関数（source 可能）。

### 4-3. `.claude/review-agents/code-reviewer.md`
「レビュー観点 > テスト妥当性」節付近と「出力フォーマット」節に追記:
- 「**決定論ゲートは注入済みの実 exit code を使い、Read/Grep の読解で PASS と断定しない**。証跡（コマンド＋exit code）を受け入れ条件照合の備考に併記する。スクリプトが実走・注入した `### 決定論ゲート実行結果` を上書き・無視しない」
- 追記前に既存の VERDICT 説明・判定根拠節を Read し、「LLM 独自判定を記録の根拠にしない（注入済み実結果を優先）」と矛盾する記述がないことを確認して整合させる（Info I2）。

### 4-4. `docs/tests/templates/auto_test_template.md`
機械可読セクション規約を追加（既存の heavy 例示ブロックは残置＝P1 で omission 非検出を保証）:
```markdown
## 決定論ゲート（自動実走）
<!-- code-review.sh がこの見出し直後の単一 ```bash ブロックを 1 行 1 コマンドで抽出し実走する。
     許可: bash scripts/claude/tests/*.sh / grep / python3 -m json.tool / bash -n / python3 -m py_compile。
     heavy（pytest/Jest/E2E・docker）はここに書かず /test に委譲。チェーン（; && | 等）不可・1 行 1 コマンド。 -->
```bash
bash scripts/claude/tests/test_xxx.sh
```
```

### 4-5. `scripts/claude/tests/test_review_gates.sh`（新規）
`REVIEW_LIB_SOURCE_ONLY=1 source scripts/claude/code-review.sh` で新規関数を単体テスト（§6・詳細は auto_test.md）。

---

## 5. 実装手順（ステップ）

> 各ステップは「関数追加 → 単体テスト → 本体配線」を薄く縦に貫く。検証コマンドはステップ本文に書かず auto_test.md の TC を参照する（plan-writing-rules 準拠）。

1. **ステップ1（最大の未知リスク先行・抽出と分類の核）**: `code-review.sh` に `extract_gate_commands` / `classify_gate` を追加。`test_review_gates.sh` を新規作成し抽出・分類の TC を通す。→ TC-EX1..、TC-CL1.. 参照。
   - 依存: なし。ここが不成立なら以降を止める（抽出契約が全ての土台）。
2. **ステップ2（実走と fail-closed）**: `run_one_gate` / `run_declared_gates` / `verdict_rank` / `combine_verdict` を追加。ALLOW 実走・FAIL→BLOCKER・実行不能→BLOCKER・HEAVY 委譲・UNSAFE→BLOCKER を単体テストで固定。→ TC-RUN1.. 参照。
   - 依存: ステップ1。
3. **ステップ3（omission-lint）**: `omission_lint` を追加。宣言外 allowlist 行→HIGH、heavy のみ/散文裸語→OK を固定。→ TC-OM1.. 参照。
   - 依存: ステップ1。ステップ2 と並行実施可。
4. **ステップ4（本体配線・注入・VERDICT 上書き）**: §4-2 の配線と `inject_gate_result` を追加。既存フロー（`case detect_code_verdict`・PR コメント・commit）の無回帰を固定。→ TC-INJ1.. / TC-WIRE1.. 参照。
   - 依存: ステップ2・3。
5. **ステップ5（レビューア指示・テンプレ規約・ドッグフーディング）**: `code-reviewer.md` 追記、`auto_test_template.md` にセクション規約追加、I084 自身の `auto_test.md` に `## 決定論ゲート（自動実走）` を記載。→ TC-DOC1.. 参照。
   - 依存: ステップ1〜4（契約が確定してから文書化）。

---

## 6. テスト計画
### 自動（`docs/tests/open/I084_auto_test.md` が正）
- 新規 `test_review_gates.sh`（source-only 単体）: 抽出・分類・実走・fail-closed・VERDICT 合成・omission-lint・破壊系非実走・I080 回帰（false-green 注入）・bash -n。
- 既存 `test_review_verdict.sh`（無回帰・PASS 維持）。
- **false-green 自己検証（必須）**: 否定/回帰 TC は判定行を壊して NG（非ゼロ）になることを対で確認してから採用（TC-FG 群）。
- pytest / Jest / E2E: **非該当**（Backend/Frontend/DB 変更なし・bash とテンプレのみ）。

### 手動（`docs/tests/open/I084_manual_test.md`）
- Claude 実施: 生成物の存在・構文・テンプレ規約反映の目視/grep 確認。
- Human 実施: 実 `/code-review` を feature ブランチで走らせ、決定論ゲート実行結果セクションが記録・PR コメントに現れること（ハーネス実挙動）。

---

## 7. ロールバック
- 全変更は追加的（新規関数・新規テスト・追記）。`git revert` で `code-review.sh`・`code-reviewer.md`・`auto_test_template.md`・`test_review_gates.sh` の差分を戻せば旧挙動（LLM 読解のみ）へ復帰。DB・データ変更なしのため副作用なし。

## 8. Risk & 回避策
| Risk | 回避策 |
|------|--------|
| 抽出コマンドの実行面（破壊的コマンド混入） | positive allowlist ＋ チェーンメタ文字拒否。UNSAFE は実走せず fail-closed BLOCKER（§3 セキュリティ・TC-CL/TC-RUN で固定） |
| 宣言ゲートのハングで code-review 無限待機 | `timeout 120` で束ね超過は非ゼロ＝fail-closed（TC-RUN で固定） |
| omission-lint の heavy 例示ブロック誤検知（自傷） | lint 対象を allowlist パターン行に限定・heavy/裸語 非検出（P1・TC-OM で固定） |
| VERDICT 上書きが既存 routing を壊す | `detect_code_verdict` の入力（VERDICT 行）を書換える方式で既存 `case` を変えない・`test_review_verdict.sh` 無回帰（TC-WIRE） |
| 対話シェルの grep ラッパー誤動作 | テストは `bash` スクリプト実行（フルパス・source-only）で決定論化（既存 test_review_verdict.sh と同方式） |

---

## 9. 承認ポイント
- [ ] **設計判断（すべてイシューに明記済み／grill-me 4 巡で確定）**: 抽出=ハイブリッド(a宣言+b lint) / 実走=副作用なし allowlist ∩ 宣言 / FAIL→BLOCKER 決定論上書き / 実行不能=fail-closed / omission=HIGH(allowlist行のみ) / timeout 120s。**仮定で決めた項目なし**。
- [ ] **セキュリティ**: 新規コマンド実行面を positive allowlist ＋ チェーン拒否 ＋ heavy 除外で多層防御（§3）。認証・認可・個人情報の変更なし → **P9 影響なし**。
- [ ] **テスト計画**: 再発防止（I080 false-green 回帰）・false-green 自己検証・破壊系非実走・無回帰を単体テストで固定。認可テストは対象外（認可変更なし）。
- [ ] **要件適合**: AC を超えた仕様追加なし。横展開（plan-review/issue-review 適用・敵対レビュー自動化）は scope 外（別イシュー）。
- [ ] **P3/P5/P8**: DB/外部API/非同期なし → データ整合性・運用設計セクション非該当。保守負荷＝bash 関数追加のみで過剰構成なし → **P3/P5/P8 影響なし**。
- [ ] **P6**: UI なし → **P6 影響なし**。

---

📋 計画書を作成しました: docs/plans/open/plan_I084.md

⏸️ **承認待ち中**: 実際の修正作業は開始しません
✅ 承認いただけましたら「OK」または「承認」とお答えください
❌ 修正が必要でしたら具体的な指示をお願いします

## レビュー結果
- [20260701_2243 判定: ✅ 完了](../../reviews/I084_plan_review_20260701_2243.md)
