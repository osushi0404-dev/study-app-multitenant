# worktree ベースの並行作業運用

複数の作業（例: 「ハーネス改善」と「アプリ開発」、または同じトラックの別イシュー）を、**作業ツリーの分離 + セッションの分離 + ファイルベースの引き継ぎ**で無損失に並行させるための手順。単一作業ツリーでブランチを切り替える方式は、片方の未コミット変更がもう片方を妨げ、1 セッションで複数の作業を扱うとコンテキストが混在する。git worktree で作業場所ごとに独立したディレクトリを持つことでこれを解消する。

- **トラック** = 作業の束（GitHub ラベルで区別）。**ワークツリー** = 作業場所。1 トラックに複数のワークツリーを持ってよい。
- 作成・設定ファイルのコピー・変更が無いときの片付けは **Claude Code の公式機能**（`claude --worktree`・`.worktreeinclude`・自動片付け）に任せる。自作スクリプトは公式に無い部分（ポート割当・Docker データの後始末・横断書込ガード・採番）だけを受け持つ。
- 公式機能の仕様: https://code.claude.com/docs/en/worktrees （細かい仕様はここに書き写さない）

---

## 1. 用語

| 用語 | 意味 |
|------|------|
| トラック | 独立して並行させたい作業の束（例: ハーネス改善 / アプリ開発）。GitHub ラベル（`track:harness` / `track:app`）で区別する（→ §10）。 |
| worktree | `git worktree` が作る、同一リポジトリを共有する別ディレクトリの作業ツリー。 |
| primary checkout | 最初に `git clone` した本体の作業ツリー。`git worktree list` の先頭に出る。ワークツリーの作成元（親）で、撤去しない。 |
| 入れ子ワークツリー | 公式 `claude --worktree <name>` が作るワークツリー。primary の中の `<primary>/.claude/worktrees/<name>` に置かれる（`.gitignore` 済み）。 |
| linked worktree | `git worktree add` で後から生やした作業ツリーの総称（入れ子も含む）。 |

---

## 2. ワークツリーの作り方（公式 `claude --worktree`）

**作る前の確認（primary で行う。1 と 2 は一度合わせれば以後は確認だけ）**:

```bash
cd <primary>
# 1. 基点の確認: refs/remotes/origin/develop と出ること
git symbolic-ref refs/remotes/origin/HEAD
#    別のもの（refs/remotes/origin/main など。clone した時点の既定のまま残っている）が出る、または
#    「fatal: ref refs/remotes/origin/HEAD is not a symbolic ref」で失敗する（未設定）なら、リモートの今の既定ブランチに合わせる
git remote set-head origin --auto
#    （refs/remotes/origin/HEAD は全ワークツリー共有の参照。合わせ直しても origin/HEAD を使う手順・スクリプトは無い）
# 2. primary のブランチが I179 以降の内容を含むこと（.worktreeinclude・.gitignore の .claude/worktrees/・入れ子対応のガード）
test -f .worktreeinclude && grep -qx '.claude/worktrees/' .gitignore \
  && grep -q '_owning_root' scripts/claude/hooks/pretooluse_guard.py && echo ok
```

```bash
# 作成: 必ず primary checkout で実行する（例: ハーネス改善の 2 つ目 → harness-2）
claude --worktree <track>-<連番>
```

