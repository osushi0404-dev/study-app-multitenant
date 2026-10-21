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

> **計画変更記録 7（2026-10-22）**: develop の I174 を取り込み、Docker・`git clean` の判定は I174 の見張りに一本化した。A3 の GC5 は止める側（2）、GC6 は確認（exit 0）、GC7 は `git clean -n -d` → 0 に変更し、FG-GC1 は削除。Docker の FG-DV1〜3 と、`docker.exe` の DV-sh・cat のヒアドキュメント本文の DV-sh を削除し、DV20（コミットメッセージ中の文字列）と DV20b（cat のヒアドキュメント本文）は通す側（0）にした。

### A3. `git clean -ff` の承認制（計画変更記録 6・2026-10-21・A2 を置き換え）
| TC | cwd | 入力 | 期待 |
|----|-----|------|------|
| GC1〜GC4 | `$MAIN` | `git clean -ffdx`・`git clean -f -f -d`・`git clean --force -f`・`cd /tmp && git clean -ffd` | 2 |
| GC5 | `$MAIN` | `git clean -fdx`（記録 7 で I174 の判定に一本化。f の数によらず止める） | 2 |
| GC6 | `$MAIN` | `DANGER_OK=1 git clean -ffdx`（I174 では人の確認） | 0 |
| GC7 | `$MAIN` | `git clean -n -d`（試すだけ。記録 7 で入力を変更） | 0 |
| ~~FG-GC1~~ | — | 記録 7 で `_git_clean_ff` ごと削除 | — |
| FG-DV4 | — | I174 の判定から `remove` を外した複製で DV15（`docker volume remove foo`）が exit 0（記録 7 で足した 1 語が停止要因である証明） | 0 |

### A2. 〔廃止・計画変更記録 6〕別ワークツリーの削除・破棄と相対パス書込（計画変更記録 5・2026-10-21 追加）
> 計画変更記録 6 で判定ごと廃止し、テスト（X1〜X161・FG-X1〜X5・X21b）も削除した。以下は経緯の記録として残す。

テスト環境は A と同じ（`$MAIN`・`$OTHER`・`$MAIN/.claude/worktrees/nest`・`nest2`）。`$MAIN` の `.gitignore` に `.claude/worktrees/` を入れる。cwd 欄の `$MAIN` は primary 役。すべて判定のみ（実際の削除はしない）。

**止める側（期待 exit 2）**
| TC | cwd | 入力（Bash） |
|----|-----|------|
| X1 | `$MAIN` | `rm -r .claude/worktrees/nest`（相対パス） |
| X2 | `$MAIN` | `rm -fr $MAIN/.claude/worktrees/nest/x.py`（絶対パス・`-fr`） |
| X3 | `$MAIN` | `rm -r -f .claude/worktrees/nest`（オプションを分けた形） |
| X4 | `$MAIN` | `cd .claude/worktrees/nest && rm x.py`（非再帰・前のセグメントの `cd` を反映） |
| X5 | `$MAIN` | `rm -r .claude`（中に別のワークツリーの root を含む） |
| X6 | nest | `rm -r $OTHER/src`（兄弟） |
| X7 | nest | `rm -r ../nest2`（入れ子 → 別の入れ子・相対） |
| X8 | `$MAIN` | `find .claude/worktrees/nest -name '*.py' -delete` |
| X9 | `$MAIN` | `find .claude/worktrees/nest -name x -exec rm {} +` |
| X10 | `$MAIN` | `git -C .claude/worktrees/nest checkout -- .` |
| X11 | `$MAIN` | `git -C .claude/worktrees/nest reset --hard` |
| X12 | `$MAIN` | `git -C $MAIN/.claude/worktrees/nest clean -fd` |
| X13 | `$MAIN` | `git -C .claude/worktrees/nest stash -u` |
| X14 | `$MAIN` | `git --work-tree=.claude/worktrees/nest restore .` |
| X15 | `$MAIN` | `git clean -ffdx`（中に nest がある） |
| X16 | `$MAIN` | `git clean -f -f -d` |
| X17 | `$MAIN` | `git worktree remove --force .claude/worktrees/nest` |
| X18 | `$MAIN` | `git worktree remove -f $OTHER` |
| X19 | `$MAIN` | `echo x > .claude/worktrees/nest/f`（相対パスの書込） |
| X20 | `$MAIN` | `cd .claude/worktrees/nest && echo x > f`（`cd` 越しの書込） |
| X21 | `$MAIN` | `rm -r <$MAIN の表記を大文字にした /mnt/c/… パス>/.claude/worktrees/nest`（`/mnt/<ドライブ>/` 配下で実行できる環境のみ。それ以外は SKIP を表示） |
| X22 | `$MAIN` | `DANGER_OK=1 rm -r .claude/worktrees/nest`（`DANGER_OK` でも解除しない） |
| X21b | 実リポジトリ | 中に別ワークツリーを含む親フォルダを大文字表記で `rm -r`（削除の判定でも大文字小文字をそろえる。X21 と同じ条件で SKIP） |
| X23〜X28 | `$MAIN` | 空白なしの `;`・`sudo -E`・`timeout 60 git -C …`・`mv <入れ子> /tmp/x`・`cd .claude/worktrees && git -C nest …`・改行の後 |
| X36（第 5 周で通す側から移動） | `$MAIN` | `git worktree remove .claude/worktrees/nest`（`--force` なしでも入れ子の作業ごと消えるため止める。撤去は `wt-remove.sh`） |
| X42〜X51（第 5 周） | `$MAIN` | 語の途中の `#` の後（`echo a#b; rm …`・`--format=%h#x; git -C …`）・閉じていないクォート（`$'\''`・ヒアドキュメント本文の `don't` の後）・`git worktree remove -ff`・`pushd`・`env -C`・`GIT_WORK_TREE=`・`rm -r .claude/worktrees/*`・`rm -r .*` |
| X52〜X57（第 5 周） | `$MAIN` | 相対パスの `tee`・`cp`・`cp -t`・`sed -i`、`git clean --force --force`・`-f --force` |

