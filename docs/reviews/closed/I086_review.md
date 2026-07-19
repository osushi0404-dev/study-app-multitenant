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
- 自動: 決定論ゲート全 14 件 exit=0＋TC-11 注入 9 件全て非ゼロ＋既存ハーネステスト 17 本 PASS（2026-07-19 実装時実走）。test_adversarial_trigger.sh は敵対レビュー対応で 20→40 アサートに拡充・全 PASS。
- 手動: （/test 時に記録）

## 敵対的レビューステージ（ドッグフード・本イシューの自己適用）
本イシューは `.claude/skills/` 等の変更を含むためパス決定論トリガで RISK=YES となり、実装した敵対ステージが**自分自身に対して初めて自動起動**した（AC1/AC6 の実地検証）。基本レビュー（`claude -p`）FINAL_VERDICT OK・決定論ゲート 14 件 exit=0 だったにもかかわらず、独立ステージが設計・実装の穴を検出:
- 周回1（固定 3 観点＋観点①深掘り）: New High 5（H1 非権威化の構造未達／H2 RISK 行 fail-open（引用注入）／H3 非 ASCII パス fail-open（core.quotePath）／H4 監視パスに指示階層欠落／H5 配線の false-green）。記録: `docs/reviews/I086_adversarial_review_20260719_1225.md`
- 対応: H2/H3/H4/H5 を本イシューで根治（RISK 行探索を VERDICT 近傍に限定・GIT_FILES を quotePath=false・監視パスに CLAUDE.md/workflow.md/review-rules.md/.claude/agents/ 追加・配線を関数化＋挙動/変異テスト）。H1（下流ゲート新設）はスコープ大のため別イシュー化（ユーザー承認 2026-07-19）。
- 周回2（修正差分に 2 観点）: New High 1（H6 本体配線が引数レベルの誤配線でも全緑）。対応: emit を関数化し本体配線 4 行を厳密文字列 grep で固定（誤配線 3 パターンの検出を変異テストで確認）。
- ＝ 基本レビュー・決定論ゲートが見逃す欠陥を敵対ステージが捕捉した実証（ステージが load-bearing）。

## 計画との差分
- （実装後に記録）

## ロールバック
- git revert のみ（DB・設定・サービス影響なし。revert で現行フローに完全復帰）