- **必ず primary で作る**: `claude --worktree` は実行したフォルダの中（`.claude/worktrees/`）に作る。primary 以外で実行すると、そのワークツリーの中に入れ子が作られる（外側を撤去するときは `wt-remove.sh` が入れ子を検出して止める → §4）。primary は撤去しないので、ここを作成元に固定する。
- **基点**: 公式の既定（`worktree.baseRef` の `"fresh"`）は `origin/<既定ブランチ>` から作る。既定ブランチは GitHub に問い合わせず、**手元の `refs/remotes/origin/HEAD`** で決まる（2.1.304 の実装で確認）。これが `origin/main`（初期コミットのみで中身が無い）を指していると、CLAUDE.md・`.claude/settings.json`（ガード）・スキルが何も無い空のワークツリーができるので、上の確認 1 で必ず `origin/develop` に合わせておく。
- **primary のブランチ**: `.worktreeinclude`・`.gitignore`・ガード（サブエージェントのフックは primary の `pretooluse_guard.py` が動く）は、primary が今チェックアウトしているブランチの内容で決まる。I179 より前に作られたブランチを primary で使っている間は、設定ファイルがコピーされない・primary で `git add -A` すると入れ子が embedded repository として追加される・入れ子が自分のファイルに書けない、が起きる。確認 2 が `ok` にならないときは作らない（primary のブランチに develop を取り込むか、そのブランチの作業が終わってから作る）。
- **初期ブランチ**: `worktree-<name>` で作られる。`/plan-issue` で feature ブランチを作った後、不要なら `git branch -d worktree-<name>` で消してよい。
- **設定ファイル**: gitignore 済みの `backend/.env`・`e2e/.env.e2e` は、リポジトリ直下の `.worktreeinclude` に従って公式機能が自動でコピーする（`--worktree`・サブエージェントの `isolation: worktree`・`EnterWorktree` のどれでも同じ）。**primary に `backend/.env` が無いとコピーされない**（黙って飛ばされる）。Docker を使う前に `wt-ports.sh` がこれを検査して止める（§5）。
- **終了時の確認**: 対話セッションの終了時に「ワークツリーを残すか」を聞かれたら、続けて使うワークツリーは「残す」を選ぶ。変更が無いワークツリーは公式機能が自動で片付ける。
- **ロック**: `claude --worktree` はセッションの間、ワークツリーを `claude session <name> (pid N ...)` という理由でロックする（`git worktree list` に `locked` と出る）。`claude -p --worktree` など、セッションが終わってもロックが残る場合がある（2.1.304 で確認）。ロックされたワークツリーは素の `git worktree remove` では消せないので、撤去は §4 の `wt-remove.sh` で行う。
- ロックの判定は pid で行うため、同じ環境（同じ WSL ディストリ）で動く Claude のロックだけを正しく判定できる。Windows 側など別の環境で動く Claude からワークツリーを使っている場合、その pid はこの環境に見えないので「終了済み」と判定される。その場合は `wt-remove.sh` を使う前に、そのセッションを終了しておく。
- サブエージェントに `isolation: worktree` で作業させる場合も同じ仕組み（作成・コピー・自動片付け）が使われる。サブエージェントは、呼び出したセッションのワークツリーの中にさらに入れ子を作る。変更があった入れ子は自動では片付かずに残る（ロックは付かない）。
- **自動片付けと入れ子の注意**: 公式機能の「変更が無い」の判定は、そのワークツリー自身の `git status` で行う。中の入れ子（`.claude/worktrees/` は gitignore 済み）の変更は見えないため、外側のワークツリーに変更が無く、中のサブエージェントの入れ子にだけ未コミットの変更があると、外側が「変更なし」として片付けられ、入れ子ごと消える恐れがある（ガードでは止められない）。サブエージェントに `isolation: worktree` で作業させたワークツリーは、終了時の確認で「残す」を選び、中の入れ子を確かめて（`git worktree list`）から §4 の `wt-remove.sh` で撤去する（`wt-remove.sh` は中に入れ子があると止まる）。

**セッションを開く**: 各ワークツリーでは別々に `claude` を起動する（`claude --worktree` で作った直後のセッションはそのまま使える。再開するときは、そのワークツリーのフォルダで `claude` を起動する）。Cursor / VSCode では別のウィンドウで開く:
- メニュー: File > New Window → Open Folder で対象のワークツリーを開く。または CLI: `cursor -n <path>` / `code -n <path>`（`-n` = 新しいウィンドウ）
- **落とし穴**: 既に開いているフォルダを「Open Folder」で開き直しても、新しいウィンドウにはならず既存のウィンドウにフォーカスが戻るだけ。別ウィンドウにしたいときは必ず New Window から開く。入れ子ワークツリーは primary のフォルダの中にあるので、primary のウィンドウのエクスプローラーからではなく、別ウィンドウで入れ子のフォルダ自体を開く。

**fallback（公式機能が使えない場合の手動手順）**:

```bash
# primary のセッションで作る
cd <primary>
git fetch origin
git worktree add <primary>/.claude/worktrees/<name> -b <ブランチ> origin/develop
git worktree list                                              # 現在の worktree 一覧を確認
# 作ったワークツリーのセッション（そのフォルダで起動した claude・ターミナル）で設定ファイルをコピーする
cp <primary>/backend/.env backend/.env                         # 中身は読まない・存在を確認する
cp <primary>/e2e/.env.e2e e2e/.env.e2e                         # E2E を行う場合のみ
```

- コピーは作ったワークツリーのセッションで行う。primary のセッションから入れ子へ書き込む形（`cp backend/.env .claude/worktrees/<name>/…`）は、別ワークツリーへの書込としてガードが止める（§9。`DANGER_OK=1` でも解除しない）。

---

## 3. 次のイシューへ移る（同じワークツリーで続ける）

1 つのワークツリーで、複数のイシューを順番に扱ってよい。

1. いまのイシューの未コミット変更を片付ける（コミット・push する。不要なら捨てる）。新しいイシューのイシューファイル（untracked）は残してよい。
2. `/plan-issue I<番号>` を実行する。`origin/develop` から直接 feature ブランチを作るため、develop をチェックアウトしない（別のワークツリーが develop を使っていても失敗しない）。未コミットのイシューファイルはそのまま新ブランチへ持ち越される。

---

## 4. 撤去