**通す側（期待 exit 0）**
| TC | cwd | 入力（Bash） |
|----|-----|------|
| X30 | nest | `rm -r build`（自分のワークツリー内・相対） |
| X31 | nest | `rm $MAIN/.claude/worktrees/nest/tmp.txt`（自分のワークツリー内・絶対） |
| X32 | `$MAIN` | `rm -r <scratch の一時フォルダ>/x`（どのワークツリーにも属さない） |
| X33 | `$MAIN` | `git -C .claude/worktrees/nest status`・`log -1`・`diff`（読み取り） |
| X34 | `$MAIN` | `git clean -fdx`（`f` が 1 個＝git が入れ子を飛ばす） |
| X35 | nest | `git clean -ffdx`（中に別のワークツリーが無い） |
| X37 | `$MAIN` | `find .claude/worktrees/nest -name '*.py'`（`-delete` なし） |
| X38 | `$MAIN` | `echo x > ok.txt`（自分のワークツリー内の相対書込） |
| X39〜X41 | `$MAIN` | commit メッセージ中の `rm -r <入れ子>`・`git checkout -b`・`2>&1 >/dev/null` |
| X62〜X66（第 5 周） | `$MAIN`／nest | `rm -f tmp_*.log`（非再帰）・行頭 `#` のコメント・`git worktree add`・`git worktree prune`・`cd ../nest2 && cd - && git checkout -- .`（`cd -` で自分に戻る）。※ 第 5 周に通す側だった `rm -r tmp_*`・`mv *.md docs/`（X60・X61）は fix-loop 2 回目で止める側へ移した |
| X67〜X69・X93（fix-loop 2 回目） | `$MAIN`／nest | `rm *.log`（非再帰・浅い）・`(cd /tmp && ls) && git status`・`(cd <入れ子> && git status) ; git commit -m x`（括弧の中の cd を外に持ち越さない）・入れ子のセッションでの `rm -r tmp_*` |

