# I179 自動テスト: ワークツリー運用の見直し

実行コマンド（例）: `bash scripts/claude/tests/test_pretooluse_worktree_guard.sh` / `bash scripts/claude/tests/test_wt_port_offset.sh` / `bash scripts/claude/tests/test_wt_lifecycle.sh` / `bash scripts/claude/tests/test_i179_worktree_docs.sh`

アプリ（backend / frontend）のコード変更は無いため pytest・Jest・E2E は対象外。すべて使い捨て git リポジトリと docker のスタブで動くシェルの決定論テスト（実物の Docker データ・ワークツリーには触れない）。

結果:
- backend: 対象外（コード変更なし）
- frontend: 対象外（コード変更なし）
- 計画時（実装前・2026-10-20）: 下記「計画時の実行記録」
- 実装時（2026-10-21・/implement）: guard pass=35・port pass=46・lifecycle pass=78（ロックの R13〜R15・FG4 追加後）・docs pass=12・test_i107 6 PASS・test_next_issue_num pass=21・構文行すべて exit 0（すべて fail=0）。修正前のガードでは G1・G2・G7 が FAIL することを確認済み
- 敵対的レビュー第 2 周の対応後（2026-10-21）: guard pass=60・port pass=53・lifecycle pass=146・docs pass=15・test_i107 exit 0・test_next_issue_num pass=21（すべて fail=0）。既存のガードのテスト（adversarial_trigger 40・checkout 14・gh_pr 245・push 87）も fail=0
- 実装後: （/test で記入）

## ベースライン（実装前・2026-10-20）
| テスト | 結果 |
|-------|------|
| `test_wt_lifecycle.sh` | pass=55 fail=0 |
| `test_wt_port_offset.sh` | pass=34 fail=0 |
| `test_pretooluse_worktree_guard.sh` | pass=27 fail=0 |

## テストケース

### A. 横断書込ガード（`scripts/claude/tests/test_pretooluse_worktree_guard.sh` に追加）
テスト環境: 既存の `$MAIN`（現ワークツリー役）・`$OTHER`（兄弟ワークツリー）に加え、`$MAIN/.claude/worktrees/nest` と `$MAIN/.claude/worktrees/nest2` を `git worktree add` で作る。フックへ stdin JSON を渡し exit code を見る（0=許可 / 2=ブロック）。

| TC | 内容 | cwd | 対象 | 期待 exit |
|----|------|-----|------|-----------|
| G1 | 入れ子が自分のファイルを Edit（**再発防止**） | nest | `nest/x.py` | 0 |
| G2 | 入れ子が自分のファイルへ Bash リダイレクト（**再発防止**） | nest | `echo x > nest/ok.txt` | 0 |
| G3 | 入れ子 → 親（primary 役）のファイルを Edit | nest | `$MAIN/x.py` | 2 |
| G4 | 親 → 入れ子のファイルを Edit | `$MAIN` | `nest/x.py` | 2 |
| G5 | 入れ子 → 兄弟ワークツリーを Edit | nest | `$OTHER/x.py` | 2 |
| G6 | 入れ子 → 別の入れ子を Write | nest | `nest2/x.py` | 2 |
| G7 | ブロック時の stderr に、所有者として入れ子の root（`nest2`）が表示され、親 root ではない | nest | `nest2/x.py` | stderr に `.claude/worktrees/nest2` を含む |
| FG-G1 | 失敗注入: ガードの複製で `_owning_root` を「最初に一致した root を返す」（旧ロジック相当）に書き換えると、G1 が 2（ブロック）になる | nest | `nest/x.py` | 2（＝G1 が回帰を捕まえる証明） |
| A1〜A23 | 既存ケース（fail-safe・DANGER_OK 非解除・symlink・兄弟名 decoy 等）が全て従来どおり | — | — | 既存の期待値 |

### B. ポート割当（`scripts/claude/tests/test_wt_port_offset.sh` を `wt-ports.sh` 対象に書き換え）
テスト環境: 使い捨ての primary 役（`backend/.env` あり・直下 `.env` なし）。追加ワークツリーは `git worktree add` で作り、`backend/.env` を置いてから、そのワークツリーを cwd にして `wt-ports.sh` を実行する。

| TC | 内容 | 期待 |
|----|------|------|
| P1 | 他に割当なし → offset 10 | exit 0・`.env` に `DB_PORT=5442`/`REDIS_PORT=6389`/`BACKEND_PORT=8010`/`FRONTEND_PORT=3010` |
| P2 | `--port-offset 20` | exit 0・`DB_PORT=5452`/`REDIS_PORT=6399`/`BACKEND_PORT=8020`/`FRONTEND_PORT=3020` |
| P3 | 既存 offset 10 のワークツリーがある所で `--port-offset 10` | exit 2・stderr に「既存 worktree と衝突」・`.env` は作られない |
| P4 | 1 つ目が offset 10 のとき 2 つ目を自動割当 | exit 0・2 つ目の `BACKEND_PORT=8020` |
| P5 | `--port-offset abc` / `--port-offset`（値なし） | どちらも exit 2・「--port-offset は数字」/「--port-offset に値がありません」 |
| P6 | `--port-offset 0`（primary の既定ポートと衝突） | exit 2・「既存 worktree と衝突」 |
| P7 | 割当済みワークツリーが**入れ子配置**（`<primary>/.claude/worktrees/a`・offset 10）にあるとき、別のワークツリーで自動割当 | exit 0・`BACKEND_PORT=8020`（入れ子も走査される） |
| P8 | 2 回目の実行（既に `BACKEND_PORT` あり） | exit 0・`.env` の内容が 1 回目と完全一致（`cmp`）・stdout に「割当済み」 |
| P9 | 生成 `.env` に `COMPOSE_PROJECT_NAME` が無い | `COMPOSE_PROJECT_NAME` を含まない |
| P10 | primary で実行 | exit 2・stderr に「primary は既定ポート」・primary に `.env` が作られない |
| P11 | `backend/.env` が無いワークツリーで実行 | exit 2・stderr に「backend/.env がありません」・`.env` が作られない |
| P12 | 直下 `.env` にポート以外の行（`FOO=1`）だけがある | exit 0・`FOO=1` が残り、4 つのポート行が追加される |
| P13 | `COMPOSE_PROJECT_NAME=foo` を設定して実行 | exit 0・stderr に `COMPOSE_PROJECT_NAME` の警告 |
| FG-P1 | 失敗注入: 衝突判定を `false` に置換した複製では P3 の条件でも exit 0 で `.env` が作られる | 複製で exit 0（＝衝突ガードが停止要因である証明） |
| FG-P2 | 失敗注入: `backend/.env` 検査行を削除した複製では P11 の条件でも exit 0 | 複製で exit 0（＝P11 の停止要因である証明） |

### C. 撤去（`scripts/claude/tests/test_wt_lifecycle.sh` を書き換え）
テスト環境: 使い捨ての bare origin＋primary 役。撤去対象は `git worktree add` で `origin/develop` 基点に作る（旧配置 `<base>/wt-app` と公式配置 `<primary>/.claude/worktrees/app2` の 2 種）。docker はスタブ: 環境変数 `STUB_CONTAINERS`・`STUB_VOLUMES` に入れた文字列を `docker ps -a -q ...`・`docker volume ls -q ...` の出力として返し、`DOCKER_FAIL_ON` に一致する呼び出しは exit 1。呼び出しはすべて記録する。