| ワークツリーの種類 | 撤去の方法 |
|------------------|-----------|
| Docker を起動したことがある | primary から `bash scripts/claude/wt-remove.sh <ワークツリーのパス>` |
| Docker を使っていない | 公式の自動片付けに任せる（変更が無ければ自動で消える）。残したもの・ロックが残ったものは、同じく primary から `bash scripts/claude/wt-remove.sh <ワークツリーのパス>`（docker が使える環境ならデータ無しと判定され、許可は不要。docker が使えない環境では判定できずに止まるので、データを消さずに撤去してよければ `KEEP_DATA=1` を付けて再実行する。`down -v` は実行されない） |

```bash
cd <primary>
# データ（当該 Compose プロジェクトのコンテナ・named volume）が無ければ、そのまま撤去する
bash scripts/claude/wt-remove.sh <primary>/.claude/worktrees/<name>
# データがある場合は停止する。停止メッセージに出るバックアップの手順（撤去対象のプロジェクトを -p で指定した pg_dump）を
# primary で実行してから、許可付きで再実行する（scripts/db_backup.sh は今いるフォルダのプロジェクトが対象なので使えない）
DANGER_OK=1 bash scripts/claude/wt-remove.sh <primary>/.claude/worktrees/<name>
# docker が使えない環境で、データを消さずに撤去する（down -v はしない。DANGER_OK とは別の合図）
KEEP_DATA=1 bash scripts/claude/wt-remove.sh <primary>/.claude/worktrees/<name>
```

- 撤去対象は `git worktree list` に登録されたワークツリーのパスで指定する（登録外のフォルダは扱わない）。公式配置も旧配置（`/mnt/c/app/wt-harness` など）も同じ形。
- 未コミット変更・未 push コミットがあると中止する（作業消失防止）。primary と、撤去対象の内側からの実行は拒否する。`--force` は使わない。
- **中に別のワークツリー（入れ子）があると中止する**。`.claude/worktrees/` は gitignore 済みなので、未コミット変更の検査にも `git worktree remove` にも引っかからず、そのままだと入れ子の中身（未コミットの作業を含む）ごと消えてしまう。サブエージェントが作った入れ子などは、中のものを先に（同じ `wt-remove.sh` で）撤去してから外側を撤去する。中の入れ子が未 push のコミットで止まる場合は、残したい作業ならその入れ子のセッションで push してから撤去し、不要な作業なら外側の撤去を見送る（`--force` は使わない。作業を捨てる判断は人が行う）。フォルダが既に無い登録（`git worktree list` に `prunable` と出るもの）は数えないので止まらない（登録は `git worktree prune` で消せる）。中に**登録の無い `.git`**（登録が消えた入れ子のフォルダ・入れ子に置いた clone など）があって止まった場合は、`wt-remove.sh` にもその内側を渡せない（登録されたワークツリーではない）。**外側のワークツリーのセッションで**中身（未コミットの作業が無いか）を確かめ、不要なら `rm -r .claude/worktrees/<内側>` で消してから、primary で `wt-remove.sh` を再実行する（primary のセッションからの削除はガードが止める）。登録が消えた入れ子では `git status` が `fatal: not a git repository` で使えないので、先に `git worktree repair <内側のパス>` で登録の復旧を試す（復旧できれば `wt-remove.sh` で撤去できる）。復旧できなければ、ファイルの更新日時（`ls -lt`）で最近の作業が無いかを確かめ、残したいものは外側の外へコピーしてから消す（確かめられないまま消さない）。
- ロック（§2）: 終了済みの Claude セッションが残したロック（pid のプロセスが無い）だけを外して撤去する。使用中のセッションのロックがあれば、何も消さずに止まる（そのセッションを終了してから再実行）。Claude 以外の理由のロックも止まるので、使っている人に確認のうえ `git worktree unlock <パス>` してから再実行する。
- データの判定: Compose プロジェクト名（フォルダ名を小文字にし、英数字・`_`・`-` 以外を除いたもの＝Compose の既定名）のラベルで `docker ps -a`・`docker volume ls` を調べる。`down -v` は必ず `docker compose -p <既定名> down -v` で、消す相手を既定名に固定して実行する（環境変数・`.env`・親フォルダの compose ファイルで primary など別のプロジェクトが選ばれないようにするため）。
- **消す相手を確定できないときは、`DANGER_OK=1` でも止まる**（何も消さない）:
  - プロジェクト名を変える指定がある: 環境変数 `COMPOSE_PROJECT_NAME`／直下 `.env` の `COMPOSE_PROJECT_NAME`・`COMPOSE_FILE`（`export`・空白・`:` 区切りを含む）／compose ファイル（`compose.yaml`・`docker-compose.yml`・override 等の 8 種）の最上位 `name:`／既定名が空になるフォルダ名。→ 指定を外し、コミットして push してから再実行する（未 push だと撤去前チェック（2）で止まる）。指定していた名前のプロジェクトのデータは `wt-remove.sh` では消えずに残るので、下の「取り残しの発見と削除」で片付ける（この場合は「止まったときの片付け」の手順 4 は使えない。指定が残っている限り何度実行しても止まる）。
  - コンテナの作業フォルダのラベル（`com.docker.compose.project.working_dir`）が撤去対象と違う（同じ名前の別のプロジェクト・親フォルダの compose で起動したもの）。
  - 既定名が別のワークツリーと同じ（親の違う同名の入れ子・primary と同じフォルダ名など）でデータがある。ワークツリーは同じ名前で作らない。同じ PC の別のクローンに同じ名前のワークツリーがある場合は、コンテナが残っていれば作業フォルダのラベルで止まるが、volume だけが残っている場合は区別できない（別のクローンで同じ名前を使わない）。