**止める側（fix-loop 2 回目・期待 exit 2・`rm` は `-r` で書き `rm -rf` の既存規則と区別する）**
| TC | cwd | 入力（Bash） |
|----|-----|------|
| X60・X61 | `$MAIN` | `rm -r tmp_*`・`mv *.md docs/`（primary 直下の展開を含む再帰削除・移動＝誤ブロックとして受容） |
| X70〜X73 | `$MAIN` | `DANGER_OK=1 rm -rf .[^.]*`・`rm -r .claude/worktrees/[^.]*`・`[[:alpha:]]*`・`.claude/worktree[^z]` |
| X74〜X78 | `$MAIN` | 中かっこ: `rm -r .claude/worktrees/{nest,zz}`・`{.claude,zz}`・`.claude/worktree{s,}`・`mv .claude/{worktrees,old}`・`rm .claude/worktrees/{nest,zz}/f.txt`（非再帰でも段数で止める） |
| X79〜X81 | `$MAIN` | `shopt -s dotglob; rm -r *`・`GLOBIGNORE=x; rm -r *`・`rm -r ~+/.claude` |
| X82・X83 | `$MAIN` | `(cd /tmp && ls) && git -C <入れ子> reset --hard`・`(cd /tmp) ; rm -r <入れ子>` |
| X84〜X89 | `$MAIN` | `timeout -s KILL 60 rm …`・`timeout --signal KILL 5 rm …`・`exec -a foo rm …`・`sudo -D .claude/worktrees rm -r nest`・`env -C.claude/worktrees rm -r nest`・`sudo -u git rm …` |
| X90〜X92 | `$MAIN` | `pushd <入れ子> && pushd /tmp && popd && git checkout -- .`・`cd <入れ子> && cd /tmp && cd - && git checkout -- .`・`GIT_DIR=<入れ子>/.git git checkout -- .` |
| X94〜X112（第 7 周） | `$MAIN` | `{ cd <入れ子>; rm -r src; }`・`if …; then cd …`・`X=1 cd …`・`command cd …`・`time cd …`（シェル内で cd が効く形）・`cp f .claude/worktrees/n*`・`cp -t .claude/worktrees/n* f`・`env -u cd -C .claude/worktrees rm -r nest`・`rm -r ~-/nest`・`env cd /tmp; rm -r <入れ子>`・`sudo cd /tmp && rm -r <入れ子>`（別プロセスの cd は効かない）・`sudo mv`/`timeout 60 find -delete`/`sudo sed -i`/`sudo tee`/`sudo cp`・`rm -r .claude/worktree?`・`env --chdir=…`・`sed -i -e '…' <入れ子>/f` |
| X115（第 7 周・通す側） | `$MAIN` | `{ cd /tmp; rm -r x; }`（候補の /tmp・自分のどちらでも別ワークツリーに当たらない） |
| X116〜X136（fix-loop 3 回目・止める側） | `$MAIN` | sed の続けて書く形（`-es/a/b/`・`-e's/.*//'`・`-f/tmp/s.sed`・`--expression=`）・`cd /tmp & rm -r <入れ子>`・`cd /tmp \| :; rm -r <入れ子>`・`mv -t /tmp/x <入れ子>`・`--target-directory=`・`builtin cd`・`time -p cd`・`nohup`/`nice -n 5`/`stdbuf -oL`/`ionice -c3`/`doas` の後・`(cd /var) ; cd -` の後・`GIT_WORK_TREE=… nice git checkout`・`time xargs rm -r`・`cp f <入れ子>?`/`[t]`/`{zz,nest}` |
| X66・X69・X113・X114（fix-loop 3 回目で止める側へ・受容した誤ブロック） | `$MAIN` | `cd <入れ子> && cd - && git checkout -- .`・`(cd <入れ子> && git status) ; git commit -m x`（1 つのコマンドで別ワークツリーへ移動してから自分側を変更）・`sed -i '2{s/foo/bar/}' f`・`sed -i -e '1,3{…}' backend/x.py`（primary で展開文字を含む sed のスクリプト） |
| FG-X5 | — | 「判定不能」の検出を外した（常に連鎖なしとして判定する）複製で X27・X138 が exit 0（FG-X4 は括弧の目印の処理ごと削除。fix-loop 5 回目で候補集めのループを削除したため対象を判定不能の検出に変更） |
| X137〜X145（fix-loop 4 回目・止める側） | `$MAIN` | `git --work-tree <入れ子> checkout -- .`（空白区切り）・`f(){ cd worktrees/nest && git checkout -- .; }; cd .claude && f`（後ろの移動が手前の相対移動の基準＝2 回目以降のまわり）・`cd ~+/<入れ子>; rm -r src`・`git -C ~+/<入れ子> …`・`cp --target-directory <入れ子>/src f`・`cp -t<入れ子>/src f`・`cp -vt <入れ子>/src f`・`cp --target=…`・`mv --target <入れ子> f` |
| X146〜X148（fix-loop 4 回目に通す側で追加 → fix-loop 5 回目で止める側へ・受容した誤ブロック） | nest | `cd backend && cd .. && git add -A`・`cd backend && cd ../frontend && rm -r build`・`cd docs && cd .. && echo a > x.txt`（移動を 2 つ以上含み判定できない。Bash 呼び出しを分ければ通る） |
| X149〜X154（fix-loop 5 回目・止める側・第 10 周①の後退） | nest / `$MAIN` | `cd backend && pytest; cd -; cd ../nest2 && git checkout -- .`・`pushd backend && … && popd && cd ../nest2 && git checkout -- .`・`git -C backend log -1 && cd ../nest2 && rm -r src`・`git -C backend status && cd ../other-wt && git checkout -- .`・`cd frontend && … && cd ~- && cd ../other-wt && git checkout -- .`・`cd /tmp && cd /var && rm -r <入れ子>`（絶対パスの移動先だけなら通常どおり判定） |
| X155〜X157（fix-loop 5 回目・通す側） | nest / `$MAIN` | `cd backend && cd .. && pytest`（読み取り・テストだけ）・`cd backend && rm -r build`（移動先 1 つ）・`cd a && cd b && rm -r <リポジトリ外の絶対パス>`（判定不能でも絶対パスの対象は判定する） |
| X158・X159（fix-loop 5 回目・処理量・第 10 周 C1） | `$MAIN` | `cd` を 12 個並べた後の `rm -r x` が exit 2・`ls` が exit 0。どちらもメモリ 1GB・10 秒の上限内（修正前のガードでは exit 1） |
| X160・X161（fix-loop 5 回目・fail-closed） | `$MAIN` / nest | 判定関数が例外（`MemoryError`）を出す複製で `ls` が exit 2（修正前は exit 1＝フックが止めない）・判定不能で止めたときに「Bash 呼び出しを分ける」案内が出る |
| FG-X3 | — | 中かっこを展開文字から外した複製で X74 が exit 0 |
| FG-X4 | — | 括弧の目印を捨てた複製で X82 が exit 0 |

