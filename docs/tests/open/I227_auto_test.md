<!--
## 自動テスト品質基準
各テストケースが以下を満たすことを確認してください:
- アサーションに具体的な期待値（status_code の数値・body の具体フィールド等）があるか
- 「正常レスポンスを確認」のような曖昧な記述になっていないか
- 他テナントデータへのアクセス拒否テストが含まれているか（認可変更がある場合）
- テストが実装詳細をトレースするだけでなく、仕様を検証する形になっているか
-->

# I227 自動テスト: レビューの判定を機械が読む形・変数に置き換える

実行コマンド（例）: 下の「決定論ゲート（自動実走）」のコマンド（pytest・Jest・E2E は対象外。アプリのコードを変えない）

結果:
- backend: 対象外
- frontend: 対象外

## テストケース

| TC | 対象 | 中身と期待値（合格=exit 0） | 失敗の注入（FG） |
|---|---|---|---|
| TC-01 | 既存のハーネステスト | `test_i193_official_flow.sh`（C8 を `official_output_readable code …` の形にし、空の配列の入力を ```` ```json ```` の囲みにした版。C12 の和文の文は期待を 1〔読めていない〕に替えた版。C23 を 3 引数にした版）・`test_i197_review_ledger.sh`（変更なし。185 行目の呼び出しの部分一致が通る）・`test_i202_ledger_cleanup.sh`（変更なし）・`test_review_gates.sh`（変更なし）が全 PASS で exit 0 | 既存のテストの FG のまま |
| TC-02 | `/security-review` の判定（`test_i212_review_base.sh` の U7・U9） | U7（`NO_DELTA=0`）: YES＋`SECURITY_FINDINGS: 0` の行 → OK／`SECURITY_FINDINGS: 2` → OK／和文の「報告する脆弱性はありません。」だけ → HIGH／判定の行の後に締めの文 → OK／文の中に `SECURITY_FINDINGS: 0` の語があるだけ → HIGH／`(実行できず: exit=124…)` → HIGH／NO → OK。U9: YES＋`NO_DELTA=0`＋出力 `(実行していない: 差分なし)` だけ → HIGH／YES＋`NO_DELTA=0`＋本文の中に `(実行していない: 差分なし)` を引用し判定の行なし → HIGH／YES＋`NO_DELTA=1`＋出力が空 → OK／YES＋`NO_DELTA=1`＋判定の行の無い文 → OK／YES＋`NO_DELTA` が空＋判定の行なし → HIGH | FG-U7（`findings_line_present` の行全体の固定 `^…$` を外す）で「文の中の語だけ → HIGH」が OK になり不合格／FG-U9（`NO_DELTA` の判定を前の文字列の部分一致に戻す）で「引用だけ → HIGH」が OK になり不合格。実装の前に、直す前の本体で U9 の引用のケースが OK（期待と違う）になることを確かめて記録する |
| TC-03 | 「読めたか」（`test_i212_review_base.sh` の U10） | `official_output_readable`: `code`＋```` ```json ```` の囲みの指摘の配列（`"file"` つき）→ exit 0／`code`＋囲みの中が `[]` → 0／`code`＋囲みの無い裸の配列 `[ {"file": "a.sh"} ]` → 0／`code`＋```` ```python ```` の囲みの後に ```` ```json ```` の囲みの指摘の配列 → 0／`code`＋「指摘はありません。」だけ → 1／`code`＋`No issues found.` だけ → 1／`code`＋本文に `"file": "a.sh"` の語があるだけ → 1／`code`＋`[1, 2]`（要素に `"file"` が無い）→ 1／`code`＋`SECURITY_FINDINGS: 0` の行だけ → 1／`security`＋`SECURITY_FINDINGS: 0` の行 → 0／`security`＋指摘の配列だけ → 1／`security`＋「報告する脆弱性はありません。」だけ → 1／種類が空＋指摘の配列 → 1 | FG-U10（`code` の判定を前の和文の正規表現に替える）で「指摘はありません。だけ → 1」が 0 になり不合格。実装の前に、直す前の本体（引数 1 つ）で和文の文だけが読めた（exit 0）になることを確かめて記録する |
| TC-04 | 差分なしの回の通し（`test_i212_review_base.sh` の E2・既存） | パス判定 YES のブランチで、見終えた記録の後に記録の場所だけ変えた 3 周目（`NO_DELTA=1`）は、範囲 0 本・claude を呼ばない・記録に `REVIEW_COMPLETE: YES`（`SECURITY_VERDICT` が OK）。スクリプト全体が `fail=0` で exit 0 | FG-E2（本体の写しの呼び出し `official_security_verdict "$RISK_PATH" "$NO_DELTA" "$OFFICIAL_SECURITY"` の `"$NO_DELTA"` を `0` にする）で 3 周目が `REVIEW_COMPLETE: NO` になり不合格 |
| TC-05 | 判定の行の正規表現が 1 か所 | `code-review.sh` に `findings_line_present()` の定義があり（`grep -q` が exit 0）、`FINDINGS:[[:space:]]` の形の書き込みの正規表現が無い（`! grep -qF` が exit 0） | 直す前の本体（95 行目・188 行目に `SECURITY_FINDINGS:[[:space:]]` がある）では、2 本とも不合格（実装の前に確かめて記録する） |
| TC-06 | 構文 | `code-review.sh`・`test_i212_review_base.sh`・`test_i193_official_flow.sh` の `bash -n` が exit 0 | — |

