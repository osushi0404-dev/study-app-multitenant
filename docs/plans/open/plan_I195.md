# I195 計画書: Claude で確かめられる手動テストを人に振らない仕組みを固める

## 基本情報
- **計画書ID**: plan_I195
- **関連イシュー**: #329
- **Draft PR**: #351
- **作成根拠資料**: docs/issues/open/I195.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I195_review.md
- **作成日**: 2026-10-28

## 1. 背景/目的
- 背景: Claude で確かめられる手動テストを人に頼むことが、I187（承認画面）と I193（対話画面の `/` の候補・手動 No.5）で起きた。今の仕組みには次の 4 つの穴がある。(1) 実施者の基準の「Claude で実施可」が閉じた列挙で、対話画面（TUI）の観測手段が無い。(2) `check-manual-test-executor.sh` は理由が空かどうかしか見ない。(3) 実施者の基準が 3 か所に写しで書かれていて、ずれる。(4) tmux は許可に無く、使うたびに承認画面が出る
- 目的: 手順（do）と関所（gate）の 2 段で、Claude で確かめられる手動テストが人に振られない状態にする。do は観測手段（対話画面のスクリプト）と 1 か所の基準、gate は判定スクリプトの「試した手段:」の必須化と計画レビュー役の観点

### 調査結果
- 原因の概要: 「Claude で確かめられるか」を、手段を試す前に列挙の文字で決めていた。列挙に無い手段は人に回り、回した理由の中身は誰も確かめていなかった
- 詳細:
  1. I193 の手動 No.5: 理由「`claude -p` は一覧を出さない」で Human にした。tmux で `claude` を起動して `tmux capture-pane` で読めば確かめられた（`docs/tests/closed/I193_manual_test.md` 11 行）
  2. 実施者の基準の写し: `.claude/skills/plan-issue/SKILL.md` 93〜95 行・`docs/runbooks/plan-writing-rules.md` 442〜451 行・`docs/tests/templates/manual_test_template.md` 7〜9 行の 3 か所。`test-gate/SKILL.md` 58 行も Human の備考の書き方（`Claude で確かめられない理由: …`）を持つ
  3. `scripts/claude/check-manual-test-executor.sh` 63〜76 行: `Claude で確かめられない理由:` の後ろが空かどうかと、承認画面の言葉だけを見る
  4. `.claude/settings.json` の allow に `tmux` は無い。`Bash(bash scripts/claude/*)` はある
- 実証（スパイク・2026-10-28・このセッション）: `tmux new-session -d -s i195spike -x 200 -y 50 -c <ワークツリー> "claude --permission-mode default"` で起動し、プロンプトの行（`❯` で始まる行）が出るまで待ち、`tmux send-keys -l "/plan-"` → `tmux capture-pane -p` で、候補 `/plan-issue`・`/plan`・`/issue-bootstrap` と説明が読めた（成立）。下の行に `⏸ manual mode on` が出て、通常モードで起動したことも読めた。`tmux kill-session` で閉じた。claude には何も送信していない（Enter を押していない）ので、費用はかからない
- 環境の前提: `tmux 3.4`・`claude 2.1.311`（手元）。CI（`.github/workflows/ci.yml` の Harness Tests・ubuntu-latest）に tmux と claude があるかは確かめない。`.github/` は変えない（止める条件 2 の安全装置）ので、テストは偽物の `tmux`・`claude` を PATH の先頭に置いて確かめ、本物の起動は手動テストで Claude が確かめる
- 書き方を変えたときの消費箇所（grep で全件を確かめた）:
  - `Claude で確かめられない理由`: `plan-issue/SKILL.md` 95・`test-gate/SKILL.md` 58・`plan-writing-rules.md` 446・`manual_test_template.md` 9/17・`check-manual-test-executor.sh` 10/63/74・`test_check_manual_test_executor.sh`（X1・X3・X5・X11・X12・X16・X17）。ほかは closed の記録だけ（書き換えない）
  - 実施者の基準・「プレーン default 新規セッション」: `plan-writing-rules.md` 90（スパイクの手段）・460（実施環境の表）。`.claude/agents/plan-reviewer.md` 75 の「Human 目視」は計画のスパイクの扱いで、手動テストの実施者の基準ではないので変えない
  - テストが文言に依存する箇所: `test_i193_official_flow.sh` の S21（`s21_test`〔test-gate〕・`s21_old`〔テンプレート〕・470 行の `check-manual-test-executor.sh I193`〔終わった記録〕）。`test_check_manual_test_executor.sh` の X9（`check-manual-test-executor.sh I187`〔終わった記録〕）