**失敗注入・その他**
| TC | 内容 | 期待 |
|----|------|------|
| FG-X1 | ガードの複製で `_bash_destroy_targets` を常に空リストを返すように書き換えると、X1・X8・X10・X15・X17 が exit 0 になる | 5 件とも 0（＝止める側の停止要因が新しい判定である証明） |
| FG-X2 | ガードの複製で相対パスの絶対化を外す（相対パスを対象から除く）と、X1・X19 が exit 0 になる | 2 件とも 0 |
| DO1 | `echo DANGER_OK=1; docker compose down -v`（区切りの後ろの `DANGER_OK=1` では解除しない） | 2 |
| DO2 | `echo hi && DANGER_OK=1 git reset --hard`（同上） | 2 |

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
| DV20〜DV23 | guard | コミットメッセージ中の文字列（DV20）・`pytest -k down -v`／`pytest -k "count down" -v`（DV21/DV21b）・`system prune`（`--volumes` なし・DV22）・`down --volumes=false`（DV23） | DV20・DV23 は exit 2（fix-loop 案 A で文字列も止める・`--volumes=false` は安全側）、DV21・DV21b・DV22 は exit 0 |
| DV-sh 行継続（敵対的レビュー第 4 周） | guard | `docker compose down \⏎ -v`・前置コマンド（`timeout`・`sudo -E`）・空白なしの区切り（`true;`）・`bash -lc`・`$( )` の後の行継続、`docker \⏎ volume rm`・`system prune -af \⏎ --volumes`、`bash -c "$(cat <<'EOF' … EOF)"` | すべて exit 2（正規表現の層は空白をまとめた文字列に当てる）。NOREG にも行継続 3 形を追加 |
| FG-DV1（変更） | guard | `_docker_volume_wipe` を常に None にした複製 | DV2・DV10 が exit 0 |
| P15 | ports | 他のワークツリーの `.env` が `export DB_PORT = "5442"` 等の書き方（`BACKEND_PORT2=9` は別の変数） | `--port-offset 10` は衝突で exit 2・自動割当は 8020 |

