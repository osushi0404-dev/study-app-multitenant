# I064 手動テスト

対象: レビュー命名・状態管理規約の一本化（`review-rules.md` / `plan-writing-rules.md` ヘッダ / `issue-flow.md`）。
本イシューはドキュメント規約のみで UI 変更がないため、確認は文書通読中心。ファイル通読・整合確認は Claude で実施可。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `review-rules.md` を通読し、命名・状態・採番の記述が新系統（`IXXX_review.md` / `IXXX_{code,plan,issue}_review_<ts>.md` / open・closed）で一貫しているか確認 | 旧系統（`reviewXXX` 通し番号・`_post`・`in_progress`）の記述が残らず、新旧併存による誤読が生じない。かつ簡素化後も「レビュー作成は必須」「実装後評価は `IXXX_review.md` に記録する」旨の説明が残り、必須性コンテンツが欠落していない | Claude | - | |
| 2 | `plan-writing-rules.md` の「## 基本情報」ヘッダブロックを通読 | `作成根拠資料`=issue パス / `実装後評価`=`IXXX_review.md`（または未作成）/ `Draft PR` 行あり。`reviewXXX`/`_post` 概念が残らない | Claude | - | |
| 3 | `issue-flow.md` の計画書命名（ステップ6）と close 移動（ステップ23/24）を通読 | 命名が `plan_I###.md`、close グロブが `plan_IXXX*.md`（無印・再作成版の双方を拾う）で実体と一致 | Claude | - | |
| 4 | 3ファイル横断で、レビュー/計画書の命名規約に矛盾がないか確認 | runbook 間で命名・状態の記述が一致し、相互参照リンクも新系統（`IXXX_review.md`）を指す | Claude | - | |
| 5 | 命名無関係部分（A/B/C/D 必須要素・スキル変更時の準拠チェックリスト）が保持されているか確認 | 削除・改変されず原文の趣旨を維持 | Claude | - | |