| TC | 内容 | 期待 |
|----|------|------|
| R0 | データ無し（両方空）・`DANGER_OK` なし | exit 0・ワークツリー撤去済み・記録に `compose down` が無い |
| R1 | コンテナあり・`DANGER_OK` なし | exit 2・stderr に「破壊的操作」・`down` 非実行・ワークツリー残存 |
| R1b | volume のみあり・`DANGER_OK` なし | exit 2・`down` 非実行・ワークツリー残存 |
| R1c | 判定失敗（`docker ps` が失敗）・`DANGER_OK` なし | exit 2・`down` 非実行・ワークツリー残存 |
| R1d | 判定失敗（PATH に docker が無い）・`DANGER_OK` なし | exit 2・ワークツリー残存 |
| R1e | 判定失敗（環境変数 `COMPOSE_PROJECT_NAME=foo`）・データ無し・`DANGER_OK` なし | exit 2・ワークツリー残存 |
| R1f | 判定失敗（撤去対象の `docker-compose.yml` に最上位 `name: x`）・データ無し・`DANGER_OK` なし | exit 2・ワークツリー残存（※テスト内で対象に未コミット変更を作らないよう、`name:` 入りの compose を develop にコミットした repo で作る） |
| R2/R3 | データあり・`DANGER_OK=1` | exit 0・`compose down -v` 呼び出し・down の時点でワークツリーが存在（順序）・撤去済み |
| R4 | 未コミット変更あり | exit 2・「未コミット変更あり」・`down` 非実行 |
| R5 | 未 push コミットあり | exit 2・「HEAD が未 push」・`down` 非実行 |
| R6 | primary を指定 | exit 2・「primary checkout は撤去できません」 |
| R7 | 撤去対象の内側から実行 | exit 2・「内側からは実行できません」・ワークツリー残存 |
| R8 | データあり・`DANGER_OK=1`・`down -v` が失敗 | exit 2・「docker compose down -v が失敗しました」・ワークツリー残存 |
| R9 | 公式配置（`<primary>/.claude/worktrees/app2`）・データ無し | exit 0・撤去済み |
| R9b | フォルダ名 `Wt.App` のワークツリー・データ無し（Compose の既定と同じ名前変換） | exit 0・docker の呼び出しの filter が `label=com.docker.compose.project=wtapp` |
| R10 | 撤去後もブランチが残る（R0・R9 の後で `git show-ref --verify refs/heads/<ブランチ>`） | exit 0・stdout に「ブランチ」と残ったブランチ名 |
| R11 | `git worktree list` に無いフォルダを指定（ただのディレクトリ） | exit 2・stderr に「登録されたワークツリーではありません」・フォルダは残る |
| R12 | 引数なし | exit 非ゼロ・Usage 表示 |
| R13 | 終了済みセッションのロック（`claude session app (pid 99999999 start 1)`＝存在しない pid）・データ無し（2026-10-21 追加・S10） | exit 0・撤去済み・stdout に「ロックを解除しました」 |
| R14 | 使用中セッションのロック（pid＝テストのシェル）・データあり・`DANGER_OK=1` | exit 2・「使用中の Claude セッション」・`down` 非実行・ワークツリーとロックが残る |
| R15 | Claude 以外の理由のロック（`on usb drive`）・データあり・`DANGER_OK=1` | exit 2・「ロックされています（理由: on usb drive）」・`down` 非実行・ワークツリー残存 |
| C1 | `COMPOSE_PROJECT_NAME` 設定時は警告が出る（R1e と同時に確認） | stderr に `COMPOSE_PROJECT_NAME` |
| FG1 | 失敗注入: `DANGER_OK` 判定を `true` に置換した複製では R1 の条件でも `down -v` が呼ばれる | 複製で記録に `compose down -v`（＝許可ゲートが停止要因である証明） |
| FG3 | 失敗注入: データ判定を常に「無し」（`return 0`）にした複製では R1 の条件でも `DANGER_OK` なしで撤去される | 複製で exit 0・撤去済み（＝データ判定が停止要因である証明） |
| FG4 | 失敗注入: 使用中判定（`ps -p`）を `false` にした複製では R14 の条件（データ無し）でも撤去される | 複製で exit 0・撤去済み（＝使用中判定が停止要因である証明） |

