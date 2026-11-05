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
- 手動のやり直し（test-gate・aca29350）: M-02 は鍵を出さない確かめ方で OK（`osushi0404-claude[bot] GH_TOKEN success`）。結論 OK

## 計画との差分
- 計画変更記録 2: `~/.bashrc` の PAT の行の削除は Claude ではできなかった（自動の判定に止められた）ので、close でユーザーにお願いする
- 計画変更記録 3: `claude -p` を起こす所が計画の調査より 4 か所多く、すべてに読み取りだけの指定を付け、静的なテスト G6 で守る（計画レビューをやり直して OK）

## ロールバック
- PR を revert する。この端末は `~/.cache/github-app/backup/` の前の版を `~/.local/bin/` に戻す（plan_I223.md §7）

## 振り返り

### かんたんなまとめ
**良かった点**
- 計画の前に「読み取りだけの鍵なら GitHub が書き込みを断るか」を実際に試して確かめた（理由: 文字列の見張りではなく GitHub の権限で止める設計を、実装の前に根拠つきで決められた）
- 実装の後の整理（`/simplify`）の「直す深さ」の観点が、計画で数え漏らした Claude の起動の所（レビュー役 4 か所）を見つけ、レビューがさらに tmux の起動（`tui-capture.sh`）を見つけた。今は、起動の行が増えても付け忘れを CI で止めるテストがある（理由: 漏れを手順の心がけでなく、決定論のテストで塞いだ）
- 手動テストで鍵が画面に出たとき、すぐに GitHub で失効させて、使えなくなったことまで確かめた（理由: 書き込みのできる鍵が会話の記録に残ったままにならなかった）

**今回の問題への直接の対処**
- 手順書の名義の確かめ方（`gh auth status`）が、App の長い鍵の大部分を画面に出した。`gh` の伏せ字が昔の短い鍵向けだったため。→ 鍵の欄を出さない `--json` の形に直した（このイシューの中で直した）。漏れたときの手順の正確さなどの残りは、I225（#415）にまとめた
- CI でだけテストが 1 件落ちた。この端末では git がスクリプトの実行権を記録しないのに、入口が別のスクリプトを直接実行していたため。→ `bash` で起こす形に直し、テストも CI と同じ条件（実行権なし）で流すようにした（このイシューの中で直した）

**同じ問題を次回から防ぐ改善**
- 鍵や秘密を扱う手順で「確かめ方のコマンドそのものが秘密を画面に出す」ことを確かめる段取りが無く、見張りも一部の書き方（`-t` 付きなど）しか止めていなかった。→ 秘密を出す書き方を見張りか静的なテストで締め出し、計画レビュー役に「確かめ方が秘密を出さないか」の観点を足すことを、I225（#415）に入れた（次のハーネスの作業で最優先）

### 詳細
**良かった点**
- 計画の段階のスパイクで、読み取りだけの鍵（`permissions` を絞った installation token）で書き込み（API・`git push --dry-run`）が 403 になることを実証した
- `/simplify` の altitude の観点 → 計画変更記録 3 → G6（静的なテスト）。review-gate の F1 → G6 の対象を tmux の起動にも広げた
- 漏れた鍵は `DELETE /installation/token` で失効させ、401 を確認した

**是正処置（Corrective）**
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 予期しない問題 | 手順書・M-02 の確かめ方 `gh auth status` が App の新しい形式の鍵の大部分を出す | fix-loop で `gh auth status --json hosts --jq …` に直した（計画変更記録 5）。残り（F13・F14 など）は I225 #415 |
| C2 | 予期しない問題 | `core.filemode=false` で実行権が記録されず、入口の直接実行が CI で失敗 | fix-loop で `bash` で起こす形に直し、テストの写しを 644 にして FG を足した |

**予防処置（Preventive）**
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | セキュリティ・スキル・規約 | 秘密を扱う手順の確かめ方を決めるとき、そのコマンドが秘密を画面に出すかを確かめる段取りが無い。見張りは一部の書き方だけを確認にしている | 秘密を出す書き方を決定論のチェック（見張り または 静的な検査）で締め出し、計画レビュー役の観点に「秘密を扱う手順の確かめ方が、表示の伏せ字に頼らず要る欄だけを取り出す形か」を足す（I225 #415 に同梱・新規起票） | `scripts/claude/hooks/pretooluse_guard.py`（候補）・`.claude/agents/plan-reviewer.md` |

**なぜを繰り返す原因分析（P1）**
- Why 1: なぜ鍵が画面に出たか → 手順書と手動テストが確かめ方に `gh auth status` を指示していて、それを流したから
- Why 2: なぜその確かめ方になったか → 計画のとき、名義を確かめるふつうのコマンドとして選び、そのコマンドが何を出すかを確かめなかったから（今までの短い鍵では伏せ字で隠れていた）
- Why 3: なぜ確かめなかったか → 計画の書き方にも計画レビュー役にも「秘密を扱う手順の確かめ方が秘密を出さないか」を見る段取りが無く、見張りも `-t`・`token` の書き方だけを止めていたから
- 根本原因（I223 固有の名前を外して）: 秘密を扱う手順の確かめ方を決めるときに、出力に秘密が含まれるかを確かめる仕組み（決定論のチェック・レビューの観点）が無い。鍵の形式が変わると、表示の伏せ字に頼った確かめ方は黙って秘密を出す

**見送り**
- 計画の調査で Claude の起動の所を数え漏らした件: その場で `/simplify` とレビューが捕まえ、今は G6（決定論のテスト）が起動の行の付け忘れを CI で止める。手順を足しても G6 と二重になる
- CI でだけ落ちた実行権の件: CI（決定論のゲート）がその場で捕まえ、手戻りは 1 周だけ。テストが CI と同じ条件で流れるようにしたので、手元でも同じ形で捕まる
- `~/.bashrc` の行の削除が自動の判定に止められた件: 回避せずにお願いに回し、受け入れ条件にも影響しない。手順を足す理由が無い
- M-01 で見張りが `HOME` を変える git の実行を止めた件: スクリプトにまとめて流せた。手戻りが小さく、見張りを変える理由が無い

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
- [review-gate] 4 回目（20261105_1440・差分のレビュー）は CI 全緑・FINAL_VERDICT: OK・敵対的レビューは不要。F13・F14（Medium・ハーネスで止める条件に当たらない）・F15（Low）は台帳に残し retro へ — 止める指摘はスクリプトが決め、自分で増やさないため
- [retro] 台帳の残り（`code-review.sh --route`・記録 20261105_1440）: F7・F9・F13・F14・F15 → I225（#415）にまとめて起票（「次のハーネスの作業で最優先」と書いた。SECURITY=yes を含むため）／F2・F3・F4・F5・F6・F8・F10・F11・F12 → `docs/reviews/backlog/I223.md`（B1〜B4 と同じファイル）
- [retro] 予防処置 P1（秘密を出す確かめ方を決定論で締め出す・計画レビュー役の観点）は、台帳の残りと同じ仕組みの話なので I225（#415）に入れた（新規起票）— 同梱先の既存イシューが無く、実害（鍵の露出）が出たため
- [retro] 見送り 4 件（起動の所の数え漏らし・実行権・`~/.bashrc`・M-01 の見張り）— どれもその場で捕まり、決定論のチェックがある・手戻りが小さいため（「## 振り返り」の見送り）
- [retro] I225 のイシューファイル（`docs/issues/open/I225.md`）と自己完結度レビューの記録は未コミットのまま残す — 起票のハンドオフの決まり（I225 の `/plan-issue` が初コミットする）

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
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