- 一覧の確認（plan-issue の「台帳の残りの一覧」。実装対象 10 ファイルと `FILE=- |` で grep）: 当たる行なし
- ベースライン（2026-10-28・develop 068357c）: `bash scripts/claude/tests/test_check_manual_test_executor.sh` → pass=23 fail=0。`bash scripts/claude/tests/test_i193_official_flow.sh` → pass=160 fail=0

## 2. 受け入れ条件
イシューの AC と同じ（番号を振る）。
- AC1: 対話画面にだけ出る表示（`/` の候補・ステータス行・ダイアログなど）を、Claude が `scripts/claude/tui-capture.sh` で tmux を使って確かめられ、`.claude/settings.json` を変えずに承認画面なしで実行できる（`check-permission-prompt.sh` で確かめる）。I193 の No.5（`/` の候補の出方）がこのスクリプトで確かめられる
- AC2: 実施者の基準（Claude で実施可の手段・Human の条件・「試した手段:」の書き方）が `plan-writing-rules.md`「実施者の区別」の 1 か所にあり、`plan-issue/SKILL.md`・`test-gate/SKILL.md`・`manual_test_template.md` は 1 行の要約と参照になっている
- AC3: `plan-issue/SKILL.md`・`plan-writing-rules.md`・`manual_test_template.md` に「承認画面が出るかどうか」を Human とする書き方が無い
- AC4: `check-manual-test-executor.sh` が「試した手段:」の後ろに中身の無い Human の行を不合格にする
- AC5: `plan-reviewer.md` に、Human の行が試した手段で本当に観測できないかを見る観点がある
- AC6: 上の決まりが `scripts/claude/tests/run-all.sh` から流れるテストで確かめられ、決まりを消した版、および I193 の No.5 の当初の書き方（作った例）で不合格になる
- AC7: S21 が終わったイシューの手動テスト記録に依存しない（作った例で確かめる）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra（ハーネス）: `scripts/claude/tui-capture.sh`（新規）・`scripts/claude/check-manual-test-executor.sh`・`docs/runbooks/plan-writing-rules.md`・`.claude/skills/plan-issue/SKILL.md`・`.claude/skills/test-gate/SKILL.md`・`docs/tests/templates/manual_test_template.md`・`.claude/agents/plan-reviewer.md`・`scripts/claude/tests/test_tui_capture.sh`（新規）・`scripts/claude/tests/test_check_manual_test_executor.sh`・`scripts/claude/tests/test_i193_official_flow.sh`
- `.claude/settings.json`・`.github/`・`path_risk_trigger()` の集合には触れない

## 4. 変更点一覧（具体）

### 4.1 対話画面を確かめるスクリプト `scripts/claude/tui-capture.sh`（新規・AC1）
修正方針: tmux の操作を、`claude` を起動して画面を読むことだけに閉じたスクリプトにする。`Bash(bash scripts/claude/*)` の許可に当たるので承認画面は出ず、`Bash(tmux *)` の広い許可は要らない。

- 使い方: `bash scripts/claude/tui-capture.sh [--wait <秒>] [--start-timeout <秒>] <入力> [<入力> ...]`
  - 入力は前から 1 つずつ送る。ふつうの入力は文字のまま送る（`tmux send-keys -l`）。`{Enter}`・`{Escape}`・`{Tab}`・`{Up}`・`{Down}`・`{BSpace}` の 6 つはキーとして送る（`tmux send-keys <キー名>`）。ほかの `{…}` は文字として送る
  - 入力の間は 0.5 秒あける。最後の入力の後、`--wait` 秒（既定 2）待ってから画面を読み、標準出力に出す
- 起動: `tmux new-session -d -s "tui-capture-$$" -x 200 -y 50 -c "<リポジトリのルート>" "claude --permission-mode default"`。起動するコマンドは固定（引数で変えられない）。通常モードにするのは、セッションの既定が自動承認モードでも、確認の画面の出方を通常モードで見るため
- 起動の待ち: プロンプトの行（行頭の `❯`）が画面に出るまで 1 秒ごとに読み、`--start-timeout` 秒（既定 30）で出なければ exit 2
- 後始末: `trap` で終了時に必ず `tmux kill-session -t "tui-capture-$$"`（途中で失敗しても claude を残さない）
- 止める入力: 先頭（前の空白を除く）が `!` の入力は、何も起動する前に exit 2（claude の `!` はシェルのコマンドをそのまま動かすため）。普通の書き方の事故を止めるためのもので、わざと避ける書き方（`/` のコマンドで設定を変えるなど）は対象にしない（9 のセキュリティ）
- 終了コード: 0=画面を読めた・2=使い方の誤り（入力が無い・`--wait` などが数でない・`!` の入力）／`tmux`・`claude` が無い／起動しない
- 冒頭のコメントに使い方・終了コード・「Enter を送ると claude が動き、費用がかかり、通常モードの許可の範囲でツールを使う。候補や画面の表示を見るだけなら Enter を送らない」を書く