- docker が使えない（コマンドが無い・デーモン停止）ときは判定できないので止まる。docker を起動して再実行するか、データを消さずに撤去してよければ `KEEP_DATA=1` を付けて再実行する（`down -v` は実行せず、データは残るので、docker が使えるときに下の「取り残し」の手順で片付ける）。`KEEP_DATA=1` は docker が使えないときだけ効き、データがあると判定できた場合は止まる。
- **ブランチは消さない**。完了メッセージに残ったブランチ名が出るので、不要なら `git branch -d <ブランチ>` で消す。

**止まったときの片付け（持ち主を確かめてから手で行う）**: コンテナの作業フォルダが撤去対象と違う・同じ名前の別のワークツリーがある、で止まった場合（データが本当に撤去対象のものでも、Windows 側から起動して作業フォルダが `C:\…` の表記になっている場合などに起きる）:

```bash
# 1. 持ち主を確かめる（コンテナごとの作業フォルダ・名前）
docker ps -a --filter label=com.docker.compose.project=<名前> --format '{{.Names}} {{.Label "com.docker.compose.project.working_dir"}}'
# 2. 撤去対象のデータだと確認できたら、必要ならバックアップ（wt-remove.sh の停止メッセージに出る 3 手順）
# 3. 承認を得て、primary から手で消す（-p で相手を固定）
DANGER_OK=1 docker compose -p <名前> down -v
# 4. データが無くなったので、wt-remove.sh を再実行する（今度は「データ無し」で撤去まで進む）
bash scripts/claude/wt-remove.sh <ワークツリーのパス>
```

- 持ち主が別のワークツリー・別のクローンなら、手順 3 は行わない（そのワークツリーの持ち主が片付ける）。
- **手順 1 の出力が空（コンテナが無く volume だけが残っている）なら、持ち主を確定できない**。volume には作業フォルダの記録が無いので、空の出力を「他に持ち主はいない」と読まない。同じ名前の別のワークツリー・別のクローンが無いことを人が確かめられない限り、手順 3 は行わない（`docker volume inspect <volume 名>` の作成日時が、撤去対象のワークツリーを使っていた時期と合うかも手がかりになる）。
- 手順 2 のバックアップの 3 手順は、`wt-remove.sh` がどの理由で止まった場合も停止メッセージに表示する。

**取り残しの発見と削除**:

```bash
docker compose ls -a                 # Compose プロジェクトの一覧（名前＝ワークツリーのフォルダ名）
git worktree list                    # いまあるワークツリー
docker volume ls -f dangling=true    # どのコンテナにも使われていない volume（ラベルの無い匿名 volume を含む）
```

- `docker compose ls -a` にあって、対応するワークツリーが無いプロジェクトは取り残し。`docker compose -p <名前> down -v` で消す。**破壊的操作**（Postgres 開発データの削除）なので `docs/runbooks/danger-ops.md` に従い、承認を得てから `DANGER_OK=1 docker compose -p <名前> down -v` の形で実行する（ガードが `DANGER_OK=1` の無い形を止める）。`<名前>` は、上の「止まったときの片付け」の手順 1 で持ち主を確かめたものだけを指定する（確かめずに primary の `study-app-multitenant` などを指定すると、そのワークツリーのデータが消える）。dangling volume の削除（`docker volume rm`・`docker volume prune`）も同じ扱い。

---

## 5. Docker を使う場合のセットアップ

このプロジェクトの開発環境は **Docker Compose**。ホストでの `venv` / `pip install` / `npm install` は使わない（依存はイメージに焼き込み、`node_modules` は frontend コンテナの匿名ボリュームで管理される）。

```bash
# 対象のワークツリーで実行する（backend/.env・e2e/.env.e2e は .worktreeinclude で自動コピー済み）
bash scripts/claude/wt-ports.sh      # (1) 直下 .env にポートを割り当てる（Docker 起動前に 1 回・→ §6）
docker compose up -d                 # (2) 起動（正準手順・テスト実行方法は common-commands.md を参照）
```

