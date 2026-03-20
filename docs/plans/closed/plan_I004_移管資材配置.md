# I004 計画書: 移管用フォルダの資材をリポジトリに配置

## 基本情報
- **計画書ID**: plan_I004_移管資材配置
- **関連イシュー**: #004 (GitHub #12)
- **作成根拠資料**: docs/issues/open/004.md
- **実装後評価**: （未作成）
- **作成日**: 2026-03-19

---

## 1. 背景/目的
- **大命題**: 学習アプリをデバッグモードでエラーなく起動できる状態にする
- `移管用/` フォルダの資材をリポジトリルートに配置し、`docker-compose up -d` で全コンテナが正常稼働することを確認する

## 2. 受け入れ条件
- [ ] **【主目的】** `docker-compose up -d` 後、全コンテナ（backend・frontend・db・nginx・redis）が正常稼働
- [ ] Claude: コンテナログ・`docker-compose ps`・Django ログにエラーなしを確認
- [ ] ユーザー: ブラウザでアプリにアクセスし、画面が正常に表示されることを確認
- [ ] DB データが正常にリストアされ、テーブルが存在する（`\dt` で確認）
- [ ] 移管ファイル一覧（✅）の全ファイル・ディレクトリがリポジトリルートに存在する
- [ ] 移管しない（❌）ファイルがコミットに含まれていない（`.env`・`backup_migration.sql` 含む）

## 3. 影響範囲
- Backend: `backend/` 全体を新規追加（Django アプリケーション）
- Frontend: `frontend/` 全体を新規追加（React TypeScript）
- DB: `backup_migration.sql`（移管用フォルダ配置済み）を PostgreSQL にリストア（DB名: `learning_app`、ユーザー: `postgres`）
- Config/Infra: `docker-compose.yml`, `nginx/`, `.gitignore`, `rules/` を追加

## 4. 変更点一覧（具体）

### 新規追加するファイル・ディレクトリ
| 対象 | 対応 |
|------|------|
| `docker-compose.yml` | 移管用からコピー |
| `.gitignore` | 移管用からコピー（`.env` 除外が含まれていることを確認）|
| `rules/` | 移管用からコピー |
| `dev_diary/` | 移管用からコピー |
| `answer/` | 移管用からコピー |
| `backend/` | 移管用からコピー（`.env` は除外）|
| `frontend/` | 移管用からコピー |
| `nginx/` | 移管用からコピー |

### 既存ファイルの扱い
| 対象 | 対応 |
|------|------|
| `CLAUDE.md` | 現リポジトリのものを維持（移管用は参照のみ）|
| `README.md` | 移管用で上書き |
| `docs/` | 現リポジトリのものを維持（移管用の `docs/` は性質が異なるため上書きしない）|

### 除外するファイル（移管しない）
- `backend/.env`（`.env.example` からの再設定が必要）
- `backend/logs/`, `backend/staticfiles/`, `backend/celerybeat-schedule`
- `backend/organization_backup.json`
- `frontend/node_modules/`, `frontend/build/`
- `backup_*.sql`
- `push_to_github.sh`, `.github_push.sh`, `test_registration.py`
- `学習アプリ.code-workspace`, `.claude/`, `get-docker.sh`

## 5. 実装手順（ステップ）

1. **`.gitignore` を配置**
   - 移管用からコピーし、`.env` が除外対象に含まれているか確認

2. **`docker-compose.yml` を配置**
   - 移管用からコピー

3. **`rules/` を配置**
   - 移管用からまるごとコピー

4. **`backend/` を配置**
   - `backend/.env` を除いた全ファイル・ディレクトリをコピー
   - `.env.example` が存在することを確認

5. **`frontend/` を配置**
   - `node_modules/`, `build/` を除いた全ファイル・ディレクトリをコピー

6. **`nginx/` を配置**
   - `nginx/default.conf` をコピー

7. **`dev_diary/`, `answer/` を配置**
   - 移管用からコピー

8. **`README.md` を配置**
   - 移管用で上書き

9. **`.env` のセットアップ確認**
   - `backend/.env.example` をもとに `backend/.env` を作成するよう促す（ユーザー作業）

10. **DB リストア**
   - `docker-compose up -d db` で DB コンテナのみ先行起動
   - `docker-compose exec -T db psql -U postgres learning_app < 移管用/backup_migration.sql` でリストア
   - `docker-compose exec db psql -U postgres learning_app -c "\dt"` でテーブル存在を確認

11. **起動確認（Claude）**
    - `docker-compose up -d` で全コンテナ起動
    - `docker-compose ps` で全コンテナの STATUS を確認
    - `docker-compose logs backend` で Django 起動ログを確認
    - `docker-compose logs frontend` でフロントエンド起動ログを確認

12. **起動確認（ユーザー）**
    - ブラウザでアプリにアクセスし、画面が正常に表示されることを確認

## 6. テスト計画
### 自動
- `docker-compose ps` で全コンテナが `Up` または `running` 状態であることを確認
- `docker-compose logs backend 2>&1 | grep -i error` でエラーログがないことを確認
- `docker-compose logs frontend 2>&1 | grep -i error` でエラーログがないことを確認
- `docker-compose exec db psql -U postgres learning_app -c "\dt"` でテーブルが存在することを確認

### 手動
- ブラウザでトップページ（`http://localhost` または指定ポート）にアクセスし、正常に表示されることを確認

## 7. ロールバック
- 資材配置はファイルコピーのみ（既存コードを上書きしない方針）
- 問題が発生した場合は `git checkout .` または追加ファイルを削除することで元の状態に戻せる
- コミット前であれば `git clean -fd` で未追跡ファイルを削除可能

## 8. Risk & 回避策
| リスク | 回避策 |
|--------|--------|
| `backend/.env` が誤ってコミットされる | `.gitignore` に `.env` が含まれているか事前確認。`git status` で確認後にコミット |
| `docs/` の既存ファイルが上書きされる | 移管用の `docs/` は配置しない（現リポジトリの `docs/` を維持）|
| `docker-compose up` でポート競合 | 事前に使用中のポートを確認し、競合があればユーザーに報告 |
| `backend/.env` が未設定で起動失敗 | `.env.example` の存在を確認し、設定手順をユーザーに案内 |
| DB リストア失敗（`learning_app` DB が未作成） | `init-db.sql` により DB コンテナ初回起動時に自動作成される。未作成の場合は手動で `CREATE DATABASE learning_app;` を実行 |
| `backup_migration.sql` が誤ってコミットされる | `.gitignore` に `backup_migration.sql` を追加して防止 |

## 9. 承認ポイント
- [ ] 計画内容（変更点/影響）
- [ ] Danger Ops（無）
- [ ] テスト計画

## ユーザー承認
- **承認日時**: 2026-03-20
- **承認者**: ユーザー
- **承認内容**: 計画書に問題ないと確認・承認

## 追加変更（実装中に発見・承認済み）

### 環境変数のセキュリティ改善
- **発見**: `docker-compose.yml` に `SECRET_KEY`・`DB_PASSWORD` がベタ書きされていた
- **承認**: ユーザーが即時修正を選択（2026-03-20）
- **修正内容**:
  - `docker-compose.yml` の機密値を `${変数名}` 参照に変更、`env_file` ディレクティブを追加
  - `backend/.env` を新規作成（`.gitignore` 除外済み）
  - `db` サービスの `POSTGRES_PASSWORD` も変数参照に変更

## 完了情報
- **完了日時**: 2026-03-20
- **対応者**: Claude Code
- **レビュー結果**: OK
