# plan_I092: worktree ベースの並行トラック運用を runbook 化

## 基本情報
- **計画書ID**: plan_I092
- **関連イシュー**: #177
- **Draft PR**: #178
- **作成根拠資料**: docs/issues/open/I092.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I092_review.md
- **作成日**: 2026-07-02

---

## 1. 背景/目的

「ハーネス改善」トラックと「アプリ開発」トラックを**並行**で進めたいが、標準手順が docs に無く属人化している。単一作業ツリーでブランチを切り替える方式は、片方の未コミット変更がもう片方を妨げ、1 セッションで両トラックを扱うとコンテキストが混在する。さらにセッション間引き継ぎを口頭メモで行うと記録が `docs/` に残らず憲法5「記録が残る形」に反する。

実際に本イシュー起票準備中、worktree を **`main`（初期コミットのみ）から**作成して空ツリーが生成される事故が発生した。手順を docs 化すれば防げる。

**目的**: `docs/runbooks/worktree.md` を新規作成し、CLAUDE.md の参照先に 1 行追加して、トラック並行運用（worktree 分離・ベースブランチ選択・トラック/ブランチ設計・環境の非共有点・採番一貫性・セッション間引き継ぎ原則）を再現可能な手順として確立する。

---

## 2. 調査結果

### 環境前提確認
- `git worktree` 使用可（`git worktree list` 成功）。
- `origin/develop` 存在（ベースブランチとして使用可）。`main` は初期コミット `Initialize README` のみ。
- `gh` 認証済み（GitHub 同期・PR 作成可）。
- 現在の作業ツリー: `/mnt/c/app/wt-harness`（branch `feature/I092-worktree-runbook`、develop 分岐）は linked worktree。primary checkout は `/mnt/c/app/study-app-multitenant`。

### 参照先実在性の全件機械検証（ドキュメント整合系）
現行 CLAUDE.md が参照する `docs/**.md` / `rules/**.md` を全件 `test -f` した結果、**17 件すべて実在**（デッドリンクなし）。`docs/runbooks/worktree.md` のみ未作成（本イシューで新規作成）。→ 追加する 1 行のリンク先は実装で作成されるため、実装後にリンク切れ 0 を維持できる（AC の「リンク切れなし」達成可能）。

### 共有/非共有の事実確認（`.gitignore` / tracked 状態）
- **非共有（gitignore 対象）**: `venv/` `.venv` `node_modules/` `frontend/node_modules/` `db.sqlite3` `.env` `*.env` `.env.e2e`。
- **共有（tracked）**: `.claude/settings.json` `backend/.env.example` `frontend/.env.development` `frontend/.env.production` ほかコミット済みファイル・`.git` 履歴。

### 実行環境の事実確認（`docker-compose.yml` / `common-commands.md` 実査）※前提訂正
初回グリルでは「venv/pip/npm でセットアップ」「SQLite ロック競合」を前提にしたが、**docker-compose.yml と common-commands.md の実査で前提が誤りと判明**したため訂正する:
- **開発環境は Docker Compose**（`docker compose up -d`／テストも `docker compose exec ...`）。ホストでの `venv`/`pip install`/`npm install` の運用は文書化されておらず、依存は image に焼き込み。`frontend` は `volumes: - /app/node_modules`（**匿名ボリューム**）で node_modules をコンテナ内管理 → ホスト `frontend/node_modules` は起動アプリに使われない。
- **dev DB は Postgres コンテナ**（`ports: 5432`・named volume）。`db.sqlite3`（gitignore）は起動 dev DB ではない。
- **`COMPOSE_PROJECT_NAME` 未設定・override ファイル無し** → 既定の project 名＝ディレクトリ名。よって `wt-harness` と `study-app-multitenant` はコンテナ名・named volume（Postgres データ含む）が**自動分離**される（DB データはロック競合せず独立）。
- **ただしホスト固定ポートが衝突する**: `5432/6379/8000/3000/80/443` は全サービスで固定。2 worktree で**同時に `docker compose up`** すると全ポートが衝突 → 同時起動不可。これが「並行運用の真の衝突点」（SQLite ロックではない）。
- `env_file: ./backend/.env`（gitignore・非共有）→ 新 worktree で**コピーが必要**。E2E は `e2e/.env.e2e`（gitignore・任意）。
- 帰結: セットアップは「backend `.env` コピー → `docker compose up -d`」に集約し、venv/pip/npm 手順は記載しない（既存アーキと矛盾するため）。共有/非共有の説明も Docker 前提に是正する。