- **⚠️ (B) `.env` 欠落は静かに壊れる**: `backend/.env` は `env_file` の `required: false` で参照されるため、無くても `docker compose up` は**失敗しない**。その代わり `SECRET_KEY` / `DB_PASSWORD` などが **insecure な既定値のまま静かに起動**する。→ `wt-ports.sh` は `backend/.env` が無ければ明示エラーで止める（primary に元ファイルが無く `.worktreeinclude` がコピーしなかった場合もここで気づく）。
- **(C) `COMPOSE_PROJECT_NAME` を global に export しない**: Compose のプロジェクト名は既定でディレクトリ名になり、ワークツリーごとにコンテナ・named volume（Postgres データ含む）が自動的に分離される。global に export すると全ワークツリーが同一プロジェクト名になり、この分離が壊れる。→ `wt-ports.sh` / `wt-remove.sh` は当該変数が設定されていれば警告し、`wt-remove.sh` は消す相手を確定できないとして `DANGER_OK=1` でも止まる（変数を外してから再実行する → §4）。
- **(D) 掃除**: ワークツリーごとに named volume が増える。Docker を使ったワークツリーは `wt-remove.sh` で撤去し、`down -v` → `git worktree remove` の順で volume を回収する（§4）。

---

## 6. 並行実行のポート分離（同時起動可能・I097）

ワークツリーごとにコンテナ・volume は `COMPOSE_PROJECT_NAME`（既定＝ディレクトリ名）で分離される。ホストの publish ポートは **環境変数でテンプレート化**されており（I097）、ワークツリーごとに直下 `.env` でオフセットすることで**同時に `docker compose up` してもポートが衝突しない**。

`docker-compose.yml` のホストポートは既定値付き環境変数で publish される（**変数未設定時は下表の既定値**＝後方互換）:

| サービス | 環境変数 | 既定ポート |
|---------|---------|-----------|
| db (Postgres) | `DB_PORT` | 5432 |
| redis | `REDIS_PORT` | 6379 |
| backend | `BACKEND_PORT` | 8000 |
| frontend | `FRONTEND_PORT` | 3000 |

（`nginx` の 80 / 443 は `profiles: production` 配下のため、既定の `docker compose up` では起動しない＝ポート変数化の対象外。）

**オフセット規約**: STEP=10。primary=offset 0（既定ポート）、追加ワークツリーは +10 ずつ（次=10, 次=20 ...）。`port = 既定 + offset`（例: offset=10 → db 5442 / redis 6389 / backend 8010 / frontend 3010）。base 間隔が広いためサービス間衝突は起きない。

**運用**: Docker を起動する前に、対象のワークツリーで `bash scripts/claude/wt-ports.sh [--port-offset N]` を 1 回実行する。
- `--port-offset` 未指定時は他のワークツリー（入れ子配置を含む `git worktree list` の全件）の `.env` を走査し、**空きオフセット（max+10）を自動割当**。
- `--port-offset N` で明示指定も可能。他のワークツリーとポートが衝突する場合は **fail**（`.env` を書かずに停止）。
- primary では実行しない（既定ポートで使うため拒否する）。既に割当済みなら何も変えない（2 回実行しても安全）。ポート以外の既存行は残して追記する。
- 生成される `.env` は gitignore 対象（`.env` / `*.env`）でワークツリーごとに非共有。`COMPOSE_PROJECT_NAME` は書かない。
- 実行し忘れて既定ポートのまま起動した場合は、primary のスタックとポートが衝突して `docker compose up` がエラーで止まる（静かには壊れない）。

```bash
# 例: 2 つのワークツリーを同時起動。それぞれのワークツリーのセッション（そのフォルダで起動した claude・ターミナル）で実行する
# （1 つのセッションから cd して別のワークツリーの .env を書くのは §9 の「他のワークツリーを直接編集しない」に反する）
bash scripts/claude/wt-ports.sh && docker compose up -d    # app-2 のセッションで → offset=10 → backend 8010 等
bash scripts/claude/wt-ports.sh && docker compose up -d    # app-3 のセッションで → offset=20 → backend 8020 等

# 割当ポートの確認（publish されるホストポートをレンダリングして確認）
docker compose config | grep -A1 published
```

---

## 7. 共有されるもの / されないもの

同一リポジトリを共有するため、**コミット済みの内容は全ワークツリーで共有**される。一方で gitignore 対象・コンテナ管理のものは共有されない。

**共有される（コミット済み / `.git`）**:
- `.git` 履歴・コミット済みファイル全般
- `CLAUDE.md`・`docs/runbooks`（この runbook 含む）
- `.claude/settings.json`（権限・フック設定）
- tracked な `frontend/.env.*`（`frontend/.env.development` / `frontend/.env.production`）
- **git stash のスタック**: 全ワークツリー・全セッションで 1 つ。素の `git stash` / `git stash pop` は使わない（別セッションの退避を取り出す恐れがある）。退避は一時的な WIP コミットを優先する。どうしても使う場合は `git stash push -u -m "<固有のタグ>"` → `git stash list --format='%H %gs'` で自分の SHA を控える → `git stash apply <sha>`（pop しない）→ 最後にタグで `stash@{n}` を探し直して drop する。
- **git config**（リポジトリ単位の設定・`core.hooksPath` などの git hooks を含む）: 1 つのワークツリーで変えると全ワークツリーに効く。

