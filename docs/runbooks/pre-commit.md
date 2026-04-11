# pre-commit 運用手順

## 概要

このリポジトリでは `pre-commit` を使って `git commit` 時にシークレット検出・基本的なコード品質チェックを自動実行します。

## セットアップ（初回のみ）

### 1. pipx のインストール

```bash
sudo apt-get install pipx
```

### 2. pre-commit・detect-secrets のインストール

```bash
pipx install pre-commit
pipx install detect-secrets
```

### 3. git hooks への登録

リポジトリルートで実行します。

```bash
pre-commit install
```

`.git/hooks/pre-commit` が作成され、以降の `git commit` 時に自動でフックが走ります。

---

## フック一覧

| フック | 役割 |
|--------|------|
| `detect-secrets` | シークレット（APIキー・パスワード等）のハードコードを検出 |
| `check-yaml` | YAML ファイルの構文チェック |
| `end-of-file-fixer` | ファイル末尾の改行を統一 |
| `trailing-whitespace` | 行末の空白を除去 |
| `check-added-large-files` | 大きなファイルの誤コミットを防止 |
| `check-merge-conflict` | マージコンフリクトマーカーの残留を検出 |

---

## 日常的な使い方

### コミット時（自動）

`git commit` を実行すると全フックが自動で走ります。フックが失敗した場合はコミットがブロックされます。

### 全ファイルへの手動実行

```bash
pre-commit run --all-files
```

---

## detect-secrets の誤検知への対処

テスト用ダミー値やドキュメント内の例示文字列が誤検知された場合は、`.secrets.baseline` を更新して除外します。

### 方法1: audit コマンドで対話的に処理

```bash
detect-secrets audit .secrets.baseline
# y = 本物のシークレット（true positive）
# n = 誤検知（false positive）→ baseline から除外
# s = スキップ（後で判断）
```

処理後、`.secrets.baseline` をコミットします。

```bash
git add .secrets.baseline
git commit -m "docs: update secrets baseline (false positive)"
```

### 方法2: インラインで特定行を無視

誤検知が発生している行に `# pragma: allowlist secret` を追加します。

```python
dummy_password = "example_only"  # pragma: allowlist secret
```

---

## `.secrets.baseline` の更新（新しいシークレット検知パターン追加時）

detect-secrets のバージョンアップや設定変更後は baseline を再生成します。

```bash
detect-secrets scan > .secrets.baseline
detect-secrets audit .secrets.baseline  # 誤検知を除外
git add .secrets.baseline
git commit -m "docs: regenerate secrets baseline"
```

---

## ロールバック

```bash
pre-commit uninstall
git rm .pre-commit-config.yaml .secrets.baseline
git commit -m "revert: remove pre-commit hooks"
```