### 4.2 判定スクリプト `scripts/claude/check-manual-test-executor.sh`（AC4）
修正方針: Human の行の備考の書き方を `試した手段: …` にし、後ろに中身が無ければ不合格にする（粗い fail-closed。中身の正しさは文字では見ない。4.5 の計画レビュー役が見る）。

- 理由の読み取り（63〜67 行）: `Claude\ で確かめられない理由[:：]` を `試した手段[:：]` に変える（読んだ中身を `tried` に入れる）
- 承認画面の言葉の判定（70 行）: 通す条件を「`tried` に `check-permission-prompt.sh` がある」に変える（今の意味のまま）
- 空の判定（73〜75 行）: メッセージを「Human の行に『試した手段: …』がありません（Playwright MCP・check-permission-prompt.sh・claude -p・tui-capture.sh のどれを試し、なぜ観測できなかったか。書き方: docs/runbooks/plan-writing-rules.md「実施者の区別」）」に変える
- 前の書き方（`Claude で確かめられない理由:` だけ）の行は不合格になる（前の書き方を通す例外は作らない。終わったイシューの記録はこの判定にかけない＝7 の S21・X9 の置き換え）
- 冒頭のコメント（6〜11 行）を新しい規則に合わせる

### 4.3 実施者の基準を 1 か所に（`docs/runbooks/plan-writing-rules.md`・AC2・AC3）
修正方針: 基準の正をこの文書の「実施者の区別」だけにし、観測手段の一覧に対話画面を足す。

- 「実施者の区別」の表（445〜446 行）:
  - `Claude` の行の「意味」に「対話画面（TUI）にだけ出る表示〔`/` の候補・ステータス行・ダイアログなど。`scripts/claude/tui-capture.sh`〕」を足す。「例」に「`/` の候補の出方」を足す
  - `Human` の行: 「Claude が使える観測手段（Read・Bash・Playwright MCP・`check-permission-prompt.sh`・`claude -p`・`tui-capture.sh`）を試し、どれでも観測できなかったものだけ。備考に `試した手段: <試した手段>。<観測できなかったわけ>` を必ず書く（例: `試した手段: Playwright MCP・tui-capture.sh。どちらも Figma の画面は開けない`）。承認画面の言葉を含む行は、`check-permission-prompt.sh` では確かめられないわけも書く」
- 表の下に 1 行: 「この基準の正はこの節。`.claude/skills/plan-issue/SKILL.md`・`.claude/skills/test-gate/SKILL.md`・`docs/tests/templates/manual_test_template.md` は要約と参照だけを持つ（写しを増やさない）」
- 「振り分けの判定」（451 行）の括弧書きを「Human の行に『承認画面』がある・『試した手段:』が無い行を止める」に変える
- 「ハーネス挙動テストの実施環境」の表（458〜461 行）に行を足す: `対話画面の判定` | `/` の候補・ステータス行・ダイアログなど、対話のセッションの画面にだけ出る表示（`bash scripts/claude/tui-capture.sh '<入力>'`。使い方はスクリプトの冒頭）。`プレーン default 新規セッション` の行は「`claude -p` でも `tui-capture.sh` でも観測できない、対話のセッションに固有の挙動（その理由を備考に書く）」に変える
- スパイクの (2)（90 行）の「まず `claude -p` で…試す」に「対話画面にだけ出る表示は `scripts/claude/tui-capture.sh`」を足す

