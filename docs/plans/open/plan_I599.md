# I599 計画書: サンドボックスの中から scripts/claude/ に書いたスクリプトをレビュー前に外で流せる穴を塞ぐ

<!-- 各節に何を書くかは docs/runbooks/plan-writing-rules.md「計画書の節（形はひな形）」 -->

## 基本情報
- **計画書ID**: plan_I599
- **関連イシュー**: #599
- **Draft PR**: #601
- **作成根拠資料**: docs/issues/open/I599.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I599_review.md
- **作成日**: 2026-11-20

## 1. 背景/目的
- Claude が `scripts/claude/` に書いた（書き換えた）中身を、レビューの前にサンドボックスの外で動かせないようにする。`bash *` を外に出さない決まり（`docs/runbooks/danger-ops.md:42`）と同じ理由（書いたファイルを外で動かせる）を、`scripts/claude/` とフックにも効かせる

### 調査結果
**原因の概要**: サンドボックスの外に出すかは「コマンドの書き出し（`bash scripts/claude/*`）」だけで決まり、そのファイルの中身がレビュー済みかを誰も見ていない。Claude はそのフォルダに承認なしで書けるので、書いてすぐ外で動かせる。

**詳細**:
1. `.claude/settings.json` の `sandbox.excludedCommands` の `bash scripts/claude/*` は文字の並びの一致なので、新しいファイル・書き換えたファイル・`bash scripts/claude/../../どこか/x.sh`（「..」で外へ出る形）・`bash scripts/claude/$X` も当たり、外で動く
2. `Edit(scripts/claude/**)` が allow（`.claude/settings.json:13`）。サンドボックスの書き込みも作業フォルダの下を許す
3. フック（`.claude/settings.json` の `hooks`）は `python3 "$CLAUDE_PROJECT_DIR"/scripts/claude/hooks/<名前>.py` で作業ツリーのファイルを直接動かす。フックはサンドボックスの外で動くので、書き換えた見張りは次の道具の呼び出しから外で動く。`posttooluse_check.py:12` は `code-review.sh` も外で動かす
4. レビュー済みのスクリプトでも、引数で渡したものを動かす「入口」がある（`grep -nE '"\$@"' scripts/claude/*.sh` で全件を調べた）:
   - `scripts/claude/tests/run-all.sh:30-31`: 引数のファイルを（どこにあっても）`bash` で動かす。引数が無いときは `tests/test_*.sh` を全部拾う（新しく置いたテストも）
   - `scripts/claude/tests/stress-repeat.sh:9-10`: 2 番目の引数のファイルを動かす
   - `scripts/claude/test-session.sh:8`: 引数をそのまま `claude -p` に渡す。`--settings <自分で書いた設定>` でフックを足すと、そのフックが外で動く（この計画の確かめで実際にこの形を使った）
   - `scripts/claude/code-review.sh:416-425`（`run_one_gate`）: 自動テスト文書（`docs/tests/open/I###_auto_test.md`。Claude が書ける）の「決定論ゲート」の行のうち `bash scripts/claude/tests/*.sh` を `bash -c` で外で動かす。新しく書いたテストもレビューの前に外で動く（文字列を命令として流す箇所は `grep -nE 'bash -c|eval |sh -c' scripts/claude/*.sh` で全件を見た。他は `pr-base-sync.sh:84` の固定の中身だけ）
   - 他（`check-permission-prompt.sh`・`tui-capture.sh` など）は、起こすものが固定で、引数はイシュー番号・判定するコマンドの文字だけ（子のセッションは、このセッションと同じ設定で動く）
5. スクリプトどうしは、ほぼすべて固定の名前で呼び合う（`grep -nE '(bash|source|python3|exec)\s+"?\$' scripts/claude/*.sh`: `"$SCRIPT_DIR/issue-source.sh"`・`"$REPO_ROOT/scripts/claude/fix-review-lib.sh"`・`"$dir/gh-app-token"` など）。ファイル名を変数で組み立てて呼ぶのは、上の入口（引数）と `run-all.sh` の `test_*.sh` だけ
6. **スパイク（2026-11-20・計画の前に確かめた・plan-writing-rules「外部/ハーネス挙動依存のスパイク実証」(2)）**: `bash scripts/claude/test-session.sh --settings <試しの設定>` で子のセッションを起こし、外に出す一覧に当たるコマンドを、PreToolUse のフックが `updatedInput` で書き換えたときに中で動くかを見た。探りは `~/.cache` へ書けるか（中なら拒否される）
   - A（書き換えなし）: `WRITE_OK`（外）
   - B（フックが `true && ` を前に付ける・`permissionDecision: allow` つき）: `WRITE_DENIED`（中）
   - C（同じ書き換え・`permissionDecision` なし）: `WRITE_DENIED`（中）・承認の画面なし
   - **成立**: 外に出すかは、フックが書き換えた後のコマンドで決まる。許可の判定を変えずに（`permissionDecision` を返さずに）書き換えられる