### C2. 敵対的レビュー第 1 周（2026-10-21）で追加した TC
| TC | スクリプト | 内容 | 期待 |
|----|-----------|------|------|
| R3b | lifecycle | `down -v` を実行したフォルダ（スタブが記録する `cwd=`） | 撤去対象のフォルダ |
| R1g | lifecycle | `docker volume ls` が失敗 | exit 2・残存 |
| R1h | lifecycle | 直下 `.env` に `export COMPOSE_PROJECT_NAME = study` | exit 2・「プロジェクト名を確定できません」 |
| R1i | lifecycle | 直下 `.env` に `COMPOSE_FILE=` | exit 2 |
| R1j | lifecycle | `compose.yaml`・`docker-compose.override.yml` に最上位 `name:`（コミット・push 済み） | どちらも exit 2 |
| R1k | lifecycle | フォルダ名 `___`（プロジェクト名が空） | exit 2・残存 |
| R16 | lifecycle | ロックあり・PATH に `ps` が無い | exit 2・「ps が無いため」 |
| R17 | lifecycle | 中に登録済みの入れ子（未コミットの `work.txt`）・データあり・`DANGER_OK=1` | exit 2・「中に別のワークツリー」・`down` 非実行・`work.txt` が残る |
| R18 | lifecycle | 中に未登録の `.git`（gitdir ファイル） | exit 2 |
| R19 | lifecycle | 撤去対象のフォルダ名が primary と同じ（`other/primary`）・データあり・`DANGER_OK=1` | exit 2・「別のワークツリーと同じです」・`down` 非実行 |
| R19b | lifecycle | R19 と同じ名前・データ無し | exit 0（撤去できる） |
| R20 | lifecycle | PATH に docker が無い・`DANGER_OK=1` | exit 0・「down -v を実行せずに撤去します」・撤去済み |
| FG5 | lifecycle | `down -v` の前の `cd` を外した複製 | 記録の `cwd=` が撤去対象でない（R3b が捕まえる証明） |
| FG6 | lifecycle | 入れ子の検査を `if false` にした複製で R17 の条件 | 入れ子の `work.txt` が消える（R17 が停止要因である証明） |
| P14 | ports | primary の `.env` が `SOME_VAR=1` だけ・`--port-offset 0` | exit 2・衝突 |
| DV1〜DV6 | guard | `docker compose down -v`・`-p <名前> down -v`・`--project-name … down --volumes`・`docker-compose -f x.yml down -v`・`docker volume rm`・`docker volume prune` | すべて exit 2 |
| DV7〜DV9 | guard | `-p <名前> down`（`-v` なし）・`DANGER_OK=1 docker compose -p … down -v`・`docker volume ls` | すべて exit 0 |
| FG-DV1 | guard | 旧パターン（compose の直後に down）に戻した複製で DV2 | exit 0（DV2 が回帰を捕まえる証明） |
| D3 追加 | docs | `git remote set-head origin --auto`・`refs/remotes/origin/HEAD` | worktree.md に在る |
| FG-D1 追加 | docs | `settings.json`・`issue-bootstrap/SKILL.md`・`worktree.md` を削除した複製 | それぞれ D7・D11・D4 が FAIL（不在チェックがファイル不在で PASS しない） |

