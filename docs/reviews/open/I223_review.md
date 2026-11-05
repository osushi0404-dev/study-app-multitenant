# I223 レビュー: GitHub の操作を GitHub App に移したことを記録と仕組みに残し、点検の範囲に GitHub の認証を入れる

## 変更概要
- App の鍵の仕組みと `gh` の入口をリポジトリ（`scripts/claude/gh-app/`）に入れ、`claude -p` で起こすセッション（テスト用・レビュー役）にはすべて読み取りだけの鍵を渡す。GitHub の MCP を外し、手順書の bot・PAT の前提を直す。総点検の常設の一覧と、計画レビュー役の観点を足す

## 変更点
- `scripts/claude/gh-app/gh-app-token`（新規）: 1 時間の App の鍵を出す。`GH_APP_READONLY=1` なら読み取りだけの鍵（本文に `permissions` を付け、控えを `token-readonly` に分け、応答の権限がすべて read でなければ止める）
- `scripts/claude/gh-app/gh`（新規）: `~/.local/bin/gh` として入れる入口。読み取りだけの指定は `GH_APP_DISABLE` で外せない
- `scripts/claude/gh-app/install.sh`（新規）: 前提を確かめて入れる（前の版を写す・credential helper・作者・疎通）。`--check` でずれを見る
- `scripts/claude/test-session.sh`（新規）: テスト用のセッションの入口（`GH_APP_READONLY=1` で `claude -p`）
- `claude -p` を起こす所すべて（`check-permission-prompt.sh`・`review-process-lib.sh`・`code-review.sh`・`plan-issue-review.sh`・`issue-review.sh`・`fix-review-lib.sh`）に `GH_APP_READONLY=1`
- `scripts/claude/tests/test_i223_gh_app.sh`（新規）: G1〜G6 と FG（16 件）。`test_i187_frontend_verify_config.sh` ② を「github の MCP が無い」に
- `.mcp.json`: GitHub の MCP を外した。`.gitignore`: `*.pem`
- 手順書: `mcp-github-setup.md` → `github-app-setup.md`（改名して書き直し）・`harness-audit.md`（新規）・`mcp-usage.md`・`branch-protection-setup.md`・`issue-flow.md`・`onboarding.md`・`plan-writing-rules.md`・`CLAUDE.md`（参照先 2 行）
- `.claude/agents/plan-reviewer.md`: P5 に「名義と鍵（ハーネス）」の観点
- `docs/reviews/backlog/I223.md`（新規）: bot が戻らないとできない片付け B1〜B4

## 影響範囲
- Backend/Frontend/DB: なし
- Config/Infra: `scripts/claude/`・`.mcp.json`・`.gitignore`・`CLAUDE.md`（参照先）・`docs/runbooks/`・`.claude/agents/plan-reviewer.md`・`docs/reviews/backlog/I223.md`。この端末のリポジトリの外の設定（`~/.local/bin/`・`~/.bashrc`）。安全装置（`path_risk_trigger` の集合）には触らない

## テスト結果
- 自動: 決定論ゲート 10 本すべて exit 0・CI 全緑（`docs/reviews/I223_code_review_20261105_1410.md`）。test-gate に回された重いテストは無い
- 手動（test-gate・ccaef3d0）: M-02 が NG（`gh auth status` が App の鍵の大部分を画面に出した。出た鍵は `gh api -X DELETE installation/token` で失効させ、控えを取り直した）。M-01・M-03・M-05・M-07・M-09・M-10 OK、M-04 は代わりの確かめで OK、M-06 は ① OK・② はマージの後（ワークツリーは元のリポジトリの `.mcp.json` を読む）、M-08 は記録だけ。Human の項目なし

## 計画との差分
- 計画変更記録 2: `~/.bashrc` の PAT の行の削除は Claude ではできなかった（自動の判定に止められた）ので、close でユーザーにお願いする
- 計画変更記録 3: `claude -p` を起こす所が計画の調査より 4 か所多く、すべてに読み取りだけの指定を付け、静的なテスト G6 で守る（計画レビューをやり直して OK）

## ロールバック
- PR を revert する。この端末は `~/.cache/github-app/backup/` の前の版を `~/.local/bin/` に戻す（plan_I223.md §7）

