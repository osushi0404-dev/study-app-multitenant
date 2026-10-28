# I210 手動テスト: ハーネスのテスト N10（敵対的レビューの締め切り）が実時間に依存して揺れるのを直す

負荷をかけた状態での繰り返し（AC1）と、前の形の判定スクリプトに新しい回帰テストを当てたときに落ちること（AC6 の失敗注入）を、test-gate で Claude が確かめる。どちらもコマンドの実行と出力の確認だけで、画面・承認画面は関係しない。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `bash scripts/claude/tests/stress-repeat.sh 20 scripts/claude/tests/test_i202_ledger_cleanup.sh` を Bash ツールの `run_in_background` で流す（負荷は CPU の数だけのループ） | `RUN 1: PASS` 〜 `RUN 20: PASS` の 20 行と `STRESS: 20/20`、exit 0 | Claude |  | AC1。1 回 約 1 分なので 20〜30 分かかる |
| 2 | 前の判定スクリプトを写して当てる: `git show 506f3ee5:scripts/claude/check-frontend-evidence.sh` の出力をスクラッチパッドの `old_check.sh` に保存し、`CHECK=<そのファイルの絶対パス> bash scripts/claude/tests/test_check_frontend_evidence.sh` を流す | exit 1。出力に `FAIL E16 frontend/src と大きな一覧（記録なし）は対象で不合格 expected=1 got=0`（ほかの E1〜E15・E17・E18 は PASS） | Claude | OK（2026-10-28・implement で実施）: exit 1。`FAIL E16 … expected=1 got=0` の 1 件だけで、ほかの 18 項目は PASS（pass=18 fail=1） | AC6 の失敗注入（テストに入れない理由: 計画書 6・一覧 I195 F11） |

結論:
