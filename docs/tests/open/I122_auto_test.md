# I122 自動テスト: 決定論テストの合否判定インターフェース統一（合格=exit 0）

<!--
  実行コマンド欄の書き方（I117）:
  - heavy な実行例はインラインコード表記で書く。fenced の bash ブロックはここに作らない。
  - ゲート系コマンド（grep 判定等）は必ず「## 決定論ゲート（自動実走）」セクションに書く。
-->
実行コマンド（例）: 下記「決定論ゲート（自動実走）」の grep 6 件（pytest/Jest/E2E はアプリコード変更なしのため非該当）

結果:
- backend: 非該当（コード変更なし）
- frontend: 非該当（コード変更なし）
- 決定論ゲート: **全 TC 合格・exit 0**（2026-07-18 実装時実走・/code-review 決定論ゲート 6 件 exit=0・/test 再実走でも TC-01〜05/07 全て exit 0＋TC-06 注入 6 件全て exit 1。TC-04 は code-review 初回 BLOCKER 対応でパイプ文字なしの一意フレーズ判定に変更後の形で確認）

## テストケース一覧

| TC | 検証内容 | 判定コマンド（合格=exit 0） | 結果 |
|----|---------|---------------------------|------|
| TC-01 | plan-writing-rules.md の false-green 節に合否判定インターフェース統一規定が存在（AC1） | `grep -q '合否判定インターフェースの統一' docs/runbooks/plan-writing-rules.md` | OK（exit 0） |
| TC-02 | 同規定に不在判定の合格=exit 0 形（`! grep -q 文言 file`）の例示が存在（AC1） | `grep -qF '! grep -q 文言 file' docs/runbooks/plan-writing-rules.md` | OK（exit 0） |
| TC-03 | plan-reviewer.md の P4 観点に exit code 向き一致チェックが存在（AC2） | `grep -q 'exit code の向きと一致しているか' .claude/review-agents/plan-reviewer.md` | OK（exit 0） |
| TC-04 | plan-reviewer.md の差し戻しファースト「自動テストケース」表に Blocker パターン行が存在（AC3。表行の第1セル文言「合否基準が合格時に非ゼロ終了する」はファイル内で一意 — P4 観点は語順が異なる「…コマンドを合否基準にしていないか」のため不一致。`grep -c` で 1 件を機械確認済み） | `grep -q '合否基準が合格時に非ゼロ終了する' .claude/review-agents/plan-reviewer.md` | OK（exit 0・修正後再実走） |
| TC-05 | plan-issue/SKILL.md の文書品質ゲートにセルフチェック項目が存在（AC4） | `grep -q '合否判定インターフェースが exit code に統一' .claude/skills/plan-issue/SKILL.md` | OK（exit 0） |
| TC-07 | fix-test-reviewer.md の false-green 観点（観点3）に exit code 向き一致の確認が存在（AC5） | `grep -q 'exit code の向きと一致しているか' .claude/review-agents/fix-test-reviewer.md` | OK（exit 0） |
| TC-06 | 失敗注入（false-green 防止・AC6）: 該当行を欠いた入力に対し TC-01〜05・TC-07 の判定コマンドが非ゼロ終了する | 該当行を除去した一時コピー（mktemp・`grep -vF`）に対し各判定コマンドを実行 | OK（6 件全て exit 1・2026-07-18） |

- 合否インターフェース: **合格 = exit 0**（本イシューで導入するルールを本文書の TC 自体で dogfood する。不合格=非ゼロ終了・出力値の目視比較は合否基準にしない）。
- 計画時実証（2026-07-18・plan_I122 調査結果）: TC-01〜05・TC-07 の判定コマンドを**文言未追記の現状ファイル**に対して実行し、**全て exit 1（NG）**を確認済み（失敗条件で不合格になる＝false-green でない）。
- TC-04 の判定形の変更（2026-07-18・code-review 20260718_1303 の Blocker 対応）: 当初の行頭罫線アンカー `grep -qF '| ...'` は、コマンド文字列中の `|` を code-review.sh のゲート分類器がシェルパイプと誤判定し「実走対象外（fail-closed）」→ BLOCKER 化するため、パイプ文字を含まない一意フレーズ判定に変更した。表行への限定は文言一意性（上記 grep -c = 1）で担保する。分類器側の精緻化は別イシュー候補。
- TC-06 注入手順（実装後の再確認・各 TC ごとに実施）: ①`TMP=$(mktemp)` ②`grep -v '<当該 TC の判定文言>' <対象ファイル> > "$TMP"`（該当行を除去したコピーを作成） ③当該 TC の判定コマンドの対象ファイルを `"$TMP"` に replace して実行し**非ゼロ終了**を確認 ④`rm -f "$TMP"`。6 件の判定コマンド（TC-01〜05・TC-07）すべてで非ゼロ終了になれば TC-06 合格。

## 決定論ゲート（自動実走）
```bash
grep -q '合否判定インターフェースの統一' docs/runbooks/plan-writing-rules.md
grep -qF '! grep -q 文言 file' docs/runbooks/plan-writing-rules.md
grep -q 'exit code の向きと一致しているか' .claude/review-agents/plan-reviewer.md
grep -q '合否基準が合格時に非ゼロ終了する' .claude/review-agents/plan-reviewer.md
grep -q '合否判定インターフェースが exit code に統一' .claude/skills/plan-issue/SKILL.md
grep -q 'exit code の向きと一致しているか' .claude/review-agents/fix-test-reviewer.md
```
