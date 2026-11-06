# I226 レビュー: I225 のレビューの残り: 失効の確かめの取り違え・鍵を出す書き方の検査の狭さ

## 変更概要
- F1: `revoke.sh` が失効の前に鍵の有効を確かめ、もともと無効な鍵を「失効を確認」と出さない
- F6: G10 が `gh auth token` を落とし、行末の `\` で分けた `--json` 付きの書き方を通す
- 同梱: F2（ログインなしの `auth status` の置き換えを exit 1 に）・F4（`plan-writing-rules.md` の記述）・omission-lint を自動テスト文書を書いた直後に PostToolUse のフックで流す
- F5 は grill-me で見送り

## 変更点
- `scripts/claude/gh-app/revoke.sh`: `token_state`（0=有効・1=401・2=確かめられない）を足し、`revoke_one` が失効の前にも読む。もともと無効は 3 を返し、`--stdin` は「最初から無効」で exit 1、控えは「もともと無効」で控えを消して成功扱い
- `scripts/claude/gh-app/gh`: 置き換えた `auth status` は、アカウントが 0 件のとき exit 1
- `scripts/claude/code-review.sh`: `--lint-auto-test <ファイル>…` の入口（既存の `omission_lint` を呼ぶだけ）
- `scripts/claude/hooks/posttooluse_check.py`: `docs/tests/open/I<数字>_auto_test.md` の Edit/Write の直後に上の入口を呼び、宣言漏れなら exit 2 で知らせる
- `scripts/claude/tests/test_i223_gh_app.sh`: G8 に空の hosts、G9 に g・h・i、G10 に `gh auth token` と行末の `\` のつなぎ、それぞれの FG
- `scripts/claude/tests/test_posttooluse_check.sh`: TC-10g〜i
- 文書: `github-app-setup.md`（失効の新しい表示）・`plan-writing-rules.md`（F4）・`CLAUDE.md`（PostToolUse の説明の 1 文）・`docs/reviews/backlog/I225.md`（F2・F4 の行を消した）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `scripts/claude/gh-app/revoke.sh`・`scripts/claude/gh-app/gh`・`scripts/claude/code-review.sh`・`scripts/claude/hooks/posttooluse_check.py`・`scripts/claude/tests/test_i223_gh_app.sh`・`scripts/claude/tests/test_posttooluse_check.sh`・`docs/runbooks/github-app-setup.md`・`docs/runbooks/plan-writing-rules.md`・`docs/reviews/backlog/I225.md`・`CLAUDE.md`

## テスト結果
- 自動: OK — review-gate がゲート 9 本を実走し全 exit 0・CI 全緑。test-gate に回された重いゲートは無い（`docs/tests/open/I226_auto_test.md` の実行記録）
- 手動: OK — M-01〜M-03 をすべて Claude が実施（Human の項目なし）

## 計画との差分
- 振る舞いの差分なし。コードの形は計画変更記録 2 のとおり整理した（/simplify）

## ロールバック
- PR を revert する。手元の入口を入れ直していれば `bash scripts/claude/gh-app/install.sh` をもう一度流す

## 振り返り

### かんたんなまとめ
良かった点
- 計画の前に、本物の `gh` がログインなしで何を返すかを実際に流して確かめた（理由: 足りないのが終了コードだけだと分かり、案内の文を 2 回出す直し方を避けられた）
- 見出しの検査を pre-commit に載せる前に、今ある 136 本の文書に流してみた（理由: 古い文書 1 本で CI が落ちることが分かり、影響の小さいフックに置けた）
- テストを先に書き、直す前の版で落ちることを確かめてから直した（理由: 新しいテストが本当に後退を捕まえることを示せた）
- 自分で確かめられる手動テストを全部自分で行い、人の作業はマージだけにできた

今回の問題への直接の対処
- 鍵を出す書き方の検査（G10）で、語の終わりの判定に使った記号が日本語の文字も「語の続き」とみなすため、「gh auth tokenを打つ」のように日本語がすぐ続く書き方を見落とすようになった（レビューが見つけた。止める条件には当たらない）。語の終わりを決める判定を英数字だけで見る形にし、その書き方のテストを足す必要がある。→ 1 文字の直しとテスト 1 つで済むので、新しいイシューは作らず、次のハーネスの作業である I212 に同梱した

同じ問題を次回から防ぐ改善
- 新しい決まりは足さない。今回の見落としはレビューの機械的な判定がその場で見つけ、直し方も決まっている。同じ穴を 2 つの工程で塞がない

### 詳細
良かった点
- F2 の前提をスパイクで実証（`plan_I226.md` の調査結果）・omission-lint の全件実走で pre-commit 案の落とし穴を計画で発見・TDD の Red を記録（`I226_auto_test.md`）・手動テスト 3 件とも Claude が実施

是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 予期しない問題 | G10 の語の境目を `\b` に任せ、和文が続く形の FG を足さなかった（Python の `\w` は和文を含む） | I212（#358）のイシューファイルに同梱 6 として追記（次のハーネスの作業で最優先）。#358 は bot の停止で見えないため、GitHub へのコメントは停止が解けてから |

予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| （なし） | | | | |

見送り
- 「正規表現の語の境目は和文を考える」をレビュー役の観点や計画の決まりに足す: 見送り — 実害は出たが review-gate の台帳がその場で捕まえ、直し方も決まっている。決まりを足すと毎回のイシューに確認が増える（2.7 の問 2）

5 Whys: G10 の `\b` の後退
- Why 1: なぜ和文が続く書き方を見落とすか → `\b` は `\w`（和文を含む）と非 `\w` の境目にしか当たらないため
- Why 2: なぜ `\b` を足したか → `gh auth tokens` のような長い語への誤検知を避けようとした（実在しない語への備えで、要らなかった）
- Why 3: なぜテストで気づかなかったか → FG に足したのは「auth token は不合格」「行末の \ は合格」の 2 つだけで、元の版が止めていた形（和文が続く）を回帰のケースにしていなかった
- 根本原因: 判定の式を変えるとき、元の版が止めていた形を回帰のケースとして残していなかった。ただし review-gate がその場で見つけたので、新しい手順は足さない

## 自律判断の記録
- [plan] omission-lint を流す場所を PostToolUse のフックにした — pre-commit は CI の `--all-files` で古い open の I034 が落ち、避けると `ci.yml` も直すことになり高リスクのパスに当たる。スキルの手順は流し忘れる。フックは決定論で最も早く、高リスクのパスでない（plan_I226.md §9）
- [plan] F2 は終了コードだけ直す — スパイクで本物の `gh` が「ログインしていない」の案内を標準エラーに出すことを確かめた（文を足すと 2 回出る）
- [plan-review] PLAN_VERDICT: OK（20261106_2128）。Warning 3 件は計画書・テスト文書に反映し、再レビューはしない — 方式・範囲・受け入れ条件を変えない追記だけ（計画変更記録 1）。Info の戻り値の定数化は見送り — コメントで足りる
- [implement] テストを先に書き、本体を直す前に落ちることを確かめてから直した（TC-02・TC-03 の記録） — 新しいケースが false-green でないことを、直す前の版で示すため
- [implement] フックがこのワークツリーの版を動かすことを、実装の直後に M-02 の手順で確かめた（宣言漏れの知らせが届き、見出しを直すと消えた。確かめ用のファイルは消した） — 計画レビューの Warning 1。新しいセッションでの確かめは要らなかった
- [implement] /simplify の 4 つの観点の指摘のうち、G10 の結合の写し・フックの出口が 2 本・`revoke_one` の余計な変数・偽の gh の余計なファイルは直した。`omission_lint` を別のライブラリに出す案（高さの観点・Low）は見送った — `--route` と同じ入口の形にそろえてあり、本体が壊れたときは TC-10g が捕まえる
- [implement] shellcheck は手元に無いので、commit 時の pre-commit と CI に任せた
- [review-gate] FINAL_VERDICT: OK・ADVERSARIAL_STAGE: NOT_REQUIRED（20261106_2139・CI 全緑・ゲート 9 本 exit 0）。台帳の F1（Medium・G10 の `\b` が和文の続く書き方を見落とす後退）〜F5（Low）は止める指摘でないので直さず、retro に回す — fix-loop が直すのは止める指摘だけ（I197）
- [test-gate] gate-check OK。M-01（本物の GitHub に、ありえない形の鍵）・M-02（このセッションのフック）・M-03（ログインなしの入口）を自分で行い、すべて OK — どれも Claude が観測できる。M-01 は最初の読みが 401 なので DELETE を送らず、本物の鍵には触れていない
- [retro] 台帳の残りの振り分け: F1（Medium・SECURITY=yes）→ I212（#358）のイシューファイルに同梱 6（次のハーネスの作業で最優先）／F2〜F5（Low）→ `docs/reviews/backlog/I226.md` — `code-review.sh --route` の結果に従った。F1 は 1 文字の直しとテスト 1 つなので新しいイシューを作らず、次に着手するハーネスのイシューに入れた（I223 → I225 → I226 と後続が続くのを止める）。#358 は bot の停止で GitHub から見えずコメントできないため、手元のイシューファイルに書き、コメントは停止が解けてから付ける
- [retro] 予防処置は足さない — 見落としは review-gate がその場で捕まえ、直し方も決まっている（2.7 の問 2）
- [retro] マージの後に手元の入口を入れ直す（`bash scripts/claude/gh-app/install.sh`）— `~/.local/bin/gh` は写しなので、入れ直すまで F2 の直しが手元の `gh` に効かない（計画 §8）。close のマージ依頼に書く
- [close] PR #418 を Ready にし、最終チェック（BEHIND でない・CI 全緑）を通した。マージ依頼にあわせて、マージの後に手元の入口を入れ直す（`bash scripts/claude/gh-app/install.sh`）ことを伝える — 入口は写しなので、入れ直すまで F2 の直しが手元の `gh` に効かない

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
STAGE_DONE: close NEXT: merge
