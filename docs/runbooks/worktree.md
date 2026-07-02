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

```bash
git fetch origin
# ベースは必ず origin/develop。追加トラックを linked worktree として作る
git worktree add /mnt/c/app/wt-<track> -b feature/I<番号>-<概要> origin/develop

git worktree list          # 現在の worktree 一覧を確認

# 作業完了後: 先に volume を回収してから worktree を削除する（§5(D)）
docker compose down -v      # 当該 worktree の named volume を回収
git worktree remove /mnt/c/app/wt-<track>
```

- **落とし穴（重大）**: **`main` は使わない**。`main` は初期コミット（`Initialize README`）のみで、テンプレート・スクリプト・runbook・アプリコードが一切無い。ここから worktree を作ると空ツリーになる。必ず **`origin/develop` を基点**にする。

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

```bash
# (1) backend の .env を既存 worktree からコピー（.env は gitignore 対象で worktree 間で共有されない）
cp /mnt/c/app/study-app-multitenant/backend/.env backend/.env
# E2E を行う場合は e2e/.env.e2e も同様にコピーする

# (2) スタックを起動（正準手順・テスト実行方法は common-commands.md を参照）
docker compose up -d
```

- **⚠️ (B) `.env` 欠落は静かに壊れる**: `.env` は `env_file` の `required: false` で参照されるため、コピーを忘れても `docker compose up` は**失敗しない**。その代わり `SECRET_KEY` / `DB_PASSWORD` などが **insecure な既定値のまま静かに起動**する（エラーで気づけない）。必ずコピーできているか確認する。
- **(C) `COMPOSE_PROJECT_NAME` を global に export しない**: Compose のプロジェクト名は既定でディレクトリ名になる。これにより worktree ごとにコンテナ・named volume（Postgres データ含む）が自動的に分離される。シェルで `COMPOSE_PROJECT_NAME` を global に export すると全 worktree が同一プロジェクト名になり、この分離が壊れる。
- **(D) 掃除**: worktree ごとに named volume が増える。不要になった worktree は `git worktree remove` の前に、そのディレクトリで `docker compose down -v` を実行して volume を回収する（§3 参照）。

---

## 6. 並行実行の衝突（重要）

worktree ごとにコンテナ・volume は分離されるが、**ホストのポートは共有**される。既定の `docker compose up` が起動するサービスは固定のホストポートを使う:

| サービス | ホストポート |
|---------|------------|
| db (Postgres) | 5432 |
| redis | 6379 |
| backend | 8000 |
| frontend | 3000 |

（`nginx` の 80 / 443 は `profiles: production` 配下のため、既定の `docker compose up` では起動しない。）

- **2 つの worktree で同時に `docker compose up` すると、これらのポートが衝突**して片方が起動に失敗する。
- **対処（推奨）**: 現行の人手による並行運用では、**同時にスタックを up せず 1 スタックずつ**起動する。トラックを切り替えるときは、使っていない方を `docker compose down` してから他方を up する。
- 同時起動がどうしても必要な場合のみ、worktree ごとに compose override でポートと `COMPOSE_PROJECT_NAME` を変える。ただしポートは環境変数でテンプレート化されておらず compose ファイルの編集が要るため、この override 化は本 runbook の対象外（必要なら別イシューで仕組み化する）。

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

## 8. 採番の一貫性

- `/issue-bootstrap` 直後のイシューファイルは **untracked（未コミット）** で、それを作った worktree からしか見えない。
- 別の worktree でイシューを起票すると、互いの untracked イシューが不可視なため**採番が食い違う**恐れがある。
- **ルール**: 採番は権威となる作業ツリー（未コミットのイシューが見える primary checkout = `study-app-multitenant`）で行うか、起票後すみやかに develop へ取り込んで全 worktree から見える状態にする。

---

## 9. セッション間の引き継ぎ原則（自己完結）

- **口頭メモ（チャット上のメモ）での引き継ぎは禁止**。メモ漏れで受け手セッションがぶれ、記録が `docs/` に残らず憲法5「記録が残る形」に反する。
- 引き継ぎは**イシュー / 計画 / レビューのファイルに自己完結で記述**する。**文脈ゼロの新規セッションが、そのファイルだけを読んで同じ結論に到達し作業を続行できる状態**を必須とする。
- トラックをまたぐ依頼も同様。現セッションから他トラックの worktree を直接編集せず、引き継ぎはファイル経由で行う。

---

## 10. 現時点のトラック構成（参考・2026-07 時点）

> この節は現状のスナップショット（参考）。手順本文の一般形とは別枠。構成が変わったら更新する。

| トラック | 作業ツリー | 種別 | 用途 |
|---------|-----------|------|------|
| ハーネス改善 | `/mnt/c/app/wt-harness` | linked worktree | バイブコーディングの仕組み改善イシュー |
| アプリ開発 | `/mnt/c/app/study-app-multitenant` | primary checkout（採番権威） | 学習アプリ開発 |