**共有されない（手当てが要る）**:
- backend `.env`・`e2e/.env.e2e`（gitignore。`.worktreeinclude` で作成時に自動コピー → §2）
- 直下 `.env`（ポート割当。ワークツリーごとに `wt-ports.sh` で作る → §6）
- 未コミット / untracked のファイル（他ワークツリーからは見えない → §8）

**コンテナ管理（ホストでは共有されないが手当ても不要）**:
- 依存パッケージ（イメージに焼き込み）
- `node_modules`（frontend コンテナの匿名ボリューム `/app/node_modules`）
- dev DB のデータ: **Postgres コンテナ + named volume**。`COMPOSE_PROJECT_NAME`（既定 = ディレクトリ名）ごとに自動分離される。`db.sqlite3`（gitignore）は起動中の dev DB ではない。

**入れ子配置の検索の注意**: primary の中の `.claude/worktrees/` には別のワークツリー（ファイル一式）がある。`grep -r`・`find` など gitignore を見ないコマンドで primary を検索すると、入れ子ワークツリーの中身が混ざる。`git grep`・Claude の Grep/Glob ツールは `.gitignore` に従うため混ざらない。

**WSL 表示確認**: WSL 環境では、Windows 側エクスプローラや Cursor のパス表示が `/mnt/c/...` と `\\wsl$\...` で食い違うことがある。開いているフォルダのパスが目的のワークツリーと一致しているか確認する。

---

## 8. 採番の一貫性（採番権威の単一化・I098）

- `/issue-bootstrap` 直後のイシューファイルは **untracked（未コミット）** で、それを作ったワークツリーからしか見えない。かつては別ワークツリーで起票すると互いの untracked が不可視で**採番が食い違う**恐れがあった（primary で採番する人手規律に依存）。
- **ルール（機械化）**: 採番は必ず `scripts/claude/next-issue-num.sh` 経由で行う。本スクリプトは `git worktree list` で**全ワークツリーの `docs/issues`（untracked 含む・入れ子配置も含む）**＋`git log --all`（削除済み含む）を横断集計し `max(...)+1` を返すため、**どのワークツリーから実行しても同一の大域一意番号**が得られる（採番権威が単一化）。primary 固定・起票後の事前取り込みといった人手規律は不要。
  - 読み取りのみ（find / git log）で他ワークツリーを参照するため、I095 の横断ガード（書込のみブロック・読み取りは許可）に抵触しない。
  - CWD 非依存（git 履歴 pathspec を `:/docs/issues` に固定）。アンカー正規表現 `/I?\K\d+(?=\.md$)` で `I###.md`/`###.md` のみを対象にし、`draft-I200.md` 等の decoy を誤カウントしない（I094）。
- **スコープ外（既知の残存）**: 2 ワークツリーがほぼ同時に採番する競合（TOCTOU）、および**既存の**二重採番（過去に別々採番された同番号・同一番号の open/closed 共存）の検出/修復は本スクリプトの対象外（単一逐次オペレータ前提）。将来の二重採番の防止のみを保証する。

---

## 9. セッション間の引き継ぎ原則（自己完結）

