# I086 レビュー: 高リスク変更の敵対的レビューステージ自動化

- 関連イシュー: #169
- 対象計画書: docs/plans/open/plan_I086.md

## 変更概要
- /code-review の高リスク判定を機械可読化（RISK 行 fail-closed＋パス決定論トリガ）し、高リスク時のみ敵対的レビューステージ（反証マンデート×固定 3 観点＋動的最大 2・loop-until-dry・依頼側修正→対応後再レビュー・上限打ち切り）をスキル主導で自動起動する。実装者の自己認証を非権威化。

## 変更点
- scripts/claude/code-review.sh: `detect_risk_flag`（RISK 行 anchored 解析・欠落/不正形式=YES fail-closed）と `path_risk_trigger`（監視 7 パスの決定論トリガ）を追加し、高リスク判定を GATE_EVIDENCE 証跡＋機械可読 stdout（REVIEW_FILE / RISK / FINAL_VERDICT / ADVERSARIAL_STAGE 行）に結線。OK 分岐の案内を高リスク時の敵対ステージ案内に分岐
- .claude/review-agents/code-reviewer.md: 「高リスク判定の条件」（plan-reviewer 11 条件＋harness 固有）と RISK 行の出力仕様（VERDICT 行直前・fail-closed 明記）を追記
- .claude/review-agents/adversarial-reviewer.md（新規）: 反証マンデートのレビューア定義（インジェクション防御・観点/既知 findings プレースホルダ・Bash 安全境界・実機 repro・NEW_CRITICAL/NEW_HIGH 機械集計行）
- .claude/skills/code-review/SKILL.md: 敵対的レビューステージのオーケストレーション（固定 3 観点＋動的最大 2・並列 Agent 起動・loop-until-dry・最大 3 周/総数 15・打ち切りエスカレーション・依頼側修正・記録/commit/PR コメント/最終判定合成）。allowed-tools を Bash 単独から Bash/Read/Grep/Glob/Edit/Write/Agent へ拡張
- docs/runbooks/review-rules.md: 「高リスク変更の敵対的レビューステージ（自己認証の非権威化）」規定と命名表 `I###_adversarial_review_<timestamp>.md` 行を追加
- scripts/claude/tests/test_adversarial_trigger.sh（新規）: 判定関数 16 系＋結線 4 系の決定論テスト（TDD Red→Green 実施・20 アサート）

## 影響範囲
- Backend/Frontend/DB: なし・Config はハーネススクリプト/文書 5 変更＋新規 2（adversarial-reviewer.md・test_adversarial_trigger.sh）

## テスト結果
- 自動: 決定論ゲート全 14 件 exit=0＋TC-11 注入 9 件全て非ゼロ＋既存ハーネステスト 17 本 PASS（2026-07-19 実装時実走。/code-review・/test での再実走結果は追記）
- 手動: （/test 時に記録）

## 計画との差分
- （実装後に記録）

## ロールバック
- git revert のみ（DB・設定・サービス影響なし。revert で現行フローに完全復帰）
