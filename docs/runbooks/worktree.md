# worktree ベースの並行作業運用

複数の作業（例: 「ハーネス改善」と「アプリ開発」、または同じトラックの別イシュー）を、**作業ツリーの分離 + セッションの分離 + ファイルベースの引き継ぎ**で無損失に並行させるための手順。単一作業ツリーでブランチを切り替える方式は、片方の未コミット変更がもう片方を妨げ、1 セッションで複数の作業を扱うとコンテキストが混在する。git worktree で作業場所ごとに独立したディレクトリを持つことでこれを解消する。

- **トラック** = 作業の束（GitHub ラベルで区別）。**ワークツリー** = 作業場所。1 トラックに複数のワークツリーを持ってよい。
- 作成・設定ファイルのコピー・変更が無いときの片付けは **Claude Code の公式機能**（`claude --worktree`・`.worktreeinclude`・自動片付け）に任せる。自作スクリプトは公式に無い部分（ポート割当・Docker データの後始末・横断書込ガード）だけを受け持つ。
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

**作る前の確認（primary で行う。一度合わせれば以後は確認だけ）**:

```bash
cd <primary>
# 基点の確認: refs/remotes/origin/develop と出ること
git symbolic-ref refs/remotes/origin/HEAD
#    別のもの（refs/remotes/origin/main など。clone した時点の既定のまま残っている）が出る、または
#    「fatal: ref refs/remotes/origin/HEAD is not a symbolic ref」で失敗する（未設定）なら、リモートの今の既定ブランチに合わせる
git remote set-head origin --auto
#    （refs/remotes/origin/HEAD は全ワークツリー共有の参照。合わせ直しても origin/HEAD を使う手順・スクリプトは無い）
```

```bash
# 作成: 必ず primary checkout で実行する（例: ハーネス改善の 2 つ目 → harness-2）
claude --worktree <track>-<連番>
```

