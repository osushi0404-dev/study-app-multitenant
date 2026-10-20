# I179 自動テスト: ワークツリー運用の見直し

実行コマンド（例）: `bash scripts/claude/tests/test_pretooluse_worktree_guard.sh` / `bash scripts/claude/tests/test_wt_port_offset.sh` / `bash scripts/claude/tests/test_wt_lifecycle.sh` / `bash scripts/claude/tests/test_i179_worktree_docs.sh`

アプリ（backend / frontend）のコード変更は無いため pytest・Jest・E2E は対象外。すべて使い捨て git リポジトリと docker のスタブで動くシェルの決定論テスト（実物の Docker データ・ワークツリーには触れない）。

結果:
- backend: 対象外（コード変更なし）
- frontend: 対象外（コード変更なし）
- 計画時（実装前・2026-10-20）: 下記「計画時の実行記録」
- 実装時（2026-10-21・/implement）: guard pass=35・port pass=46・lifecycle pass=63・docs pass=12・test_i107 6 PASS・test_next_issue_num pass=21・構文行すべて exit 0（すべて fail=0）。修正前のガードでは G1・G2・G7 が FAIL することを確認済み
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
| C1 | `COMPOSE_PROJECT_NAME` 設定時は警告が出る（R1e と同時に確認） | stderr に `COMPOSE_PROJECT_NAME` |
| FG1 | 失敗注入: `DANGER_OK` 判定を `true` に置換した複製では R1 の条件でも `down -v` が呼ばれる | 複製で記録に `compose down -v`（＝許可ゲートが停止要因である証明） |
| FG3 | 失敗注入: データ判定を常に「無し」（`return 0`）にした複製では R1 の条件でも `DANGER_OK` なしで撤去される | 複製で exit 0・撤去済み（＝データ判定が停止要因である証明） |

### D. 文書・設定（`scripts/claude/tests/test_i179_worktree_docs.sh` 新規）
検査は関数 `check_all <root>` にまとめ、実物（repo root）に対して実行して全 PASS、続けて失敗注入した複製に対して実行して FAIL を確認する。終了コード 0=全 PASS / 1=FAIL あり。

| TC | 内容 | 合否 |
|----|------|------|
| D1 | `scripts/claude/wt-new.sh` が存在しない | `test ! -e` |
| D2 | `git grep -n wt-new` の結果が、closed の記録類（`docs/{issues,plans,tests,reviews}/closed/`）と I179 自身の記録（`docs/issues/open/I179.md`・`docs/plans/open/plan_I179.md`・`docs/tests/open/I179_*.md`・`docs/reviews/open/I179_review.md`）以外に 0 件 | 0 件で PASS |
| D3 | `docs/runbooks/worktree.md` に次の文言がすべてある: `claude --worktree`・`.worktreeinclude`・`wt-ports.sh`・`wt-remove.sh`・`git stash push -u -m`・`git config`・`docker compose ls -a`・`git worktree list`・`track:harness`・`track:app`・`/plan-issue`・`wt-harness` の移行節の見出し（`旧方式からの移行`）・`grep -r` | 全件 `grep -qF` 成功で PASS |
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
