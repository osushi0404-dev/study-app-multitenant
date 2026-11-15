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
- 自動: `test_i468_lint_frontend.sh` 合格（TC-01〜TC-05・FG-01〜FG-05）。CI 全ジョブ合格（2 回目以降）。コードレビュー OK（止める指摘なし・Low 7 件は台帳）・敵対的レビュー 2 周目 OK
- 手動（すべて Claude）: No.1〜No.4 OK（本物のワークツリーで、コンテナ停止中・起動中のどちらでも違反のコミットが止まり、違反なしは通った）。No.5 は一部（tui-capture が MCP を渡さない作りのため playwright の項目は観測できず・I452 の実績で補う）

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
- [fix-loop] CI の S21（test_i193）の失敗は、test-gate の行の元の言い回しを残して §11 の確かめを前に置く案 A で直した — I187 の決まりの目印をこのイシューの都合で緩めない（テストを変える案 B は採らない）。診断レビュー PASS
- [review-gate] 基本レビュー 2 回目（20261115_1103）は止める指摘なし（Low 7 件は台帳に残し retro へ）。敵対的レビュー 1 周目（20261115_1112）は新しい指摘 0・V3 だけ実験の拒否で未検証 — 3-3 のとおり決定論の TC-05（本物の pre-commit と git・FG-05）を足して V3 を読んで可に下げ、ついでにテスト文書の古い変数名（台帳 F6）を直した。基本レビューを通してから 2 周目へ
- [test-gate] 違反の無い確かめは `pre-commit run` でなく本物の `git commit`（送らずに `git reset --soft` で取り消し）で行った — Claude の Bash では `pre-commit run` がサンドボックスの中で動いて Docker に届かない（`git commit`・`docker` はサンドボックスの外）。この止まり方自体が AC2 の確かめになった。retro で手順書に書くかを決める
- [test-gate] manual No.5 は「一部」で合格扱いにした — tui-capture は MCP を渡さない決まり（I225）で playwright の項目を観測できない。AC3・AC4 は No.3・No.4 の文書の中身で判定し、再接続の操作は I452 の実績で補う
- [plan-review] 計画レビューの Warning 2 件（test-gate の場所を文言で指す・後始末の確認）は計画書で対応し、再レビューは省いた — 方式・範囲・受け入れ条件を変えないため

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