### AC の性質
本イシューの AC は「runbook / CLAUDE.md の**記載有無**」の照合であり、lint/audit/scan の出力では決まらない（監査系ツール実走は非該当）。→ AC は grep ベースの決定論チェックで機械検証する（自動テスト文書 I092_auto_test.md）。

---

## 3. 影響範囲

- **Backend**: なし
- **Frontend**: なし
- **DB**: なし
- **Config/Infra**: `docs/runbooks/worktree.md`（新規）・`CLAUDE.md`（参照先 1 行追加）
- **変更対象外（説明目的でのみ言及・参照）**: `.claude/settings.json` / `db.sqlite3` / backend `.env` / frontend `.env.*` / `e2e/.env.e2e` / `docker-compose.yml` / `docs/runbooks/common-commands.md` は共有/非共有・セットアップ・ポート衝突を説明・参照するため runbook 本文で言及するが、いずれも本イシューでは編集しない。
- **P3/P5/P8 影響なし**（DB 変更・依存関係変更・外部 API/非同期/バッチなし。requirements/package の変更なし → Dockerfile/compose への波及なし）。
- **P6 影響なし**（UI 変更・データ量/外部 API 懸念なし → 性能・UX 設計セクション不要）。
- **P9 影響なし**（個人情報・未成年データ・テナントデータを扱わない → プライバシー設計セクション不要）。
- **セキュリティ影響なし**（バックエンド/フロントエンドのコード変更なし。runbook と CLAUDE.md 参照 1 行の docs 追加のみ）。

---

## 4. 変更点一覧

| ファイル | 種別 | 変更内容 |
|---------|------|---------|
| docs/runbooks/worktree.md | 新規 | worktree 並行トラック運用の手順・ベースブランチ選択・トラック/ブランチ設計・独立セッション起動・新 worktree セットアップ・共有/非共有・採番一貫性・セッション間引き継ぎ原則・現構成の参考例（下記§5 の構成に従う） |
| CLAUDE.md | 編集 | 「0. 参照先」運用・ルール: リストの **`運用フロー: workflow.md` の直後**に `- 並行トラック運用（worktree）: docs/runbooks/worktree.md` を 1 行追加 |

### 4.1 CLAUDE.md への追加内容（確定文言）
worktree 並行トラック運用は運用フロー（workflow.md）の直接拡張であり、発見容易性・概念的近接から**運用・ルール: 区分の 2 番目**（`- 運用フロー: docs/runbooks/workflow.md` の直後）に置く。挿入する行:
```
- 並行トラック運用（worktree）: docs/runbooks/worktree.md
```

---

## 5. runbook（worktree.md）の構成（記述方針＝2層）

**記述構成の原則**: 手順本文は固有名に依存しない**一般形**で書き、末尾に「現時点のトラック構成（参考・日付つき）」を**別枠**で置く（AC「一般表現」と実行者の具体性を両立）。

runbook は以下のセクションで構成する:

1. **目的**: 複数トラックを作業ツリー＋セッション分離＋ファイルベース引き継ぎで無損失に並行する。
2. **用語**: トラック / worktree / primary checkout / linked worktree の定義。
3. **トラック/ブランチ設計**:
   - トラック単位で作業ツリー、その中でイシュー単位にブランチ（`feature/I###-...`）を切る。
   - アプリ開発トラック＝既存の primary checkout（`study-app-multitenant`＝**採番権威**）を使う。
   - 追加トラック＝`wt-<track>` 名の linked worktree（例 `wt-harness`）として生やす。`wt-app` は新設しない。
4. **worktree 作成手順（一般形）**: ベースブランチ＝`develop` を明示。
   ```bash
   git fetch origin
   git worktree add /mnt/c/app/wt-<track> -b feature/I<番号>-<概要> origin/develop
   git worktree list      # 一覧確認
   git worktree remove /mnt/c/app/wt-<track>   # 作業完了後の削除
   ```
   - **落とし穴**: `main` は初期コミットのみ。必ず `develop` を基点にする。
5. **独立 Claude セッションの起動**:
   - 各 worktree ディレクトリで別々に `claude` を起動する。
   - Cursor/VSCode で**別フォルダを別ウィンドウ**で開く手順（File > New Window → Open Folder、または `code -n <path>` / `cursor -n <path>`）。
   - **落とし穴**: 同じフォルダを再オープンすると既存ウィンドウにフォーカスが戻るだけで新規セッションにならない。
