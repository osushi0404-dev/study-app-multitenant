# 計画書: I051 — e2e/.env.e2e.example を作成してローカル E2E セットアップを簡略化する

## 基本情報
- **計画書ID**: plan_I051
- **関連イシュー**: #105
- **作成根拠資料**: I049 振り返り（是正処置 #1）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-24

---

## 1. 背景/目的

I049 で E2E テスト基盤を導入したが、`e2e/.env.e2e` は `.gitignore` 対象のためリポジトリにコミットできない。
初回セットアップ時にどの環境変数が必要かが不明瞭で、設定漏れによるテスト失敗が起きた。
`e2e/.env.e2e.example`（テンプレートファイル）をリポジトリに含めることで必要な環境変数を明示し、セットアップ手順を簡略化する。

---

## 2. 受け入れ条件

- [ ] `e2e/.env.e2e.example` がリポジトリに存在し、`E2E_TEST_PASSWORD=` の行を含む
- [ ] `e2e/.env.e2e.example` に実際のパスワードが含まれていない（プレースホルダーのみ）
- [ ] `docs/runbooks/common-commands.md` の `cp e2e/.env.e2e.example e2e/.env.e2e` コマンドが `e2e/.env.e2e.example` の存在を前提にしており、コマンドが正常動作する

---

## 3. 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `e2e/.env.e2e.example`（新規ファイル）、`docs/runbooks/common-commands.md`（確認のみ・変更不要）

---

## 4. 変更点一覧

| # | ファイル | 種別 | 内容 |
|---|---------|------|------|
| 1 | `e2e/.env.e2e.example` | 新規作成 | `E2E_TEST_PASSWORD=` と `BASE_URL=` のプレースホルダーを含むテンプレート |
| 2 | `docs/runbooks/common-commands.md` | 確認のみ | `cp e2e/.env.e2e.example e2e/.env.e2e` コマンドが既に存在することを確認（変更不要） |

### 調査結果

- `docs/runbooks/common-commands.md:86` に `cp e2e/.env.e2e.example e2e/.env.e2e` コマンドが既に存在する → 変更不要
- `e2e/global-setup.ts:14-18` のエラーメッセージが既に `.env.e2e.example` を参照している
- 必要な環境変数:
  - `E2E_TEST_PASSWORD`: 必須（未設定時は `global-setup.ts` がエラーをスロー）
  - `BASE_URL`: オプション（デフォルト値 `http://localhost:3000` が `playwright.config.ts:6` と `global-setup.ts:5` に設定済み）

---

## 5. 実装手順

### ステップ1（唯一のステップ）: `e2e/.env.e2e.example` を作成する

`e2e/.env.e2e.example` を以下の内容で新規作成する。

```dotenv
# E2E テスト用環境変数テンプレート
# このファイルを e2e/.env.e2e にコピーしてから値を設定してください:
#   cp e2e/.env.e2e.example e2e/.env.e2e

# E2E テストユーザーのパスワード（必須）
# 任意の文字列を設定してください
E2E_TEST_PASSWORD=

# テスト対象のベース URL（省略可）
# デフォルト: http://localhost:3000
# BASE_URL=http://localhost:3000
```

**方針**:
- `E2E_TEST_PASSWORD=` は値なしで記載（プレースホルダー）
- `BASE_URL=` はコメントアウトして任意設定であることを示す（デフォルト値があるため）
- コピー手順のコメントを冒頭に記載してセルフドキュメント化する

---

## 6. テスト計画

| 種別 | 内容 |
|------|------|
| 自動テスト | なし（設定ファイルの追加のみ） |
| 手動テスト | ファイル内容の目視確認（Claude 実施可） |

詳細は `docs/tests/open/I051_manual_test.md` を参照。

---

## 7. ロールバック

`e2e/.env.e2e.example` を削除するだけで元に戻る。`common-commands.md` は変更しないため影響なし。

```bash
git rm e2e/.env.e2e.example
git commit -m "revert: remove e2e/.env.e2e.example"
```

---

## 8. Risk & 回避策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| `.env.e2e.example` に実パスワードを誤記入 | 高（シークレット漏洩） | プレースホルダーのみ記載・CI の secret scan（pre-commit の Detect secrets フックが検知） |
| `common-commands.md` のコマンドが将来のファイル名変更で乖離 | 低 | ファイル名は変更しない方針 |

セキュリティ影響: プレースホルダーのみのテンプレートファイルのため、機密情報の漏洩リスクはない。

---

## 9. 承認ポイント

- [ ] `e2e/.env.e2e.example` の内容（変数・コメント構成）が適切か
- [ ] `BASE_URL` をコメントアウトで含める方針でよいか（必須でないためオプション扱い）
- [ ] `docs/runbooks/common-commands.md` は変更不要という判断でよいか（既にコマンドが存在）

**セキュリティ影響なし**（バックエンド・フロントエンドのコード変更なし、プレースホルダーのみのテンプレート）

**P3/P5/P8 影響なし**（DB変更なし・外部API・バッチなし・新規インフラリソースなし）

**P6 影響なし**（UIなし・データ量や外部API懸念なし）

---

## セキュリティレビュー結果

**実施日**: 2026-04-24

### セキュリティ設計レビュー

変更内容: `e2e/.env.e2e.example`（新規ファイル）のみ。バックエンド・フロントエンド・DBのコード変更なし。

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Low | 機密情報 | `.env.e2e.example` に実パスワードを誤記入してコミットするリスク | `E2E_TEST_PASSWORD=`（値なし）のみ記載。pre-commit の Detect secrets フックが検知するため二重防御済み |

### 攻撃シナリオレビュー

攻撃シナリオなし（コード変更なし）

### 残余リスク処遇
（/retro で決定する）
