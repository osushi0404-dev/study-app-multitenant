# よく使うコマンド

## エラー調査手順
エラーが発生したら以下のコマンドを実行してClaude Codeに情報を渡す：
```bash
# 直近のエラーを操作履歴付きで確認
python manage.py analyze_logs --last-errors=1
```

## よく使用するコマンド

### 開発環境起動
```bash
docker-compose up -d
```

### ログ確認
```bash
tail -f backend/logs/django.log
```

### フロントエンド・バックエンド再起動
```bash
docker-compose restart frontend backend
```

### テスト実行
```bash
# バックエンドテスト
docker-compose exec backend python manage.py test

# フロントエンドテスト
docker-compose exec frontend npm test
```

## API エンドポイント
- ユーザー登録: `POST /api/auth/register/`
- ユーザー設定: `GET/PATCH /api/settings/`
- 学習ストリーク: `GET /api/streak/`

## ディレクトリ構造
```
backend/        - Django REST API
frontend/       - React TypeScript
docs/          - ドキュメント
nginx/         - Nginx設定
```

## 注意事項
- 開発環境ではメール送信をスキップ
- ログファイル: `backend/logs/django.log`
- フロントエンドのURL変更時はキャッシュクリア必要

## webpack キャッシュトラブル対処

### 症状
新規 `.ts`/`.tsx` ファイル追加後に `TS2307: Cannot find module '...'` が発生する。

### 恒久対処（I024 実装済み）
コンテナ起動時に自動でキャッシュクリアされます。`docker-compose restart frontend` で解消します。

### 手動回避（緊急時）
```bash
docker-compose exec frontend rm -rf /app/node_modules/.cache
docker-compose restart frontend
```

## 修正済みの問題（履歴）
1. psutil依存関係エラー - try-catchで処理済み
2. Redis HiredisParserエラー - PARSER_CLASS削除で解決
3. IntegrityErrorエラー - get_or_create使用で解決
4. FRONTEND_URL設定不足 - settings.py追加済み
5. SMTPエラー - 開発環境でスキップ設定
6. 404エラー - フロントエンドURL修正済み