6. **新 worktree のセットアップ手順（Docker Compose 前提）**:
   - backend `.env` を既存 worktree からコピー（gitignore・非共有）: `cp /mnt/c/app/study-app-multitenant/backend/.env backend/.env`。E2E を行う場合は `e2e/.env.e2e` も同様に用意。
   - `docker compose up -d` で起動（正準手順・テスト実行は `common-commands.md` 参照）。**ホストの `venv`/`pip install`/`npm install` は不要**（依存は image に焼き込み・`node_modules` は frontend コンテナの匿名ボリューム管理）。
   - `COMPOSE_PROJECT_NAME` は既定でディレクトリ名になるため、worktree ごとにコンテナ・named volume（Postgres データ含む）は自動分離される（追加設定不要）。
7. **並行実行の衝突（重要）**:
   - ホスト固定ポート `5432(db)/6379(redis)/8000(backend)/3000(frontend)/80,443(nginx)` は全 worktree 共通。**2 worktree で同時に `docker compose up` するとポートが衝突**する。
   - 対処: 現行の人手2トラック運用では**同時に up せず 1 スタックずつ**起動する（推奨）。同時起動が必要な場合のみ worktree ごとに compose override でポート＋`COMPOSE_PROJECT_NAME` を変える（override 構築は本イシュー対象外＝別イシュー化）。
8. **共有 / 非共有の一覧**:
   - **共有される**: `.git` 履歴・コミット済みファイル・`CLAUDE.md`・`docs/runbooks`・`.claude/settings.json`・tracked な `frontend/.env.*`。
   - **共有されない（手当てが要る）**: backend `.env`（要コピー）・`e2e/.env.e2e`（任意）・未コミット/untracked ファイル。
   - **コンテナ管理（ホスト非共有だが手当て不要）**: 依存（image）・`node_modules`（frontend の匿名ボリューム `/app/node_modules`）。
   - **dev DB**: **Postgres コンテナ + named volume**。`COMPOSE_PROJECT_NAME`（既定＝ディレクトリ名）ごとに自動分離されるためロック競合は起きない。`db.sqlite3`（gitignore）は起動 dev DB ではない旨を補足。
   - **WSL 表示確認**: WSL 環境でのパス表示・エクスプローラ確認の注意。
9. **採番の一貫性**: 起票直後の untracked イシューは他 worktree から不可視。採番は権威ツリー（未コミット分が見える primary checkout `study-app-multitenant`）で行うか、起票後すみやかに develop へ取り込む。
10. **セッション間引き継ぎ原則**: 口頭メモ禁止。引き継ぎはイシュー/計画/レビューのファイルに**自己完結**で記述し、文脈ゼロのセッションが同じ結論に到達できる状態を必須とする。
11. **現時点のトラック構成（参考・2026-07 時点）**（別枠・日付つき）:
    | トラック | 作業ツリー | 種別 | 用途 |
    |---------|-----------|------|------|
    | ハーネス改善 | /mnt/c/app/wt-harness | linked worktree | 仕組み改善イシュー |
    | アプリ開発 | /mnt/c/app/study-app-multitenant | primary checkout（採番権威） | 学習アプリ開発 |

---

## 6. 実装手順（ステップ）

> 本イシューは docs のみ。垂直スライス/未知リスク先行の対象となるコード層は無いため、単一ステップで完結する。検証は各 TC（I092_auto_test.md）に委譲する。

- **ステップ1**: `docs/runbooks/worktree.md` を §5 の構成（1〜11）で新規作成する。→ TC-A1〜A9, TC-A13, TC-A11 参照
- **ステップ2**: `CLAUDE.md` 運用・ルール: の 2 番目（`運用フロー: workflow.md` の直後）に §4.1 の 1 行を追加する。→ TC-A10, TC-A12 参照
- **依存関係**: ステップ2 はステップ1 の完了が前提（追加するリンク先が存在してからリンクを張る＝TC-A11 のリンク切れ回避）。

---

## 7. テスト計画

- **自動テスト**: なし（pytest / npm test の対象コードは変更しない）。代わりに **docs 内容の決定論チェック**（grep/`test -f`）を I092_auto_test.md の TC として定義し、`/test` で実行する。テストレベルは「静的検証（grep/ファイル存在）」。
- **手動テスト**: I092_manual_test.md。runbook の可読性・手順の再現性の目視確認（大半は Claude が Read/Bash で実施可、可読性の最終確認のみ Human）。
- **再発防止**: 「main からの worktree 作成事故」の再発防止として、TC で「ベースブランチ＝develop」「main を使わない旨」が runbook に明記されていることを検証する。
- 認可・テナント境界テストは非該当（コード変更なし）。

---

## 8. ロールバック