- **必ず primary で作る**: `claude --worktree` は実行したフォルダの中（`.claude/worktrees/`）に作る。primary 以外で実行すると、そのワークツリーの中に入れ子が作られる（外側を撤去するときは `wt-remove.sh` が入れ子を検出して止める → §4）。primary は撤去しないので、ここを作成元に固定する。
- **基点**: 公式の既定（`worktree.baseRef` の `"fresh"`）は `origin/<既定ブランチ>` から作る。既定ブランチは**手元の `refs/remotes/origin/HEAD`** で決まる。これが `origin/main`（初期コミットのみで中身が無い）を指していると、CLAUDE.md・`.claude/settings.json`（ガード）・スキルが何も無い空のワークツリーができるので、上の確認で必ず `origin/develop` に合わせておく。
- **primary のブランチ**: `.worktreeinclude`・`.gitignore`・ガード（サブエージェントのフックは primary の `pretooluse_guard.py` が動く）・許可の判定の一部は、primary が今チェックアウトしているブランチの内容で決まる。primary は develop に置いておく（I200・I219: develop にいて追跡済みファイルがきれいなら、セッションの開始時に裏で自動で `origin/develop` へ早送りされる〔§9 の例外〕。結果は次の開始時の文脈の「primary: 前回 …」の行に出る。その行が「そろえません」「そろえられませんでした」なら、その行の手順で手でそろえる）。
- **初期ブランチ**: `worktree-<name>` で作られる。`/plan-issue` で feature ブランチを作った後、不要なら `git branch -d worktree-<name>` で消してよい。
- **設定ファイル**: gitignore 済みの `backend/.env`・`e2e/.env.e2e` は、リポジトリ直下の `.worktreeinclude` に従って公式機能が自動でコピーする（`--worktree`・サブエージェントの `isolation: worktree`・`EnterWorktree` のどれでも同じ）。**primary に `backend/.env` が無いとコピーされない**（黙って飛ばされる）。Docker を使う前に `wt-ports.sh` がこれを検査して止める（§5）。
- **初めて使うフォルダ**: `claude --worktree` は、そのフォルダを Claude Code が信頼済みでないと「Workspace trust not yet accepted」で失敗する。新しく clone した primary などでは、先に `claude` を一度起動して信頼の確認を承認し、終了してから実行する（`claude -p` は信頼の確認を飛ばす）。
- **終了時の確認**: 変更もコミットも無いワークツリーは、終了のときに自動で消える。名前を付けたセッション・未コミットの変更や自分のブランチのコミットがあるワークツリーでは「Exiting worktree session」の確認が出る。続けて使うワークツリーは「**Keep worktree**」を選ぶ（「Remove worktree」は変更とコミットごと消す）。`/plan-issue` の後は feature ブランチにコミットがあるので、確認が出る。
- **ロック**: `claude --worktree` はセッションの間、ワークツリーを `claude session <name> (pid N ...)` という理由でロックする（`git worktree list` に `locked` と出る）。終了したプロセスのロックは、後のセッションの掃除が自動で外す。待てないときやロックが残ったときは、§4 の `wt-remove.sh` で撤去する（素の `git worktree remove` はロックされたワークツリーを消せない）。
- ロックの判定は pid で行うため、同じ環境（同じ WSL ディストリ）で動く Claude のロックだけを正しく判定できる。Windows 側など別の環境で動く Claude からワークツリーを使っている場合、その pid はこの環境に見えないので「終了済み」と判定される。その場合は `wt-remove.sh` を使う前に、そのセッションを終了しておく。
- サブエージェントに `isolation: worktree` で作業させる場合も同じ仕組み（作成・コピー・自動片付け）が使われる。サブエージェントは、呼び出したセッションのワークツリーの中にさらに入れ子を作る。動いている間はロックされ、終われば外れる。変更があった入れ子は自動では片付かずに残る。
- **自動片付けと入れ子の注意**: 公式機能の「変更が無い」の判定は、そのワークツリー自身の `git status` で行う。中の入れ子（`.claude/worktrees/` は gitignore 済み）の変更は見えないため、外側のワークツリーに変更が無く、中のサブエージェントの入れ子にだけ未コミットの変更があると、外側が「変更なし」として片付けられ、入れ子ごと消える恐れがある（ガードでは止められない）。サブエージェントに `isolation: worktree` で作業させたワークツリーは、終了時の確認で「残す」を選び、中の入れ子を確かめて（`git worktree list`）から §4 の `wt-remove.sh` で撤去する（`wt-remove.sh` は中に入れ子があると止まる）。

**セッションを開く**: 各ワークツリーでは別々に `claude` を起動する（`claude --worktree` で作った直後のセッションはそのまま使える。再開するときは、そのワークツリーのフォルダで `claude` を起動する）。IDE（VS Code・Cursor など）を使うときは、ワークツリーごとに新しいウィンドウで開く（例: `code -n <パス>`。`-n` = 新しいウィンドウ）。既に開いているフォルダを開き直しても新しいウィンドウにはならない。入れ子ワークツリーは primary のフォルダの中にあるので、primary のウィンドウからではなく、別のウィンドウで入れ子のフォルダ自体を開く。

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

- コピーは作ったワークツリーのセッションで行う。primary のセッションから入れ子へ書き込む形（`cp backend/.env .claude/worktrees/<name>/…`）はしない（§9。絶対パスで書いた場合はガードが止める）。

---

## 3. 次のイシューへ移る（同じワークツリーで続ける）

1 つのワークツリーで、複数のイシューを順番に扱ってよい。

1. いまのイシューの未コミット変更を片付ける（コミットする。不要なら捨てる。push は `docs/runbooks/workflow.md`「GitHub への書き込みの時点」の時点だけ）。今までのイシュー（I426 以下）のイシューファイル（untracked）は残してよい。新しいイシュー（I427 以上・I221）は GitHub にだけあり、手元に持ち越すものは無い。
2. `/plan-issue I<番号>` を実行する。`origin/develop` から直接 feature ブランチを作るため、develop をチェックアウトしない（別のワークツリーが develop を使っていても失敗しない）。未コミットのイシューファイルはそのまま新ブランチへ持ち越される。新しいイシューは、`/plan-issue` が GitHub の本文の写しを作ってコミットするので、どのワークツリーからでも始められる。

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

