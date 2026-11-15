# I468 レビュー: ワークツリーで ESLint のフックをコンテナで流す・Playwright MCP が切れたときの手順

## 変更概要
- pre-commit の ESLint のフックを `scripts/claude/lint-frontend.sh` 経由にし、起動中のコンテナ → 使い捨てのコンテナ → ホストの eslint → 止める、の順で流す
- `docs/runbooks/frontend-verify.md` に「11. MCP が使えないとき」を足し、implement の最初と test-gate の画面確認の前に MCP を確かめる

## 変更点
- （implement 後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.pre-commit-config.yaml`（ESLint のフックの `entry`）
- ハーネス: `scripts/claude/lint-frontend.sh`（新規）・`scripts/claude/tests/test_i468_lint_frontend.sh`（新規）・`.claude/skills/implement/SKILL.md`・`.claude/skills/test-gate/SKILL.md`・`docs/runbooks/pre-commit.md`・`docs/runbooks/frontend-verify.md`

## テスト結果
- 自動: （未実施）
- 手動: （未実施）

## 計画との差分
- なし

## ロールバック
- PR を revert する（データの変更なし）

## 自律判断の記録
- [plan] 使い捨てのコンテナに `--entrypoint npm` と `--build` を付ける — スパイクで、入口のスクリプトが引数を無視して開発サーバーを起動すると分かったため・package*.json の変更に追従するため（plan_I468 の「確かめたこと」）
- [plan] test-gate のスキルにも MCP の確かめを足す — implement と手順の粒度をそろえる（イシューの実装対象の表の外・AC4 と同じ目的）
- [plan-review] 計画レビューの Warning 2 件（test-gate の場所を文言で指す・後始末の確認）は計画書で対応し、再レビューは省いた — 方式・範囲・受け入れ条件を変えないため

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