- `git` で全変更（worktree.md 追加・CLAUDE.md 差分）を復元可能。runbook 削除と CLAUDE.md の 1 行削除で原状復帰。破壊的操作なし。

---

## 9. Risk & 回避策

| Risk | 回避策 |
|------|--------|
| 追加した CLAUDE.md リンクがリンク切れ | ステップ2 をステップ1 の後に実施。TC-A11/A12 でリンク先実在を機械検証 |
| runbook が I092 固有表現に依存し一般性を欠く | 手順本文は `<track>`/`I<番号>` プレースホルダの一般形。具体値は §5-11 の「参考・日付つき」別枠に隔離。TC-A12 で検証 |
| 記載漏れ（AC 項目の抜け） | AC の各項目を TC-A1〜A13 に 1:1 対応させ、`/test` で全件検証 |
| 初回グリルの誤前提(venv/npm・SQLite)の残存 | イシュー本文・メモ・プラン・テストを Docker 現実へ同時是正済み。TC-A6/A7/A8 を docker/ポート/Postgres 検証に更新 |

---

## 10. 設計判断の明示（イシュー明記 / 仮定の区別）

| 設計判断 | 区分 | 根拠 |
|---------|------|------|
| ベースブランチ＝develop | イシュー明記 | 解決方針・設計確認メモ |
| アプリ開発＝既存 study-app-multitenant、追加＝wt-<track>、wt-app 新設なし | イシュー明記 | /grill-me メモ（2ラウンド目） |
| 2層構成（一般手順＋参考の現構成） | イシュー明記 | /grill-me メモ（2ラウンド目） |
| 共有/非共有の具体項目（backend .env 非共有・frontend .env.* 共有・DB 独立） | イシュー明記 | /grill-me メモ（1ラウンド目）＋ .gitignore 実査 |
| CLAUDE.md の挿入位置＝運用・ルール: の 2 番目（workflow.md の直後） | 決定（理想基準） | worktree 運用は運用フローの直接拡張。発見容易性・概念的近接で最適位置と判断 |
| セットアップ手順＝backend `.env` コピー → `docker compose up -d`（venv/pip/npm は不使用） | 決定（Docker 現実に整合） | docker-compose.yml/common-commands.md 実査。初回グリルの venv/pip/npm 前提は誤りと判明し是正 |
| 並行衝突点＝ホスト固定ポート（SQLite ロックではない） | 決定（Docker 現実に整合） | docker-compose.yml 実査（固定ポート・override 無し・PROJECT_NAME 未設定） |
| dev DB＝Postgres コンテナ+named volume（COMPOSE_PROJECT_NAME で自動分離） | 決定（Docker 現実に整合） | docker-compose.yml 実査。`db.sqlite3` は起動 dev DB でないと確認 |

※ 上記はいずれも**理想・現実整合を基準に決定済み**（仮定なし）。初回グリルで確定した venv/pip/npm・SQLite 前提は Docker 実査により誤りと判明したため、イシュー本文・メモも同時に是正済み（plan-writing-rules「計画変更時に関連ドキュメントを同時更新」に準拠）。

---

## 11. 承認ポイント（チェックリスト）

**重要（前提訂正）**: 初回グリルで確定した「venv/pip/npm でセットアップ」「SQLite ロック競合」は、docker-compose.yml/common-commands.md の実査により**既存アーキ(Docker Compose)と矛盾する誤り**と判明しました。理想・現実整合を基準に以下へ是正済みです（イシュー本文・メモも同時更新）:

1. **セットアップ＝Docker 前提**: backend `.env` コピー → `docker compose up -d`（正準手順は common-commands.md 参照）。ホストの venv/pip/npm install は不要（依存はコンテナ管理・node_modules は匿名ボリューム）。
2. **並行の衝突点＝ホスト固定ポート**（5432/6379/8000/3000/80/443）。同時 `up` 不可 → 1 スタックずつ起動（推奨）。同時起動用の compose override は別イシュー化。
3. **dev DB＝Postgres コンテナ+named volume**。`COMPOSE_PROJECT_NAME`（既定＝ディレクトリ名）で worktree ごとに自動分離。`db.sqlite3` は起動 dev DB ではない。
4. **CLAUDE.md 挿入位置**: 運用・ルール: の 2 番目（`運用フロー: workflow.md` の直後）。worktree 運用は運用フローの直接拡張のため最適位置と判断。

上記の是正方針で **`docs/runbooks/worktree.md` を §5 の構成（1〜11）** で作成し、CLAUDE.md に 1 行追加します。この方針で承認いただけますか。その他はイシュー本文・/grill-me メモの確定値どおりで、仕様追加・逸脱はありません。
