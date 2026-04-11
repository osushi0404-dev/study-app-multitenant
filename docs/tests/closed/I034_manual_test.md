# I034 手動テスト: pre-commit hooks の導入（シークレット検出・コード品質チェック）

| No | 手順 | 期待結果 | 実結果 | 備考 |
|---:|------|----------|--------|------|
| 1 | `.pre-commit-config.yaml` が存在することを確認 | ファイルが存在する | OK | |
| 2 | `.secrets.baseline` が存在することを確認 | ファイルが存在し、valid JSON である | OK | |
| 3 | `docs/runbooks/pre-commit.md` が存在することを確認 | インストール手順・運用手順が記載されている | OK | |
| 4 | `pipx list` で両ツールの確認 | `pre-commit` と `detect-secrets` がリストに表示される | OK | pre-commit 4.5.1 / detect-secrets 1.5.0 |
| 5 | `pre-commit install` を実行 | `.git/hooks/pre-commit` が作成される | OK | |
| 6 | シークレット文字列を含む一時ファイルを作成し `git commit` を試みる（`tmp.py` を作成し `SECRET_KEY = "abc123secretxyz"` を記述） | detect-secrets によりコミットがブロックされる | OK | テスト後 `tmp.py` は削除する。ファイル内に `# pragma: allowlist secret` は付けないこと | # pragma: allowlist secret |
| 7 | 一時ファイルを削除して通常のファイルを `git commit` | コミットが通る（全フック passed） | OK | |
| 8 | 行末スペースを含むファイルをステージして `git commit` を試みる | `trailing-whitespace` フックが自動修正し、再ステージ後にコミットが通る | OK | |
| 9 | 不正な YAML ファイル（例: インデント崩れ）をコミット試行 | `check-yaml` によりコミットがブロックされる | OK | |
| 10 | `.secrets.baseline` に `frontend/` および `backend/` 両方のスキャン結果が含まれていることを確認（シークレットが存在しない場合は `results: {}` でも可） | リポジトリ全体がスキャン対象になっている | OK | backend/ 配下・docs/ 配下・rules/ 配下・.github/ 配下を確認 |

結論: OK（2026-04-11）