- 撤去対象は `git worktree list` に登録されたワークツリーのパスで指定する（登録外のフォルダは扱わない）。`--force` は使わない。
- 止まる理由（何も消さずに止まる。止まったときはスクリプトの出力の手順に従う）:
  - 未コミット変更・未 push コミットがある
  - primary か撤去対象の内側から実行した
  - 中に別のワークツリー（入れ子）がある（gitignore 済みなので入れ子の作業ごと消える。中のものを先に `wt-remove.sh` で撤去する）
  - 使用中のセッションのロック・Claude 以外の理由のロックがある（終了済みのロックは外して進む。Claude 以外のロックは、使っている人に確認してから `git worktree unlock <パス>`）
  - 消す相手（Compose のプロジェクト）を確定できない（`COMPOSE_PROJECT_NAME` などの指定・作業フォルダのラベルの違い・同じ名前の別のワークツリー。`DANGER_OK=1` でも止まる）
  - docker が使えない（データを消さずに撤去してよければ `KEEP_DATA=1`）
- **登録の無い `.git`** が中にあって止まった場合（登録が消えた入れ子・入れ子に置いた clone）は、`wt-remove.sh` にその内側を渡せない。**外側のワークツリーのセッションで**、まず `git worktree repair <内側のパス>` で登録の復旧を試す（復旧できれば `wt-remove.sh` で撤去できる）。復旧できなければファイルの更新日時（`ls -lt`）で最近の作業が無いかを確かめ、残したいものは外側の外へコピーしてから `rm -r .claude/worktrees/<内側>` で消す（確かめられないまま消さない・primary のセッションからは消さない＝§9）。
- データの判定と削除: Compose の既定のプロジェクト名（フォルダ名から作る）のラベルで調べ、`down -v` は必ず `docker compose -p <既定名> down -v` で消す相手を固定して実行する（別のプロジェクトを消さないため）。
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
docker compose up -d --build --renew-anon-volumes   # (2) 起動（正準手順。作り直しの理由は common-commands.md「開発環境起動」、テストの流し方は同「テスト実行」）
```

- **⚠️ (B) `.env` 欠落は静かに壊れる**: `backend/.env` は `env_file` の `required: false` で参照されるため、無くても `docker compose up` は**失敗しない**。その代わり `SECRET_KEY` / `DB_PASSWORD` などが **insecure な既定値のまま静かに起動**する。→ `wt-ports.sh` は `backend/.env` が無ければ明示エラーで止める（primary に元ファイルが無く `.worktreeinclude` がコピーしなかった場合もここで気づく）。
- **(C) `COMPOSE_PROJECT_NAME` を global に export しない**: Compose のプロジェクト名は既定でディレクトリ名になり、ワークツリーごとにコンテナ・named volume（Postgres データ含む）が自動的に分離される。global に export すると全ワークツリーが同一プロジェクト名になり、この分離が壊れる。→ `wt-ports.sh` / `wt-remove.sh` は当該変数が設定されていれば警告し、`wt-remove.sh` は消す相手を確定できないとして `DANGER_OK=1` でも止まる（変数を外してから再実行する → §4）。
- **(D) 掃除**: Docker を使ったワークツリーは `wt-remove.sh` で撤去する（volume も回収する → §4）。

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
# 例: 同時に起動するワークツリーごとに、そのワークツリーのセッション（そのフォルダで起動した claude・ターミナル）で実行する
# （1 つのセッションから cd して別のワークツリーの .env を書くのは §9 の「他のワークツリーを直接編集しない」に反する）
# （2 つのコマンドはつながずに 1 つずつ流す。つなぐとサンドボックスの外に出ない・docs/runbooks/danger-ops.md「外に出すコマンドの書き方」）
bash scripts/claude/wt-ports.sh                               # 1 つ目の追加ワークツリー → offset=10 → backend 8010 等（2 つ目は 20）
docker compose up -d --build --renew-anon-volumes

# 割当ポートの確認（起動後）
docker compose port backend 8000
```