7. 公式の機能だけで表せるか（`docs/runbooks/danger-ops.md`「見張りに判定を足すときの決まり」1）: `sandbox.excludedCommands` はコマンドの文字の型だけで、ファイルの中身・git の状態では分けられない。`permissions` も同じ。公式の差し込み口は PreToolUse の `updatedInput`（上で成立を確かめた）なので、見張りで書き換える
8. 事故の実例（同 2）: I597（2026-11-20）の implement で、新しく書いた `scripts/claude/db-backup.sh` を、レビューの前にテスト（`bash scripts/claude/tests/test_i597_db_backup.sh`）の中から外で動かした（中身は無害）
9. 一覧の残り: `docs/reviews/backlog/I430.md` F1（このイシューそのもの）・F2（git の穴。I600 で扱う）

## 2. 受け入れ条件
- [ ] AC1: Claude が `scripts/claude/` に新しく書いた・書き換えたスクリプトを、レビューの前（`git merge-base HEAD origin/develop` の時点と中身が違う）に `bash scripts/claude/…` で流すと、サンドボックスの中で動き、出力の頭に「レビュー前のため中で動かした」旨と、届いた変更のファイル名が出る
- [ ] AC2: 変えていないスクリプトでも、それが呼ぶファイル（名前で呼ぶもの・`run-all.sh` がまとめて拾うテスト・引数で渡したファイル）をたどって変えたファイルに届くときは、中で動く
- [ ] AC3: `bash scripts/claude/` の後ろに「..」・`$`・バッククォート・`*?[`・`~` を含むときは、変更の有無によらず中で動く
- [ ] AC4: 変えたファイルに届かないレビュー済みのスクリプト（`issue-source.sh`・`code-review.sh`・`db-backup.sh` など）は、今までどおり承認なしに外で動く（`scripts/claude/` に変更が無いときは、見張りは git を呼ばずに今までどおり）
- [ ] AC5: `test-session.sh` に、決まった引数（モデル・許可のモード・最大の回数・出力の形・`--setting-sources`・中身がレビュー済みの設定ファイルの `--settings`）以外を渡すと、外で動かす前にユーザーの承認を求める
- [ ] AC6: フック（SessionStart・PreToolUse・PostToolUse）は、`scripts/claude/` に変更があるあいだ、分かれた時点（merge-base）の版で動く（書き換えた見張りは、マージされるまで外で動かない）
- [ ] AC7: 見張りが確認（ask）を返すときも、AC1〜3 に当たれば書き換え（中で動かす）を付けて返す（承認しても外では動かない）
- [ ] AC8: 上を、失敗の注入つきの決定論のテストで固定する（CI で流れる）
- [ ] AC9: `docs/runbooks/danger-ops.md` の説明（外に出すコマンド・外で流す必要があるときの頼み方・受け入れた残り）が、この方式と一致している

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `scripts/claude/hooks/pretooluse_guard.py`（安全装置）・`.claude/settings.json`（安全装置・フックの呼び方）・新規 `.claude/hooks/reviewed-hook.sh`（フックの起動役）・新規 `.claude/hooks/unreviewed.py`（レビュー済みかの判定）・`scripts/claude/code-review.sh`（ゲートの実走）・`docs/runbooks/danger-ops.md`・`docs/runbooks/harness-audit.md`・`scripts/claude/tests/`（新規 `test_i599_unreviewed_scripts.sh`・`test_settings_permissions.sh` に 1 項目）・`docs/reviews/backlog/I430.md`（F1 を消す）

## 4. 変更点一覧（具体）