### 4.4 写しを要約と参照に（AC2・AC3）
- `.claude/skills/plan-issue/SKILL.md` 93〜95 行（「テスト文書の『実施者』欄は以下の基準で判定する…」と 2 つの箇条書き）を次の 1 段落にする:
  「テスト文書（`$ARGUMENTS_manual_test.md`）の『実施者』欄は `docs/runbooks/plan-writing-rules.md`「実施者の区別」で決める（要約: 原則 Claude。Claude で確かめられるものを人に頼まない。Human にするのは、そこに挙げた観測手段〔Playwright MCP・`check-permission-prompt.sh`・`claude -p`・`tui-capture.sh` など〕を試して、どれでも観測できなかったものだけ。Human の行の備考には `試した手段: …` を必ず書く）」
  - 97〜100 行の `check-manual-test-executor.sh` の実行はそのまま
- `.claude/skills/test-gate/SKILL.md` の 4.:
  - 「実施者: Claude」の箇条に 1 行足す: 「対話画面（TUI）にだけ出る表示（`/` の候補・ステータス行・ダイアログなど）は `bash scripts/claude/tui-capture.sh '<入力>'` で確かめる（使い方はスクリプトの冒頭。表示を見るだけなら `{Enter}` を送らない）」
  - 58 行の「本当に Claude で確かめられない Human の行だけ、備考に `Claude で確かめられない理由: …` を書く」を「本当に Claude で確かめられない Human の行だけ、備考に `試した手段: …` を書く（書き方は `docs/runbooks/plan-writing-rules.md`「実施者の区別」）」にする
- `docs/tests/templates/manual_test_template.md`:
  - 7〜9 行（実施者の区別の 3 行）を 1 行にする: 「- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude。Human の行は備考に「試した手段: …」が必須。scripts/claude/check-manual-test-executor.sh が確かめる）」
  - 17 行の例の行の備考を `試した手段:` にする

### 4.5 計画レビュー役の観点（`.claude/agents/plan-reviewer.md`・AC5）
修正方針: 書いてあるかは機械の判定、中身が正しいかは計画レビュー役が見る（2 段）。

- 「差し戻しファースト原則」の「手動テストケース」の表に 1 行足す（この表は Blocker）:
  | 実施者が Human の行で、`試した手段:` に挙げた手段、または `docs/runbooks/plan-writing-rules.md`「実施者の区別」の観測手段（Playwright MCP・`check-permission-prompt.sh`・`claude -p`・`tui-capture.sh`）で観測できるのに Human になっている | 「`/` の候補の出方」を `試した手段: claude -p（一覧が出ない）` で Human | 「`/` の候補の出方」を Claude にし、`tui-capture.sh` で確かめる |

### 4.6 テスト（AC1・AC4・AC6・AC7）
- `scripts/claude/tests/test_tui_capture.sh`（新規）: 偽物の `tmux`（呼ばれた引数を記録し、`capture-pane` では決まった画面を出す）と `claude`（何もしない）を一時のフォルダに置いて PATH の先頭にし、本物は使わない。項目は auto_test の TC-01
- `scripts/claude/tests/test_check_manual_test_executor.sh`: 例の書き方を `試した手段:` に変え（X1・X3・X5・X11・X12・X16・X17）、X18〜X20 と FG を足す。X9（`check-manual-test-executor.sh I187`）は消す（終わった記録に新しい書き方を求めることになる。AC7 と同じ理由）。項目は TC-02
- `scripts/claude/tests/test_i193_official_flow.sh` の S21: 470 行（`check-manual-test-executor.sh I193`）を消し、`s21_rules` と FG を足す。項目は TC-03

## 5. 実装手順（ステップ）
未知リスク（tmux で claude の画面を読めるか）はスパイクで成立を確かめた（1 の調査結果）。
1. テストを先に書く（TDD）: 4.6 → TC-01〜TC-03（今のコードで新しい項目が不合格になった件数を記録）
2. 4.1（`tui-capture.sh`）→ TC-01
3. 4.2（判定スクリプト）→ TC-02
4. 4.3・4.4・4.5（文書・スキル・レビュー役）→ TC-03
5. 手動テスト No.1〜No.4 は test-gate で Claude が行う
- 依存: 2・3・4 は 1 の後。2・3・4 は互いに独立（並べて行ってよい）

## 6. テスト計画
### 自動（docs/tests/open/I195_auto_test.md）
- テストのレベル: ハーネスの単体（偽物の `tmux`・`claude` でスクリプトの振る舞い・作った手動テスト文書で判定スクリプト）と、指示ファイルの文言の確認。アプリのテスト（pytest・Jest・E2E）は非該当
- 再発防止: I193 の No.5 の当初の書き方（`Claude で確かめられない理由: claude -p は一覧を出さない`・試した手段なし）が不合格になることを X19 で固定する
- 否定・不在の項目にはすべて失敗注入（FG）を付ける
### 手動（docs/tests/open/I195_manual_test.md）
- 本物の tmux と claude で `tui-capture.sh` が `/` の候補を読めること・承認画面なしで通ること・`!` の入力を止めること・セッションを残さないこと。すべて Claude が行う（Human の項目なし）

