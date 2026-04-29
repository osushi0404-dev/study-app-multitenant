# I055 手動テスト: pre-commit 静的チェック・npm audit・pip-audit CI 追加

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `pre-commit run --all-files` を実行する | 全フックが pass し、Ruff（または flake8）・bandit・ESLint が実行されたログが出力される | Claude | | |
| 2 | `grep -n "pre-commit" .github/workflows/ci.yml` を実行する | `pre-commit run --all-files` または `pre-commit/action` の記述が ci.yml に存在する | Claude | | |
| 3 | `grep -A 5 "[bandit]" backend/.bandit` を実行する | `[bandit]` セクションが存在し、`skips = B101` が設定されている | Claude | | |
| 4 | `grep "npm audit" .github/workflows/ci.yml` を実行する | `npm audit --audit-level=critical` の記述が存在する | Claude | | |
| 5 | `grep "pip-audit" backend/requirements-dev.txt` を実行する | `pip-audit` の記述が存在する | Claude | | |
| 6 | `echo "import os,sys,re" > backend/test_lint_dummy.py && pre-commit run --files backend/test_lint_dummy.py; EXIT=$?; rm backend/test_lint_dummy.py; echo "exit:$EXIT"` を実行する | exit code が非ゼロとなり、フックがエラーを検出したログが出力される | Claude | | `/tmp/` は `files: ^backend/` フィルタでスキャン対象外になる可能性があるためリポジトリ内パスを使用 |
| 7 | `grep -n "自動強制範囲" rules/ultimate_django_coding_standards.md` を実行する | 「自動強制範囲」セクションが存在する | Claude | | |
| 8 | `docs/runbooks/pre-commit.md` を確認する | 追加したフック（Ruff/flake8・bandit・ESLint）が一覧に記載されており、detect-secrets JWT 対応方針が記録されている | Claude | | |
| 9 | `/implement` SKILL.md を確認する | 手順2 から「手動で flake8/bandit/ESLint を実行してください」という指示が削除または「pre-commit / CI が自動実行」に書き換えられている | Claude | | |

結論: OK / NG
