# I599 計画書: サンドボックスの中から scripts/claude/ に書いたスクリプトをレビュー前に外で流せる穴を塞ぐ

<!-- 各節に何を書くかは docs/runbooks/plan-writing-rules.md「計画書の節（形はひな形）」 -->
<!-- 2026-11-20 方式の見直し（第 2 版）: review-gate の上限でユーザーの判断。第 1 版（見張りがコマンドの文字から
     レビュー前の中身に届く形を見つけて中に回す）は計画変更記録とレビューの記録に残す -->

## 基本情報
- **計画書ID**: plan_I599
- **関連イシュー**: #599
- **Draft PR**: #601
- **作成根拠資料**: docs/issues/open/I599.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I599_review.md
- **作成日**: 2026-11-20（第 2 版 2026-11-20）

## 1. 背景/目的
- Claude が `scripts/claude/` に書いた（書き換えた）中身を、レビューの前にサンドボックスの外で動かせないようにする。`bash *` を外に出さない決まり（`docs/runbooks/danger-ops.md:42`）と同じ理由（書いたファイルを外で動かせる）を、`scripts/claude/` とフックにも効かせる

### 調査結果
**原因の概要**: サンドボックスの外に出すかは「コマンドの書き出し（`bash scripts/claude/*`）」だけで決まり、そのファイルの中身がレビュー済みかを誰も見ていない。Claude はそのフォルダに承認なしで書けるので、書いてすぐ外で動かせる。

**詳細**:
1. `.claude/settings.json` の `sandbox.excludedCommands` の `bash scripts/claude/*` は文字の並びの一致なので、新しいファイル・書き換えたファイル・`bash scripts/claude/../../どこか/x.sh`・`bash scripts/claude/$X` も当たり、外で動く
2. `Edit(scripts/claude/**)` が allow（`.claude/settings.json:13`）。サンドボックスの書き込みも作業フォルダの下を許す
3. フック（`.claude/settings.json` の `hooks`）は作業ツリーのファイルを直接動かす。フックはサンドボックスの外で動くので、書き換えた見張りは次の道具の呼び出しから外で動く。`posttooluse_check.py:12` は `code-review.sh` も外で動かす
4. 引数で渡したものを動かす入口: `scripts/claude/tests/run-all.sh`（引数のファイル・`tests/test_*.sh`）・`scripts/claude/tests/stress-repeat.sh`（2 番目の引数）・`scripts/claude/test-session.sh`（引数をそのまま `claude -p` へ。`--settings` のフックは外で動く）・`scripts/claude/code-review.sh:416-425`（自動テスト文書の決定論ゲートの `bash scripts/claude/tests/*.sh` を外で動かす）
5. **第 1 版の方式の限界（2026-11-20・review-gate 5 周）**: 外で動くのを既定にし、見張りがコマンドの文字（`shlex` での区切り・振り向け・置き換え・かっこ）からレビュー前の中身に届く形を見つけて中に回す方式は、直すたびに「外に漏れる」（F1・F2・F7・F11・F17・F18）か「普段の呼び出しを壊す」（F12・F13・F16）のどちらかが出て収まらなかった。シェルの書き方は数え切れず、既定が外である限り、読み落としが穴になる
6. **外で動く必要のあるスクリプト**（`grep -lE '(^|[^a-z_-])(gh|claude|docker|curl)( |$)' scripts/claude/*.sh` と、それを呼ぶ入口を読んだ。2026-11-20）: `adversarial-review.sh`・`check-permission-prompt.sh`・`code-review.sh`・`db-backup.sh`・`dependency-audit-issue.sh`・`fix-diagnosis-review.sh`（`fix-review-lib.sh` で `claude -p`）・`issue-review.sh`・`issue-source.sh`・`lint-frontend.sh`・`plan-issue-review.sh`・`post-review-comment.sh`・`pr-base-sync.sh`・`test-session.sh`・`tui-capture.sh`・`wt-ports.sh`・`wt-remove.sh`。ほか（`flow-stage.sh`・`gate-check.sh`・`check-*.sh`・`tests/*`）は git とファイルの読み書きだけで、中で動く（この会話で中から流して確かめた: `flow-stage.sh`・`check-manual-test-executor.sh`・`tests/test_*.sh`）。ライブラリ（`fix-review-lib.sh`・`review-process-lib.sh`）は入口から読み込まれるだけ
7. **スパイク（2026-11-20）**: `test-session.sh --settings <試しの設定>` の子のセッションで、PreToolUse のフックの `updatedInput` で書き換えたコマンドは、書き換えた後のコマンドで外に出すかが決まった（A 書き換えなし: 外・B/C `true && ` を前に付ける: 中・`permissionDecision` なしでも効く）。サンドボックスの中では環境変数 `SANDBOX_RUNTIME` がある（このセッションの中の Bash で `env` の名前を見た・探りの Python が中で `SANDBOX_RUNTIME` を見て「中」と出した）。外で無いことは手動 No.1（ステップ 3.5 の関所）で確かめる
7b. 外に出す型は文字の一致で、`bash .claude/hooks/reviewed-run.sh *` は相対パス。Bash ツールの作業フォルダ（cwd）は呼び出しをまたいで保たれるので、`cd x` の後に Claude が書いた `x/.claude/hooks/reviewed-run.sh` も型に当たる（計画レビュー 2026-11-20 の Blocker。第 1 版の `bash scripts/claude/*` にも同じ穴）。PreToolUse のフックの入力には `cwd` がある（公式のフックの入力の共通の欄）
8. 公式の機能だけで表せるか（`danger-ops.md`「見張りに判定を足すときの決まり」1）: 外に出すかは `excludedCommands` の文字の型だけ。中身が「レビュー済みか」は表せない。そこで、外に出す型を「起動役 1 つ」に絞り（公式の設定）、起動役が中身を確かめる。見張りは、決まった単純な形を起動役の形に付け替えるだけ（公式の `updatedInput`）
9. 事故の実例（同 2）: I597（2026-11-20）の implement で、新しく書いた `scripts/claude/db-backup.sh` を、レビューの前にテストの中から外で動かした（中身は無害）
10. 一覧の残り: `docs/reviews/backlog/I430.md` F1（このイシューそのもの・第 1 版で行を消した）・F2（git の穴。I600 で扱う）

## 2. 受け入れ条件
- [ ] AC1: 外に出す一覧に `bash scripts/claude/*` が無く、`bash .claude/hooks/reviewed-run.sh *` だけがある。`bash scripts/claude/…` は、どの形でも、そのままではサンドボックスの中で動く（新しく書いた・書き換えた・「..」・変数・置き換え・振り向け・前置きのどれでも）
- [ ] AC2: 外で動く必要のあるスクリプト（調査結果 6 の一覧）を単体の形（`bash scripts/claude/<名前> <引数…>`。`$`・バッククォート・`(`・`)`・`{`・`}`・`;`・`&`・`|`・`<`・`>`・改行・前置きの代入を含まない）で流すと、見張りが起動役の形に付け替え、`scripts/claude/` にレビュー前の中身（`git merge-base HEAD origin/develop` との差・追跡していない新規・git が無視するファイル）が無ければ、承認なしに外で動く
- [ ] AC3: レビュー前の中身があるときは、起動役は外で動かさず、理由と「ユーザーに `! bash scripts/claude/<名前> …` で流してもらう」案内を出して終了コード 3 で終わる（スクリプトは動かない）。基準を求められないときも同じ
- [ ] AC4: 起動役は、一覧に無い名前・`/`・「..」を含む名前を終了コード 2 で拒む。起動役を単体でない形（つなぎ・置き換え・振り向け・前置き）で流すと、見張りが止める
- [ ] AC5: `test-session.sh` に許可の表に無い引数（表に無い名前・`--permission-mode` の `bypassPermissions` など・プロジェクトの設定を読まない `--setting-sources` に `.claude/settings.json` 以外・レビュー前の `--settings`）を渡すと、承認を求める（スクリプトの形・起動役の形の両方）
- [ ] AC6: フック（SessionStart・PreToolUse・PostToolUse）は、`scripts/claude/` にレビュー前の中身があるあいだ、分かれた時点（merge-base）の写しで動く
- [ ] AC7: `code-review.sh` は、レビュー前の中身があるとき、自動テスト文書の決定論ゲートの `bash scripts/claude/tests/test_*.sh` を手元で流さない（CI の Harness Tests が流す）
- [ ] AC8: 上を、失敗の注入つきの決定論のテストで固定する（CI で流れる）
- [ ] AC9: `docs/runbooks/danger-ops.md` の説明が、この方式と一致している

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `.claude/settings.json`（安全装置: 外に出す一覧・allow・フックの呼び方）・新規 `.claude/hooks/reviewed-run.sh`（スクリプトの起動役）・`.claude/hooks/reviewed-hook.sh`（フックの起動役・第 1 版のまま）・`.claude/hooks/unreviewed.py`（判定。第 1 版のたどりを消して小さくする）・`scripts/claude/hooks/pretooluse_guard.py`（安全装置: 付け替え・起動役の形の確かめ）・`scripts/claude/code-review.sh`（ゲート）・`docs/runbooks/danger-ops.md`・`docs/runbooks/harness-audit.md`・`scripts/claude/tests/`（`test_i599_unreviewed_scripts.sh` を作り直す・`test_settings_permissions.sh`）