## 7. ロールバック
- PR を revert する（ハーネスのスクリプト・テスト・文書だけ。データ・設定の変更は無い）。revert の後は前の書き方（`Claude で確かめられない理由:`）に戻るので、その間に書いた手動テスト文書の Human の行は、判定を通すために書き方を戻す

## 8. Risk & 回避策
- 進行中のイシューの手動テスト文書が前の書き方のままだと、test-gate の判定で止まる → test-gate の手順どおり Claude が自分で書き直して判定をやり直す（fix-loop に回らない・4. の 0 以外の扱い）。develop の `docs/tests/open/` にある文書は I013〜I047 の古いものだけで、今の流れでは使われていない
- `tui-capture.sh` で `{Enter}` を送ると、中の claude が動いて費用がかかり、通常モードの許可の範囲でツールを使う → 冒頭のコメントと test-gate の手順に「表示を見るだけなら Enter を送らない」と書く。中の claude の許可は外の Claude と同じ設定と見張りなので、外から直接できること以上はできない（`!` だけは許可を通らずシェルを動かすので止める）
- claude の画面の形が変わり、プロンプトの行（`❯`）が出なくなる → 起動の待ちが時間切れで exit 2 になり、黙って空の画面を返さない。手動テスト No.1 で今の版を確かめる
- 終了時に tmux のセッションが残る → `trap` で必ず閉じる（TC-01 の T1・T6 と FG で固定。手動 No.3 で本物でも確かめる）
- 「試した手段:」に中身の無いことを書いて通す → 文字の判定の範囲外。計画レビュー役の観点（4.5）で見る
- 基準の要約が参照先とずれる → 要約は「原則 Claude・観測手段を試す・試した手段が必須」の 3 点だけにし、手段の細部は持たない。TC-03 が要約と参照の両方の存在を確かめる

## 9. 確定事項と自律判断
イシューに明記されている（解決方針・スコープ）:
- 対話画面は `scripts/claude/` の専用スクリプトで確かめる。起動は `claude` に固定し、`!` で始まる入力は送らない。`.claude/settings.json` は変えない（tmux の広い許可は足さない）
- 実施者の基準の正は `plan-writing-rules.md`「実施者の区別」。`plan-issue/SKILL.md`・`test-gate/SKILL.md`・`manual_test_template.md` は 1 行の要約と参照
- Human の行は `試した手段:` 必須。判定は粗い fail-closed（中身の正しさは文字で見ない）。承認画面の言葉の判定は残す。「画面」「表示」などの言葉で tmux を求める判定は入れない
- 計画レビュー役に Human の行の妥当性の観点を 1 行
- S21 は終わったイシューの記録に依存しない。終わったイシューの記録は書き換えない
- `check-permission-prompt.sh`・`check-frontend-evidence.sh` は変えない

Claude が決めた（技術的な選択と理由。要件・基本設計・UI/UX の仮定は無い）:
- スクリプトの名前は `tui-capture.sh`（仮定で決めた）。理由: イシューの例のとおりで、何をするか（対話画面を読む）が名前で分かる
- 送れるキーは `{Enter}`・`{Escape}`・`{Tab}`・`{Up}`・`{Down}`・`{BSpace}` の 6 つ（仮定で決めた）。理由: イシューの対象の「ダイアログ」は、選ぶ・閉じるにキーが要る。一覧を広げるより、決まった形だけにして誤りを減らす
- 中の claude は `--permission-mode default` で起動する（仮定で決めた）。理由: 外のセッションの既定が自動承認モードでも、承認の画面・ダイアログの出方を通常モードで見るため（`docs/runbooks/frontend-verify.md` の「承認画面が出るかは通常モードで」と同じ考え）
- 起動の待ちは行頭の `❯` が出るまで（既定 30 秒・`--start-timeout` で変えられる）（仮定で決めた）。理由: スパイクでプロンプトの行が `❯` で始まることを確かめた。時間切れは exit 2 にして、黙って空の画面を返さない。テストで待ち時間を短くできるよう引数にした（テストだけの仕掛けではなく、遅い環境で延ばす使い道もある）
- テストは偽物の `tmux`・`claude` を PATH の先頭に置いて確かめる（仮定で決めた）。理由: CI に tmux と claude があるかは分からず、`.github/` は変えない。スクリプトの中は差し替えず、外から呼ばれるコマンドだけを置き換えるので、スクリプトの振る舞いそのものを確かめられる。本物の起動は手動テストで Claude が確かめる
- 前の書き方（`Claude で確かめられない理由:`）を通す例外は作らない（仮定で決めた）。理由: 例外を作ると、前の書き方で新しい行を書けて規則が効かない。終わった記録は判定にかけないので困らない
- `test_check_manual_test_executor.sh` の X9（I187 の終わった記録）も消す（仮定で決めた）。理由: S21 の 470 行と同じく、終わった記録に新しい書き方を求めることになる（AC7 と同じ理由）
- `plan-reviewer.md` の観点は「差し戻しファースト原則」の「手動テストケース」の表に置く（仮定で決めた）。理由: この表は Blocker で、Claude で確かめられるのに人に頼む行は、計画の段階で直すべきもの
- `plan-reviewer.md` 75 行の「Human 目視」（スパイクの扱い）は変えない（仮定で決めた）。理由: 計画のスパイクが実証できないときの扱いで、手動テストの実施者の基準ではない（範囲外）
- 一覧の該当なし

