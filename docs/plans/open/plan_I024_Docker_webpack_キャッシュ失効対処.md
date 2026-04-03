# 計画書: Docker 開発環境 webpack キャッシュ失効対処

## 基本情報
- **計画書ID**: plan_I024_Docker_webpack_キャッシュ失効対処
- **関連イシュー**: I024
- **作成根拠資料**: docs/issues/open/I024.md
- **実装後評価**: （未作成）
- **作成日**: 2026-04-03

---

## 1. 背景/目的

Docker 開発環境（`docker-compose up frontend`）で新規 `.ts`/`.tsx` ファイルを追加した際、コンテナ内の webpack 5 persistent cache（`node_modules/.cache/default-development/`）が失効せず、`TS2307: Cannot find module` エラーが発生する。

現状の回避策は手動での `docker-compose exec frontend rm -rf /app/node_modules/.cache` + restart であり、開発体験を損ねている。

コンテナ起動時にキャッシュを自動クリアし、かつ Windows/WSL 環境での新規ファイル検知ポーリングを完備することで恒久対処する。

---

## 2. 受け入れ条件

- [ ] コンテナ起動時に `node_modules/.cache` が自動クリアされ、手動操作が不要になること
- [ ] `docker-compose up` / `docker-compose restart frontend` で TS2307 エラーが再現しないこと
- [ ] `docker-compose stop` / `Ctrl+C` でコンテナが graceful shutdown できること（シグナル伝播の確認）
- [ ] `docs/runbooks/common-commands.md` に暫定回避手順が記載されていること

---

## 3. 影響範囲

| 層 | 変更有無 | 対象 |
|----|---------|------|
| Backend | なし | — |
| Frontend | あり | `Dockerfile.dev`、新規 `docker-entrypoint.sh` |
| DB | なし | — |
| Config/Infra | あり | `docker-compose.yml`（frontend サービスの environment） |
| Docs | あり | `docs/runbooks/common-commands.md` |

---

## 4. 調査結果

### 根本原因の概要

webpack 5 はビルドの高速化のために TypeScript コンパイル結果を `node_modules/.cache/default-development/` に永続キャッシュする。`docker-compose.yml` の `volumes` 設定で `node_modules` は anonymous volume として永続化されているため、コンテナを再起動してもキャッシュが残り続ける。新規ファイルはキャッシュ作成時点では存在しなかったため、コンテナ再起動後も「存在しないファイル」として扱われ TS2307 が発生する。

### 詳細な原因分析

1. `docker-compose.yml` の volumes:
   ```yaml
   volumes:
     - ./frontend:/app
     - /app/node_modules   # ← anonymous volume で永続化
   ```
   `node_modules/.cache` もこの anonymous volume に含まれるため、コンテナ停止・起動をまたいで保持される。

2. `Dockerfile.dev` の CMD は `npm start` のみ。キャッシュクリア処理なし。

3. `CHOKIDAR_USEPOLLING=true` は既設定だが、これは webpack dev server の HMR 用であり、webpack 5 の watchpack（ビルドトリガー用ファイル監視）は別の env `WATCHPACK_POLLING` で制御される。Windows/WSL では inotify が Docker コンテナに届かないため、`WATCHPACK_POLLING=true` がないと新規ファイルの変更検知が不完全になる。

### 既存ファイルの状態

| ファイル | 現状 |
|---------|------|
| `frontend/Dockerfile.dev` | `CMD ["npm", "start"]` のみ。キャッシュクリアなし |
| `docker-compose.yml` | `CHOKIDAR_USEPOLLING=true` のみ。`WATCHPACK_POLLING` なし |
| `frontend/docker-entrypoint.sh` | 存在しない |

---

## 5. 修正対象と具体的変更内容

### 修正アプローチ

コンテナ起動時に必ずキャッシュをクリアする entrypoint スクリプトを導入し（案B）、`WATCHPACK_POLLING=true` を追加することで Windows/WSL のファイル監視を完備する。entrypoint スクリプトで `exec npm start` を使うことで、`npm` プロセスが PID 1 相当として動作し SIGTERM が正しく伝播する（graceful shutdown）。

### 変更項目1: `frontend/docker-entrypoint.sh`（新規作成）

**修正方針**: コンテナ起動のたびに `node_modules/.cache` を削除してから `npm start` を起動する。`exec` により npm プロセスがシグナルを直接受け取る。

```sh
#!/bin/sh
set -e

echo "[entrypoint] Clearing webpack/TypeScript cache..."
rm -rf /app/node_modules/.cache

echo "[entrypoint] Starting development server..."
exec npm start
```

### 変更項目2: `frontend/Dockerfile.dev`