---

## 7. 共有されるもの / されないもの

同一リポジトリを共有するため、**コミット済みの内容は全ワークツリーで共有**される。一方で gitignore 対象・コンテナ管理のものは共有されない。

**ワークツリー間の反映のタイミング**: 「共有される」のはコミットの履歴であって、作業中のファイルではない。各ワークツリーのファイル（スキル・手順書・`.claude/settings.json` を含む）は、そのワークツリーが今チェックアウトしているブランチの内容で動く。
- 別のワークツリーで直したスキル・手順書は、PR で develop にマージされ、さらに自分のワークツリーがそれを取り込むまで反映されない（どこかで直せば即全体に効く、ではない）。新しいイシューは `/plan-issue` が最新の `origin/develop` からブランチを作るので自然に入る。
- 作業途中のワークツリーに取り込むときは、そのワークツリーのセッションで `git fetch origin` → `git merge origin/develop` を行う（未コミットの変更は先にコミットしておく）。
- 例外（ブランチによらない）: `~/.claude` の個人設定・メモリ、git config、git stash は 1 つで全ワークツリーに即効く（下の「共有される」）。ワークツリーのセッションで承認画面の「今後は聞かない」を選ぶと、その許可は primary の `.claude/settings.local.json` に入り、全ワークツリーに効く（公式の仕様）。サブエージェントのフック（ガード）と `.worktreeinclude` は、作業しているワークツリーではなく primary が今チェックアウトしているブランチの内容で決まる（§2「primary のブランチ」）。

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
- 未コミット / untracked のファイル（他ワークツリーからは見えない。今までのイシューのファイルの扱いは docs/runbooks/issue-flow.md「イシューの番号と置き場所（I221）」）

**コンテナ管理（ホストでは共有されないが手当ても不要）**:
- 依存パッケージ（イメージに焼き込み）
- `node_modules`（frontend コンテナの匿名ボリューム `/app/node_modules`）
- dev DB のデータ: **Postgres コンテナ + named volume**。`COMPOSE_PROJECT_NAME`（既定 = ディレクトリ名）ごとに自動分離される。`db.sqlite3`（gitignore）は起動中の dev DB ではない。

**入れ子配置の検索の注意**: primary の中の `.claude/worktrees/` には別のワークツリー（ファイル一式）がある。`grep -r`・`find` など gitignore を見ないコマンドで primary を検索すると、入れ子ワークツリーの中身が混ざる。`git grep`・Claude の Grep/Glob ツールは `.gitignore` に従うため混ざらない。

**WSL 表示確認**: WSL 環境では、Windows 側のエクスプローラーや IDE のパス表示が `/mnt/c/...` と `\\wsl$\...` で食い違うことがある。開いているフォルダのパスが目的のワークツリーと一致しているか確認する。

---

## 8. イシューの番号（I221）

正は docs/runbooks/issue-flow.md「イシューの番号と置き場所（I221）」（番号は GitHub が振るのでワークツリー間でぶつからない・今までのイシューは起票したワークツリーで扱う）。

---

## 9. セッション間の引き継ぎ原則（自己完結）

- **口頭メモ（チャット上のメモ）での引き継ぎは禁止**。メモ漏れで受け手セッションがぶれ、記録が `docs/` に残らず CLAUDE.md 絶対ルール 5「記録が残る形」に反する。
- 引き継ぎは**イシュー / 計画 / レビューのファイルに自己完結で記述**する。**文脈ゼロの新規セッションが、そのファイルだけを読んで同じ結論に到達し作業を続行できる状態**を必須とする。
- ワークツリーをまたぐ依頼も同様。現セッションから他のワークツリーを直接編集せず、引き継ぎはファイル経由で行う。読み取り（参照・調査）はしてよい。
- **例外: primary の早送り（I200・I219）**: 開始時のフック（`scripts/claude/hooks/sessionstart_context.py` の `--sync-primary`）が、どのワークツリーのセッションでも裏で primary を `origin/develop` へ早送りする（許可の判定の一部は primary の `.claude/settings.json` で行われるため）。動くのは primary が develop にいて追跡済みファイルがきれいで早送りで済むときだけで、何も消さない。結果は次の開始時の文脈の「primary: 前回（日時）: …」の 1 行に出る（合わないときはその行に理由と手で行うコマンドが出る）。
- **技術強制**: 公式のワークツリーの分離は、ワークツリーのセッションから primary（main checkout）への Edit と git の向け直しを止める。primary から入れ子・兄弟の間は、Bash の書き込みをサンドボックス、Edit 系の書き込みを見張りが止める（仕組みの正は `docs/runbooks/danger-ops.md`「サンドボックス（第 1 層・I430）」「見張り（pretooluse_guard.py）の扱い（I174）」1.）。外に出したコマンド（`docker`・`gh`・`git`・スクリプトの起動役 `python3 .claude/hooks/unreviewed.py run`）の中の書き込みは止めない
- **削除・破棄は文字列の判定では止めない**（I179 で、コマンドの文字列から読み取る方式は抜け道と止めすぎが出続けた）。ローカルが壊れても GitHub から復旧できる（例外は `docs/runbooks/danger-ops.md`「GitHub から復旧できる範囲」）ので、次を守る:
  - **こまめに commit する**（push は `docs/runbooks/workflow.md`「GitHub への書き込みの時点」の時点だけ）
  - **別のワークツリーの中身を消さない**: primary のセッションで `.claude/worktrees/` 配下を `rm`・`mv`・`git -C <入れ子> reset/checkout/clean/stash` しない。撤去は `bash scripts/claude/wt-remove.sh <パス>`（`git worktree remove` は使わない）
  - `git clean -f`・`rm -r`・`git reset --hard` などは、見張りが危険操作として場所によらず止める（`docs/runbooks/danger-ops.md`）
- **既知の限界（入れ子）**: 「どれが現ワークツリーか」はフックを実行したときの作業フォルダ（`git rev-parse --show-toplevel`）で決まる。入れ子ワークツリーは primary のフォルダの中にあるため、primary のセッションで `cd .claude/worktrees/<name>` すると作業フォルダがそのまま残り、それ以降はそのセッションが入れ子のワークツリーとして扱われる（入れ子への書込が通る）。primary のセッションから入れ子へ `cd` しない。入れ子で作業するときは、そのワークツリーのセッションを使う（§2「セッションを開く」）。サブエージェントのフックは primary の設定で動くため、作業フォルダ以外（`CLAUDE_PROJECT_DIR` 等）で判定すると、サブエージェントが自分の入れ子に書けなくなる。このため作業フォルダでの判定を維持している。

---

## 10. 現在の構成の確認とトラック⇔ラベル対応

現在のワークツリーは `git worktree list` で確認する（手書きの一覧は古くなるため置かない）。

トラックは GitHub のラベル `track:harness`（ハーネス改善）／`track:app`（アプリ開発）で区別する（付け方の決まりは docs/runbooks/issue-flow.md「起票」）。ワークツリーはトラックに固定しない。どのワークツリーでどのトラックのイシューを扱ってもよい（同時に扱うのは 1 ワークツリー 1 イシュー）。

---

## 11. 勉強用のワークツリー（I586）

開発とは別に、本物の利用者としてアプリで勉強するためのワークツリー（`study`）。勉強の記録を長く残すため、開発の作業には使わない。