## 4. 変更点一覧（具体）

### 修正アプローチ
- **既定は中**。外に出すのは起動役（`.claude/hooks/reviewed-run.sh`）だけ。起動役は、`scripts/claude/` にレビュー前の中身が 1 つも無いとき、一覧にあるスクリプトだけを動かす。レビュー前の中身があれば外では動かさず、ユーザーに `!` で頼む案内を出す
- 見張りは安全の判定をしない。単体の形の `bash scripts/claude/<一覧の名前> …` を起動役の形に付け替える（便利のため）・起動役が単体の形で呼ばれているかを確かめる・`test-session.sh` の引数を確かめる（承認）だけ。読み切れない形は何もしない（中で動く）
- 「レビュー済み」＝このブランチが develop から分かれた時点（`git merge-base HEAD origin/develop`）の中身と同じ（第 1 版と同じ）
- フックは第 1 版の起動役（分かれた時点の写し）のまま

### 4-1. 判定（`.claude/hooks/unreviewed.py`・第 1 版から小さくする）
達成すること: AC2〜AC5・AC7 の判定の本体。
- 残すもの: `_git`（安全な `-c`・`GIT_` を外す）・`_files`（レビュー前の中身＝BASE との差・追跡していない新規・git が無視するファイル〔無視されるフォルダはまとめて数えない〕）・`_test_session_ask`（第 1 版の F4・F8 の確かめを含む）
- 足すもの: `OUTSIDE_SCRIPTS`（調査結果 6 の 16 本の名前の集合）・`SIMPLE_RE`（単体の形でない文字 `[$`(){};&|<>\n]` が無いこと）・`route(command, root) -> Route(new_command, ask_reason, block_reason)`:
  - コマンドに `.claude/hooks/reviewed-run.sh` を含む: 単体の形で、`bash .claude/hooks/reviewed-run.sh <名前> …` の 1 つの命令（前置きの代入なし）で、かつフックの入力の `cwd` の実体がプロジェクトの最上位（`CLAUDE_PROJECT_DIR` の実体）と同じでなければ `block_reason`（調査結果 7b。別のフォルダの偽の起動役が型に当たるのを止める）。`<名前>` が `test-session.sh` なら引数を `_test_session_ask` にかけて `ask_reason`
  - そうでなく、単体の形で `bash scripts/claude/<名前> …`（`<名前>` は `OUTSIDE_SCRIPTS` にあり `/` を含まない）で、`cwd` が最上位のとき（違えば何もしない＝中）: `new_command = "bash .claude/hooks/reviewed-run.sh <名前> <元の引数の文字>"`。`test-session.sh` なら `ask_reason` も
  - それ以外: 何も返さない（中で動く）
- CLI: `unreviewed.py outside-ok <名前>`（0=一覧にあり・レビュー前の中身なし／1=一覧に無い・名前の誤り／3=レビュー前の中身がある・基準を求められない）・`unreviewed.py dirty`（0=なし／1=あり・求められない）
- 消すもの: 第 1 版のたどり（`_reach`・`RUNNER_GLOBS`・`EXEC_SUFFIXES`・`TRIGGER_RE`・`_check_unparsed`・`rewrite_command` など）

### 4-2. スクリプトの起動役（新規 `.claude/hooks/reviewed-run.sh`）
達成すること: AC2〜AC4。
- `bash .claude/hooks/reviewed-run.sh <名前> [引数…]`。`root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"`
- 最初に、サンドボックスの中で動いていないかを見る（中では環境変数 `SANDBOX_RUNTIME` がある。調査結果 7 のスパイクの探りで確かめた）。中なら「起動役がサンドボックスの中で動いています（外に出す型に当たっていない）」と出して終了コード 4（中では gh・`claude -p` が動かないので、早く失敗させる。手動 No.1 の外か中かの観測にもなる）
- `python3 "$root/.claude/hooks/unreviewed.py" outside-ok "<名前>"` が 0 のときだけ `cd "$root" && exec bash "scripts/claude/<名前>" "$@"`。1 なら「一覧に無い名前」と終了コード 2。3 なら「レビュー前の中身があるので外では流せません。外で流す必要があれば、ユーザーに `! bash scripts/claude/<名前> …` で流してもらってください（docs/runbooks/danger-ops.md）」と終了コード 3
- 置き場所 `.claude/hooks/` はサンドボックスから書けず、Edit は承認が要る（第 1 版の手動 No.5 で確かめた）

