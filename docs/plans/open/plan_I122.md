# I122 計画書: 決定論テストの合否判定インターフェース統一 — 「合格=exit 0」を plan-writing-rules に明文化し、出力値判定の反転リスクを plan-reviewer の確認観点に追加

## 基本情報
- **計画書ID**: plan_I122
- **関連イシュー**: #225
- **Draft PR**: #234
- **作成根拠資料**: docs/issues/open/I122.md（/grill-me 設計確認メモ 2 件を含む）
- **実装後評価**: docs/reviews/open/I122_review.md
- **作成日**: 2026-07-18

## 1. 背景/目的

### 原因の概要
I121 の自動テスト TC-02 は「対象 advisory の不在」を `npm audit --json | grep -c "GHSA-..."` の**出力値が 0** であることで判定した。この形は合格（0 件一致）のとき grep が exit code 1 を返すため、exit code を合否に使う自動実行（CI・スクリプト・`set -e` 環境）に組み込むと「合格なのに失敗扱い」に反転する。plan review（Info）と code review（Low）の独立レビュー 2 回で同じ指摘が出ており、ルール不在による再発性が実証されている。

### 詳細な原因分析
- plan-writing-rules の false-green 節（「否定・回帰系の決定論テストの自己検証」）は「失敗条件を注入して NG（非ゼロ終了）になること」＝**失敗側の向き**のみを要求し、**合格側の向き（合格=exit 0 の統一）**を規定していない。このため出力値判定（合格時に非ゼロ終了）と exit code 判定が TC 間で混在できる（I121 retro の 5 Whys で特定）。
- plan-reviewer の P4 観点は false-green（失敗条件で不合格になるか）を見るが、合否基準の exit code 向き一致は明文観点でない。I121 では指摘が出たが Info 止まりで、差し戻し（Blocker）にはならず素通りした。

### 目的
do（作成時に防ぐ）＋ gate（レビューで止める）の 2 層で、合否判定インターフェースを「合格=exit 0」に統一する。gate は観点追記だけでなく差し戻しファースト原則（該当すれば必ず Blocker）の表にも載せ、「検知はしたが止まらない」再発を防ぐ（/grill-me 確定）。

## 調査結果（計画時実証・すべて実行済み・2026-07-18）

### 失敗注入の事前実証（false-green でないことの確認）
決定論 TC-01〜05・TC-07（下記 6. 参照）を**文言未追記の現状ファイル**に対して実行し、**全て exit 1（NG）**を確認済み（scratchpad スクリプト i122_tc_prerun.sh ＋ fix-test-reviewer 追加分の単体実行）。「該当行を欠いた入力で NG を返す」注入確認は計画時点で完了している。実装後は TC-01〜05・TC-07 が exit 0 に転じることを確認する。

### 消費箇所の全件確認（`false-green` を repo 全体 grep 済み）
現行ルール・指示ファイルでのヒットは以下で全件。歴史的記録（docs/issues・plans・reviews・tests の open/closed 配下）は遡及改修対象外（イシュー確定）:
| ファイル | 分類 | 本計画での扱い |
|---------|------|---------------|
| docs/runbooks/plan-writing-rules.md | 宣言（false-green 節） | **変更対象 A** |
| .claude/skills/plan-issue/SKILL.md | 消費（文書品質ゲートのセルフチェック項目） | **変更対象 C**（grill Q1 確定） |
| .claude/review-agents/plan-reviewer.md | 消費（P4 観点・差し戻しファースト表） | **変更対象 B**（grill Q2 確定・表にも追加） |
| .claude/review-agents/code-reviewer.md | 消費（false-green 観点） | 対象外（イシュー「含まない」確定） |
| .claude/review-agents/fix-test-reviewer.md | 消費（false-green 観点 l.27。exit code 向き規定なし） | **変更対象 D**（承認前確認 → ユーザー確定 2026-07-18: fix 経路の TC は plan-reviewer を通らず、除外すると gate 層のない経路が残るため含める。code-reviewer の除外＝同一経路の重複回避とは事情が異なる） |
| scripts/claude/fix-review-lib.sh・fix-test-review.sh | VERDICT 処理のコメント言及のみ（TC 作法に非依存） | 変更不要 |

