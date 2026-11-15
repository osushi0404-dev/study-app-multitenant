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
- [implement] Write ツールが使えない時間があったため、新しいファイルは 1 行の仮のファイルを作ってから Edit で中身を入れた — 中身は計画どおり
- [implement] /simplify（4 観点）で直したもの: Docker に届くかの確かめを `docker version --format` に替えた・テストの 3 つの似たループを 1 つの関数にした・失敗の注入の置き換えを python から bash にした・置き換えの文字列を変数から作る・test-gate の §11 の参照を短くした — 同じ判定のまま重複と無駄を減らすため
- [implement] /simplify で見送ったもの: 使い捨てのコンテナで compose の匿名ボリュームを使わずにイメージを直接動かす案・Dockerfile.dev を依存だけの段に分ける案・frontend/.dockerignore の追加・入口のスクリプトを `exec "$@"` に直す案 — どれも `frontend/` のアプリの起動の仕組みを変えるので計画の範囲外（計画 9）。retro で別イシューの要否を決める。pre-commit.md のコマンドの写し・implement の 0) の説明の重なりは、読む人がその場で分かるように残した
- [plan-review] 計画レビューの Warning 2 件（test-gate の場所を文言で指す・後始末の確認）は計画書で対応し、再レビューは省いた — 方式・範囲・受け入れ条件を変えないため

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