- **作り方**: primary で `claude --worktree study`（§2）→ そのワークツリーで `wt-ports.sh`・起動（§5）→ ユーザーが画面（`http://localhost:<FRONTEND_PORT>/register`）で会員登録する（本人ひとりの組織ができ、本人がその管理者になる）
- **使い方の決まり**:
  - このワークツリーでほかのイシューの作業をしない（ブランチの切り替え・作業中のマイグレーション・E2E で DB が変わる）。`seed_e2e --flush` など DB を消す操作をしない
  - 起動のたびに確かめ用のデータ（`verify_i487`）が作り直されるが、本人の利用者・組織には触れない（`frontend-verify.md` §11）
  - アプリの更新は、PR がマージされた後に `git fetch origin` → `git switch --detach origin/develop` → 起動し直す（develop は primary が使っているので切り替えられない）
  - 控えは `bash scripts/claude/db-backup.sh`（勉強の記録を消す前・アプリを更新する前に取る）
- **Claude が本人の利用者で画面を操作するとき**: ユーザーがこのワークツリーの `e2e/.env.e2e` に `STUDY_USER_PASSWORD=<パスワード>` の行を足し、`/mcp` で playwright をつなぎ直す。Claude はパスワード欄に名前 `STUDY_USER_PASSWORD` を入れる（値は会話・出力に出ない・`frontend-verify.md` の `--secrets`）。値は `'` で囲む（`STUDY_USER_PASSWORD='<パスワード>'`。囲まないと `#` から後ろが消える。値が空と読まれた名前は置き換わらず、名前のまま入力される）。行を足す・直すたびに `/mcp` でつなぎ直す（起動したときしか読まない）。置き換わったかは、パスワード欄の値が名前と同じでないこと・8 文字以上であることだけを `browser_evaluate` で真偽で確かめる（値そのものは出さない）
- **過去問の扱いの決まり**（IPA の使用条件: https://www.ipa.go.jp/shiken/faq.html ）:
  - 問題・選択肢・正解は IPA の公開 PDF（問題冊子・解答例）からだけ取る。PDF はユーザーが保存する（Claude の `curl` は止められる）
  - 出典の欄に「<年度> <期> <試験区分> <時間区分> 問N」（例: 令和6年度 秋期 データベーススペシャリスト試験 午前Ⅱ 問3）。改行・字下げ以外で表記を変えたら（下線が消える・枠の空欄を文字にする など）「（一部改変）」を付ける。上付き・下付きは Unicode の文字（B⁺・T₁）で書けば改変にならない。図・表を画像のまま付けるのは改変にならない
  - 解説は Claude が書き、先頭に「（Claude 作成の解説。IPA の公式の解説ではありません）」を付ける。過去問サイト・参考書の解説は見ない・写さない。書いたら、別の点検役（Agent）に問題冊子・解答例だけを材料に全問を見てもらう。誤りに気づいたら問題管理の画面で直す（DB を `manage.py shell` で直すと問題一覧の一時保存が古いまま残る。そのときは `from core.cache_service import cache_service; cache_service.invalidate_problems_cache(<科目 ID>)` で消す）。Linux の確かめ用のブラウザでは `⇄` が別の記号で出るので使わない（`→`・`⁺`・`₁`・`¹⁶`・`ⁿ` は出る）
  - 問題の Markdown・画像・PDF はリポジトリに入れない（`.evidence/I###/` に置く。git の対象外）
- **道具の注意**:
  - `import_problems` は欄を 1 行だけ読み（改行は捨てられる）、難易度はファイルごと（`--difficulty`）。難易度ごとにファイルを分けて流す。ファイルは `docker compose cp <ファイル> backend:/tmp/` で渡す。画面は選択肢の記号を出さないので、選択肢の本文の先頭に記号（ア〜エ）を書く
  - 画像は `import_problems` では付かない。問題管理の画面の「問題用画像」で付ける
  - PDF を画像にするのは使い捨てのコンテナの `pdftoppm`（`docker run --rm -v <PDF のフォルダ>:/in:ro -v <置き場所>:/out python:3.11-slim sh -c "apt-get update -qq && apt-get install -y -qq poppler-utils && pdftoppm …"`。範囲は `-x -y -W -H`、150dpi で A4 は 1240×1754px）