### 既存決定論テストへの影響（機械確認済み）
`scripts/claude/tests/` で対象 3 ファイルを参照するのは `test_review_verdict.sh` のみ（TC-18b/18c: `VERDICT: ...`・`消費箇所` の**存在** grep）。本計画は行の追記のみで既存文言を変更しないため、既存テストは壊れない。

### 現行文言との整合
既存 false-green 節は失敗側について「不合格（NG / 非ゼロ終了）」を既に要求しており、今回の「合格=exit 0」追記と矛盾しない（純追加）。イシューの制約どおり既存の注入検証ルールは変更しない。

### 参照先実在性・環境前提
- 変更対象 3 ファイルはすべて Read 済み・実在確認済み（挿入位置の現行文言も確認済み）。
- 使用ツール bash/grep は事前実証スクリプトで本環境（WSL2）実走済み。pytest/Jest/E2E: アプリコード変更なしのため非該当。

## 2. 受け入れ条件（イシューの AC を転記）
- [ ] plan-writing-rules.md に「合格=exit 0 統一・出力値比較を合否基準にしない・不在判定は `! grep -q` 等」の規定が追記されている（TC-01/02）
- [ ] plan-reviewer.md の P4 テスト妥当性観点に exit code 向き一致チェックが追記されている（TC-03）
- [ ] plan-reviewer.md の差し戻しファースト原則「自動テストケース」表に exit code 向き反転の Blocker パターン行が追記されている（TC-04）
- [ ] plan-issue/SKILL.md の false-green セルフチェック項目に合格=exit 0 統一が反映されている（TC-05）
- [ ] fix-test-reviewer.md の false-green 観点に exit code 向き一致チェックが追記されている（TC-07）
- [ ] 追記の決定論ゲートが false-green でない（該当行を欠いた入力で NG を返すことを注入確認 — 計画時実証済み・TC-06）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: docs/runbooks/plan-writing-rules.md・.claude/review-agents/plan-reviewer.md・.claude/skills/plan-issue/SKILL.md・.claude/review-agents/fix-test-reviewer.md（ハーネス文書 4 ファイルのみ・行追記のみ）

## 4. 変更点一覧（具体・追記文言の全文）

### 4-1. docs/runbooks/plan-writing-rules.md（変更対象 A）
**修正方針**: 「否定・回帰系の決定論テストの自己検証（false-green 禁止）」節の箇条書き末尾（「これは『検証コマンドを書かない』ルールの品質保証であり…」の直前）に、合否判定インターフェース統一の bullet を 1 件追加する。既存 bullet は変更しない。

追記文言（全文）:
```markdown
- **合否判定インターフェースの統一（合格=exit 0）**: 決定論 TC の合否判定は exit code に統一する（合格=exit 0・不合格=非ゼロ終了）。コマンド出力値の目視比較（例: `grep -c` の出力が `0` であること）を合否基準にしない。不在・否定の判定は `! grep -q 文言 file` のように合格時に exit 0 を返す形で書き、出力値に基づく判定が必要な場合も `[ "$(grep -c 文言 file)" -eq 3 ]` のように exit code へ畳み込む。合格時に非ゼロ終了する TC は、exit code を合否に使う自動実行（CI・スクリプト・`set -e` 環境）で「合格なのに失敗扱い」に反転する。
```

### 4-2. .claude/review-agents/plan-reviewer.md（変更対象 B・2 箇所）
**修正方針 B1**: 「P4. テスト妥当性・回帰防止」の bullet 末尾（false-green 観点の直後）に観点を 1 件追加する。

追記文言（全文）:
```markdown
- TC の合否基準が exit code の向きと一致しているか（合格=exit 0・不合格=非ゼロ終了。`grep -c` の出力値の目視比較など、合格時に非ゼロ終了するコマンドを合否基準にしていないか）
```

**修正方針 B2**: 「差し戻しファースト原則」の「自動テストケース」表の末尾に Blocker パターン行を 1 行追加する（該当すれば必ず差し戻し）。