### C3. 敵対的レビュー第 2 周（2026-10-21）で追加・変更した TC
| TC | スクリプト | 内容 | 期待 |
|----|-----------|------|------|
| R2（変更） | lifecycle | データあり・`DANGER_OK=1` | 記録に `compose -p wt-app down -v`（`-p` で固定） |
| R1c2 | lifecycle | docker はあるが `ps -a` が失敗・`DANGER_OK=1` | exit 2・`down` 非実行 |
| R1f（変更） | lifecycle | compose に `name: x` | 「プロジェクト名を確定できません」 |
| R1i（変更） | lifecycle | `.env` の行頭に空白のある `COMPOSE_FILE=` | exit 2 |
| R1j（変更） | lifecycle | compose ファイル 8 種すべてに `name : study`（コロンの前に空白） | すべて exit 2 |
| R20a | lifecycle | docker 無し・`DANGER_OK=1` だけ | exit 2・「KEEP_DATA=1」の案内・残存 |
| R20（変更） | lifecycle | docker 無し・`KEEP_DATA=1` | exit 0・「down -v を実行せずに撤去します（KEEP_DATA=1）」 |
| R20c | lifecycle | docker あり・データあり・`KEEP_DATA=1` | exit 2・`down` 非実行（KEEP_DATA は docker 不在専用） |
| R21 | lifecycle | コンテナの作業フォルダのラベルが primary・データあり・`DANGER_OK=1` | exit 2・「作業フォルダが撤去対象と違います」・`down` 非実行 |
| R22 | lifecycle | `COMPOSE_PROJECT_NAME=<primary 名>`・データあり・`DANGER_OK=1` | exit 2・「DANGER_OK=1 でも撤去しません」・`down` 非実行 |
| R22b | lifecycle | `.env` に `COMPOSE_PROJECT_NAME: prim`（コロン区切り）・`DANGER_OK=1` | exit 2・`down` 非実行 |
| R23 | lifecycle | 中の入れ子の登録がフォルダごと消えている（prunable） | exit 0・`worktree <撤去対象>` の行が一覧から消える（撤去前の一覧には在ったことも確認） |
| FG1（変更） | lifecycle | `if [ "${DANGER_OK:-}" != "1" ]` を `if false` にした複製で R1 の条件 | `compose -p wt-app down -v` が呼ばれる |
| FG5（変更） | lifecycle | `-p` 付き `down -v` の前の `cd` を外した複製 | `cwd=` が撤去対象でない |
| DV10〜DV19 | guard | `docker --context x compose down -v`・`-H`・クォートした `"down" "-v"`・`-vt 5`・`docker --log-level error volume rm`・`volume remove`・`--context x system prune --volumes`・`bash -c "…down -v"`・改行の後・`sleep 1 & ( … )` | すべて exit 2 |
| DV20〜DV23 | guard | コミットメッセージ中の文字列・grep の引数と `pytest -k "count down" -v`・`system prune`（`--volumes` なし）・`down --volumes=false` | すべて exit 0 |
| FG-DV1（変更） | guard | `_docker_volume_wipe` を常に None にした複製 | DV2・DV10 が exit 0 |
| P15 | ports | 他のワークツリーの `.env` が `export DB_PORT = "5442"` 等の書き方（`BACKEND_PORT2=9` は別の変数） | `--port-offset 10` は衝突で exit 2・自動割当は 8020 |

### D. 文書・設定（`scripts/claude/tests/test_i179_worktree_docs.sh` 新規）
検査は関数 `check_all <root>` にまとめ、実物（repo root）に対して実行して全 PASS、続けて失敗注入した複製に対して実行して FAIL を確認する。終了コード 0=全 PASS / 1=FAIL あり。