### 4-3. 見張り（`scripts/claude/hooks/pretooluse_guard.py`）
達成すること: AC2・AC4・AC5。
- 第 1 版の `_unreviewed_rewrite` を `route(command, root, cwd)` を呼ぶ形に替える（`cwd` はフックの入力の `cwd`。無ければ最上位と違うものとして扱う）。`block_reason` は `_block`、`ask_reason` は `_ask`（`new_command` があれば `updatedInput` を付ける）、`new_command` だけなら `updatedInput` だけを返す（`permissionDecision` を返さない）
- 判定を読み込めないとき: コマンドに `.claude/hooks/reviewed-run.sh` があれば止める（`_block`）。それ以外は何もしない（既定は中なので安全）
- 第 1 版の「`scripts/claude/` を含めば `echo … &&` を前に付ける」は消す（既定が中になったので要らない）

### 4-4. 設定（`.claude/settings.json`）
達成すること: AC1。
- `sandbox.excludedCommands` の `bash scripts/claude/*` を `bash .claude/hooks/reviewed-run.sh *` に替える
- `permissions.allow` に `Bash(bash .claude/hooks/reviewed-run.sh *)` を足す（`Bash(bash scripts/claude/*)` は残す。中で動くので承認なし）
- フックの `command`（5 か所）は第 1 版のまま `reviewed-hook.sh` を通す

### 4-5. レビューのゲート（`scripts/claude/code-review.sh`）
達成すること: AC7。
- `gate_reviewed` を「`unreviewed.py dirty` が 0」に替える（第 1 版のコマンドごとのたどりをやめる）。レビュー前の中身があれば `bash scripts/claude/tests/test_*.sh` は手元で流さず `⏭`（CI が流す）、`test_` で始まらないものは今までどおり止める

### 4-6. 手順書（`docs/runbooks/danger-ops.md`・`docs/runbooks/harness-audit.md`）
達成すること: AC9。
- 「サンドボックス（第 1 層）」の外に出すコマンドを書き直す: 外に出すのは起動役だけ・起動役が動かす一覧・単体の形で流す・レビュー前の中身があるあいだは外で動かない（`!` で頼む）・`test-session.sh` の承認・フックは分かれた時点の写し。第 1 版の書き換え（`[I599]` の印）・たどり・置き換えの規則の説明は消す
- 一覧に足すとき: 外で動く必要のある入口のスクリプトを足すときは `OUTSIDE_SCRIPTS` に足す（`.claude/hooks/` なので承認が要る）。`harness-audit.md` に一覧を見直す `grep`（調査結果 6 の式）を書く
- `harness-audit.md` の I599 の行を「起動役で外に出るか・レビュー前の中身があると止まるか」に直す

### 4-7. テスト（`scripts/claude/tests/`）
達成すること: AC8。6 章のとおり。`test_i599_unreviewed_scripts.sh` は第 2 版の振る舞いに作り直す（第 1 版の TC の多くは消える）

