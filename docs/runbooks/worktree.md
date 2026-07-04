# worktree ベースの並行トラック運用

複数の作業トラック（例: 「ハーネス改善」と「アプリ開発」）を、**作業ツリーの分離 + セッションの分離 + ファイルベースの引き継ぎ**で無損失に並行させるための手順。単一作業ツリーでブランチを切り替える方式は、片方の未コミット変更がもう片方を妨げ、1 セッションで複数トラックを扱うとコンテキストが混在する。git worktree でトラックごとに独立したディレクトリを持つことでこれを解消する。

> この runbook の手順本文は特定トラックに依存しない**一般形**（`<track>` / `<番号>` はプレースホルダ）で書く。現時点の具体的なトラック構成は末尾の「現時点のトラック構成（参考）」を見ること。

---

## 1. 用語

| 用語 | 意味 |
|------|------|
| トラック | 独立して並行させたい作業の束（例: ハーネス改善 / アプリ開発）。トラック = 1 作業ツリー。 |
| worktree | `git worktree` が作る、同一リポジトリを共有する別ディレクトリの作業ツリー。 |
| primary checkout | 最初に `git clone` した本体の作業ツリー。`git worktree list` の先頭に出る。 |
| linked worktree | `git worktree add` で後から生やした作業ツリー。 |

---

## 2. トラック / ブランチ設計

- **トラック単位で作業ツリー**、その中で**イシュー単位にブランチ**（`feature/I<番号>-<概要>`）を切る。
- **アプリ開発トラック**は既存の **primary checkout（`study-app-multitenant`）** をそのまま使う。ここは未コミットのイシューファイルが見える**採番権威**でもある（→ §7）。
- **追加トラック**は `wt-<track>` という名前の **linked worktree**（例: `wt-harness`）として生やす。
- 命名例: ハーネス改善トラック → `/mnt/c/app/wt-harness`。専用の `wt-app` は**新設しない**（アプリ開発は primary checkout を使う）。

---

## 3. worktree の作成・一覧・削除（ベースブランチ = develop）

**推奨: ヘルパースクリプト（`scripts/claude/wt-new.sh` / `wt-remove.sh`）を使う**（I096）。下記 §3 の手動手順は fallback（スクリプトを使わない場合）として残す。スクリプトは基点 origin/develop 固定・`.env` コピー検証・volume 回収の順序を機械化し、§3/§5 の foot-gun を人手規律に頼らず防ぐ。

```bash
# 作成: <base>/wt-<track> を origin/develop 基点で作る（base は primary checkout の親から自動導出）。
# backend/.env を primary からコピー＆存在検証（欠落なら停止）。up は既定 OFF・--up で opt-in。
# ポート分離（§6・I097）: 直下 .env に *_PORT を自動生成。--port-offset 未指定時は空きオフセット(+10)を自動割当。
bash scripts/claude/wt-new.sh <track> <番号> <概要> [--env-source <path>] [--up] [--port-offset N]

git worktree list          # 現在の worktree 一覧を確認

# 撤去: down -v（named volume 回収）→ git worktree remove。down -v は破壊的なため DANGER_OK=1 必須。
# 未コミット変更・未 push コミットがあると（作業消失防止のため）中止する。
DANGER_OK=1 bash scripts/claude/wt-remove.sh <track>
```

**fallback（スクリプトを使わない手動手順）**:

```bash
git fetch origin
# ベースは必ず origin/develop。追加トラックを linked worktree として作る
git worktree add /mnt/c/app/wt-<track> -b feature/I<番号>-<概要> origin/develop

git worktree list          # 現在の worktree 一覧を確認

# 作業完了後: まず当該 worktree のディレクトリに移動し、volume を回収してから削除する（§5(D)）
cd /mnt/c/app/wt-<track>
docker compose down -v      # ← 当該 worktree ディレクトリで実行（named volume を回収）
cd -                        # 元のディレクトリへ戻る（worktree remove は内部から実行不可のため）
git worktree remove /mnt/c/app/wt-<track>
```

- **落とし穴（重大）**: **`main` は使わない**。`main` は初期コミット（`Initialize README`）のみで、テンプレート・スクリプト・runbook・アプリコードが一切無い。ここから worktree を作ると空ツリーになる。必ず **`origin/develop` を基点**にする（`wt-new.sh` は基点を origin/develop に固定してこれを機械化で防ぐ）。

---

## 4. 各 worktree で独立した Claude セッションを起動する

- 各 worktree ディレクトリで**別々に `claude` を起動**する（トラックごとに独立したコンテキスト）。
- Cursor / VSCode では**別フォルダを別ウィンドウで開く**:
  - メニュー: File > New Window → Open Folder で対象 worktree を開く
  - または CLI: `code -n <path>` / `cursor -n <path>`（`-n` = 新規ウィンドウ）
- **落とし穴**: 既に開いているフォルダを再度「Open Folder」で**再オープン**しても、新規ウィンドウにならず**既存ウィンドウにフォーカスが戻るだけ**になる。別ウィンドウにしたいときは必ず New Window から開く。

---

## 5. 新しい worktree のセットアップ（Docker Compose 前提）

このプロジェクトの開発環境は **Docker Compose**。ホストでの `venv` / `pip install` / `npm install` は使わない（依存はイメージに焼き込み、`node_modules` は frontend コンテナの匿名ボリュームで管理される）。

**推奨**: §3 の `wt-new.sh` が (1) の `.env` コピー＆存在検証と (2) の起動（`--up` 指定時）を自動化する。以下の手動手順は fallback（`wt-new.sh` を使わない場合）。

```bash
# (1) backend の .env を既存 worktree からコピー（.env は gitignore 対象で worktree 間で共有されない）
cp /mnt/c/app/study-app-multitenant/backend/.env backend/.env
# E2E を行う場合は e2e/.env.e2e も同様にコピーする

# (2) スタックを起動（正準手順・テスト実行方法は common-commands.md を参照）
docker compose up -d
```

- **⚠️ (B) `.env` 欠落は静かに壊れる**: `.env` は `env_file` の `required: false` で参照されるため、コピーを忘れても `docker compose up` は**失敗しない**。その代わり `SECRET_KEY` / `DB_PASSWORD` などが **insecure な既定値のまま静かに起動**する（エラーで気づけない）。必ずコピーできているか確認する。→ `wt-new.sh` は `.env` を `cp` した後に存在検証し、欠落/コピー失敗なら明示エラーで停止して機械化で防ぐ。
- **(C) `COMPOSE_PROJECT_NAME` を global に export しない**: Compose のプロジェクト名は既定でディレクトリ名になる。これにより worktree ごとにコンテナ・named volume（Postgres データ含む）が自動的に分離される。シェルで `COMPOSE_PROJECT_NAME` を global に export すると全 worktree が同一プロジェクト名になり、この分離が壊れる。→ `wt-new.sh` / `wt-remove.sh` は当該変数が設定されていれば警告する。
- **(D) 掃除**: worktree ごとに named volume が増える。不要になった worktree は `git worktree remove` の前に、そのディレクトリで `docker compose down -v` を実行して volume を回収する（§3 参照）。→ `wt-remove.sh` は `down -v`（`DANGER_OK=1` 必須）→ `remove` の順序を機械化して volume 漏れを防ぐ。

---

## 6. 並行実行のポート分離（同時起動可能・I097）

worktree ごとにコンテナ・volume は `COMPOSE_PROJECT_NAME`（既定＝ディレクトリ名）で分離される。ホストの publish ポートは **環境変数でテンプレート化**されており（I097）、worktree ごとに直下 `.env` でオフセットすることで**同時に `docker compose up` してもポートが衝突しない**。

`docker-compose.yml` のホストポートは既定値付き環境変数で publish される（**変数未設定時は下表の既定値**＝後方互換）:

| サービス | 環境変数 | 既定ポート |
|---------|---------|-----------|
| db (Postgres) | `DB_PORT` | 5432 |
| redis | `REDIS_PORT` | 6379 |
| backend | `BACKEND_PORT` | 8000 |
| frontend | `FRONTEND_PORT` | 3000 |

（`nginx` の 80 / 443 は `profiles: production` 配下のため、既定の `docker compose up` では起動しない＝ポート変数化の対象外。）

**オフセット規約**: STEP=10。primary=offset 0（既定ポート）、追加 worktree は +10 ずつ（次=10, 次=20 ...）。`port = 既定 + offset`（例: offset=10 → db 5442 / redis 6389 / backend 8010 / frontend 3010）。base 間隔が広いためサービス間衝突は起きない。

**運用（推奨・自動）**: `scripts/claude/wt-new.sh` が新規 worktree 作成時に直下 `.env` を自動生成する。
- `--port-offset` 未指定時は既存 worktree の `.env` を走査し、**空きオフセット（max+10）を自動割当**。
- `--port-offset N` で明示指定も可能。既存 worktree とポートが衝突する場合は **fail**（作成前に停止）。
- 生成される `.env` は gitignore 対象（`.env` / `*.env`）で worktree ごとに非共有。`COMPOSE_PROJECT_NAME` は `.env` に書かない（既定＝ディレクトリ名でコンテナ/volume を分離）。

```bash
# 例: 2 トラックを同時起動
bash scripts/claude/wt-new.sh app 201 feature-a          # 自動で offset=10 → backend 8010 等
bash scripts/claude/wt-new.sh api 202 feature-b          # 自動で offset=20 → backend 8020 等
( cd <base>/wt-app && docker compose up -d )              # 両方を同時に up してもポート衝突しない
( cd <base>/wt-api && docker compose up -d )

# 割当ポートの確認（publish されるホストポートをレンダリングして確認）
docker compose config | grep -A1 published
```

**手動運用（wt-new を使わない場合）**: 対象 worktree 直下に `.env` を作り、上表の 4 変数へ「既定＋オフセット」を設定してから `docker compose up`（変数未設定なら既定ポートで起動＝従来どおり）。

---

## 7. 共有されるもの / されないもの

