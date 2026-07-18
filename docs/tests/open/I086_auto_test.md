# I086 自動テスト: 高リスク変更の敵対的レビューステージ自動化

<!--
  実行コマンド欄の書き方（I117）:
  - heavy な実行例はインラインコード表記で書く。fenced の bash ブロックはここに作らない。
  - ゲート系コマンド（grep 判定等）は必ず「## 決定論ゲート（自動実走）」セクションに書く。
-->
実行コマンド（例）: 下記「決定論ゲート（自動実走）」の 12 件（pytest/Jest/E2E はアプリコード変更なしのため非該当）

結果:
- backend: 非該当（コード変更なし）
- frontend: 非該当（コード変更なし）
- 決定論ゲート: （/code-review・/test 時に記録）

## テストケース一覧

| TC | 検証内容 | 判定コマンド（合格=exit 0） | 結果 |
|----|---------|---------------------------|------|
| TC-01 | 新規テストスクリプト全アサート合格: detect_risk_flag（YES／NO／行欠落=YES fail-closed／装飾付き=YES fail-closed／複数行 tail -1）・path_risk_trigger（監視 7 パターン各 YES・tests 配下 YES・非対象 NO・空 NO・混在 YES）・結線行の存在（AC1/5/7） | `bash scripts/claude/tests/test_adversarial_trigger.sh` | |
| TC-02 | code-review.sh の bash 構文健全性 | `bash -n scripts/claude/code-review.sh` | |
| TC-03 | code-reviewer.md に高リスク判定の条件リストが存在（AC1） | `grep -q '高リスク判定の条件' .claude/review-agents/code-reviewer.md` | |
| TC-04 | code-reviewer.md に機械判定用 RISK 行の仕様が存在（AC1） | `grep -q '機械判定用の RISK 行' .claude/review-agents/code-reviewer.md` | |
| TC-05 | SKILL.md に敵対的レビューステージのフローが存在（AC1/2） | `grep -q '敵対的レビューステージ' .claude/skills/code-review/SKILL.md` | |
| TC-06 | SKILL.md に上限（最大 3 周・総数 15・打ち切り）が存在（AC3/7） | `grep -q '最大 3 周' .claude/skills/code-review/SKILL.md` | |
| TC-07 | adversarial-reviewer.md に反証マンデートが存在（AC2） | `grep -q '合格判定を反証' .claude/review-agents/adversarial-reviewer.md` | |
| TC-08 | review-rules.md に自己認証の非権威化規定が存在（AC4） | `grep -q '自己レビューは判定根拠にしない' docs/runbooks/review-rules.md` | |
| TC-09 | review-rules.md の命名表に敵対的レビュー監査記録の行が存在（AC4） | `grep -q 'adversarial_review' docs/runbooks/review-rules.md` | |
| TC-10 | code-review.sh を source する既存テスト 3 本の無回帰（AC5） | `bash scripts/claude/tests/test_review_verdict.sh`・`bash scripts/claude/tests/test_review_gates.sh`・`bash scripts/claude/tests/test_review_commit_lifecycle.sh` | |
| TC-11 | 失敗注入（false-green 防止）: grep 系 TC（TC-03〜09）が該当行を欠いた入力に対し非ゼロ終了する | 手順は下記「TC-11 注入手順」参照 | 計画時実証済み（2026-07-19・未実装の現状ファイルで 10 件全て非ゼロ終了。scratchpad i086_tc_prerun.sh） |

- 合否インターフェース: **合格 = exit 0**（不合格=非ゼロ終了・出力値の目視比較は合否基準にしない）。
- 計画時実証（2026-07-19・plan_I086 調査結果）: TC-01〜09 相当の判定を**文言未追記・未実装の現状ファイル**に対して実行し、**全て非ゼロ終了（NG）**を確認済み（失敗条件で不合格になる＝false-green でない）。
- センチネル文言にはパイプ文字を含めない（code-review.sh の gate 分類器がシェルパイプと誤判定して fail-closed になる I122 事象の回避。分類器根治は I130）。
- TC-11 注入手順（実装後の再確認・grep 系 TC ごとに実施）: ①`TMP=$(mktemp)` ②`grep -v '<当該 TC の判定文言>' <対象ファイル> > "$TMP"`（該当行を除去したコピーを作成） ③当該 TC の判定コマンドの対象ファイルを `"$TMP"` に replace して実行し**非ゼロ終了**を確認 ④`rm -f "$TMP"`。TC-03〜09 の 7 件すべてで非ゼロ終了になれば TC-11 合格。

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_adversarial_trigger.sh
bash -n scripts/claude/code-review.sh
grep -q '高リスク判定の条件' .claude/review-agents/code-reviewer.md
grep -q '機械判定用の RISK 行' .claude/review-agents/code-reviewer.md
grep -q '敵対的レビューステージ' .claude/skills/code-review/SKILL.md
grep -q '最大 3 周' .claude/skills/code-review/SKILL.md
grep -q '合格判定を反証' .claude/review-agents/adversarial-reviewer.md
grep -q '自己レビューは判定根拠にしない' docs/runbooks/review-rules.md
grep -q 'adversarial_review' docs/runbooks/review-rules.md
bash scripts/claude/tests/test_review_verdict.sh
bash scripts/claude/tests/test_review_gates.sh
bash scripts/claude/tests/test_review_commit_lifecycle.sh
```