- **口頭メモ（チャット上のメモ）での引き継ぎは禁止**。メモ漏れで受け手セッションがぶれ、記録が `docs/` に残らず憲法5「記録が残る形」に反する。
- 引き継ぎは**イシュー / 計画 / レビューのファイルに自己完結で記述**する。**文脈ゼロの新規セッションが、そのファイルだけを読んで同じ結論に到達し作業を続行できる状態**を必須とする。
- ワークツリーをまたぐ依頼も同様。現セッションから他のワークツリーを直接編集せず、引き継ぎはファイル経由で行う。
- **技術強制済み（I095）**: この「他のワークツリーを直接編集しない」ルールは、PreToolUse フック（`scripts/claude/hooks/pretooluse_guard.py`）で技術強制されている。別ワークツリーのルート配下への **Edit/Write/MultiEdit/NotebookEdit・Bash 書込（`>`/`>>`/`>|`・`tee`・`cp`/`mv` の宛先・`sed -i`）を `exit 2` でブロック**する（`.claude/settings.json` は commit 共有のため全ワークツリーに自動適用）。**読み取りは許可**（参照・調査は可）。判定は `git worktree list` のルートとの realpath 境界一致で行い、**入れ子では、パスを含む最も内側のワークツリーを所有者として判定**する（I179。入れ子ワークツリーは自分のファイルに書け、親→入れ子・入れ子→親・兄弟間はブロック）。**fail-safe**（ワークツリー境界を確定できない場合＝git 失敗時はブロック）・**エスケープ無し**（`DANGER_OK=1` でも解除されない）。未カバー経路（変数展開越しの `cd`・`eval`/変数展開越しの宛先）は検査できないという限界を stderr に明示する。
- **削除・破棄も技術強制（I179）**: 公式配置では別のワークツリーが primary の中（`.claude/worktrees/`）にあるため、相対パスや primary 全体への操作で他のワークツリーの未コミット作業を消せる。ガードは次を `exit 2` でブロックする（書込と同じく `DANGER_OK=1` でも解除しない）。
  - 別ワークツリーのパスへの `rm`（オプションの形を問わない）・`mv` の移動元・`find … -delete`／`-exec rm`。中に別のワークツリーを含むフォルダの削除（例: primary で `rm -r .claude`）も止める。
  - 別ワークツリーを対象にした git の読み取り以外の操作（`git -C <別ワークツリー>`・`--work-tree`・`--git-dir`・`cd <別ワークツリー>` の後の `reset`・`checkout`・`restore`・`clean`・`stash` 等）。`status`・`log`・`diff`・`show` などの読み取りは通す。
  - 中に別のワークツリーがある場所での `git clean -ff`（`f` を 2 つ重ねると git は中の別リポジトリまで消す。`-f` 1 つなら git が入れ子を飛ばすので通す）。
  - `git worktree remove`（`--force` の有無を問わない）。中の入れ子は gitignore 済みで git の未コミット検査に出ないため、`--force` なしでも入れ子の作業ごと消える。撤去は `bash scripts/claude/wt-remove.sh <パス>` を使う（中に入れ子があると止まる）。
  - 書込・削除の対象は相対パスも判定する。**作業フォルダはコマンドの順番どおりには追わない**。セッションの作業フォルダと、コマンドの中に出てくるすべての移動先（`cd`・`pushd` の引数、`env -C`・`--chdir`・`sudo -D` の値、`GIT_WORK_TREE=`・`GIT_DIR=`、`git -C`・`--work-tree`）を「基準の候補」とし、相対パスはすべての候補を基準に判定して、どれか 1 つでも別ワークツリーに当たれば止める（括弧・パイプ・`&`・`cd -` の意味を再現しない＝再現漏れの抜け道を作らない。I179 敵対的レビュー第 6〜8 周）。前置きのコマンド（`command`・`time`・`sudo`・`env`・`timeout`・`exec`・`nice` 等）の後ろは、後ろに現れる既知のコマンド名（`rm`・`git` 等）の位置をすべて候補にして読む。`mv` は位置に関係なくすべての引数を移動元として見る。`sed -i` はスクリプトとファイルを区別せず、すべての引数をパスとして見る。`/mnt/<ドライブ>/` 配下は大文字小文字の違いを同じパスとみなす。
  - **このため次の書き方は止まる**（`DANGER_OK=1` でも解除しない。コマンドを分ければ通る）: 1 つのコマンドの中で別ワークツリーへ移動したうえで、自分のワークツリーの相対パスを消す・書く・git を変更する形（例: `(cd .claude/worktrees/x && git status) ; git commit …`）。primary（中に入れ子がある場所）で、スクリプトに展開文字（`{`・`*`・`?`・`[`）を含む `sed -i`（例: `sed -i '2{s/a/b/}' f`。スクリプトをファイルに書いて `-f` で渡す・サブフォルダで実行する）。
  - **展開を含むパス（`*`・`?`・`[`・`{`）は粗く判定する**。パターンの意味（`[^…]`・文字クラス・中かっこ・`dotglob` 等のシェル設定）は解釈せず、最初の展開文字より手前の固定部分のフォルダを基準にする。中身も消す操作（`rm -r`・`mv`・`find -delete`）は、そのフォルダの中に別のワークツリーがあれば止める。中身を消さない操作（`rm` の非再帰・書込）は、パターンの段数より浅い位置に別のワークツリーがあるときだけ止める（primary で `rm *.log` は通る）。`~+`・`~-` は今のフォルダ・直前のフォルダとして判定する。
  - **このため primary の直下で展開を含む再帰削除・移動（`rm -r tmp_*`・`mv *.md docs/`・`rm -r .[^.]*`）は止まる**（`DANGER_OK=1` でも解除しない。bash の展開規則を再現すると再現漏れが抜け道になるため、粗い判定を選んでいる＝I179 敵対的レビュー第 5〜6 周）。回避: サブフォルダに移ってから実行する（`cd docs && mv *.md …`）・名前を並べて書く・`find` は開始パスを絞る（`find backend …`）。