### C4. 計画変更記録 5（2026-10-21）で追加した TC
| TC | ファイル | 条件 | 期待 |
|----|---------|------|------|
| R1（追加） | lifecycle | コンテナあり・`DANGER_OK` なし | 「volume だけ」の案内（機械で確かめられません）が出ない |
| R1b2 | lifecycle | volume のみあり（コンテナなし）・`DANGER_OK` なし | exit 2・stderr に「持ち主を機械で確かめられない」と volume 名・作成日時（スタブの `volume inspect` の値）・バックアップ手順が出る・`down` 非実行 |
| R1b3 | lifecycle | volume のみあり（コンテナなし）・`DANGER_OK=1` | exit 0・`compose -p <既定名> down -v` が撤去対象の中で 1 回だけ呼ばれる（許可を出す人には R1b2 の表示で判断材料を渡したうえで、許可どおり消す） |
| R21e | lifecycle | 戻り値 4（作業フォルダのラベルが別）・`DANGER_OK=1` | exit 2・stderr にバックアップ手順（`pg_dump`・`test -s`）が出る・`down` 非実行 |
| R24 | lifecycle | 同名の別ワークツリーあり＋データあり・`DANGER_OK=1` | exit 2・stderr にバックアップ手順が出る・`down` 非実行 |
| R25 | lifecycle | 戻り値 2（compose に `name:`） | exit 2・stderr に「コミットして push」と「元の名前のデータは worktree.md §4『取り残し』で片付ける」が出る |
| P16 | ports | 自分の `.env` に `export BACKEND_PORT=8010` の形で 4 変数が割当済み | exit 0・`.env` が変わらない（4 行を重ねて書き足さない） |

### D. 文書・設定（`scripts/claude/tests/test_i179_worktree_docs.sh` 新規）
検査は関数 `check_all <root>` にまとめ、実物（repo root）に対して実行して全 PASS、続けて失敗注入した複製に対して実行して FAIL を確認する。終了コード 0=全 PASS / 1=FAIL あり。

| TC | 内容 | 合否 |
|----|------|------|
| D1 | `scripts/claude/wt-new.sh` が存在しない | `test ! -e` |
| D2 | `git grep -n wt-new` の結果が、closed の記録類（`docs/{issues,plans,tests,reviews}/closed/`）と I179 自身の記録（`docs/issues/open/I179.md`・`docs/plans/open/plan_I179.md`・`docs/tests/open/I179_*.md`・`docs/reviews/open/I179_review.md`・`docs/reviews/I179_*.md`）以外に 0 件 | 0 件で PASS |
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
| D12 | （2026-10-21 追加）`docs/runbooks/danger-ops.md` に `volume rm / prune` と `wt-remove.sh` がある。FG-D1 に `volume rm / prune` を消す注入を追加 | 2 条件成立で PASS |
| FG-D0 | 注入なしの複製に `check_all` を当てると PASS（複製の作り方そのもので FAIL していないことの確認） | PASS |
| FG-D1 | 失敗注入: repo の対象ファイルを一時ディレクトリへ複製し（D2 が `git grep` を使えるよう複製先で `git init` → `git add -A` する）、次を 1 つずつ注入した複製それぞれで `check_all` が FAIL になる: D1（空の `wt-new.sh` を置く）・D2（除外対象外の `docs/runbooks/onboarding.md` に `wt-new` を追記）・D4（`2026-07 時点` を追記）・D5（`git checkout develop` を追記）・D6（ステップ5範囲に `git checkout develop` を追記）・D7（`"WorktreeCreate"` を追記）・D8（`.worktreeinclude` の `backend/.env` 行を削除）・D9（`.gitignore` の `.claude/worktrees/` 行を削除）・D10（`common-commands.md` に `wt-new` を追記）・D11（`issue-bootstrap/SKILL.md` に `対応 worktree: wt-harness` を追記）・D12（`danger-ops.md` の `volume rm / prune` を消す） | 11 通りすべてで、注入対象の TC が FAIL に含まれれば PASS |

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

## /test 実行記録（2026-10-21・e85a33a）
- pytest・Jest・E2E: 非該当（冒頭のとおりアプリのコード変更なし）。
- 上の決定論ゲート 13 件をすべて実行し、すべて exit 0（guard pass=129・port_offset pass=61・lifecycle pass=169・docs pass=16・track label PASS・next_issue_num pass=21・`bash -n` 3 件・`py_compile`・`json.tool`・WorktreeCreate/Remove 不在）。

