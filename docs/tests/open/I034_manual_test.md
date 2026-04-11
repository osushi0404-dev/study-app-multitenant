# I034 手動テスト: pre-commit hooks の導入（シークレット検出・コード品質チェック）

| No | 手順 | 期待結果 | 実結果 | 備考 |
|---:|------|----------|--------|------|
| 1 | `.pre-commit-config.yaml` が存在することを確認 | ファイルが存在する | | |
| 2 | `.secrets.baseline` が存在することを確認 | ファイルが存在し、valid JSON である | | |
| 3 | `docs/runbooks/pre-commit.md` が存在することを確認 | インストール手順・運用手順が記載されている | | |
| 4 | `pipx list` で両ツールの確認 | `pre-commit` と `detect-secrets` がリストに表示される | | |
| 5 | `pre-commit install` を実行 | `.git/hooks/pre-commit` が作成される | | |
| 6 | シークレット文字列を含む一時ファイルを作成し `git commit` を試みる（`tmp.py` を作成し `SECRET_KEY = "abc123secretxyz"` を記述） | detect-secrets によりコミットがブロックされる | | テスト後 `tmp.py` は削除する。ファイル内に `# pragma: allowlist secret` は付けないこと | # pragma: allowlist secret |
| 7 | 一時ファイルを削除して通常のファイルを `git commit` | コミットが通る（全フック passed） | | |
| 8 | 行末スペースを含むファイルをステージして `git commit` を試みる | `trailing-whitespace` フックが自動修正し、再ステージ後にコミットが通る | | |
| 9 | 不正な YAML ファイル（例: インデント崩れ）をコミット試行 | `check-yaml` によりコミットがブロックされる | | |
| 10 | `.secrets.baseline` に `frontend/` および `backend/` 両方のスキャン結果が含まれていることを確認（シークレットが存在しない場合は `results: {}` でも可） | リポジトリ全体がスキャン対象になっている | | `cat .secrets.baseline \| python3 -m json.tool \| grep filename` で確認 |

結論:
