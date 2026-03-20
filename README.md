# 🎓 学習アプリ

React + Django + PostgreSQL で構築された学習支援Webアプリケーション

## ✨ 主な機能

### 🔐 認証・セキュリティ
- ユーザー登録・ログイン・ログアウト
- JWT トークン認証
- メール認証システム
- パスワードリセット機能
- レート制限によるセキュリティ対策

### 📚 学習機能
- 問題作成・管理（選択式）
- クイズ・テスト実行
- 学習記録の自動保存
- 学習進捗の可視化
- 間違いパターン分析

### 📊 分析・統計
- 学習時間の統計
- 正答率の推移
- 科目別分析
- ダッシュボードでの可視化

### ⚙️ ユーザー体験
- レスポンシブデザイン
- ダークモード対応
- リアルタイム通知
- アクセシビリティ対応

## 🛠 技術スタック

### フロントエンド
- **React 19** - UIライブラリ
- **TypeScript** - 型安全性
- **Material-UI** - UIコンポーネント
- **React Router** - ルーティング
- **Chart.js / Recharts** - データ可視化
- **Framer Motion** - アニメーション

### バックエンド
- **Django 4.2** - Webフレームワーク
- **Django REST Framework** - API開発
- **PostgreSQL** - データベース
- **Redis** - キャッシュ・セッション管理
- **Celery** - 非同期タスク処理

### インフラ・DevOps
- **Docker** - コンテナ化
- **Nginx** - リバースプロキシ
- **AWS** - クラウドインフラ（本番環境）

## 🚀 クイックスタート

### 前提条件
- Docker & Docker Compose
- Node.js 18+ (ローカル開発時)
- Python 3.11+ (ローカル開発時)

### 1. リポジトリクローン
```bash
git clone <repository-url>
cd 学習アプリ
```

### 2. 環境変数設定
```bash
cp .env.example .env
# .env ファイルを編集して適切な値を設定
```

### 3. Docker で起動
```bash
# 開発環境
docker-compose up -d

# 初回起動時のデータベース初期化
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
```

### 4. アクセス
- **フロントエンド**: http://localhost:3000
- **バックエンドAPI**: http://localhost:8000/api
- **管理画面**: http://localhost:8000/admin

## 📁 プロジェクト構造

```
学習アプリ/
├── docs/                    # ドキュメント
│   ├── design/             # 設計書
│   ├── requirements/       # 要件定義
│   └── images/            # 画面モック
├── frontend/               # React フロントエンド
│   ├── src/
│   │   ├── components/    # 共通コンポーネント
│   │   ├── pages/         # ページコンポーネント
│   │   ├── contexts/      # React Context
│   │   └── ...
│   └── Dockerfile
├── backend/                # Django バックエンド
│   ├── accounts/          # ユーザー管理
│   ├── learning/          # 学習機能
│   ├── quiz/              # クイズ機能
│   ├── analytics/         # 分析機能
│   ├── core/              # Django設定
│   └── Dockerfile
├── nginx/                  # Nginx設定
├── docker-compose.yml      # Docker構成
└── README.md
```

## 🔧 開発

### ローカル開発環境

#### フロントエンド
```bash
cd frontend
npm install
npm start
```

#### バックエンド
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### データベース管理
```bash
# マイグレーション作成
docker-compose exec backend python manage.py makemigrations

# マイグレーション実行
docker-compose exec backend python manage.py migrate

# スーパーユーザー作成
docker-compose exec backend python manage.py createsuperuser
```

### テスト実行
```bash
# フロントエンドテスト
cd frontend && npm test

# バックエンドテスト
docker-compose exec backend python manage.py test
```

## 📚 API ドキュメント

### 認証エンドポイント
- `POST /api/auth/login/` - ログイン
- `POST /api/auth/register/` - ユーザー登録
- `POST /api/auth/logout/` - ログアウト
- `POST /api/auth/refresh/` - トークンリフレッシュ

### ユーザー管理
- `GET /api/auth/me/` - ユーザー情報取得
- `PUT /api/settings/` - ユーザー設定更新
- `POST /api/auth/change-password/` - パスワード変更

詳細なAPI仕様は `docs/design/API仕様書.md` を参照してください。

## 🔒 セキュリティ

- JWT認証による安全なAPI アクセス
- レート制限によるブルートフォース攻撃対策
- HTTPS通信（本番環境）
- セキュリティヘッダーの適用
- 入力値の厳格なバリデーション

## 📈 デプロイ

### 本番環境（AWS）
```bash
# 本番用ビルド
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 静的ファイル収集
docker-compose exec backend python manage.py collectstatic --noinput
```

### 環境変数（本番）
本番環境では以下の環境変数を適切に設定してください：
- `SECRET_KEY` - Django秘密鍵
- `DEBUG=False`
- `ALLOWED_HOSTS` - 許可ドメイン
- `DB_*` - RDS接続情報
- `REDIS_URL` - Redis接続情報
- `SENDGRID_API_KEY` - メール送信用

## 🤝 コントリビューション

1. Forkしてください
2. Feature branchを作成してください (`git checkout -b feature/AmazingFeature`)
3. 変更をCommitしてください (`git commit -m 'Add some AmazingFeature'`)
4. BranchをPushしてください (`git push origin feature/AmazingFeature`)
5. Pull Requestを作成してください

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🆘 サポート

問題や質問がある場合は、Issueを作成してください。

---

**Happy Learning! 🎓✨**