# I480 自動テスト: SECURITY=yes でも Low・再現なしの指摘は軽い指摘の一覧に回す

実行コマンド: 下の「決定論ゲート」。pytest・Jest・E2E は対象のコードが無いので対象外（CI の `scripts/claude/tests/run-all.sh` も同じテストを流す）

結果:
- 計画時のベースライン（2026-11-13・変更前）: `test_i202_ledger_cleanup.sh` pass=157 fail=0・`test_i205_stop_criteria.sh` pass=91 fail=0
- TC-01〜TC-03: 実装前のため未実行（Q10 は実装の後でないと書けない）

| TC | AC | 内容 | 期待（合格=exit 0） | 失敗の注入 |
|---|---|---|---|---|
| TC-01 | AC1・AC2・AC3 | `test_i202_ledger_cleanup.sh` の Q10（plan §6 の F1〜F6 の台帳）と、直した Q7 | Q10 は `I:F3,F4,F5,F6 B:F1,F2`・理由に `SECURITY=yes` を含む後続イシューの行が F3・F4・F6 の 3 行・F5 の理由は `アプリ本体` だけ。Q7 は `I:F1,F7,F9,F12 B:F2,F3,F4,F5,F6,F8,F10,F11`。スクリプト全体が exit 0 | FG-Q10a: 条件を `if sec == "yes":` に戻すと F1・F2 が後続イシュー側で不合格／FG-Q10b: `if sec == "yes" and RANK[sev] >= 1:` で F3 が一覧側で不合格／FG-Q10c: `if sec == "yes" and repro == "yes":` で F4・F6 が一覧側で不合格／FG-Q7: 前の条件に戻すと F8 が後続イシュー側で不合格。どれもテストの中で写しを壊して確かめる（本物は書き換えない） |
| TC-02 | AC5 | `test_i205_stop_criteria.sh` 全体（止める判定）と `test_i202_ledger_cleanup.sh` の止める判定の項目 | どちらも exit 0（`blocking()` は変えないので期待値も変えない） | 既存の各 FG（このイシューでは足さない） |
| TC-03 | AC4 | retro 4-0 の 154 行・163 行と review-rules 70 行の説明が plan §4 の新しい決まりと一致している | 「重さに関係なく」が retro に無く、`SECURITY=yes` の条件が「再現ありか Medium 以上」、最優先の条件が「理由に `SECURITY=yes` が付いた行」になっている（manual_test No.1 で Claude が読んで確かめる。文言の固定テストは作らない・plan §6） | — |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i202_ledger_cleanup.sh
bash scripts/claude/tests/test_i205_stop_criteria.sh
```
