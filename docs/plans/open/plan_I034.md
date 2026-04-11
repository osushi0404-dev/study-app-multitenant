# I034 計画書: pre-commit hooks の導入（シークレット検出・コード品質チェック）

## 基本情報
- **計画書ID**: plan_I034
- **関連イシュー**: #78
- **作成根拠資料**: docs/proposals/I026_ai_dev_improvement_proposal.md（改善案 A）/ I029 計画策定時判断
- **実装後評価**: （未作成）
- **作成日**: 2026-04-11

---

## 1. 背景/目的
- I029 計画策定時に「シークレット検出は PostToolUse ではなく git commit 時の pre-commit hooks が業界標準」と判断した
- 現状、コード内へのシークレットハードコードを防ぐ仕組みがない（`.env` の deny はあるが、コード内の直書きは防げていない）
- `pre-commit` フレームワークを導入し、`git commit` 時に自動でシークレット検出・基本的な品質チェックを実行する

---

## 2. 受け入れ条件
- [ ] `.pre-commit-config.yaml` が作成されている
- [ ] `git commit` 時に `detect-secrets` が自動で走る
- [ ] シークレットを含むファイルをコミットしようとするとブロックされる
- [ ] `.secrets.baseline` が生成されており、既存の誤検知が除外されている
- [ ] pre-commit のインストール・初期設定手順が runbook に記載されている

---

## 3. 影響範囲
- Backend: なし（コード変更なし）
- Frontend: なし（コード変更なし）
- DB: なし
- Config/Infra:
  - `.pre-commit-config.yaml`（新規）
  - `.secrets.baseline`（新規）
  - `docs/runbooks/pre-commit.md`（新規）

---

## 4. 変更点一覧

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `.pre-commit-config.yaml` | 新規 | pre-commit フック設定（detect-secrets + 基本チェック） |
| `.secrets.baseline` | 新規 | detect-secrets 初期ベースライン |
| `docs/runbooks/pre-commit.md` | 新規 | インストール・運用手順 |

---

## 5. 実装手順

### ステップ 1: pre-commit・detect-secrets のインストール（ホスト側・pipx 経由）

git hooks はホスト側で動作するため、ホストマシン（WSL2）にインストールする。
**公式推奨方式**: `pipx` を使い、各 CLI ツールを隔離された仮想環境に入れる（システム Python を汚染しない）。

| ツール | 役割 | pipx での管理 |
|--------|------|-------------|
| `pre-commit` | git commit 時のフック実行 | フック実行時は pre-commit が自動で detect-secrets 仮想環境を管理 |
| `detect-secrets` | `.secrets.baseline` の初期生成・audit | baseline 生成専用。フック実行時とは独立した pipx 管理環境 |

```bash
# pipx をシステムパッケージとしてインストール
sudo apt-get install pipx

# pipx 経由で両ツールをインストール
pipx install pre-commit
pipx install detect-secrets
```

### ステップ 2: `.pre-commit-config.yaml` の作成

リポジトリルートに以下の内容で作成する。

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: check-yaml
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: package-lock\.json
```

**フック選定理由（イシュー明記済み）**:
- `check-yaml`: YAML ファイルの構文チェック
- `end-of-file-fixer`: ファイル末尾の改行を統一
- `trailing-whitespace`: 行末空白を除去
- `check-added-large-files`: 大きなファイルの誤コミット防止
- `check-merge-conflict`: マージコンフリクトマーカーの検出
- `detect-secrets`: シークレット検出（イシュー主目的）

### ステップ 3: `.secrets.baseline` の初期生成

ホストにインストールした `detect-secrets`（pipx 管理）でリポジトリ全体をスキャンする。
ホストで実行することで `frontend/`・`.github/`・`nginx/` 等、すべてのディレクトリが確実にスキャン対象となる。

```bash
# リポジトリルートで実行
detect-secrets scan > .secrets.baseline
```

生成後、誤検知（テスト用ダミー値・ドキュメント内の例示文字列等）があれば audit で除外するか、該当行に `# pragma: allowlist secret` を付与する。

**誤検知の対処方針（優先順）**:
1. **`# pragma: allowlist secret` インライン付与（推奨）**: ドキュメント・テストファイル内の例示文字列に付与する。baseline 再生成後も保持され、意図が自己文書化される。
2. **audit による baseline 登録**: ソースコード内でインラインコメントが書きにくい場合の代替手段。

```bash
detect-secrets audit .secrets.baseline
# 対話形式で各検知結果を確認。
# y = 本物のシークレット（true positive）/ n = 誤検知（false positive）/ s = スキップ
# 誤検知には n を入力してマークする。
```

