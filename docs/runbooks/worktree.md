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

```bash
# 必ず primary checkout で実行する（例: ハーネス改善の 2 つ目 → harness-2）
cd <primary>
claude --worktree <track>-<連番>
```

- **必ず primary で作る**: `claude --worktree` は実行したフォルダの中（`.claude/worktrees/`）に作る。primary 以外で実行すると、そのワークツリーの中に入れ子が作られ、外側を撤去するときに巻き込まれる。primary は撤去しないので、ここを作成元に固定する。
- **基点**: 公式の既定（リモートの既定ブランチ＝`origin/develop`）。`main` は初期コミットのみで中身が無いため使わない。
- **初期ブランチ**: `worktree-<name>` で作られる。`/plan-issue` で feature ブランチを作った後、不要なら `git branch -d worktree-<name>` で消してよい。
- **設定ファイル**: gitignore 済みの `backend/.env`・`e2e/.env.e2e` は、リポジトリ直下の `.worktreeinclude` に従って公式機能が自動でコピーする（`--worktree`・サブエージェントの `isolation: worktree`・`EnterWorktree` のどれでも同じ）。**primary に `backend/.env` が無いとコピーされない**（黙って飛ばされる）。Docker を使う前に `wt-ports.sh` がこれを検査して止める（§5）。
- **終了時の確認**: 対話セッションの終了時に「ワークツリーを残すか」を聞かれたら、続けて使うワークツリーは「残す」を選ぶ。変更が無いワークツリーは公式機能が自動で片付ける。
- サブエージェントに `isolation: worktree` で作業させる場合も同じ仕組み（作成・コピー・自動片付け）が使われる。

**fallback（公式機能が使えない場合の手動手順）**:

```bash
cd <primary>
git fetch origin
git worktree add <primary>/.claude/worktrees/<name> -b <ブランチ> origin/develop
cp backend/.env .claude/worktrees/<name>/backend/.env          # 中身は読まない・存在を確認する
cp e2e/.env.e2e .claude/worktrees/<name>/e2e/.env.e2e          # E2E を行う場合のみ
git worktree list                                              # 現在の worktree 一覧を確認
```

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
| Docker を使っていない | 公式の自動片付けに任せる（変更が無ければ自動で消える）。残したものは `git worktree remove <パス>` |

```bash
cd <primary>
# データ（当該 Compose プロジェクトのコンテナ・named volume）が無ければ、そのまま撤去する
bash scripts/claude/wt-remove.sh <primary>/.claude/worktrees/<name>
# データがある、または判定できない場合は停止する。バックアップ（scripts/db_backup.sh）のうえ許可付きで再実行する
DANGER_OK=1 bash scripts/claude/wt-remove.sh <primary>/.claude/worktrees/<name>
```

- 撤去対象は `git worktree list` に登録されたワークツリーのパスで指定する（登録外のフォルダは扱わない）。公式配置も旧配置（`/mnt/c/app/wt-harness` など）も同じ形。
- 未コミット変更・未 push コミットがあると中止する（作業消失防止）。primary と、撤去対象の内側からの実行は拒否する。`--force` は使わない（中に別のワークツリーがあれば git が拒否する）。
- データの判定: Compose プロジェクト名（フォルダ名を小文字にし、英数字・`_`・`-` 以外を除いたもの）のラベルで `docker ps -a`・`docker volume ls` を調べる。`COMPOSE_PROJECT_NAME` の指定・compose ファイルの最上位 `name:`・docker が使えない場合は「判定できない」として許可を求める。
- **ブランチは消さない**。完了メッセージに残ったブランチ名が出るので、不要なら `git branch -d <ブランチ>` で消す。

**取り残しの発見と削除**:

```bash
docker compose ls -a                 # Compose プロジェクトの一覧（名前＝ワークツリーのフォルダ名）
git worktree list                    # いまあるワークツリー
docker volume ls -f dangling=true    # どのコンテナにも使われていない volume（ラベルの無い匿名 volume を含む）
```