## 再発防止記録（fix-loop・2026-10-21）
- **なぜ失敗したか**: 敵対的レビュー第 2 周の対応で、ガードの Docker の volume 削除の判定を「生の文字列への正規表現」から「シェルを模したトークン判定」に**置き換えた**。トークン判定はシェルの文法（空白なしの区切り・前置コマンドのオプション・`sh -lc`・`$( )`・予約語・関数・ヒアドキュメント）を部分的にしか再現せず、develop のガードが止めていた入力を素通りさせた（後退）。誤ブロックを減らすために入れたヒアドキュメント除外も、境界の判定が不完全で、実行されるコマンドを隠す経路になった。旧方式で止まる入力が新方式でも止まることを確かめるテストが無かった。
- **何を変えたか**: 判定を「(1) 正規表現 ∪ (2) トークン判定」の和集合にし（(2) は (1) を置き換えず重ねるだけ）、ヒアドキュメント除外を撤回した。第 3 周の再現入力（DV-sh 28 形）・トークン層でしか捕まらない形（DV-tok）・develop のガードとの比較（NOREG）・各層が停止要因であることの失敗注入（FG-DV2・FG-DV3）を常設した。あわせて撤去スクリプトのバックアップ案内・止まったときの片付け手順・記録の消費箇所（イシュー・danger-ops.md・計画）を揃えた。
- **セキュリティ上の考慮点**: 承認なしの破壊的操作（開発 DB の volume 削除）を止める安全装置の後退で、アクセス制御の不備（OWASP A01 相当）。修正後は develop 以上の強さを構造的に保つ（和集合）。誤ブロック（文字列の中の記述でも止める）は develop から続く既知の種類として受容し、`DANGER_OK=1` 前置か言い換えで解ける。
- **次回どう防ぐか**: 安全装置（ガード・承認ゲート）の判定方式を変えるときは、(a) 旧方式の判定を残して新方式を重ねる（置き換えない）、(b) 旧版（`git show origin/develop:…`）と結果を比べるテスト（NOREG）を同じ変更で入れる、(c) 誤ブロックを減らす変更（除外・例外）は「除外の境界を悪用して本物を隠せないか」を失敗注入で確かめる。レビュー観点: 敵対的レビューの観点①に「旧版との比較で後退が無いか」を必ず含める。

## 再発防止記録（fix-loop 2 回目・2026-10-21）
- **なぜ失敗したか**: 第 5 周で「primary 直下の `rm -r tmp_*` などを止めない」ために、ワイルドカードを bash の展開規則に近づけて細かく判定する方式（`fnmatch` によるパターン照合）に変えた。bash の展開規則（`[^…]`・文字クラス・中かっこ・`dotglob`/`GLOBIGNORE`・`~+`）を部分的にしか再現できず、再現しなかった部分が抜け道になった（`.[^.]*` を再帰削除すると全入れ子が消える）。中かっこは第 4 周の最初の設計から展開文字に含めていなかった。作業フォルダの追跡はサブシェルの範囲を捨て、前置コマンドは値を取るオプションを列挙する方式で漏れた。第 2〜3 周（Docker 判定の置き換え）と同じく、誤ブロックを減らすための精密化が安全装置を弱めた。
- **何を変えたか**: 展開を含むパス（`* ? [ {`）はパターンを解釈せず、手前の固定部分のフォルダを基準に粗く判定する（中身も消す操作は中に別ワークツリーがあれば止める・非再帰は段数だけ見る）。`~+`/`~-` を展開。括弧（サブシェル）の目印を残して中の `cd` を外へ持ち越さない。前置コマンドの後ろは既知のコマンド名の位置をすべて候補にする。展開を含む `mv` は全引数を移動元に。§2 の手動手順・§4 の登録の無い `.git` の手順・§9 の回避を追記。primary 直下の `rm -r tmp_*`・`mv *.md docs/` は誤ブロックとして受容。
- **セキュリティ上の考慮点**: 承認（`DANGER_OK=1` でも解けない）なしに他のワークツリーの未コミット作業を消せる経路（OWASP A01 相当）を塞いだ。誤ブロックは回避手順で解ける方向に倒し、判定不能・解釈しない部分は止める側に倒した。
- **次回どう防ぐか**: 安全装置の判定は「シェルの文法を再現して精密にする」方向に変えない。誤ブロックを減らしたいときは、判定を緩めるのではなく回避手順（サブフォルダで実行・名前を並べる）を文書化する。敵対的レビューで同種の指摘（再現漏れ）が周回をまたいで出たら、個別に塞がず判定を粗くする（I181・I176 の打ち切り条件の材料）。止める側の TC は既存規則（`rm -rf` の `DANGER_OK`）に当たらない書き方にし、新しい判定が停止要因であることを失敗注入で確かめる。

