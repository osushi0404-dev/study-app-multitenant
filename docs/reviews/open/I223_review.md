# I223 レビュー: GitHub の操作を GitHub App に移したことを記録と仕組みに残し、点検の範囲に GitHub の認証を入れる

## 変更概要
- （実装後に記入）App の鍵の仕組みと `gh` の入口をリポジトリ（`scripts/claude/gh-app/`）に入れ、テスト用のセッションには読み取りだけの鍵を渡す。GitHub の MCP を外し、手順書の bot・PAT の前提を直す。総点検の常設の一覧と、計画レビュー役の観点を足す

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config/Infra: `scripts/claude/`・`.mcp.json`・`.gitignore`・`CLAUDE.md`（参照先）・`docs/runbooks/`・`.claude/agents/plan-reviewer.md`・`docs/reviews/backlog/I223.md`。この端末のリポジトリの外の設定（`~/.local/bin/`・`~/.bashrc`）。安全装置（`path_risk_trigger` の集合）には触らない

## テスト結果
- （test-gate で記入）

## 計画との差分
- （実装後に記入）

## ロールバック
- PR を revert する。この端末は `~/.cache/github-app/backup/` の前の版を `~/.local/bin/` に戻す（plan_I223.md §7）

## 自律判断の記録
- [plan] テスト用のセッションには「鍵を渡さない」ではなく「読み取りだけの App の鍵」を渡す — GitHub の側で書き込みを拒否でき（スパイクで成立）、テストで GitHub の状態は読めるため
- [plan] 記憶の場所への書き込みを止める件（I222 #402）は同梱しない — I222 は公式の設定を先に調べる計画で、二度手間になるため。入口（`test-session.sh`）はこのイシューで作る
- [plan] MCP の手順書は `github-app-setup.md` に改名して書き直す・総点検の一覧は `harness-audit.md` に新しく置く — 中身と名前を合わせ、常設の置き場所を作るため
- [plan] この端末の入れ直しと `~/.bashrc` の PAT の行の削除は Claude が行い、PAT の失効だけ close でお願いする — 手元の設定は前の版の写し・作り直しで戻せ、失効は持ち主の画面でしかできないため
- [plan-review] 計画レビュー（20261105_1259）は OK・高リスク No。Warning 4 件は findings への対応の追記だけ（M-05・M-08 を単体のコマンドに・残りの範囲は close で報告）で、やり直しはしない — 方式・範囲・受け入れ条件を変えないため
- [plan-review] push は段階ごとにせず、review-gate の CI 待ちの前にまとめる — 書き込みの回数を減らす今の方針（I224 まで）のため

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
