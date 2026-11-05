# I225 レビュー: GitHub の鍵が画面に出る・漏れたときの手順と、テスト用のセッションの抜け道を塞ぐ

## 変更概要
- `gh` の入口が、`--json` なしの `auth status` を鍵の出ない表示に置き換える。手順書などへの書き戻しは CI（G10）で止める
- 鍵が出たときの失効をスクリプト `revoke.sh` にした（控えの 2 つ・`--stdin` で控えに無い鍵）。失効は HTTP 401 で確かめる
- テスト用のセッションの起動にすべて `--strict-mcp-config`、tmux の中の `claude` に入口のある `PATH` を渡す

## 変更点
- `scripts/claude/gh-app/gh`（auth status の置き換え）・`scripts/claude/gh-app/revoke.sh`（新規）
- `scripts/claude/` の起動の行: `code-review.sh`・`review-process-lib.sh`・`issue-review.sh`・`plan-issue-review.sh`・`fix-review-lib.sh`・`test-session.sh`・`check-permission-prompt.sh`・`tui-capture.sh`（`adversarial-review.sh` の重複した `--strict-mcp-config` を消した）
- テスト: `test_i223_gh_app.sh`（G7〜G10・g6/g7 の共通化）・`test_tui_capture.sh`（T1・FG-T1b・FG-T8）
- 手順書: `github-app-setup.md`（1.・5.・漏れたときの手順）・`harness-audit.md`（古い鍵の点検コマンド）
- 台帳: `backlog/I223.md` の F11・F12、`backlog/I195.md` の F5 を消した

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `scripts/claude/gh-app/`・`scripts/claude/` の Claude の起動の行・`scripts/claude/tui-capture.sh`・`scripts/claude/tests/`・`docs/runbooks/github-app-setup.md`・`docs/runbooks/harness-audit.md`

## テスト結果
- 自動: review-gate（fb4b563a）で CI 全緑・決定論ゲート 6 本とも exit 0（`test_i223_gh_app.sh` 33/33 ほか）。TC-03 OK
- 手動（test-gate・22ae10d4）: M-01〜M-04 すべて OK（すべて Claude。Human の項目なし）

## 計画との差分
- なし

## ロールバック
- PR を revert し、`bash scripts/claude/gh-app/install.sh` を流し直す（前の版は `~/.cache/github-app/backup/`）

## 自律判断の記録
- [plan] 失効の手順をスクリプト `scripts/claude/gh-app/revoke.sh` にし、控えの 2 つの鍵を直接失効させて確かめる — 手順書の散文では取り違え（F13）が起きる。1 コマンドなら偽物の `gh` でテストできる
- [plan] 静的な検査（G10）の対象を、決まりの置き場（手順書・スキル・エージェント・スクリプト・テンプレート）に絞り、個々のイシューの記録を外した。イシューの受け入れ条件 2 も同じ範囲に直した — 計画・テスト文書は置き換えを確かめるために `--json` なしの書き方を名指しする必要があり、打っても入口が置き換える。I223 の事故の元の手順書は対象に入る
- [plan] 総点検の点検コマンドは `env -u GH_APP_READONLY` でなく `GH_APP_READONLY=`（空）にした — 計画の段階で流したら、ワークツリーの見張りが `env` の形を止めた。入口は空を「指定なし」と読む
- [plan] GitHub への書き込みをまとめた: ブランチの push・Draft PR の作成は、計画の記録を全部コミットしてから 1 回で行う（I224 の当面の運用。段階ごとに push しない）

- [plan-review] 1 回目の Blocker（控えに無い漏れた鍵が失効しない）は revoke.sh --stdin を足して直し、2 回目で OK。残りの Warning 3 件は計画変更記録 2 で直し、再レビューはしない — 方式・範囲・受け入れ条件を変えない直しのため
- [implement] 失効の確かめを「読みに行って失敗」でなく「HTTP 401 が出る」にした（計画変更記録 3） — 通信の失敗を「無効」と取り違えて控えを消さないため。本物の `gh` で 401 の文言を確かめた
- [implement] `--strict-mcp-config` を置く位置を、既存のテスト（S1・FG-S1）が前提にする形に合わせた（`"$@"` の前・`--permission-prompts none)` の前・複数行の呼び出しは 1 行目） — テストを直すより起動の行を合わせるほうが変更が小さく、既存の守りをそのまま使える
- [implement] /simplify の指摘のうち、G6・G7 の重複（共通の関数にした）と G9 の使わない代入を直した。見送り: 起動を 1 つの入口にまとめる案（直す深さの指摘。8 か所の起動の形と既存テストを作り直すことになり、計画の方式を変えるので retro で扱う）・控えの名前と形を共通のファイルにまとめる案（`revoke.sh` の名前の一覧は FG が守り、控えの形は 1 か所でしか書かない）・G10 を狭める案（計画 §9 で決めた範囲）・失効を並行にする案（効果が 1 秒未満）
- [review-gate] 1 回目は FINAL_VERDICT: HIGH。止める指摘は 0 件で、HIGH は自動テスト文書の決定論ゲートの見出し違い（宣言なし・omission-lint）によるもの。決まりどおり fix-loop に回した — 判定はスクリプトの決定論の出力に従う
- [fix-loop] 見出しを `## 決定論ゲート（自動実走）` に直した（診断メモ 20261106_0100 の案 A・診断レビュー PASS） — テンプレートどおりの 1 行の直しで、次の review-gate がゲートを実走して証跡を残す。台帳の F1〜F7 は止める指摘ではないので直さない（retro）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