- `docker compose ls -a` にあって、対応するワークツリーが無いプロジェクトは取り残し。`docker compose -p <名前> down -v` で消す。**破壊的操作**（Postgres 開発データの削除）なので `docs/runbooks/danger-ops.md` に従い、`DANGER_OK=1` の承認を得てから行う。dangling volume の削除（`docker volume rm`）も同じ扱い。

---

## 5. Docker を使う場合のセットアップ

このプロジェクトの開発環境は **Docker Compose**。ホストでの `venv` / `pip install` / `npm install` は使わない（依存はイメージに焼き込み、`node_modules` は frontend コンテナの匿名ボリュームで管理される）。

```bash
# 対象のワークツリーで実行する（backend/.env・e2e/.env.e2e は .worktreeinclude で自動コピー済み）
bash scripts/claude/wt-ports.sh      # (1) 直下 .env にポートを割り当てる（Docker 起動前に 1 回・→ §6）
docker compose up -d                 # (2) 起動（正準手順・テスト実行方法は common-commands.md を参照）
```

- **⚠️ (B) `.env` 欠落は静かに壊れる**: `backend/.env` は `env_file` の `required: false` で参照されるため、無くても `docker compose up` は**失敗しない**。その代わり `SECRET_KEY` / `DB_PASSWORD` などが **insecure な既定値のまま静かに起動**する。→ `wt-ports.sh` は `backend/.env` が無ければ明示エラーで止める（primary に元ファイルが無く `.worktreeinclude` がコピーしなかった場合もここで気づく）。
- **(C) `COMPOSE_PROJECT_NAME` を global に export しない**: Compose のプロジェクト名は既定でディレクトリ名になり、ワークツリーごとにコンテナ・named volume（Postgres データ含む）が自動的に分離される。global に export すると全ワークツリーが同一プロジェクト名になり、この分離が壊れる。→ `wt-ports.sh` / `wt-remove.sh` は当該変数が設定されていれば警告し、`wt-remove.sh` はデータ判定を「判定できない」に倒して許可を求める。
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
# 例: 2 つのワークツリーを同時起動
( cd <primary>/.claude/worktrees/app-2 && bash scripts/claude/wt-ports.sh && docker compose up -d )   # offset=10 → backend 8010 等
( cd <primary>/.claude/worktrees/app-3 && bash scripts/claude/wt-ports.sh && docker compose up -d )   # offset=20 → backend 8020 等

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
- **技術強制済み（I095）**: この「他のワークツリーを直接編集しない」ルールは、PreToolUse フック（`scripts/claude/hooks/pretooluse_guard.py`）で技術強制されている。別ワークツリーのルート配下への **Edit/Write/MultiEdit/NotebookEdit・Bash 書込（`>`/`>>`/`>|`・`tee`・`cp`/`mv` の宛先・`sed -i`）を `exit 2` でブロック**する（`.claude/settings.json` は commit 共有のため全ワークツリーに自動適用）。**読み取りは許可**（参照・調査は可）。判定は `git worktree list` のルートとの realpath 境界一致で行い、**入れ子では、パスを含む最も内側のワークツリーを所有者として判定**する（I179。入れ子ワークツリーは自分のファイルに書け、親→入れ子・入れ子→親・兄弟間はブロック）。**fail-safe**（ワークツリー境界を確定できない場合＝git 失敗時はブロック）・**エスケープ無し**（`DANGER_OK=1` でも解除されない）。未カバー経路（`cd <別ワークツリー>` 後の相対書込・`eval`/変数展開越しの宛先）は絶対パス宛先のみ検査という限界を stderr に明示する。

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

- **既存の `wt-harness`（`/mnt/c/app/wt-harness`・I179 より前の自作スクリプト方式で primary の外に作ったワークツリー）**: そこで進めているイシュー（I178・I179）が完了・クローズした後に、primary から `bash scripts/claude/wt-remove.sh /mnt/c/app/wt-harness` で撤去する（Docker のデータが無ければ許可は不要。未コミット変更・未 push があれば止まるので、先に片付ける）。必要なら primary で `claude --worktree harness-<連番>` で作り直す。
- **primary は移行しない**（そのまま作成元として使う）。