### 修正アプローチ
- 「レビュー済み」＝このブランチが develop から分かれた時点（`git merge-base HEAD origin/develop`、以下 BASE）の中身と同じこと。作業中のブランチでレビュー段階を通った版は済みとしない
- スクリプト: 見張りが、流すスクリプトから呼ぶファイルをたどり、BASE と違うファイルに届くときだけコマンドを書き換えて中で動かす（ユーザーの判断・2026-11-20「推奨どおり」）。外で動かす必要があるとき（中では gh・`claude -p` が動かない）は、ユーザーに `! bash scripts/claude/…` で流してもらう
- フック: Claude が書けない場所に置いた起動役が、`scripts/claude/` に変更があるあいだ BASE の版の写しでフックを動かす
- `test-session.sh` に任意の設定を渡す形は、外でしか動かない（claude はネットワークが要る）ので、ユーザーの承認を求める

### 4-1. 見張り: レビュー前の中身を中で動かす（新規 `.claude/hooks/unreviewed.py`・`scripts/claude/hooks/pretooluse_guard.py`）
達成すること: AC1〜AC5・AC7。
- 判定の本体は新規 `.claude/hooks/unreviewed.py`（Python の標準ライブラリだけ）に置く。置き場所の理由: ① `scripts/claude/` の外なので、判定そのものがたどりの対象にならない（見張り・`code-review.sh` から呼んでも、判定を直したことで呼び元まで中に回らない） ② `.claude/hooks/` はサンドボックスから書けず、Edit は承認が要る ③ 見張りと `code-review.sh`（4-6）が同じ判定を使う（写しを作らない）
  - 関数 `check(command, root) -> Result(rewrite: bool, ask_reason: str | None, reached: list[str])`。CLI: `python3 .claude/hooks/unreviewed.py check -- '<コマンド>'`（終了コード 0=レビュー済み・1=中で動かす・3=承認が要る・2=使い方の誤り）
  - 見張りは `importlib.util.spec_from_file_location` で `<CLAUDE_PROJECT_DIR>/.claude/hooks/unreviewed.py` を読み込む。読み込めなければ、コマンドに `scripts/claude/` があるときは書き換え（安全側）
- 見張りの新しい関数 `_unreviewed_rewrite(raw)`: 上の `check()` を呼ぶ。Bash の判定の最初（`_analyze` の前）で 1 回だけ呼び、結果をモジュールの変数 `_REWRITE` に置く
- `check()` の中身:
  - 起動条件: コマンドの文字に `scripts/claude/` を含むときだけ（含まなければ git を呼ばずに None）
  - 参照の取り出し: `(?:\./|<作業ツリーの絶対パス>/)?scripts/claude/[^\s'"`;|&<>()]*` の語。語に `..`・`$`・`` ` ``・`*`・`?`・`[`・`~` を含めば「たどれない」として書き換え（AC3）
  - BASE: `git <_GIT_SAFE_OPTS> merge-base HEAD origin/develop`（`_clean_git_env()`・作業ツリーは `CLAUDE_PROJECT_DIR`、無ければ cwd の最上位）。失敗したら書き換え（安全側）
  - 変更の一覧 CHANGED: `git diff --name-only BASE -- scripts/claude`（コミット済み・ステージ・未ステージ）＋ `git ls-files --others --exclude-standard -- scripts/claude`（追跡していない新しいファイル）。空なら None（AC4 の速い道）
  - たどり（閉包）: 出発点＝取り出した参照（＋入口の引数）。`scripts/claude/` の下の全ファイル（`git ls-files` ＋ 追跡していない新しいファイル）の中身から、他のファイルの「リポジトリからの相対パス」か「ファイル名（語の境目つき）」が出てくれば辺を張る。出発点から届くファイルに CHANGED が入れば書き換え
  - まとめて拾う入口の表 `_RUNNER_GLOBS`: `scripts/claude/tests/run-all.sh` → `scripts/claude/tests/` の下すべて（`test_*.sh` を拾い、テストは fixtures を読む）
  - 引数で渡すものを動かす入口の表 `_ARG_EXEC`: `run-all.sh`（位置引数すべて）・`stress-repeat.sh`（2 番目）。引数のファイルを出発点に足す。`scripts/claude/` の外のパスは書き換え
  - `test-session.sh`: 引数が許可の表（位置引数 1 つ〔指示〕・`--model`・`--permission-mode`・`--permission-prompts`・`--max-turns`・`--output-format`・`--verbose`・`--setting-sources`・`--settings <BASE と同じ中身の作業ツリーのファイル>`）に無ければ ask_reason（AC5）。書き換えでは足りない（中では claude が動かない）ため
  - 書き換えの形: `updatedInput.command = "echo '[I599] レビュー前の中身があるので、サンドボックスの中で動かします（届いた変更: <最大 5 件>）。外で動かす必要があれば、ユーザーに ! で流してもらう: docs/runbooks/danger-ops.md' >&2 && " + 元のコマンド`。ファイル名は `[A-Za-z0-9._/-]` 以外を `_` に置き換えてから埋める。`echo` は外に出す一覧に無いので、コマンド全体が中で動く（調査結果 6）
