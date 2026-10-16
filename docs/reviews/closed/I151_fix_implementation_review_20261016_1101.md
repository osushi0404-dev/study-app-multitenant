# 実装レビュー [I074]

## 指摘一覧

| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 前回NG指摘の解消 | H1（GitHub #266/#274 本文への同期）は diff 外の外部操作のため直接確認不可。ただし review.md §10 AC・手動 No.8・計画書に「GitHub 本文への反映確認」が要件として明記されており、手動テストで担保される設計。diff 上で追える範囲は達成 | review.md §10・手動 No.8・plan §2-8 |

## 判定の根拠

### H2（beat→broker→worker 経路）の解消を確認

- 判定 1c（`update_daily_analytics_task` succeeded ≥ 2 件）追加 ✓
- 判定 2c・2d（beat ログの ERROR / Traceback = 0）追加 ✓
- 合格条件が `1・1b・1c・2a・2b・2c・2d・3s・3a・3b・4a・4b` に更新 ✓
- `Scheduler.apply_entry` の動作（送信前に `Sending due task` を出す）の根拠説明を追記 ✓

### M1（実メール危険）の記述正確化を確認

- `celery_probe.py`：beat の定期実行は対象外と明記、`settings.DEBUG` ガード（`DEBUG=False` なら `NG PROBE ABORTED` で終了）追加 ✓
- `auto_test.md`：`locmem で止めるのはスクリプトが足す 1 回分だけ` と明記 ✓
- 計画書・I151.md：既存の問題として `send_study_reminders_task` の SMTP 常設設定リスクを記録 ✓

### M2（承認記録の統一）を確認

- I151.md（7-B・Danger Ops）、計画書（ステップ1・§テスト）、auto_test.md すべてで「条件付きのユーザー承認（理想的・最適なものを基準として問題ないなら OK。条件の充足は Claude が判定し、敵対的レビューで検証）」に統一 ✓

### M3（後続イシュー追跡）を確認

- 計画書ステップ5 に `/close` での PR 本文「後続タスク」節への列挙を追加 ✓
- 手動 No.8 に確認項目追加 ✓
- review.md §10 に対応 AC チェック追加 ✓

### M4（既存不具合の記録・TC-AUTO-03 訂正）を確認

- `send_study_reminders_task` の `User.get_full_name` 不在を §2-8 に記録 ✓
- 「TC-AUTO-03 が担う」を「tasks を参照するテストは 0 件」に訂正 ✓

### M5・L（各種訂正）を確認

- review.md §7 を現行判定（判定 1c・2c・2d 含む）に更新 ✓
- 「同じイメージ・同じ版」→「別イメージだが依存の版は一致」に訂正 ✓
- 判定 3s の説明を「件数だけを見る」と正確化 ✓
- auto_test.md 冒頭注記を「第 1〜3 周」に更新 ✓

### スコープ整合

未追跡新規ファイル群（I074〜I165 等のイシュー・レビューファイル多数）は、プロジェクトの invariant 管理（MEMORY.md に `全ローカル未コミット` と記録された各種ファイル）であり、I151 fix-loop の修正対象外。I151 の PR には含まれない設計になっており、スコープ逸脱なし。

修正対象の 5 ファイル（I151.md・plan_I151.md・I151_review.md・I151_auto_test.md・I151_celery_probe.py）はすべて診断メモ案1の方針範囲内。

VERDICT: OK