セキュリティ・ベストプラクティス:
- セキュリティ影響: アプリのコード・認証認可・個人情報・依存ライブラリは変えない（bandit・npm audit の対象の変更なし）
- `tui-capture.sh` の入力の扱い: 起動するコマンドは固定で、引数は tmux に `-l`（文字のまま）か、決まった 6 つのキー名でだけ渡す（シェルを通さない。`tmux send-keys` の引数として渡す）。`!` で始まる入力は起動前に止める。わざと避ける書き方（`/` のコマンドから設定を変えるなど）は対象にしない。中の claude は外と同じ設定・見張りで動くので、外の Claude が直接できること以上の権限は持たない。`.claude/settings.json` の変更は GitHub の差分とレビューが最後の守り
- 許可: `.claude/settings.json` を変えない。`Bash(tmux *)` を足さない（tmux の画面に送る文字で禁止しているコマンドも動かせるため）
- 公開リポジトリ: 画面の内容は標準出力に出すだけで、記録には手動テストの結果として要点だけを書く（秘密情報を含む画面は対象にしない）

要件適合性: 受け入れ条件の範囲を超えた仕様の追加は無い（`tui-capture.sh` のキーと引数は AC1 の「ダイアログなど」を確かめるのに要る範囲）。マルチテナント・ステータス遷移は非該当

P3/P5/P8 影響なし（DB・外部 API・非同期処理・インフラの追加なし。依存関係ファイルの変更なし。tmux はスクリプトを使うときだけの道具で、CI には足さない）。P6 影響なし（UI・データ量の懸念なし）。P9 影響なし（個人情報・未成年データ・テナントデータを扱わない）

設計品質: 実施者の基準は 1 か所（写しを減らす）。判定は粗い規則 1 つ（`試した手段:` の中身があるか）で、言葉の一覧を増やさない。設定値はスクリプトの引数の既定値（`--wait 2`・`--start-timeout 30`）と画面の大きさ（200x50）だけで、冒頭のコメントに書く

高リスク判定: `path_risk_trigger()` の集合（`.github/`・`.pre-commit-config.yaml`・`.secrets.baseline`・見張り・settings）に触れない。手元のハーネス（スキル・エージェント・`scripts/claude/` のスクリプトとテスト・runbook）だけの変更 → No の見立て（判定は plan-review）

Danger Ops（有無/手順/ロールバック）:
- 無（データ削除・破壊的変更・強制 push は無い）

## 必ず確かめる項目
（高リスク判定が Yes になったときに敵対的レビューが使う。No なら使わない）
| 項目 | 確かめ方 |
|---|---|
| 1. `tui-capture.sh` は `claude --permission-mode default` 以外を起動できず、`!` で始まる入力を送る前に止まる | 読んで可（TC-01 の T2・T8・FG） |
| 2. `tui-capture.sh` は失敗しても tmux のセッションを残さない | 読んで可（TC-01 の T1・T6・FG） |
| 3. `check-manual-test-executor.sh` は `試した手段:` の中身の無い Human の行・前の書き方だけの行を不合格にする | 読んで可（TC-02 の X5・X18・X19・FG） |

## 計画変更記録
（実装中に計画と違うことをするときに書く）

## レビュー結果