- 出力: 書き換えがあり、他の判定が素通しのときは、`permissionDecision` を返さず `updatedInput` だけを返す（スパイク C。許可の判定は今までどおり）。`_ask()` は `_REWRITE` があれば `updatedInput` を同じ出力に足す（AC7。公式: ask と updatedInput の組み合わせはユーザーに書き換えた入力を見せて確かめる）。`_block()` はそのまま（動かない）
- ask_reason（test-session）は `_ask()` で返す
- 性能: 起動条件に当たらない呼び出しは今までどおり（git を呼ばない）。当たるときは git 3 回＋ `scripts/claude/` の下のファイルの読み取り（今 約 120 本）

### 4-2. フックの起動役（新規 `.claude/hooks/reviewed-hook.sh`・`.claude/settings.json`）
達成すること: AC6。
- `.claude/hooks/` はサンドボックスが書き込みを禁じ（このセッションのサンドボックスの `denyWithinAllow` にある）、Edit ツールの allow にも無い（書くたびに承認）。起動役をここに置く
- 動き（`bash .claude/hooks/reviewed-hook.sh <scripts/claude/hooks/X.py>`。標準入力はそのままフックに渡す）:
  1. `git <安全な -c 3 つ（見張りの _GIT_SAFE_OPTS と同じ）> -C "$CLAUDE_PROJECT_DIR" merge-base HEAD origin/develop` で BASE。失敗したら作業ツリーの版を動かし、標準エラーに理由を 1 行（R4 で受け入れ）
  2. `git diff --quiet BASE -- scripts/claude` が真かつ追跡していない新しいファイルが無ければ、作業ツリーの版を `exec python3`
  3. 違えば、`~/.cache/claude-reviewed-hooks/<BASE>/` に BASE の `scripts/claude` を `git archive BASE scripts/claude | tar -x` で写し（一時フォルダに書いてから名前を変える・できあがりの印 `.complete`）、写しの `scripts/claude/hooks/X.py` を `exec python3`。`~/.cache` はサンドボックスから書けない（調査結果 6 の探りで確かめた）
- `.claude/settings.json` の `hooks` の 5 か所の `command` を `bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/reviewed-hook.sh scripts/claude/hooks/<名前>.py` に替える（timeout・onFailure は今のまま）
- 写しの `posttooluse_check.py` は `__file__` から写しの `code-review.sh` を呼ぶ（レビュー済みの版）

### 4-3. 手順書（`docs/runbooks/danger-ops.md`）
達成すること: AC9。
- 「サンドボックス（第 1 層）」の外に出すコマンド（`:41-43`）に、4-1・4-2 の決まりを書く: 中で動く条件・出力の印・外で流す必要があるとき（gh・`claude -p` を使うスクリプトを変えたとき）はユーザーに `! bash scripts/claude/…` を頼む・`test-session.sh` に任意の設定を渡すと承認・フックは BASE の版で動く（見張りを直したイシューでは、直した見張りが効くのはマージの後）
- `docs/runbooks/harness-audit.md` の点検の表に 1 行: 「見張りの書き換えで中で動くか（R1）・`scripts/claude/test-session.sh` で子のセッションを起こして確かめる」
- 受け入れた残り（8 の R2〜R4）を書く。`:43`「スクリプトを足すときは外で動いてよいものかをレビューで見る」は「入口（引数で渡したものを動かすスクリプト）を足すときは `_ARG_EXEC`・`_RUNNER_GLOBS` に足す」に直す

### 4-4. テスト（`scripts/claude/tests/`）
達成すること: AC8。6 章のとおり。

### 4-5. 一覧の片付け（`docs/reviews/backlog/I430.md`）
- F1 の行を消す（このイシューで解消）

