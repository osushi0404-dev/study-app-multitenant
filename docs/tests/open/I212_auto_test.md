<!--
## 自動テスト品質基準
各テストケースが以下を満たすことを確認してください:
- アサーションに具体的な期待値（status_code の数値・body の具体フィールド等）があるか
- 「正常レスポンスを確認」のような曖昧な記述になっていないか
- 他テナントデータへのアクセス拒否テストが含まれているか（認可変更がある場合）
- テストが実装詳細をトレースするだけでなく、仕様を検証する形になっているか
-->

# I212 自動テスト: 差分のレビューの起点を「見終えた最新の記録」にする

実行コマンド（例）: 下の「決定論ゲート（自動実走）」のコマンド（pytest・Jest・E2E は対象外。アプリのコードを変えない）

結果:
- backend: 対象外
- frontend: 対象外

## テストケース

| TC | 対象 | 中身と期待値（合格=exit 0） | 失敗の注入（FG） |
|---|---|---|---|
| TC-01 | 既存のハーネステスト | `test_i197_review_ledger.sh`（R1 の記録に `REVIEW_COMPLETE: YES` を足し、FG-R1 の置き換え前の文字列を新しい形に合わせた版）・`test_i193_official_flow.sh`（C23 の「読めた結果 → OK」の出力に `SECURITY_FINDINGS: 0` の行を足した版）・`test_i202_ledger_cleanup.sh`（変更なし）・`test_review_gates.sh`（変更なし）が全 PASS で exit 0 | 既存のテストの FG のまま |
| TC-02 | 起点の選び方・見終えたかの行（`test_i212_review_base.sh` の U1〜U6・U8・E1・E2） | U1: 記録 A（周 1・`REVIEW_COMPLETE: YES`・c1）→ B（周 2・`NO`・c2）で `review_mode I900 develop` が `delta｜3｜c1｜<B>`。U2: さらに C（周 3・`NO`・c2）で `delta｜4｜c1｜<C>`。U3: A も `NO` なら `delta｜4｜<develop との merge-base>｜<C>`。U4: 最新が `VERDICT: HIGH`・`REVIEW_COMPLETE: YES` ならその記録の SHA が起点。U5: `REVIEW_COMPLETE` の行が無い記録は起点にしない。U6: 見終えた記録の SHA が HEAD の祖先でなければ起点にしない。U8: `neutralize_machine_lines` が `REVIEW_COMPLETE: YES` を `> REVIEW_COMPLETE: YES` にする。E1: パス判定 YES のブランチで 1 周目の `/security-review` が判定の行を出さない → `FINAL_VERDICT: HIGH`・記録に `REVIEW_COMPLETE: NO`・gate-check が `GATE_CHECK: FAIL REASON=verdict`。記録だけのコミットの後の 2 周目 → 出力に `範囲のファイル 0 本` と `呼ばずに台帳を引き継ぎます` が無い・偽の claude の呼び出しに agent と security がある・`FINAL_VERDICT: OK`・記録に `REVIEW_COMPLETE: YES` と `LEDGER_ROUND: 2`・gate-check が `GATE_CHECK: OK`。E2: その後に記録の場所だけ変えた 3 周目は、範囲 0 本でレビュー役を呼ばない・`REVIEW_COMPLETE: YES`。スクリプト全体が `fail=0` で exit 0 | FG-U1（`if record_complete "$rec" &&` → `if : &&`）で U1 が不合格／FG-E1（本体の写しの起点を最新の記録の SHA に戻す）で E1 の 2 周目が範囲 0 本になり不合格／FG-U8（`neutralize_machine_lines` の一覧から `REVIEW_COMPLETE` を外す）で U8 が不合格。実装の前に、直す前の本体で U1〜U3・U5・U8・E1 が不合格になることを確かめて記録する |
| TC-03 | `/security-review` の判定（`test_i212_review_base.sh` の U7・`test_i193_official_flow.sh` の C23） | `official_security_verdict`: YES＋最後の行 `SECURITY_FINDINGS: 0` → OK／YES＋`SECURITY_FINDINGS: 2` → OK／YES＋「報告する脆弱性はありません。」だけ → HIGH／YES＋`SECURITY_FINDINGS: 0` の後に締めの文 → OK／YES＋文の中に `SECURITY_FINDINGS: 0` の語がある行だけ（行全体ではない）→ HIGH／YES＋`(実行できず: exit=124。124 は時間切れ)` → HIGH／YES＋`(実行していない: 差分なし)` → OK／NO → OK | FG-U7（行頭の固定 `^SECURITY_FINDINGS:` を外す）で「文の中に語がある行だけ → HIGH」が OK になり不合格。直す前の版で「報告する脆弱性はありません。」だけ → HIGH が OK になる（期待と違う）ことを記録する |
| TC-04 | G10 の語の境目（`test_i223_gh_app.sh`） | `g10_fg "和文がすぐ続く auth token は不合格" 1 'gh auth tokenを打つ'` が PASS。既存の G10 と FG はそのまま PASS。スクリプト全体が `fail=0` で exit 0 | 直す前の `\b` の版では新しい `g10_fg` が rc=0 で FAIL になる（実装の前に確かめて記録する） |
| TC-05 | 構文 | `code-review.sh`・`test_i212_review_base.sh` の `bash -n` が exit 0 | — |

## 実行記録

| 日時 | TC | 結果 | メモ |
|---|---|---|---|
| 2026-11-08 | TC-01（計画の時点のベースライン・直す前） | OK | `test_i197_review_ledger.sh` pass=64 fail=0・`test_i193_official_flow.sh` pass=174 fail=0・`test_i202_ledger_cleanup.sh` pass=157 fail=0・`test_i223_gh_app.sh` pass=37 fail=0 |
| 2026-11-08 | TC-02〜TC-05 | 実装前のため未実行 | 新しいテストのファイルは実装のステップ 1 で書く |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i212_review_base.sh
bash scripts/claude/tests/test_i197_review_ledger.sh
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_i202_ledger_cleanup.sh
bash scripts/claude/tests/test_review_gates.sh
bash scripts/claude/tests/test_i223_gh_app.sh
bash -n scripts/claude/code-review.sh
bash -n scripts/claude/tests/test_i212_review_base.sh
```