## 5. 実装手順（ステップ）
1. 4-1 の判定を小さくし `route`・CLI を足す（`.claude/` への書き込みは承認の画面が出る）→ TC-01〜TC-06
2. 4-2 の起動役（ステップ 1 の後）→ TC-07〜TC-10
3. 4-3 の見張り・4-4 の設定（ステップ 1 の後）→ TC-01〜TC-06・TC-13
3.5. **ゲート**: ステップ 2・3 の直後に手動 No.1 を流し、起動役の形が本物の Claude Code で外に出ることを確かめる（`excludedCommands` の新しい型が当たるか・plan-writing-rules「外部/ハーネス挙動依存のスパイク実証」(2)）。不成立（終了コード 4）なら、ここで止めて計画をやり直す
4. 4-5 の `code-review.sh`（ステップ 1 の後）→ TC-11
5. 4-6 の手順書（ステップ 1〜4 の後）→ TC-15
6. 注意: このセッションは起動時の設定（`bash scripts/claude/*` が外に出る・見張りは作業ツリーのファイル）のまま。ステップ 3 の後、このセッションでは見張りが起動役の形に付け替えるが、起動時の設定では起動役が外に出ないので中で動き、gh・`claude -p` を使うものは失敗する。review-gate などはユーザーに `!` で流してもらう（このブランチはレビュー前の中身があるので、新しい方式でも同じ）

## 6. テスト計画
### 自動
- `scripts/claude/tests/test_i599_unreviewed_scripts.sh`（作り直し）。一時の git リポジトリ（`origin/develop` に当たる参照・`scripts/claude/` の小さな写し・`.claude/hooks/` の本物の写し）で、見張り・起動役・判定の CLI・`code-review.sh` のゲートを流す。期待値は `docs/tests/open/I599_auto_test.md`
- `scripts/claude/tests/test_settings_permissions.sh`: 外に出す一覧に `bash scripts/claude/*` が無く起動役がある・フックは起動役を通す
- マージの後の確かめ（完了の条件に入れる）: retro で、マージの後の最初のセッションで普段の呼び出し（`bash scripts/claude/issue-source.sh body <番号>` が承認なしに外で動いて本文を出す）を確かめる項目を、後続のイシュー（I593 か新しいイシュー）の受け入れ条件に書く。close の報告にも書く
- テストレベル: 単体（JSON の入出力・終了コード）。本物の Claude Code での外に出る振る舞いは手動（No.1 が起動役が外で動くこと・No.2 が `bash scripts/claude/…` が中で動くことを、起動役の「中で動いています」の印と gh の失敗の文言で区別する）。レビュー前の中身が無いときに一覧のスクリプトが外で動くこと（AC2 の外の側）は、このブランチでは中身が常に「あり」なので手元では観測できない: 動き（起動役が `exec bash scripts/claude/<名前>` する）は TC-07 で、外に出ることは No.1 で確かめ、組み合わせはマージの後の最初のセッションの普段の呼び出し（`bash scripts/claude/issue-source.sh` など）で確かめる（close の報告に書く）
- 再発防止: I597 の形（新しく書いたスクリプトを流す）が外で動かないことを TC-03 で固定
### 手動
- `docs/tests/open/I599_manual_test.md`（実施者は Claude）

