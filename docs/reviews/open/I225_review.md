# I225 レビュー: GitHub の鍵が画面に出る・漏れたときの手順と、テスト用のセッションの抜け道を塞ぐ

## 変更概要
- （実装後に記入）

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `scripts/claude/gh-app/`・`scripts/claude/` の Claude の起動の行・`scripts/claude/tui-capture.sh`・`scripts/claude/tests/`・`docs/runbooks/github-app-setup.md`・`docs/runbooks/harness-audit.md`

## テスト結果
- 自動:
- 手動:

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

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