## 再発防止記録（fix-loop 3 回目・2026-10-21）
- **なぜ失敗したか**: 作業フォルダを「コマンドの順番どおりに追う」方式を採っていたため、bash の意味（括弧・パイプ・`&` のサブシェル、シェル内／別プロセスの前置き、`cd -`・`pushd`/`popd`）を正しく再現しないと穴になった（第 6 周の括弧・第 7 周の前置き・第 8 周のパイプと `&` で 3 回続いた）。あわせて、第 7 周で誤ブロックを減らすために足した sed のスクリプト除外が、`-es/a/b/` のような続けて書く形で本当の対象ファイルを外した（精密化が抜け道を生む構図の 3 回目）。`mv -t` は「最後の引数が宛先」という位置の前提で移動元を落とした。
- **何を変えたか**: 作業フォルダを順に追うのをやめ、セッションの作業フォルダとコマンド中のすべての移動先を「基準の候補」とし、相対パスは全候補を基準に判定する（和集合）。前置きの区別・括弧の目印・スタックを削除。sed のスクリプト除外を撤回、`mv` はすべての引数を移動元に。誤ブロック 2 種（1 つのコマンドで別ワークツリーへ移動してから自分側を変更する形・primary で展開文字を含む sed のスクリプト）は §9 に回避を書いて受容。公式のサンドボックスは入れ子のセッション・サブエージェントと両立しない恐れが大きく不採用。
- **セキュリティ上の考慮点**: `DANGER_OK=1` でも解けないはずの別ワークツリーの作業消失（OWASP A01 相当）の経路を、再現に頼らない形で塞いだ。分からないものはすべて止める側に入る。
- **次回どう防ぐか**: 安全装置で「状態を順に追う（シミュレーションする）」判定は避け、出てくる値をすべて候補にする和集合で判定する。誤ブロックを減らす変更は入れない（入れるなら回避手順の文書化で済ませる）。敵対的レビューで同じ種類の指摘が 2 周続いたら、3 周目を回す前に設計を粗くする（I181・I176 の打ち切り条件の材料）。

## 再発防止記録（fix-loop 4 回目・2026-10-21）
- **なぜ失敗したか**: 文字列を解析するガードの脅威モデル（何を守るか）を計画に書かないまま、敵対的レビューの「あらゆる抜け道」に応じ続けた。文字列からシェルの動きを完全には再現できないため、第 1〜9 周まで新しい回避形が見つかり続け、第 8 周の粗い判定（すべての移動先を全候補に当てる）は入れ子のセッションで `cd backend && cd ..` を止める止めすぎも生んだ。
- **何を変えたか**: 守る範囲を「Claude が普通の書き方で起こす事故」と §9・計画に明記し、意図的な回避の書き方（CDPATH・coproc・同じコマンドで作るリンク・オプションの省略形・逆順ループ等）は対象外とした。その範囲で、`..` を含む移動先は直前の位置だけを基準にする（止めすぎの解消）・候補集めは増えなくなるまで・`~+` の移動先・cp/mv の宛先指定の書き方（`-t<dir>`・`-vt`・`--target-directory <dir>`）を直した。
- **セキュリティ上の考慮点**: 過失による他ワークツリーの作業消失は止まる。意図的な回避は、Claude が敵対者ではない前提で対象外（強い境界は OS レベルのサンドボックスで別途。入れ子の配置と両立しない恐れがあり不採用）。
- **次回どう防ぐか**: 文字列を解析するガードを設計・拡張するときは、計画書に脅威モデル（守る範囲と対象外）を最初に書き、敵対的レビューのプロンプトにも渡す（対象外の回避形は新規に数えない・High は普通の書き方で事故が起きるものに限る）。完全な防御が要る対象は、文字列の解析ではなく OS レベルの仕組みを検討する（I181 の材料）。