| TC | 内容 | 合否 |
|----|------|------|
| D1 | `scripts/claude/wt-new.sh` が存在しない | `test ! -e` |
| D2 | `git grep -n wt-new` の結果が、closed の記録類（`docs/{issues,plans,tests,reviews}/closed/`）と I179 自身の記録（`docs/issues/open/I179.md`・`docs/plans/open/plan_I179.md`・`docs/tests/open/I179_*.md`・`docs/reviews/open/I179_review.md`）以外に 0 件 | 0 件で PASS |
| D3 | `docs/runbooks/worktree.md` に次の文言がすべてある: `claude --worktree`・`.worktreeinclude`・`wt-ports.sh`・`wt-remove.sh`・`git stash push -u -m`・`git config`・`docker compose ls -a`・`git worktree list`・`track:harness`・`track:app`・`/plan-issue`・`wt-harness` の移行節の見出し（`旧方式からの移行`）・`grep -r`・`git worktree unlock`（2026-10-21 追加） | 全件 `grep -qF` 成功で PASS |
| D4 | `docs/runbooks/worktree.md` に次の文言が無い: `2026-07 時点`・`トラック = 1 作業ツリー`・`採番権威でもある`・`新設しない` | 全件不在で PASS |
| D5 | `.claude/skills/plan-issue/SKILL.md` に `git checkout develop` が無く、`checkout --no-track -b` と `origin/develop` がある | 3 条件成立で PASS |
| D6 | `docs/runbooks/issue-flow.md` の「ステップ5」から「ステップ6」までの範囲に `git checkout develop`・`git pull origin develop` が無く、`checkout --no-track -b` がある（範囲外のステップ25 は対象外） | 3 条件成立で PASS |
| D7 | `.claude/settings.json` に `WorktreeCreate`・`WorktreeRemove` が無い | 不在で PASS |
| D8 | `.worktreeinclude` に `backend/.env` と `e2e/.env.e2e` の行がある（行全体一致） | `grep -qx` 成功で PASS |
| D9 | `.gitignore` に `.claude/worktrees/` の行がある（行全体一致） | `grep -qx` 成功で PASS |
| D10 | `docs/runbooks/common-commands.md` に `wt-ports.sh` があり、`wt-new` が無い | 2 条件成立で PASS |
| D11 | `.claude/skills/issue-bootstrap/SKILL.md`・`docs/runbooks/issue-flow.md` に `対応 worktree: wt-harness` が無い | 不在で PASS |
| DOC1 | （旧 `test_wt_port_offset.sh` から移設）`worktree.md` に `同時`・`BACKEND_PORT`・`port-offset` があり `1 スタックずつ` が無い。`common-commands.md` に `BACKEND_PORT` がある | 全条件成立で PASS |
| FG-D0 | 注入なしの複製に `check_all` を当てると PASS（複製の作り方そのもので FAIL していないことの確認） | PASS |
| FG-D1 | 失敗注入: repo の対象ファイルを一時ディレクトリへ複製し（D2 が `git grep` を使えるよう複製先で `git init` → `git add -A` する）、次を 1 つずつ注入した複製それぞれで `check_all` が FAIL になる: D1（空の `wt-new.sh` を置く）・D2（除外対象外の `docs/runbooks/onboarding.md` に `wt-new` を追記）・D4（`2026-07 時点` を追記）・D5（`git checkout develop` を追記）・D6（ステップ5範囲に `git checkout develop` を追記）・D7（`"WorktreeCreate"` を追記）・D8（`.worktreeinclude` の `backend/.env` 行を削除）・D9（`.gitignore` の `.claude/worktrees/` 行を削除）・D10（`common-commands.md` に `wt-new` を追記）・D11（`issue-bootstrap/SKILL.md` に `対応 worktree: wt-harness` を追記） | 10 通りすべてで、注入対象の TC が FAIL に含まれれば PASS |

### E. 既存の回帰ゲート（変更しないテスト）
| TC | 内容 | 期待 |
|----|------|------|
| E1 | `test_i107_track_label_docs.sh`（`worktree.md` に `track:app`/`track:harness` が残る） | exit 0 |
| E2 | `test_next_issue_num.sh`（`worktree.md` §8 に `next-issue-num.sh`・「権威」が残る） | exit 0 |
| E3 | 構文: `wt-ports.sh`・`wt-remove.sh`・テスト 4 本の `bash -n`、ガードの `py_compile`、`settings.json` の `json.tool` | すべて exit 0 |

## 計画時の実行記録（2026-10-20・実装前）
- A〜D のテストスクリプト追加分は実装ステップ1〜5で作成する（現時点では未作成）。各スクリプトは失敗注入（FG-*）を内蔵し、実装時に「注入で FAIL・実物で PASS」を記録する。
- 決定論ゲートのうち、現時点で実行できる行を実行した結果は下記（実装前なので、新規ファイル・新しい文言を前提とする行は NG になるのが正しい）。

| ゲート行 | 実装前の結果 | 判定 |
|---------|------------|------|
| `bash scripts/claude/tests/test_pretooluse_worktree_guard.sh` | exit 0（pass=27・G1〜G7 は未追加） | 既存分は緑。G 追加後、修正前のガードで G1/G2 が FAIL することを実装時に確認する |
| `bash scripts/claude/tests/test_wt_port_offset.sh` | exit 0（pass=34・旧 wt-new 対象） | 書き換え後は `wt-ports.sh` 対象 |
| `bash scripts/claude/tests/test_wt_lifecycle.sh` | exit 0（pass=55・旧 wt-new 対象） | 書き換え後は R0〜R12 |
| `bash scripts/claude/tests/test_i179_worktree_docs.sh` | exit 127（ファイル未作成） | 実装前なので NG が正しい |
| `bash scripts/claude/tests/test_i107_track_label_docs.sh` | exit 0（6 PASS） | 回帰ゲート（実装後も exit 0 であること） |
| `bash scripts/claude/tests/test_next_issue_num.sh` | exit 0（pass=21） | 回帰ゲート（実装後も exit 0 であること） |
| `! grep -q WorktreeCreate .claude/settings.json` | exit 0 | 不変条件。失敗注入: 両フックを含む scratchpad の `fg/settings_injected.json` に対して同じ形で実行し exit 1（false-green でない） |
| `! grep -q WorktreeRemove .claude/settings.json` | exit 0 | 同上（注入で exit 1） |
| `bash -n scripts/claude/wt-ports.sh` ほか構文行 | 新規ファイルは未作成 | 実装後に実行 |