- **止められないもの（既知の限界）**: 変数・コマンド置換を含むパス（`rm -r "$X"`）・`eval`／`sh -c` の中身・`xargs` 経由・rm/find/mv/git 以外の消し方（`rsync --delete`・`truncate`・`unlink`・`busybox rm` 等）・スクリプトの中のコマンド（ガードは Claude が実行するコマンドの文字列だけを見る）・公式の自動片付け（§2 の注意）。ヒアドキュメントの本文やクォートをまたぐ改行の後ろの行も 1 つのコマンドとして読むため、本文に別ワークツリーのパスを含む削除や `cd` の行があると誤って止まる場合がある（`DANGER_OK=1` では解けないので、本文をファイルに書いてから使う・パスの書き方を変える）。
- **既知の限界（入れ子）**: 「どれが現ワークツリーか」はフックを実行したときの作業フォルダ（`git rev-parse --show-toplevel`）で決まる。入れ子ワークツリーは primary のフォルダの中にあるため、primary のセッションで `cd .claude/worktrees/<name>` すると作業フォルダがそのまま残り、それ以降はそのセッションが入れ子のワークツリーとして扱われる（入れ子への書込が通る）。primary のセッションから入れ子へ `cd` しない。入れ子で作業するときは、そのワークツリーのセッションを使う（§2「セッションを開く」）。サブエージェントのフックは primary の設定で動くため、作業フォルダ以外（`CLAUDE_PROJECT_DIR` 等）で判定すると、サブエージェントが自分の入れ子に書けなくなる。このため作業フォルダでの判定を維持している。

---

## 10. 現在の構成の確認とトラック⇔ラベル対応

現在のワークツリーは `git worktree list` で確認する（手書きの一覧は古くなるため置かない）。

| トラック | 対応 GitHub ラベル | 対象 |
|---------|-------------------|------|
| ハーネス改善 | `track:harness` | `docs/runbooks/`・`scripts/claude/`・`.claude/`（skills/hooks/settings）・レビュー/ゲート/テンプレートの仕組み |
| アプリ開発 | `track:app` | `backend/`・`frontend/`・`e2e/` 等のアプリ機能・アプリのテスト |

ワークツリーはトラックに固定しない。どのワークツリーでどのトラックのイシューを扱ってもよい（同時に扱うのは 1 ワークツリー 1 イシュー）。

---

## 11. 旧方式からの移行

- **既存の `wt-harness`（`/mnt/c/app/wt-harness`・I179 より前の自作スクリプト方式で primary の外に作ったワークツリー）**: そこで進めているイシュー（I178・I179）が完了・クローズした後に、次の順で移す。
  1. `wt-harness` にしか無い未コミットのファイルを primary へ移す。`/issue-bootstrap` のイシューファイル（`docs/issues/open/I###.md`）とイシューレビュー（`docs/reviews/I###_issue_review_*.md`）は、運用上わざと未コミットにしているので、捨てると起票済みイシューの本文と採番の根拠が消える。**primary のセッションで**、`git -C /mnt/c/app/wt-harness status --porcelain --untracked-files=all` に出る `??` のファイル（`--untracked-files=all` でフォルダではなくファイル単位に出す）のうち primary に無いものを `cp /mnt/c/app/wt-harness/<パス> <パス>` で primary にコピーする（コピー元の読み取りはガードに抵触しない。`wt-harness` のセッションから primary へ書き込むのはガードで止まる）。コピー後、両方の中身が `cmp` で一致することを確かめる。**primary にも同じパスのファイルがあるもの**は、コピーせずに `cmp` で中身を比べる。違っていれば（以前に primary へ写した後、`wt-harness` 側で追記した等）どちらが新しいかを確かめ、`wt-harness` 側が新しければ primary のセッションで差分を反映してから手順 3 に進む（手順 3 で `wt-harness` 側を削除するため、確かめずに進めると新しい版が消える）。
     - **コピーしないもの**: 同じ番号が既にクローズ済み（develop に `docs/issues/closed/I###.md` がある。`git ls-tree -r --name-only origin/develop docs/issues/closed/` で確認）のイシューファイルは古い版なのでコピーしない（open と closed が内容違いで並ぶのを防ぐ）。
     - gitignore 済みのファイルは `??` に出ないが、撤去で黙って消える。`git -C /mnt/c/app/wt-harness status --porcelain --ignored` の `!!` のうち、`.claude/settings.local.json`（個人の権限設定）など残したいものは、primary の同名ファイルと見比べて必要な行を primary 側へ手で反映する（上書きしない）。
  2. `wt-harness` の中に入れ子（サブエージェントが作った `.claude/worktrees/agent-*` など）が残っていれば、先に撤去する（§4。未 push の入れ子の扱いも §4）。
  3. primary から `bash scripts/claude/wt-remove.sh /mnt/c/app/wt-harness` で撤去する（Docker のデータが無ければ許可は不要）。`wt-harness` に残っている untracked のファイル（手順 1 でコピーしたもの・「コピーしないもの」としたクローズ済みイシューの古い版の両方）は、未コミット変更として撤去を止める。primary へのコピーを確かめたうえで、**`wt-harness` のセッションで**それらをすべて削除してから実行する。
  4. 必要なら primary で `claude --worktree harness-<連番>` で作り直す（§2 の「作る前の確認」を先に行う）。
- **primary は移行しない**（そのまま作成元として使う）。