## 実行記録

| 日時 | TC | 結果 | メモ |
|---|---|---|---|
| 2026-11-08 | TC-01（計画の時点のベースライン・直す前） | OK | `test_i212_review_base.sh` pass=31 fail=0・`test_i193_official_flow.sh` pass=174 fail=0・`test_i197_review_ledger.sh` pass=64 fail=0 |
| 2026-11-08 | TC-02〜TC-04（計画の時点） | 実装前のため未実行 | テストを先に書くのはステップ 1 |
| 2026-11-08 | TC-05（計画の時点・直す前） | 期待どおり NG | 下の 2 本のうち、`grep -q '^findings_line_present()'` は定義が無く exit 1、`! grep -qF 'FINDINGS:[[:space:]]'` は 95・188 行目に当たり不合格 |
| 2026-11-08 | TC-02・TC-03（テストを先に書き、本体を直す前） | 期待どおり NG | `test_i212_review_base.sh` pass=35 fail=15（U7 の判定の行あり → OK が HIGH・U9 の NO_DELTA=1 → OK が HIGH・U10 の読めたが 1・FG は置き換え前の文字列が無く未成立）。直す前の関数そのもので、`official_security_verdict YES 'スクリプトは (実行していない: 差分なし) と書くと OK にします。'` が `OK`（F1 の穴の再現）、`official_output_readable '指摘はありません。'` が exit 0（言い回しで読めた）を確かめた |
| 2026-11-08 | TC-01〜TC-06（実装・/simplify の整理の後） | OK | `test_i212_review_base.sh` pass=50 fail=0（FG-U7・FG-U9・FG-U10・FG-E2 がすべて成立）・`test_i193_official_flow.sh` pass=174・`test_i197_review_ledger.sh` pass=64・`test_i202_ledger_cleanup.sh` pass=157・`test_review_gates.sh` PASS=67、すべて fail=0。TC-05: `findings_line_present()` の定義あり・`FINDINGS:[[:space:]]` の残りは 0。`bash -n` 3 本 exit 0 |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i212_review_base.sh
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_i197_review_ledger.sh
bash scripts/claude/tests/test_i202_ledger_cleanup.sh
bash scripts/claude/tests/test_review_gates.sh
grep -q '^findings_line_present()' scripts/claude/code-review.sh
! grep -qF 'FINDINGS:[[:space:]]' scripts/claude/code-review.sh
bash -n scripts/claude/code-review.sh
bash -n scripts/claude/tests/test_i212_review_base.sh
bash -n scripts/claude/tests/test_i193_official_flow.sh
```
