# 学習アプリ

React + Django + PostgreSQL で構築された学習支援Webアプリケーション。

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| フロントエンド | React 19 / TypeScript / Material-UI |
| バックエンド | Django 4.2 / Django REST Framework |
| DB | PostgreSQL 15 |
| キャッシュ | Redis 7 |
| 非同期 | Celery |
| インフラ | Docker / Nginx |

---

## 初回セットアップ

### 前提条件
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) がインストール済みで起動していること

### 1. リポジトリをクローン

```bash
git clone <repository-url>
cd study-app-multitenant
```

### 2. 環境変数ファイルを作成

```bash
cp backend/.env.example backend/.env
```

> `.env` の内容はデフォルトのまま開発環境では動作します。

### 3. Dockerコンテナを起動

```bash
docker compose up -d
```

### 4. DBデータをリストア

共有された `backup_*.sql` ファイルをプロジェクトルートに置いてから実行：

```bash
bash scripts/db_restore.sh backup_YYYYMMDD_HHMMSS.sql
```

> DBファイルは Google Drive 等で別途共有されます。初回のみ必要です。

### 5. ブラウザで確認

| URL | 用途 |
|-----|------|
| http://localhost:3000 | フロントエンド |
| http://localhost:8000/api | バックエンドAPI |
| http://localhost:8000/admin | Django管理画面 |

---

## DBバックアップ・リストア

### バックアップ（別PCへ共有するとき）

```bash
bash scripts/db_backup.sh
# → backup_YYYYMMDD_HHMMSS.sql が生成される
# → Google Drive 等にアップロードして共有
```

### リストア（別PCで復元するとき）

```bash
# Google Drive 等からダウンロードしたファイルをプロジェクトルートに置いて実行
bash scripts/db_restore.sh backup_YYYYMMDD_HHMMSS.sql
```

---

## 日常の開発コマンド

```bash
# コンテナ起動
docker compose up -d

# コンテナ停止
docker compose down

# ログ確認
docker compose logs backend
docker compose logs frontend

# Djangoマイグレーション
docker compose exec backend python manage.py migrate

# スーパーユーザー作成（DBリストアなしで始める場合）
docker compose exec backend python manage.py createsuperuser
```

---

## バイブコーディング運用（Claude Code）

このリポジトリでは Claude Code を使ってバイブコーディングで開発を進めています。

```
/issue-bootstrap [タイトル]  # イシュー作成・ブランチ作成
/plan-issue I###             # 計画書作成（承認待ち）
/implement I###              # 実装・テスト
/fix-loop I###               # NG時の修正ループ
/close I###                  # クローズ処理・PR整備
```

詳細ルール: `docs/runbooks/` を参照
