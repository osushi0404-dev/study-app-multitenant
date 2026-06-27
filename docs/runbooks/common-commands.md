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
docker compose up -d
```

### ログ確認
```bash
tail -f backend/logs/django.log
```

### フロントエンド・バックエンド再起動
```bash
docker compose restart frontend backend
```

### テスト実行
```bash
# バックエンドテスト
docker compose exec backend python manage.py test

# フロントエンドテスト
docker compose exec frontend npm test
```

## シェルスクリプトのロジック検証

シェルスクリプトのロジック（`grep`/`sed`/`awk` の regex 挙動に依存する関数等）を検証するときは、対象を **スクリプトファイルとして `bash` で実行**する:

```bash
bash scripts/claude/tests/test_review_verdict.sh   # 例: 検証スクリプトを bash で実行
```

> **なぜ重要か**: Claude Code の対話シェルでは `grep` 等が同梱ラッパー（`ugrep`）に置換されており、`-E`/`-o` などの挙動が実 GNU grep と異なる場合がある。対話シェルへ直接コマンドを貼り付けて検証すると偽の失敗・誤判定を招く。`bash <script>` のサブプロセスや CI では実 GNU grep が使われるため、検証は必ずスクリプト実行で行う（どうしても対話シェルで実 grep が必要な場合は `/usr/bin/grep` をフルパス指定する）。実スクリプト自体（`bash foo.sh`）の本番挙動は実 grep のため影響はなく、これは**検証手順だけの注意点**。

## Bash 実行作法（allowlist 単体コマンド）

Bash は `.claude/settings.json` の allow に定義された**単体コマンド**の形で実行する。複合化すると、コマンド全体がどの単一 allow にも一致せず、より広い `ask` に落ちて毎回プロンプト（承諾要求）になる。

- **束ねない**: `|` / `;` / `&&` / `2>&1 | tail` / inline heredoc（`<<EOF`）で複数コマンドをつなげない。1 コマンド＝1 実行にする。
- **終了コードは出力で判断**する。`; echo "exit=$?"` のような確認用の継ぎ足しを付けない（それ自体が複合化でプロンプトを誘発する）。
- **ファイル閲覧は Read ツール**を使う。`sed` / `cat` / `head` でまとめ読みしない（複合コマンドに未許可コマンドが混ざると、閲覧まで承諾対象になる）。
- **原則であり完全禁止ではない**: 検証目的で複合/パイプが本質的に必要な場合のみ許容する。その際はプロンプトが出ることを受容する（例外は明示的に）。

> **未コミット変更の取り消し**: 作業ツリーに未コミット変更があるファイルの一時変更を取り消すとき、`git checkout/restore <file>` を使わない（未コミット分も消える）。詳細は `danger-ops.md` を参照。

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

## モデル変更時の必須手順（migration drift 防止）

`backend/*/models.py` を変更した場合は **必ず** 以下を実行してコミットする。

```bash
# マイグレーションファイルを生成
docker compose exec backend python manage.py makemigrations

# 生成されたファイルを確認してからコミット
git add backend/*/migrations/
git commit -m "feat: add migration for <変更内容>"
```

### 確認コマンド（drift チェック）

```bash
# 乖離がなければ "No changes detected"（exit 0）
# 乖離があれば生成予定の migration 内容が表示される（exit 1）
docker compose exec backend python manage.py makemigrations --check --dry-run
```

> **なぜ重要か**: migration を書き忘れると、fresh DB（CI・新規デプロイ）では NOT NULL 違反などの
> IntegrityError が発生してアプリが壊れる。既存 DB では実データが入っているため発現せず、
> CI でのみ発覚する性質の問題になる（I049 の `total_points` / `points_earned` が同ケース）。
> CI の backend-lint ジョブでも `makemigrations --check` を実行するが、
> PR を出す前にローカルで確認することを推奨する。

## ローカル E2E テスト実行手順（初回セットアップ）

### 1. `.env.e2e` を作成する（初回のみ）

```bash
cp e2e/.env.e2e.example e2e/.env.e2e
# e2e/.env.e2e を開いて E2E_TEST_PASSWORD に任意のパスワードを設定する
```

> **注意**: `.env.e2e` は `.gitignore` に含まれています。コミットしないでください。

### 2. バックエンドを Rate Limiting 無効で起動する（毎回）

webpack proxy 導入後は、すべての E2E リクエストが frontend コンテナの IP からバックエンドに転送される。
この IP 集約により rate limiting のカウントが累積し、ログイン失敗テストなどが影響を受けるため、
E2E 実行前に rate limiting を無効にしてバックエンドを起動する（CI と同じ設定）:

```bash
RATELIMIT_ENABLE=false docker compose up -d backend
```

> **本番・通常開発**: `RATELIMIT_ENABLE` を設定せずに `docker compose up -d` すれば rate limiting は有効のまま動作する。

### 3. E2E テストを実行する

```bash
# e2e-init は前回の実行結果が残っているため毎回削除してから実行する
docker compose rm -f e2e-init
docker compose --profile e2e run --rm e2e
```

> **なぜ `rm -f e2e-init` が必要か**: `docker compose run --rm` は対象サービス（e2e）のみを削除する。
> `e2e-init`（シードコンテナ）は残存し、次回実行時に「完了済み」と判断されてスキップされる。
> 削除せずに実行すると、古いパスワードでシードされたままテストが実行されログインが失敗する。

### 4. パスワードを変更したい場合

```bash
# .env.e2e のパスワードを変更してから再実行
docker compose rm -f e2e-init
docker compose --profile e2e run --rm e2e
# seed_e2e は既存ユーザーを削除して再作成するため自動的に新パスワードが反映される
```

## webpack キャッシュトラブル対処

### 症状
新規 `.ts`/`.tsx` ファイル追加後に `TS2307: Cannot find module '...'` が発生する。

### 恒久対処（I024 実装済み）
コンテナ起動時に自動でキャッシュクリアされます。`docker compose restart frontend` で解消します。

### 手動回避（緊急時）
```bash
docker compose exec frontend rm -rf /app/node_modules/.cache
docker compose restart frontend
```

## 修正済みの問題（履歴）
1. psutil依存関係エラー - try-catchで処理済み
2. Redis HiredisParserエラー - PARSER_CLASS削除で解決
3. IntegrityErrorエラー - get_or_create使用で解決
4. FRONTEND_URL設定不足 - settings.py追加済み
5. SMTPエラー - 開発環境でスキップ設定
6. 404エラー - フロントエンドURL修正済み
