# I185 レビュー: 開発環境の総点検と改善

## 変更概要
- 段 A: 開発環境の点検報告書 `docs/proposals/I185_dev_env_review.md` を作成し、改善案の採否を決める
- 段 B: 採用した改善 P1〜P5 を実装する（計画変更記録 2）
  - P1 編集直後の構文チェックの終了コードを 2 にする
  - P2 計画のレビューを人の承認の前に済ませる
  - （P3 fix-loop の自動進行は、敵対的レビュー 2 周で穴が続いたため別イシューへ移した）
  - P4 スキルの `allowed-tools` を外し、制限は `disallowed-tools` にする
  - P5 セッション開始時に状態をフックで渡す
- /close 時: 効果測定イシューの起票と、1 週間後のクラウドの 1 回限りの予約

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/settings.json`（SessionStart フック追加）・`scripts/claude/hooks/`（posttooluse_check.py の修正・sessionstart_context.py の新規）・`.claude/skills/*/SKILL.md`（11 本の frontmatter・plan-issue の手順・security-review・retro の記述）・`docs/runbooks/workflow.md`・`issue-flow.md`・`onboarding.md`・`review-rules.md`・`.claude/review-agents/plan-reviewer.md`・`scripts/claude/plan-issue-review.sh`（判定不能で止める）・`scripts/migration_verify/lint_skills.py`・`docs/claude-code-structure.md`・`scripts/claude/tests/`（新規 3 本・fixtures・test_review_verdict.sh の更新）

## テスト結果
- 自動: 決定論ゲート 16 件すべて合格（/test・ba27f3f）。pytest・Jest・E2E は非該当（アプリのコード変更なし）。既存のハーネスのテスト 33 本のうち 31 本合格・2 本（D8・DOC6）は今回の変更と無関係の不合格（P12 の別イシューに同梱）
- 手動: No.1〜No.8 すべて OK（全項目 Claude 実施）
- レビュー: 基本レビュー OK（`I185_code_review_20261024_1846.md`）。敵対的レビュー 2 周で上限到達 → ユーザー一任で方式の見直し（`I185_adversarial_review_20261024_1950.md`・VERDICT OK）

## 計画との差分
- あり。計画変更記録 1〜7（承認の回数の数え方・採用した改善の実装内容・プランレビューと security-review の指摘への対応・I### の拾い方・敵対的レビュー 1 周目への対応・P3 を別イシューへ移す方式の見直し）

## ロールバック
- 段 A: 報告書のコミットを `git revert`
- 段 B: 改善ごとのコミットを `git revert`