### 4-6. レビューのゲートの実走（`scripts/claude/code-review.sh` の `run_declared_gates`）
達成すること: AC2（自動テスト文書に書いたテストを経由して外で動かない）。
- ALLOW の行を実走する前に `python3 .claude/hooks/unreviewed.py check -- "$cmd"` を呼び、0 以外（レビュー前の中身に届く・判定できない）なら実走せず、証跡に `⏭ レビュー前の中身のため手元では流さない（CI の Harness Tests が流す）` と書く。VERDICT は BLOCKER にしない（`test_*.sh` は CI の `run-all.sh` が必ず流し、review-gate は CI の合格を待ってから進む）。`test_` で始まらないファイル（CI が流さない）は今までどおり UNSAFE（BLOCKER）
- `.claude/hooks/unreviewed.py` が無い・壊れているときは実走しない（安全側。証跡に理由）

## 5. 実装手順（ステップ）
1. 未知リスク: スパイク済み（調査結果 6）。実装の最初に、テストの土台（一時の git リポジトリに `origin/develop` を作り、見張りを流す）を作る → TC-01
2. 4-1 の判定（`.claude/hooks/unreviewed.py`）と見張りの出力（ステップ 1 の後。`.claude/` への書き込みは承認の画面が出る）→ TC-02〜TC-12
3. 4-2 の起動役と `.claude/settings.json`（ステップ 2 と並行してよい。承認の画面が出る）→ TC-13〜TC-16
4. 4-6 の `code-review.sh`（ステップ 2 の後）→ TC-18
5. 4-3 の手順書・4-5 の一覧（ステップ 2〜4 の後）→ TC-17
6. 注意: ステップ 2 から、このセッションの見張り（起動時の設定のまま作業ツリーの見張りを動かす）が新しい判定で動く。このブランチは `scripts/claude/` を変えるので、変えたファイルに届くスクリプト（`code-review.sh` など）は中で動き、gh・`claude -p` を使うものは失敗する。review-gate などで要るときはユーザーに `!` で流してもらう（R7）
7. 決定論のテストの失敗の注入（ステップ 2〜4 の後）→ 各 TC の FG

## 6. テスト計画
### 自動
- 新規 `scripts/claude/tests/test_i599_unreviewed_scripts.sh`（CI の Harness Tests で流れる）。一時フォルダに git リポジトリを作り、`origin/develop` に当たる参照を置き、`scripts/claude/` の小さな写し（呼び合うスクリプト・`tests/run-all.sh`・`test-session.sh`）で見張りを流して、出力の JSON（`updatedInput`・`permissionDecision`）を確かめる。テストの段・期待値は `docs/tests/open/I599_auto_test.md`
- `scripts/claude/tests/test_settings_permissions.sh` に 1 項目: `.claude/settings.json` のフックの `command` がすべて `reviewed-hook.sh` を通ること（新しいフックを足すときに素で書いて気づかずに壊しうる）
- テストレベル: 見張り・起動役の単体（JSON の入出力・終了コード）。本物の Claude Code の振る舞いは手動（下）
- 再発防止: I597 の形（新しく書いたスクリプトをテストの中から流す）を TC-02・TC-05 で固定
### 手動
- `docs/tests/open/I599_manual_test.md`（実施者は Claude。このセッション〔起動時の設定のまま作業ツリーの見張りを動かす〕と `test-session.sh` の子のセッションで観測）