同一リポジトリを共有するため、**コミット済みの内容は全 worktree で共有**される。一方で gitignore 対象・コンテナ管理のものは共有されない。

**共有される（コミット済み / `.git`）**:
- `.git` 履歴・コミット済みファイル全般
- `CLAUDE.md`・`docs/runbooks`（この runbook 含む）
- `.claude/settings.json`（権限・フック設定）
- tracked な `frontend/.env.*`（`frontend/.env.development` / `frontend/.env.production`）

**共有されない（手当てが要る）**:
- backend `.env`（gitignore・要コピー → §5）
- `e2e/.env.e2e`（gitignore・E2E 時のみ・任意）
- 未コミット / untracked のファイル（他 worktree からは見えない → §8）

**コンテナ管理（ホストでは共有されないが手当ても不要）**:
- 依存パッケージ（イメージに焼き込み）
- `node_modules`（frontend コンテナの匿名ボリューム `/app/node_modules`）
- dev DB のデータ: **Postgres コンテナ + named volume**。`COMPOSE_PROJECT_NAME`（既定 = ディレクトリ名）ごとに自動分離される。`db.sqlite3`（gitignore）は起動中の dev DB ではない。

**WSL 表示確認**: WSL 環境では、Windows 側エクスプローラや Cursor のパス表示が `/mnt/c/...` と `\\wsl$\...` で食い違うことがある。開いているフォルダのパスが目的の worktree と一致しているか確認する。

---

## 8. 採番の一貫性（採番権威の単一化・I098）

- `/issue-bootstrap` 直後のイシューファイルは **untracked（未コミット）** で、それを作った worktree からしか見えない。かつては別 worktree で起票すると互いの untracked が不可視で**採番が食い違う**恐れがあった（primary で採番する人手規律に依存）。
- **ルール（機械化）**: 採番は必ず `scripts/claude/next-issue-num.sh` 経由で行う。本スクリプトは `git worktree list` で**全 worktree の `docs/issues`（untracked 含む）**＋`git log --all`（削除済み含む）を横断集計し `max(...)+1` を返すため、**どの worktree から実行しても同一の大域一意番号**が得られる（採番権威が単一化）。primary 固定・起票後の事前取り込みといった人手規律は不要。
  - 読み取りのみ（find / git log）で他 worktree を参照するため、I095 の横断ガード（書込のみブロック・読み取りは許可）に抵触しない。
  - CWD 非依存（git 履歴 pathspec を `:/docs/issues` に固定）。アンカー正規表現 `/I?\K\d+(?=\.md$)` で `I###.md`/`###.md` のみを対象にし、`draft-I200.md` 等の decoy を誤カウントしない（I094）。
- **スコープ外（既知の残存）**: 2 worktree がほぼ同時に採番する競合（TOCTOU）、および**既存の**二重採番（過去に別々採番された同番号・同一番号の open/closed 共存）の検出/修復は本スクリプトの対象外（単一逐次オペレータ前提）。将来の二重採番の防止のみを保証する。

---

## 9. セッション間の引き継ぎ原則（自己完結）

- **口頭メモ（チャット上のメモ）での引き継ぎは禁止**。メモ漏れで受け手セッションがぶれ、記録が `docs/` に残らず憲法5「記録が残る形」に反する。
- 引き継ぎは**イシュー / 計画 / レビューのファイルに自己完結で記述**する。**文脈ゼロの新規セッションが、そのファイルだけを読んで同じ結論に到達し作業を続行できる状態**を必須とする。
- トラックをまたぐ依頼も同様。現セッションから他トラックの worktree を直接編集せず、引き継ぎはファイル経由で行う。
- **技術強制済み（I095）**: この「他トラックの worktree を直接編集しない」ソフトルールは、PreToolUse フック（`scripts/claude/hooks/pretooluse_guard.py`）で技術強制されている。別 worktree ルート配下への **Edit/Write/MultiEdit/NotebookEdit・Bash 書込（`>`/`>>`/`>|`・`tee`・`cp`/`mv` の宛先・`sed -i`）を `exit 2` でブロック**する（`.claude/settings.json` は commit 共有のため双方向に自動適用）。**読み取りは許可**（参照・調査は可）。判定は `git worktree list` の別 worktree ルートとの realpath 境界一致で行う。**fail-safe**（worktree 境界を確定できない場合＝git 失敗時はブロック）・**エスケープ無し**（`DANGER_OK=1` でも解除されない）。未カバー経路（`cd <別worktree>` 後の相対書込・`eval`/変数展開越しの宛先）は絶対パス宛先のみ検査という限界を stderr に明示する。

---

## 10. 現時点のトラック構成（参考・2026-07 時点）

> この節は現状のスナップショット（参考）。手順本文の一般形とは別枠。構成が変わったら更新する。

| トラック | 作業ツリー | 種別 | 用途 |
|---------|-----------|------|------|
| ハーネス改善 | `/mnt/c/app/wt-harness` | linked worktree | バイブコーディングの仕組み改善イシュー |
| アプリ開発 | `/mnt/c/app/study-app-multitenant` | primary checkout（採番権威） | 学習アプリ開発 |