## 自律判断の記録
- [plan] テスト用のセッションには「鍵を渡さない」ではなく「読み取りだけの App の鍵」を渡す — GitHub の側で書き込みを拒否でき（スパイクで成立）、テストで GitHub の状態は読めるため
- [plan] 記憶の場所への書き込みを止める件（I222 #402）は同梱しない — I222 は公式の設定を先に調べる計画で、二度手間になるため。入口（`test-session.sh`）はこのイシューで作る
- [plan] MCP の手順書は `github-app-setup.md` に改名して書き直す・総点検の一覧は `harness-audit.md` に新しく置く — 中身と名前を合わせ、常設の置き場所を作るため
- [plan] この端末の入れ直しと `~/.bashrc` の PAT の行の削除は Claude が行い、PAT の失効だけ close でお願いする — 手元の設定は前の版の写し・作り直しで戻せ、失効は持ち主の画面でしかできないため
- [plan-review] 計画レビュー（20261105_1259）は OK・高リスク No。Warning 4 件は findings への対応の追記だけ（M-05・M-08 を単体のコマンドに・残りの範囲は close で報告）で、やり直しはしない — 方式・範囲・受け入れ条件を変えないため
- [plan-review] push は段階ごとにせず、review-gate の CI 待ちの前にまとめる — 書き込みの回数を減らす今の方針（I224 まで）のため
- [implement] `~/.bashrc` の PAT の行の削除は、自動の判定に止められたので回避せず、close でユーザーにお願いする（計画変更記録 2）— 受け入れ条件に含まれない手元の作業で、止められた操作を別の書き方で通すのは判定の意図に反するため
- [implement] この端末の `~/.local/bin/gh-app-token`・`~/.local/bin/gh` を `install.sh` でリポジトリの版に入れ替えた（前の版は `~/.cache/github-app/backup/`）— 以後の push と `gh` をレビュー対象の版で動かすため
- [implement] `/simplify` の「直す深さ」の指摘（`claude -p` を起こすレビュー役 4 か所に書き込みの鍵が渡る）を受けて計画変更記録 3 を書き、計画レビューをやり直した（20261105_1315・OK）— 受け入れ条件「`claude -p` の既定で書き込みが止まる」の漏れで、範囲を変えるため
- [implement] すべての起動を `test-session.sh` に通す案は採らず、各起動の行に指定を付けて G6 で守る — 起動の形を既存のテスト（i193 R7・S8・i197 S1）が見ていて、通し方を変えると守りの検査を作り直すことになるため
- [implement] `/simplify` の簡素化・無駄の指摘のうち、ムダな行の削除・環境変数の二重の名前・PATH の確かめの単純化・ファイルの一覧の 1 か所化・リポジトリ名の変数化・時刻と `dirname` のプロセスを起こさない形・壊した写しの確かめで該当のケースだけを流す、を反映した。見送り: `user.name`・`user.email` の確かめのループ化と G1 の読み方の統一（2 行で、ループにしても読みやすくならない）／入口で控えを直接読む案（鍵の扱いが 2 か所に分かれる）／既定値を共有のファイルにまとめる案（2 本のために読み込みの仕組みを足すことになる）
- [implement] M-03 は計画レビューの指摘どおり前倒しで流し、新しいセッションの Bash の `gh` の書き込みが GitHub に 403 で拒否されたことを確かめた（M-03 の実結果）
- [review-gate] CI の Harness Tests が失敗した（CI_WAIT: FAIL・run 41968150448）ので fix-loop に回す — 決まりどおり（CI の失敗は fix-loop が直す）
- [fix-loop] G4 の CI だけの失敗は、実行権が git に記録されない（core.filemode=false）のに入口が `gh-app-token` を直接実行していたため。診断レビュー（20261105_1348・PASS）を通った案 A（`bash` で起こす）で直し、テストの写しを実行権なしにして FG を足した — 実行権に頼らない作りが根治で、git に実行権を記録する案 B はリポジトリの他のスクリプトの決まり（`bash` に渡す）と揃わず、写すたびに落ちるため
- [review-gate] 2 回目（20261105_1353）は CI 全緑・FINAL_VERDICT: HIGH・敵対的レビューは不要。止める指摘は F1（`tui-capture.sh` が tmux で起こすセッションに読み取りだけの指定が無い）だけで、fix-loop に回す。F2〜F8（Low）は台帳に残し retro へ
- [fix-loop] F1 は診断レビュー（20261105_1420・PASS）を通った案 A（`tmux new-session -e GH_APP_READONLY=1`）で直し、G6 の対象を tmux の起動にも広げた — 起動のコマンドの文字列を変えないので既存の失敗の注入（test_tui_capture.sh 148 行目）が使え、`-e` は tmux サーバーの環境に関係なく効くため
- [review-gate] 3 回目（20261105_1410・差分のレビュー）は CI 全緑・FINAL_VERDICT: OK・敵対的レビューは不要。F1 は resolved。F9〜F12（Low）は台帳に残し retro へ — 止める条件に当たらないため
- [test-gate] M-02 の `gh auth status` で App の鍵の大部分が画面に出たので、すぐに GitHub で失効させ（`gh api -X DELETE installation/token`・その後 401 を確認）、控えを消して取り直した — 書き込みのできる 1 時間の鍵で、会話の記録に残ったため。手順書の確かめ方の不具合なので fix-loop に回す（この段階は手順書を直さない）
- [test-gate] M-04 は、変数を含むコマンドが承認の要る側で値を直接見られないため、G5 と M-03 ② を合わせた代わりの確かめで OK とした — 指定が claude に渡ることと、claude の中の gh に届くことを別々に確かめているため
- [test-gate] M-06 ② は、ワークツリーのセッションが元のリポジトリの `.mcp.json` を読むので、マージの後に元のリポジトリで確かめる — このブランチの設定の確かめにならないため
- [fix-loop] M-02 の NG は、診断レビュー（20261105_1450・PASS）を通った案 A（`gh auth status --json hosts --jq …` で要る欄だけを取り出す）で手順書 2 か所と M-02 を直した — 表示の伏せ字に頼らず、gh の公式の `--json` で鍵の欄を出さないため。`grep -v Token:` の案は表示の形に頼る（形が変わると出る）ので採らない

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
