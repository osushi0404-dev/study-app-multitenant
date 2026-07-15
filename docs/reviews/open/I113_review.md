# I113 レビュー: /close の base 追従チェック（pr-base-sync.sh 新設）

## 基本情報
- **対象計画書**: docs/plans/open/plan_I113.md
- **関連イシュー**: #210（docs/issues/open/I113.md）
- **Draft PR**: #219

## レビュー目的
- mergeStateStatus 全8値の分岐が設計確認メモの確定内容（sync=取り込みのみ／final=フル・合格条件は「BEHIND/DIRTY でない＋CI 全グリーン」）と 1:1 で一致していること
- fail-closed が貫かれていること（コンフリクト STOP・未知値 STOP・UNKNOWN 継続はユーザー確認・自動解決なし）
- 決定論ゲート（T1〜T14）が false-green でないこと（TDD Red・注入検証の記録）
- 既存 /close 手順（step 1〜6）と code-review.sh が無改変であること

## 期待する成果
- close 作業中〜マージ依頼直前に base（develop）が進んだ場合を機械検知し、I107 型の out-of-date 見逃し（人間の目視頼み・fail-open）が構造的に再発しない
- 2 worktree 並行運用でのトラック間干渉（他トラック PR の先行マージ）に /close が自律追従する

## 変更概要
- base 追従チェック本体 `scripts/claude/pr-base-sync.sh` を新設（sync/final 2モード・全8値分岐・リトライ 5秒×6回・CI 待機 15秒/600秒）。/close SKILL.md の step 0 と新設 step 5.5 から呼び出す。決定論テスト（gh/git スタブ・T1〜T14）を新設。

## 変更点
- `scripts/claude/pr-base-sync.sh`: 新規（計画 4-1）
- `.claude/skills/close/SKILL.md`: step 0 へ sync 呼び出し追記（計画 4-2）＋step 5.5 新設（計画 4-3）
- `scripts/claude/tests/test_pr_base_sync.sh`: 新規（計画 4-4・決定論ゲート）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `scripts/claude/pr-base-sync.sh`・`scripts/claude/tests/test_pr_base_sync.sh`・`.claude/skills/close/SKILL.md`（運用スキル・決定論ゲートのみ）

## 実装結果評価
（実装完了後に記入）

## テスト結果
（/test 完了後に記入）

## 計画との差分
（実装完了後に記入）

## ロールバック
- スクリプト2ファイル追加＋SKILL.md 変更コミットの revert（データ・インフラ影響なし）。SKILL.md の呼び出し2行削除のみでも従来挙動に戻る