## 7. ロールバック
- PR を revert する（設定・見張り・起動役・手順書・テストだけ。データの変更なし）。`~/.cache/claude-reviewed-hooks/` は消してよい

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 見張りの付け替え（`updatedInput`）の後のコマンドで外に出すかが決まることは公式の明文が無い。版が変わると付け替えた起動役が中で動く | 中で動く側に崩れるだけ（安全）。gh・`claude -p` が失敗して気づける。`harness-audit.md` で点検 | 受け入れ |
| R2: 外で動く必要のある入口を足したのに一覧に足し忘れる | 中で動いて失敗するので気づける（安全側）。手順書に書く | 受け入れ |
| R3: git が無視するフォルダ（`tests/.venv`・`__pycache__`）の中の書き換えは、レビュー前の中身に数えない（`--directory` でまとめる） | わざと避ける形。`run-all.sh` は一覧に無く中で動く。一覧のスクリプトが無視されるフォルダの中を動かす形は今は無い | 受け入れ |
| R4: BASE が求められないとき、フックの起動役は作業ツリーのフックを動かす（スクリプトの起動役は止める） | フック全体を止めると Claude が何もできず見張りも直せない | 受け入れ |
| R5: ハーネスのイシューで `scripts/claude/` を変えると、マージまで一覧のスクリプトも外で動かない（gh・レビュー役はユーザーに `!` で頼む） | 第 1 版より手間は増えうる（届かないスクリプトも止まる）が、外に漏れる穴が無い。レビュー役を写しで動かす改善は I593 で扱う | 受け入れ |
| R6: 見張りを直すイシューでは、直した見張りが手元で効くのはマージの後 | 第 1 版と同じ（ユーザーの判断） | 受け入れ |
| R7: 一覧のスクリプトが、変更の無いときに引数のファイルを外で動かす | 一覧の 16 本で引数のファイルを動かすのは `test-session.sh`（`claude -p` の設定）だけで、AC5 で承認にする。`run-all.sh`・`stress-repeat.sh` は一覧に無い | 回避 |
| R8: `origin/develop` の参照を書き換えると「済み」に見える | わざと避ける形。git の参照・設定は I600 | 受け入れ |
| R10: 一覧のスクリプトが、`scripts/claude/` の外の書き換えられるものを動かす（`lint-frontend.sh` はコンテナの中で frontend の eslint の設定・`package.json` を動かす・`pr-base-sync.sh`・`wt-*.sh` は git の設定・docker を使う） | `scripts/claude/` の中身のレビューで守れるのは `scripts/claude/` だけ。git の設定・フック・docker（compose の設定）経由で外で動く穴は I600（#600）の範囲。frontend の設定はコンテナの中で動く | 受け入れ |
| R9: 起動役に `$(…)` などを付けて外で動かす | 見張りが単体でない起動役の形を止める（AC4）。公式もつなぎ・置き換えのあるコマンドは外に出さない（danger-ops.md「外に出すコマンドの書き方」） | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 範囲は `scripts/claude/` の下（フック・`run-all.sh` を含む）。git・docker は I600（#600）
- 基準は merge-base。レビュー役のスクリプトの扱いは I593 とそろえる
ユーザーの判断:
- 2026-11-20 計画の段階: フックは分かれた時点の版・`test-session.sh` の任意の設定は承認（第 2 版でも同じ）
- 2026-11-20 review-gate の上限（5 周・延長の後）: 方式を裏返す（既定を中にし、決まったスクリプトだけを、レビュー前の中身が無いときに起動役が外で動かす）。ユーザーの言葉は `docs/reviews/open/I599_review.md` の自律判断の記録
- 第 1 版のイシューのメモ「中で動かす（承認の画面は出さない）・出したことを必ず出す」は、第 2 版では「既定で中・外に出せないときは起動役が理由を出す」になる
Claude が決めた（技術的な選択と理由）:
- 一覧（`OUTSIDE_SCRIPTS`）は判定の本体（`.claude/hooks/unreviewed.py`）に 1 か所だけ置く（起動役と見張りが同じものを使う。写しを作らない）
- 起動役はレビュー前の中身が 1 つでもあれば止める（たどりをしない。第 1 版の限界〔調査結果 5〕の原因を持ち込まない）
- 見張りの付け替えは単体の形だけ（読み切れない形は何もしない＝中）
- 起動役を直接・単体でない形で流すのは見張りが止める（外に出す型が起動役 1 つなので、そこだけ単純な規則で締める）
- 第 1 版で作ったフックの起動役・写し・判定の git の安全な `-c`・無視されるファイルの数え方・`test-session.sh` の確かめは使い回す
- 見張りに判定を足す決まりの 3 点: 1 公式で表せない（調査結果 8）・2 実例は I597（調査結果 9）・3 わざと避ける形の指摘は Low で一覧へ（R3・R8）
- 一覧の残り（`docs/reviews/backlog/`）の扱いは第 1 版と同じ（I430 F1 は消した・F2 は I600・ほかは残す）
- 要件適合性: AC はイシューの目的とユーザーの判断の範囲。業務ロジック・マルチテナントは該当なし
- セキュリティ・BP: 既定を中にする（最小権限・許可の表）。認証・認可・個人情報・OWASP・依存の追加なし。bandit は MEDIUM 以上を直す
- P3/P5/P8 影響なし。P6 影響なし（画面なし）。P9 影響なし
- 設計品質: 失敗時は中（見張り）・止める（起動役）に倒す
Danger Ops（有無）:
- 無（設定・見張りの変更。データの削除なし）。安全装置の変更なので、レビューは敵対的レビューを含む

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 外に出す一覧が起動役だけで、`bash scripts/claude/*` が無い（TC-13）。どの形の `bash scripts/claude/…` もそのままでは外に出る型に当たらない |
| V2 | 1 | 読んで可 | 起動役は、レビュー前の中身（差・追跡していない新規・無視されるファイル）が 1 つでもあれば、一覧のスクリプトも動かさない（TC-08・TC-09） |
| V3 | 1 | 読んで可 | 起動役は一覧に無い名前・`/`・「..」を拒む。見張りは単体でない起動役の形・最上位でない cwd の起動役の形を止める（TC-04・TC-10・TC-17） |
| V4 | 2 | 読んで可 | 各 TC は判定・起動役・見張りを壊すと落ちる（FG） |
| V5 | 3 | 読んで可 | 一覧の 16 本に、引数のファイルを動かすもの・外の任意のものを動かすものが `test-session.sh` のほかに無い（調査結果 6・R7） |
| V6 | 1 | 実験必須 | 本物の Claude Code で、起動役の形が外に出て、レビュー前の中身があると止まる（手動 No.1） |