追記文言（全文）:
```markdown
| 合否基準が合格時に非ゼロ終了する | 「`grep -c "GHSA-..."` の出力が 0 であることで不在を確認」 | `! grep -q "GHSA-..."`（合格=exit 0） |
```

### 4-3. .claude/skills/plan-issue/SKILL.md（変更対象 C）
**修正方針**: 「文書品質ゲート」チェックリストの false-green 項目（「否定・不在・回帰・無改変を検証する決定論テスト…」）の直後に、セルフチェック項目を 1 件追加する。

追記文言（全文）:
```markdown
- [ ] 決定論 TC の合否判定インターフェースが exit code に統一されているか（合格=exit 0・不合格=非ゼロ終了。出力値の目視比較を合否基準にせず、不在判定は `! grep -q` 等の合格=exit 0 形で書かれているか）
```

### 4-4. .claude/review-agents/fix-test-reviewer.md（変更対象 D）
**修正方針**: レビュー観点 3（false-green でないか）の本文末尾（l.28 の直後）に、観点の続きとして 1 行追加する。番号付きリストの再採番を避けるため独立項目にはせず、観点 3 のインデント継続行として追記する（既存の観点 4・5 の番号・文言は変更しない）。

追記文言（全文）:
```markdown
   決定論 TC（grep 等のシェル判定・lint 異常系）では、合否基準が exit code の向きと一致しているか（合格=exit 0・不合格=非ゼロ終了。`grep -c` の出力値の目視比較など、合格時に非ゼロ終了するコマンドを合否基準にしていないか）。
```

## 5. 実装手順（ステップ）
1. **plan-writing-rules.md へ統一規定を追記**（4-1。→ TC-01/02 参照）
2. **plan-reviewer.md へ P4 観点＋差し戻し表行を追記**（4-2。→ TC-03/04 参照。ステップ1と独立・並行可）
3. **plan-issue/SKILL.md へセルフチェック項目を追記**（4-3。→ TC-05 参照。ステップ1/2と独立・並行可）
4. **fix-test-reviewer.md へ観点3の続き行を追記**（4-4。→ TC-07 参照。ステップ1〜3と独立・並行可）
5. **決定論ゲートの実走・記録**: docs/tests/open/I122_auto_test.md の全 TC を実行し結果を記録する（ステップ1〜4完了が前提）

- 未知リスク先行: なし（外部挙動依存なし。判定ロジックは計画時に失敗注入まで実証済み）。
- 垂直スライス: 非該当（ドキュメント 3 ファイルの文言追記で完結）。
- サービス再起動: 不要。

## 6. テスト計画
### 自動（docs/tests/open/I122_auto_test.md・合格=exit 0 に統一 — 本イシューのルールを自文書で dogfood）
| TC | 検証内容 | 判定コマンド（合格=exit 0） |
|----|---------|---------------------------|
| TC-01 | plan-writing-rules に統一規定が存在 | `grep -q '合否判定インターフェースの統一' docs/runbooks/plan-writing-rules.md` |
| TC-02 | 同規定に不在判定の合格=exit 0 形（`! grep -q 文言 file`）が存在 | `grep -qF '! grep -q 文言 file' docs/runbooks/plan-writing-rules.md` |
| TC-03 | plan-reviewer P4 に exit code 向き一致観点が存在 | `grep -q 'exit code の向きと一致しているか' .claude/review-agents/plan-reviewer.md` |
| TC-04 | plan-reviewer 差し戻しファースト表に Blocker パターン行が存在（行頭 `\|` で表行にアンカー・P4 bullet と誤一致しない） | `grep -qF '\| 合否基準が合格時に非ゼロ終了する' .claude/review-agents/plan-reviewer.md` |
| TC-05 | plan-issue SKILL のセルフチェック項目が存在 | `grep -q '合否判定インターフェースが exit code に統一' .claude/skills/plan-issue/SKILL.md` |
| TC-07 | fix-test-reviewer の観点 3 に exit code 向き一致の確認が存在 | `grep -q 'exit code の向きと一致しているか' .claude/review-agents/fix-test-reviewer.md` |
| TC-06 | 失敗注入（false-green 防止）: 該当行を欠いた入力で TC-01〜05・TC-07 が非ゼロ終了 | 計画時実証済み（2026-07-18・文言未追記の現状ファイルで全て exit 1。TC-07 も同日 exit 1 確認済み）。実装後、該当行を削除した一時コピーでも再確認 |
- pytest/Jest/E2E: 非該当（アプリコード変更なし）。
### 手動
- docs/tests/open/I122_manual_test.md 参照(追記箇所の実体確認 4 件 = Claude・追記文言の平易さ確認 1 件 = Human)。