## 決定論ゲート（自動実走）
<!--
  /code-review（code-review.sh）がこのブロックを 1 行 1 コマンドで実走し、実 exit code を VERDICT に注入する。
  文書・設定の存在/不在検査は test_i179_worktree_docs.sh（D1〜D11・FG-D1）に集約し、ここでは行を増やさない。
-->
```bash
bash scripts/claude/tests/test_pretooluse_worktree_guard.sh
bash scripts/claude/tests/test_wt_port_offset.sh
bash scripts/claude/tests/test_wt_lifecycle.sh
bash scripts/claude/tests/test_i179_worktree_docs.sh
bash scripts/claude/tests/test_i107_track_label_docs.sh
bash scripts/claude/tests/test_next_issue_num.sh
bash -n scripts/claude/wt-ports.sh
bash -n scripts/claude/wt-remove.sh
bash -n scripts/claude/tests/test_i179_worktree_docs.sh
python3 -m py_compile scripts/claude/hooks/pretooluse_guard.py
python3 -m json.tool .claude/settings.json
! grep -q WorktreeCreate .claude/settings.json
! grep -q WorktreeRemove .claude/settings.json
```

## 再発防止記録（fix-loop・2026-10-21）
- **なぜ失敗したか**: 敵対的レビュー第 2 周の対応で、ガードの Docker の volume 削除の判定を「生の文字列への正規表現」から「シェルを模したトークン判定」に**置き換えた**。トークン判定はシェルの文法（空白なしの区切り・前置コマンドのオプション・`sh -lc`・`$( )`・予約語・関数・ヒアドキュメント）を部分的にしか再現せず、develop のガードが止めていた入力を素通りさせた（後退）。誤ブロックを減らすために入れたヒアドキュメント除外も、境界の判定が不完全で、実行されるコマンドを隠す経路になった。旧方式で止まる入力が新方式でも止まることを確かめるテストが無かった。
- **何を変えたか**: 判定を「(1) 正規表現 ∪ (2) トークン判定」の和集合にし（(2) は (1) を置き換えず重ねるだけ）、ヒアドキュメント除外を撤回した。第 3 周の再現入力（DV-sh 28 形）・トークン層でしか捕まらない形（DV-tok）・develop のガードとの比較（NOREG）・各層が停止要因であることの失敗注入（FG-DV2・FG-DV3）を常設した。あわせて撤去スクリプトのバックアップ案内・止まったときの片付け手順・記録の消費箇所（イシュー・danger-ops.md・計画）を揃えた。
- **セキュリティ上の考慮点**: 承認なしの破壊的操作（開発 DB の volume 削除）を止める安全装置の後退で、アクセス制御の不備（OWASP A01 相当）。修正後は develop 以上の強さを構造的に保つ（和集合）。誤ブロック（文字列の中の記述でも止める）は develop から続く既知の種類として受容し、`DANGER_OK=1` 前置か言い換えで解ける。
- **次回どう防ぐか**: 安全装置（ガード・承認ゲート）の判定方式を変えるときは、(a) 旧方式の判定を残して新方式を重ねる（置き換えない）、(b) 旧版（`git show origin/develop:…`）と結果を比べるテスト（NOREG）を同じ変更で入れる、(c) 誤ブロックを減らす変更（除外・例外）は「除外の境界を悪用して本物を隠せないか」を失敗注入で確かめる。レビュー観点: 敵対的レビューの観点①に「旧版との比較で後退が無いか」を必ず含める。