## 計画変更記録
<!-- 形は docs/runbooks/plan-writing-rules.md「計画変更記録の形」 -->
- 2026-11-20 plan-review: R9（`origin/develop` の参照）・手動 No.5・TC-20 を足した（第 1 版）。計画レビューのやり直し: 不要
- 2026-11-20 implement（/simplify）: 引数の入口の表 `_ARG_EXEC` を `EXEC_SUFFIXES` の規則に・git の回数を減らす・写しがあれば起動役は差を見ない・TC-22（第 1 版）。計画レビューのやり直し: 不要
- 2026-11-20 implement: 参照の取り出しを `shlex` の区切りに（TC-23・第 1 版）。計画レビューのやり直し: 不要
- 2026-11-20 fix-loop（延長の 1 周）: 置き換え・かっこの規則を変更があるときだけに（第 1 版）。計画レビューのやり直し: 不要
- 2026-11-20 plan-review（第 2 版）: 外に出す型が cwd に依存する穴（Blocker）に、見張りが `cwd` を確かめる規則・TC-17 を足した。`SANDBOX_RUNTIME` の根拠・マージの後の確かめ・一覧を見直す `grep` を足した。計画レビューのやり直し: 要（Blocker の直し）
- 2026-11-20 review-gate の上限（ユーザーの判断）: 計画書の記載: [外で動くのを既定にし、見張りがコマンドの文字からレビュー前の中身に届く形を見つけて中に回す（第 1 版の 4-1・4-6・AC1〜AC3・AC7）] → 採った方法: 既定を中にし、外に出すのは起動役だけ・起動役はレビュー前の中身が無いときに一覧のスクリプトだけを動かす（第 2 版） — 理由: 第 1 版は review-gate 5 周で「漏れる」と「壊す」が交互に出て収まらなかった（調査結果 5）。既定を中にすれば、読み落としは中で動くだけになり、安全の判定はコマンドの文字を読まない。計画レビューのやり直し: 要（方式・受け入れ条件を変える）

## レビュー結果
- [20261120_1958 判定: 差し戻し（Blocker 1件）](../../reviews/I599_plan_review_20261120_1958.md)
- [20261120_1957 判定: 差し戻し（Blocker 1件）](../../reviews/I599_plan_review_20261120_1957.md)
- [20261120_1718 判定: ✅ 完了](../../reviews/I599_plan_review_20261120_1718.md)（第 1 版）

## セキュリティレビュー結果（第 1 版・参考）
第 1 版のセキュリティ設計レビューの必須の防御のうち、第 2 版でも使うもの: 判定・起動役の git に安全な `-c` を付け `GIT_` を外す・写しは一時フォルダに書いてから名前を変え `.complete` を見る（フォルダは 700）・`test-session.sh` の引数は `=` の形を開いて表と照らし、表に無い語は承認。第 2 版のセキュリティ設計レビューは design-security-review 段階でやり直す。