## 7. ロールバック
- `git revert` のみ（ドキュメント 3 ファイルの行追記のみ。DB・設定・サービスへの影響なし）。

## 8. Risk & 回避策
- **R1: 追記文言と TC のセンチネル文字列の不一致**（実装時に文言を変えると TC が落ちる）→ 4 章の追記文言を全文固定し、TC は 4 章の文字列から機械的に採っている。文言を変える場合は計画書と TC を同時更新する。
- **R2: TC-04 が P4 観点の bullet に誤一致して表行の不在を見逃す** → 判定文字列の先頭を行頭のテーブル罫線 `|` にして表行のみに一致させる（bullet は `- ` 始まりのため一致しない。計画時に現状ファイルで exit 1 を確認済み）。
- **R3: 既存の grep 系決定論テスト（test_review_verdict.sh 等）が壊れる** → 対象 3 ファイルへの参照は「存在」チェックのみで、本計画は行追記のみ（既存行は不変更）のため影響なし（調査結果で機械確認済み）。
- **R4: fix-loop 経路の TC は plan-reviewer を通らず gate がかからない** → fix-test-reviewer.md を変更対象 D として含め、fix 経路にも gate 層を張る（ユーザー確定 2026-07-18）。番号付き観点リストの再採番は行わず観点 3 の継続行として追記するため、既存観点の参照（fix-loop SKILL 等からの観点番号言及）に影響しない。

## 9. セキュリティ・品質チェック（plan-issue 必須確認）
- **セキュリティ影響なし**（ハーネス文書 3 ファイルの行追記のみ。認証・認可・入力・機密データ・依存ライブラリの変更なし）。
- **P3/P5/P8 影響なし**（DB・外部API・非同期・バッチ・新規インフラ・依存関係ファイルの変更なし）。
- **P6 影響なし**（フロントエンド変更・性能懸念なし）。
- **P9 影響なし**（個人情報・未成年データ・テナントデータを扱わない）。
- **要件適合性**: 変更は AC の範囲内（4 章の追記文言は AC の文言要件をすべて含み、仕様追加なし）。マルチテナント・ステータス遷移: 非該当。
- **テスト計画**: 再発防止テスト = TC-01〜06（本イシュー自体が再発防止ルールの導入。TC は導入ルールを自文書で dogfood し合格=exit 0 に統一）。テストレベル = 決定論 grep テスト（ユニット相当）。認可テスト: 非該当。
- **Claude Code ベストプラクティス**: 指示ファイル変更（SKILL.md・review-agents）だが、追加はチェックリスト項目・レビュー観点の行追記のみで、allowed-tools・停止条件・分岐構造は変更しない。

## 10. 承認ポイント
- [x] 計画内容（変更点/影響）: 4 ファイルへの行追記（追記文言は 4 章に全文固定）・既存文言の変更なし
- [x] Danger Ops: 無（ドキュメント 4 ファイルのみ・ロールバックは revert のみ）
- [x] テスト計画: 決定論ゲート TC-01〜07（失敗注入は計画時実証済み）＋手動 5 件（Claude 4・Human 1）
- [x] 仮定事項の確認: fix-test-reviewer.md を対象に**含める**（ユーザー確定 2026-07-18。fix 経路の gate 欠落解消・理想/根治基準）

（承認済み: 2026-07-18。3 ファイル案で承認ポイント提示 → fix-test-reviewer の扱いを理想基準で再検討し「含める」で確定 → 4 ファイル案に更新のうえ /plan-issue-review へ）

## レビュー結果
（/plan-issue-review 実施後に記録）