**修正方針**: entrypoint スクリプトをコピーして実行権限を付与し、`CMD` を entrypoint スクリプト経由に変更する。

変更前:
```dockerfile
CMD ["npm", "start"]
```

変更後:
```dockerfile
# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Start via entrypoint (clears webpack cache on every start)
CMD ["/usr/local/bin/docker-entrypoint.sh"]
```

### 変更項目3: `docker-compose.yml`（frontend サービスの environment）

**修正方針**: `WATCHPACK_POLLING=true` を追加し、webpack 5 のファイル変更監視もポーリングモードにする。Windows/WSL 環境では `CHOKIDAR_USEPOLLING` と `WATCHPACK_POLLING` の両方が必要。

変更前:
```yaml
environment:
  - REACT_APP_API_URL=http://localhost:8000/api
  - CHOKIDAR_USEPOLLING=true
```

変更後:
```yaml
environment:
  - REACT_APP_API_URL=http://localhost:8000/api
  - CHOKIDAR_USEPOLLING=true
  - WATCHPACK_POLLING=true
```

### 変更項目4: `docs/runbooks/common-commands.md`

**修正方針**: 根本対処が完了するまで（および完了後も緊急時の参考として）手動キャッシュクリア手順を記載する。

追記内容（「注意事項」セクション内または末尾に追加）:
```markdown
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
```

---

## 6. 実装手順

1. `frontend/docker-entrypoint.sh` を新規作成
2. `frontend/Dockerfile.dev` に COPY・chmod・CMD 変更を追加
3. `docker-compose.yml` に `WATCHPACK_POLLING=true` を追加
4. `docs/runbooks/common-commands.md` に手順を追記
5. `docker-compose build frontend` でイメージを再ビルド（ローカル確認用コマンド記載のみ、実行は手動テストで）

---

## 7. テスト計画

| # | テスト内容 | 種別 |
|---|-----------|------|
| 1 | `docker-compose up frontend` 起動ログに `Clearing webpack/TypeScript cache...` が出力される | 手動 |
| 2 | 新規 `.ts` ファイルをホストに追加 → `docker-compose restart frontend` → TS2307 が出ない | 手動 |
| 3 | `docker-compose stop` で graceful shutdown（"Graceful shutdown" ログ or 正常終了） | 手動 |
| 4 | `common-commands.md` に手順が記載されていること | 手動 |

---

## 8. ロールバック

- `frontend/Dockerfile.dev` の CMD を `["npm", "start"]` に戻す
- `docker-compose.yml` から `WATCHPACK_POLLING=true` を削除
- `frontend/docker-entrypoint.sh` を削除
- `docker-compose build frontend` で再ビルド

---

## 9. Risk & 回避策

| リスク | 影響 | 回避策 |
|--------|------|--------|
| キャッシュ削除により起動時間が増加する | 低（開発環境のみ） | 許容範囲。初回コンパイルは毎回発生するが数秒～数十秒程度 |
| `docker-entrypoint.sh` の LF/CRLF 問題（Windows） | スクリプトが実行できない | `.gitattributes` に `*.sh text eol=lf` が設定されているか確認。なければ追加 |
| `WATCHPACK_POLLING=true` により CPU 使用率が上昇 | 低 | 開発環境のみの設定のため許容範囲 |

---

## 10. セキュリティチェック

- バックエンドのコード変更なし
- フロントエンドのアプリケーションコード変更なし（Docker/設定ファイルのみ）
- 新規依存ライブラリの追加なし
- **セキュリティ影響なし**

---

## 11. 承認ポイント

### セキュリティ
- [x] セキュリティ影響なし（Docker 設定・docs のみ変更）

### 設計判断

| 項目 | 決定内容 | 根拠 |
|------|---------|------|
| キャッシュクリア実装方法 | entrypoint スクリプト（案B） | イシューに「エントリポイントスクリプト」と例示あり、かつ `exec` によるシグナル伝播がベストプラクティス |
| `WATCHPACK_POLLING=true` の追加 | 追加する | `CHOKIDAR_USEPOLLING` と対になる設定。Windows/WSL での新規ファイル検知に必要。ユーザー確認済み |
| スクリプト配置場所 | `/usr/local/bin/` | Docker の慣例（PATH 上に配置） |

### 実装確認チェックリスト
- [ ] 新規ファイル: `frontend/docker-entrypoint.sh`
- [ ] 変更ファイル: `frontend/Dockerfile.dev`
- [ ] 変更ファイル: `docker-compose.yml`（frontend environment）
- [ ] 変更ファイル: `docs/runbooks/common-commands.md`
- [ ] `.gitattributes` に `*.sh text eol=lf` の有無を確認（なければ追加）
