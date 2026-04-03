# I024 手動テスト手順

## 対象計画書
`docs/plans/open/plan_I024_Docker_webpack_キャッシュ失効対処.md`

## 前提条件
- Docker Desktop（または Docker Engine）が起動していること
- `docker-compose build frontend` でイメージが再ビルド済みであること

---

## テストケース

### MT-01: entrypoint のキャッシュクリアログ確認

**目的**: コンテナ起動時に `node_modules/.cache` が自動削除されることを確認する

**手順**:
1. `docker-compose up frontend` を実行する
2. コンテナ起動ログを確認する

**期待結果**:
```
[entrypoint] Clearing webpack/TypeScript cache...
[entrypoint] Starting development server...
```
が表示される

**合否**: Pass / Fail

---

### MT-02: 新規ファイル追加後の TS2307 非発生確認

**目的**: コンテナ再起動後に新規ファイルが正しく認識されることを確認する

**手順**:
1. `docker-compose up frontend` でコンテナを起動する
2. ホスト側で `frontend/src/test_new_file.ts` を新規作成する（内容は `export const dummy = 1;` 等）
3. `docker-compose restart frontend` を実行する
4. 別のファイルから `import { dummy } from './test_new_file'` を追加してコンパイルが通るか確認する
5. テスト完了後、`test_new_file.ts` と import 追記を元に戻す

**期待結果**:
- TS2307 エラーが発生しない
- コンパイルが正常に完了する

**合否**: Pass / Fail

---

### MT-03: Graceful Shutdown 確認

**目的**: `exec npm start` によりシグナルが正しく伝播し、graceful shutdown できることを確認する

**手順**:
1. `docker-compose up frontend` でコンテナを起動する
2. `docker-compose stop frontend` または `Ctrl+C` で停止する
3. 停止ログを確認する

**期待結果**:
- コンテナが短時間（10秒以内）で正常終了する
- `docker ps` に frontend コンテナが残っていない

**合否**: Pass / Fail

---

### MT-04: common-commands.md の記載確認

**目的**: ドキュメントに手動回避手順が記載されていることを確認する

**手順**:
1. `docs/runbooks/common-commands.md` を開く
2. 「webpack キャッシュトラブル対処」セクションを確認する

**期待結果**:
- 症状の説明がある
- 手動回避コマンド（`rm -rf /app/node_modules/.cache` + `restart`）が記載されている

**合否**: Pass / Fail

---

## テスト結果記録

| テストID | 結果 | 実施日 | 備考 |
|---------|------|--------|------|
| MT-01 | — | — | — |
| MT-02 | — | — | — |
| MT-03 | — | — | — |
| MT-04 | — | — | — |