## 再発防止記録（fix-loop 5 回目・2026-10-21）
- **なぜ失敗したか**: fix-loop 3 回目の和集合の候補集め（全移動先を全候補に当て、増えなくなるまで最大 8 回）は、相対の移動先が自分の作った候補にも当たり続けるため、移動先の数に対して指数的に増えた（`cd` 3 個で 1GB を超える）。上限も、ガードを例外から守る仕組みも無く、PreToolUse フックは exit 2 以外の異常終了では止めないため、後ろの危険操作の検査までまとめて素通りになり得た。第 10 周の計測でメモリを使い切り、セッションが落ちた。テストは短いコマンドだけで、処理量を確かめる TC が無かった。fix-loop 4 回目に足した「書いた順の直前の位置」も `cd -`・`popd`・`git -C` でずれる部分的な再現で、後退を生んだ（作業フォルダの扱いで同じ種類の 5 回目）。
- **何を変えたか**: 作業フォルダの連鎖を解釈しないことにした。基準の候補は、セッションの作業フォルダと、各移動先を 1 回だけ解いたものに限る（線形）。連鎖を解かないと宛先が決まらない形（相対を含む 2 つ以上の移動先・`cd -`・`popd`・`~±`）では、相対パスの削除・書込と git の変更を「判定できない」として止め、分けて実行するよう案内する。判定中の例外も exit 2 で止める。`cd backend && cd .. && git add -A` の誤ブロックは、§9 に回避（Bash 呼び出しを分ける）を書いて受容した。`cp -t` の止めすぎ（Medium）も対象外として §9 に記載した。
- **セキュリティ上の考慮点**: 防御機構の可用性の欠陥（巨大な入力で落とすと危険操作の検査をまとめて外せる fail-open。OWASP A04/A05 相当）を、処理量の構造的な上限と例外の fail-closed で塞いだ。判定できない形はすべて止める側に倒れる。
- **次回どう防ぐか**: 安全装置の判定は、入力の大きさに対して処理量の上限が構造的に決まる形（線形・固定回数）だけにし、処理量の TC（大きな入力を時間・メモリの上限付きで流す）を必ず置く。安全装置の判定関数は、例外を止める側（exit 2）に倒す形で呼ぶ。同じ種類の指摘が続いたら、シェルの動きを再現する方向ではなく「判定できない形は止めて分けさせる」方向に倒す。

## 再発防止記録（計画変更記録 6・削除・破棄ガードの廃止・2026-10-21）
- **なぜ失敗したか**: 守る対象（push していない手元の変更）の重さを確かめずに、「危ない書き方の一覧」をコマンドの文字列から完全に見つける方式を選び、敵対的レビューの指摘ごとに精密化を重ねた。第 1〜11 周・延べ約 30 体・7 時間以上・fix-loop 5 回を使っても、抜け道・止めすぎ・ガード自体の不具合が出続けた。修正のたびに `/code-review` をやり直すと「1 回 3 周」の上限が戻るため、イシュー全体での歯止めも無かった。
- **何を変えたか**: 削除・破棄の判定一式を廃止し、影響の大きい `git clean -ff` だけを 1 つの文字列一致で承認制にした。残りは GitHub の保護（bot は PR を出すだけ）と、こまめな commit/push・`wt-remove.sh` の運用に任せる。
- **セキュリティ上の考慮点**: 失い得るのは push していない手元の変更だけで、GitHub 上の develop/main は保護されている。primary での入れ子ごとの全消去（`git clean -ff`）だけは承認制で残した。
- **次回どう防ぐか**: 安全装置を足す前に「守る対象が失われたら復旧できるか」「最後の守り（GitHub の保護など）がどこにあるか」を確かめ、復旧できるものはできる範囲で止める単純なルールにとどめる。文字列からシェルの動きを読み取る判定は作らない。敵対的レビューは、同じ種類の指摘が 2 周続いたら精密化をやめ、設計を単純にする方向で相談する（I181 の材料: イシュー全体での周回上限・やり直し時は差分だけを対象にする）。