## 7. ロールバック
- PR を revert する（設定・見張り・手順書・テストだけ。データの変更なし）。`~/.cache/claude-reviewed-hooks/` は消してよい（次の起動で作り直す）

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 「フックの書き換えの後のコマンドで外に出すかが決まる」は公式の明文が無い。Claude Code の版が変わると外で動きうる | スパイクで確かめた（調査結果 6）。手動 No.1 で本物のセッションで確かめ直す。ハーネスの総点検（`docs/runbooks/harness-audit.md`）の項目に足す | 受け入れ |
| R2: レビュー済みのスクリプトが、ファイル名を文字列で組み立てて呼ぶ形を新しく持つと、たどりが届かない | 今は該当なし（調査結果 5）。入口を足すときは `_ARG_EXEC`・`_RUNNER_GLOBS` に足すと手順書に書く。足すのは新しいスクリプトなのでレビューで見る | 受け入れ |
| R3: git が無視するファイル（`scripts/claude/tests/.venv`・`__pycache__` の `.pyc`）を書き換えると、変更の一覧に出ない | わざと避ける形（普通の書き方の事故では起きない）。`danger-ops.md`「見張りに判定を足すときの決まり」3 のとおり残す | 受け入れ |
| R4: BASE が求められない（`origin/develop` が無い等）と、起動役は作業ツリーのフックを動かす | 見張りは同じときに書き換え（安全側）。起動役はフック全体を止めると Claude が何もできなくなる（見張りを直せない）ので、作業ツリーの版で動かし理由を出す | 受け入れ |
| R5: 見張り・起動役が遅くなる（`/mnt/c` の git は遅い） | 起動条件に当たらないときは git を呼ばない。起動役は `git diff --quiet` だけ。手動 No.4 で測り、1 回 2 秒を超えたら直す | 回避 |
| R6: 見張りを直すイシューでは、直した見張りが手元で効くのはマージの後 | ユーザーの判断（2026-11-20）。直した見張りは CI の決定論のテストと、このセッション（起動時の設定のまま）で確かめる | 受け入れ |
| R7: gh・`claude -p` を使うスクリプト（レビュー役など）を変えたブランチでは、それが中で動けず失敗する | 手順書に「ユーザーに `!` で流してもらう」と書く。根本の扱い（変える前の版でレビューする）は I593 で扱う | 受け入れ |
| R8: 前に付ける `echo … >&2 &&` がコマンドの意味を変える | `&&` は `;`・`||`・`|`・改行・ヒアドキュメント・頭の注釈より強く結びつかない形にならないかを TC-10 で確かめる（`bash -n` と終了コードが元と同じ） | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 範囲は `scripts/claude/` の下（フック・`run-all.sh` を含む）。git・docker は I600（#600）
- 中で動かす（承認の画面は出さない）・出したことを必ず出す・中で動かないものだけユーザーに聞く・基準は merge-base・レビュー役のスクリプトの扱いは I593 とそろえる
- 前提の確かめ（`updatedInput` の後のコマンドで決まるか）→ 成立（調査結果 6）
計画の段階でユーザーに確かめた（2026-11-20。「ループ・ハーネス・グラフエンジニアリングの BP と開発効率の観点でベストなやり方で」＝ 3 問とも推奨）:
- 中で動かす範囲は「流すスクリプトから呼ぶファイルをたどって、変えたファイルに届くときだけ」（イシューのメモ「1 つでも違えばすべて中」から変えた。すべて中にすると、変えていないレビュー役も中で失敗し、段階ごとに人の手が要る）。AC2 に反映
- フックは BASE の版で動かす（R6）
- `test-session.sh` に任意の設定を渡すときは承認（AC5）
Claude が決めた（技術的な選択と理由）:
- `run-all.sh`・`test-session.sh` は直さず、見張りの側で入口の表を持つ（入口のスクリプトは引数を受けるのが役目で、そこで制限すると正当な使い方も壊す。イシューの実装対象の「`run-all.sh` を直す」から変えた）
- 書き換えは `echo '…' >&2 && ` を前に付ける形（出力に印が残るので、直しのループが「なぜ外と結果が違うか」を見失わない。追加の文脈〔additionalContext〕の届き方の確かめが要らない）
- 起動役は `.claude/hooks/` に置く（サンドボックスが書けず、Edit は承認が要る。`scripts/claude/` に置くと起動役そのものが書き換えられる）
- フックは「`scripts/claude/` 全体に変更があれば写し」で動かす（フックが呼ぶ `code-review.sh` まで含めて正しく、判定が単純）
- 写しの置き場所は `~/.cache/claude-reviewed-hooks/<BASE>/`（サンドボックスから書けない・BASE ごとに 1 回作る）
- 起動役の git は見張りと同じ安全な `-c`（`core.fsmonitor=false`・`core.hooksPath=/dev/null`・`submodule.recurse=false`）を付ける（`.git/config` はサンドボックスの中から書けるため）
- 外で動かす必要があるときは、新しい仕組みを作らず `!`（ユーザーが流す）にする（抜け道になる合図の仕組みを増やさない）
- 見張りに判定を足す決まりの 3 点: 1 公式で表せない（調査結果 7）・2 実例は I597（調査結果 8）・3 わざと避ける形の指摘は Low で一覧へ（R3）
- 一覧 `docs/reviews/backlog/I430.md` F1: 同梱 — このイシューそのもの。実装で行を消す
- 一覧 `docs/reviews/backlog/I430.md` F2: 残す — git の穴は I600 で扱う
- 一覧 `docs/reviews/backlog/I211.md` F1・F2（`run-all.sh` の相対パス・`VIRTUAL_ENV`）: 残す — 使い勝手の話で、この穴と関係しない
- 一覧 `docs/reviews/backlog/I210.md` F6（`stress-repeat.sh` の trap）: 残す — 同上
- 一覧 `docs/reviews/backlog/I200.md` F5・`I454.md` F8・F9・`I463.md` F4・`I492.md` F4（`pretooluse_guard.py` の語の判定）: 残す — 別の判定
- 一覧 `docs/reviews/backlog/I226.md` F4（`posttooluse_check.py`）・`I219.md` F3〜F6・`I221.md` F10・`I569.md` F3（`sessionstart_context.py`）: 残す — フックの中身の話で、起動のしかたと関係しない
- 一覧 `docs/reviews/backlog/I206.md` F4・`I207.md` F6・F7・`I208.md` F2・F5・`I212.md` F2〜F4・F6・`I227.md` F1・F2・F4・F5・R1・`I512.md` F2・F3・F6・F14・F15（`code-review.sh`）: 残す — 台帳・出力の読み方の話で、ゲートの実走と関係しない
- 判定の本体を `.claude/hooks/unreviewed.py` に置く（4-1 の理由 ①〜③）。`code-review.sh` のゲートは、レビュー前の中身に届く行を手元で流さず CI に任せる（CI の Harness Tests が `test_*.sh` を全部流し、review-gate は CI の合格を待つので、手元の実走は重ねての確かめ。BLOCKER にすると、テストを足すハーネスのイシューが毎回止まる）
- 一覧 `docs/reviews/backlog/I430.md` F3〜F5・`I223.md` B1〜B4・`I224.md` F9（`FILE=-` を含む）: 残す — 関係しない
- 要件適合性: 受け入れ条件はイシューの AC と、計画の段階のユーザーの判断の範囲。業務ロジック・マルチテナントは該当なし
- セキュリティ・BP: 入力の検証＝見張りが読むコマンドの語・ファイル名は埋める前に文字を絞る（R8・4-1）。認証・認可・個人情報・OWASP・依存の追加なし（Python の標準ライブラリだけ）。bandit は MEDIUM 以上を直す（`subprocess` は引数の配列・shell なし）。最小権限: 外で動くのはレビュー済みの中身だけにする変更
- テスト計画: 再発防止（I597 の形）あり。テストレベルは 6 章
- P3/P5/P8 影響なし（DB・外部 API・新しいインフラなし）。P6 影響なし（画面なし。性能は R5）。P9 影響なし
- 設計品質: 失敗時は安全側（書き換え）に倒す。例外は見張りの既存の `_fail_safe` に乗る。表（`_RUNNER_GLOBS`・`_ARG_EXEC`・test-session の許可の表）はモジュールの定数に置く
Danger Ops（有無）:
- 無（設定・見張りの変更。データの削除なし）。安全装置の変更なので、レビューは敵対的レビューを含む

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | 本物の Claude Code で、レビュー前の新しいスクリプトを `bash scripts/claude/…` で流すと中で動く（手動 No.1・調査結果 6 のスパイク） |
| V2 | 1 | 読んで可 | 変えていないスクリプトから名前で呼ぶライブラリ・`run-all.sh` が拾うテスト・引数のファイルを変えると中で動く（TC-03・TC-05・TC-06） |
| V3 | 1 | 読んで可 | 「..」・`$`・バッククォート・glob・`~` の形、BASE が求められないときは中で動く（TC-07・TC-08） |
| V4 | 2 | 読んで可 | 各 TC は見張りの判定を外すと落ちる（FG。TC-02〜TC-16 の失敗の注入） |
| V5 | 3 | 読んで可 | 入口の洗い出し（調査結果 4・5。`code-review.sh` のゲートの実走を含む）に漏れが無い。外に出す一覧の他のコマンド（git・docker）は I600 |
| V8 | 1 | 読んで可 | `code-review.sh` が、レビュー前の中身に届くゲートの行を手元で流さない（TC-18） |
| V6 | 1 | 実験必須 | フックが、`scripts/claude/` に変更があるあいだ BASE の写しで動く（手動 No.3） |
| V7 | 1 | 読んで可 | 確認（ask）を返すときも書き換えが付く（TC-11） |

## 計画変更記録
<!-- 形は docs/runbooks/plan-writing-rules.md「計画変更記録の形」 -->
-