### ステップ 4: pre-commit フックのインストール（git hooks への登録）

```bash
pre-commit install
```

これにより `.git/hooks/pre-commit` が自動生成され、`git commit` 時に自動実行される。

### ステップ 5: 全ファイルへの初回チェック実行

```bash
pre-commit run --all-files
```

初回実行時、pre-commit が detect-secrets の仮想環境を自動ダウンロード・構築する（数分かかる場合がある）。
既存ファイルへの適用結果を確認し、`trailing-whitespace` や `end-of-file-fixer` による自動修正があれば専用コミットとして分離する。

### ステップ 6: `docs/runbooks/pre-commit.md` の作成

インストール・運用手順（新規参加者向けセットアップ手順、誤検知時の対処方法、`.secrets.baseline` の更新方法）を記載する。

### ステップ 7: コミット

```bash
git add .pre-commit-config.yaml .secrets.baseline docs/runbooks/pre-commit.md
git commit -m "feat(I034): pre-commit hooks 導入（detect-secrets・基本チェック）"
```

> **注意**: このコミット自体も pre-commit が走る。`trailing-whitespace` 修正が含まれる場合は修正後に再コミット。

---

## 6. テスト計画

### 自動テスト
- Backend/Frontend のコード変更なし → ユニットテスト・統合テストの追加なし
- `pre-commit run --all-files` でフック動作確認（実行ログを記録）

### 手動テスト
- シークレットを含むファイルをコミットしようとするとブロックされること
- 正常なファイルはコミットが通ること
- `pre-commit install` 後に `.git/hooks/pre-commit` が存在すること

---

## 7. ロールバック

```bash
# フック登録解除
pre-commit uninstall

# 生成ファイルの削除
git rm .pre-commit-config.yaml .secrets.baseline
git rm docs/runbooks/pre-commit.md
git commit -m "revert(I034): pre-commit hooks 削除"
```

---

## 8. Risk & 回避策

| リスク | 影響 | 回避策 |
|--------|------|--------|
| detect-secrets の誤検知が多い | コミットがブロックされ開発が止まる | ドキュメント・テストファイル内の例示文字列には `# pragma: allowlist secret` を付与する。ソースコードの場合は `detect-secrets audit` で baseline に登録する |
| `trailing-whitespace`・`end-of-file-fixer` が既存ファイルを大量修正 | 初回 `--all-files` の差分が大きくなる | ステップ5で専用コミットとして分離する |
| ホストに pipx がない開発者 | pre-commit / detect-secrets インストール不可 | runbook に `sudo apt-get install pipx` の手順を明記する |
| detect-secrets のバージョン固定漏れ | 将来バージョンアップで挙動変化 | `.pre-commit-config.yaml` で `rev` を固定する |

---

## 9. セキュリティ影響

- Backend/Frontend のコード変更なし → OWASP Top 10 / XSS / SQLインジェクション等への直接影響なし
- **セキュリティ影響なし**（むしろシークレット検出を強化する変更）
- 追加ライブラリ（`pre-commit`・`detect-secrets`）は開発ツール用途のみ。ランタイムには含まれない。

---

## 10. 設計判断

| 項目 | 判断内容 | 根拠 |
|------|---------|------|
| pre-commit フレームワークを使用 | ✅ イシューに明記 | I034.md スコープ |
| detect-secrets フックを使用 | ✅ イシューに明記 | I034.md スコープ |
| check-yaml / end-of-file-fixer / trailing-whitespace を含める | ✅ イシューに明記 | I034.md スコープ |
| check-added-large-files / check-merge-conflict を追加 | ⚠️ 仮定で決めた | 「等」の記述から有用と判断。不要であれば削除可。 |
| rev を v4.6.0 / v1.5.0 に固定 | ⚠️ 仮定で決めた | 執筆時点の安定バージョン。最新に合わせて変更可。 |
| runbook を新規ファイル `pre-commit.md` として作成 | ⚠️ 仮定で決めた | 既存 runbook の肥大化を避けるため独立ファイルが適切と判断。 |
| pre-commit・detect-secrets を pipx 経由でインストール | ⚠️ 仮定で決めた | 両ツールとも CLI ツールであり pipx が公式推奨。システム Python を汚染しない隔離インストール。フック実行時の detect-secrets は pre-commit が自動管理する仮想環境を使用し、pipx 版は baseline 生成専用として役割を分離する。 |
| CI への組み込みは行わない | ✅ イシューに明記 | I034.md「含まない」セクション |
| flake8・eslint の pre-commit 組み込みは行わない | ✅ イシューに明記 | I034.md「含まない」セクション |
