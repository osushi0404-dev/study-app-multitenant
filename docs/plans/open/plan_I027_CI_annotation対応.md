# plan_I027_CI_annotation対応

## 基本情報
- **計画書ID**: plan_I027_CI_annotation対応
- **関連イシュー**: I027 / #56
- **作成根拠資料**: docs/issues/open/I027.md
- **実装後評価**: （未作成）
- **作成日**: 2026-04-06

---

## 1. 背景/目的

CI の flake8 / ESLint 失敗は現状ログ上にのみ出力され、修正箇所の特定にログの掘り下げが必要。
GitHub Actions の annotation 機能を使い、PR の Files changed 上にファイル・行番号付きで表示することで Claude Code の修正ループを短縮する。

---

## 2. 調査結果

| 項目 | 結果 |
|---|---|
| Backend テスト | Docker 内で動作するためローカル実行不可。CI では pass 前提 |
| Frontend テスト | 7 passed, 2 suites ✅ |
| flake8 エラー件数 | 0件（クリーン） |
| ESLint 問題件数 | 12 problems（すべて warning。CI は現状 pass） |

**ESLint 12 warnings について**: annotation 導入後、これらが PR の Files changed 上に表示されるようになる。新規に発生するものではなく、既存問題の可視化であり CI の pass/fail には影響しない。

---

## 3. 受け入れ条件

- [ ] flake8 の違反が PR の Files changed 上にファイル・行番号付きで表示される
- [ ] ESLint の違反が PR の Files changed 上にファイル・行番号付きで表示される
- [ ] 既存の CI ジョブ（backend-lint / frontend-lint）が引き続き pass する

---

## 4. 影響範囲

- Backend: なし（`requirements-dev.txt` 変更不要）
- Frontend: `frontend/package.json`（devDependencies 追加）、`frontend/package-lock.json`
- DB: なし
- Config/Infra: `.github/workflows/ci.yml`

---

## 5. 変更点一覧と修正アプローチ

### 5-1. flake8 annotation 対応

**修正アプローチ**: `flake8` の `--format` オプションで GitHub Actions annotation コマンド形式を直接指定する。新パッケージ不要。

flake8 の `--format` は Python `%` 形式のフォーマット文字列を受け付ける。GitHub Actions の annotation コマンド（`::error file=...,line=...,col=...::message`）を直接出力させることで、CI ログではなく PR の Files changed 上に violation が表示される。

**変更ファイル**: `.github/workflows/ci.yml`

```yaml
# 変更前
- name: flake8
  run: flake8 .
  working-directory: backend

# 変更後
- name: flake8
  run: flake8 . --format='::error file=%(path)s,line=%(row)d,col=%(col)d::%(code)s %(text)s'
  working-directory: backend
```

---

### 5-2. ESLint annotation 対応

**修正アプローチ**: `eslint-formatter-github` パッケージを devDependencies に追加し、ESLint の `-f` オプションで指定する。ESLint は `-f <name>` で `eslint-formatter-<name>` をフォーマッタとして使用する仕様。

**変更ファイル 1**: `frontend/package.json`

devDependencies に追加:
```json
"eslint-formatter-github": "^1.0.0"
```

**変更ファイル 2**: `.github/workflows/ci.yml`

```yaml
# 変更前
- name: ESLint
  run: npx eslint src/ --ext .ts,.tsx
  working-directory: frontend

# 変更後
- name: ESLint
  run: npx eslint src/ --ext .ts,.tsx -f github
  working-directory: frontend
```

CI 上では `npm ci` でインストール済みになるため、追加の install ステップは不要。

---

## 6. 実装手順

1. `.github/workflows/ci.yml` の `backend-lint` ジョブの flake8 コマンドを修正
2. `frontend/package.json` の devDependencies に `eslint-formatter-github` を追加
3. `frontend/package-lock.json` を更新（`npm install` 実行）
4. `.github/workflows/ci.yml` の `frontend-lint` ジョブの ESLint コマンドを修正
5. push → CI が pass することを確認
6. PR 上で annotation が表示されることを確認（手動テスト）

---

## 7. テスト計画

→ `docs/tests/open/I027_auto_test.md` / `docs/tests/open/I027_manual_test.md` 参照

---

## 8. ロールバック

- `.github/workflows/ci.yml` を変更前のコマンドに戻す（git revert または手動修正）
- `frontend/package.json` から `eslint-formatter-github` を削除、`npm install` 実行

---

## 9. Risk & 回避策

| リスク | 回避策 |
|---|---|
| flake8 の `--format` で annotation が正しく出力されない | CI ログで確認。NG なら `flake8-github-annotations` パッケージに切り替え |
| `eslint-formatter-github` の最新バージョンで動作しない | CI ログで確認。NG なら SARIF 方式（`@microsoft/eslint-formatter-sarif` + upload-sarif）に切り替え |
| 既存 ESLint 12 warnings が annotation として表示される | 仕様通りの挙動。既存問題の可視化であり CI pass/fail には影響しない |

---

## 10. セキュリティチェック

バックエンド・フロントエンドのアプリケーションコードの変更なし。CI 設定とパッケージ追加のみ。
追加する `eslint-formatter-github` はフォーマッタ専用パッケージでアプリへの影響なし。

**セキュリティ影響なし**

---

## 11. 承認ポイント

### 設計判断の区別

| 判断項目 | 根拠 |
|---|---|
| flake8 に `--format` フラグを使用（パッケージ不要） | イシューでは `flake8-github-annotations` を明記していたが、依存追加不要な方が優位として提案・承認済み |
| ESLint に `eslint-formatter-github` を使用 | イシューに明記 |
| SARIF 方式は採用しない | PR annotation が目的であり、セキュリティスキャン用途の SARIF はスコープ外として提案・承認済み |

### チェックリスト

- [ ] flake8: `--format` フラグ方式（新パッケージなし）で進める
- [ ] ESLint: `eslint-formatter-github` パッケージを追加して進める
- [ ] 既存 ESLint 12 warnings が annotation 表示されることを許容する
- [ ] `backend/requirements-dev.txt` は変更しない
- [ ] ロールバック方法を把握している
