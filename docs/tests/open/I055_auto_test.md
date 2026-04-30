# I055 自動テスト: pre-commit 静的チェック・npm audit・pip-audit CI 追加

実行コマンド:
```bash
# Backend
docker compose exec backend python3 -m pytest --tb=short -q

# Frontend
docker compose exec frontend npm test -- --watchAll=false
```

## テストケース

### TC-01 既存テストのリグレッション（Backend）
- **目的**: 設定ファイル変更により既存テストが壊れていないことを確認
- **実行**: `docker compose exec backend python3 -m pytest --tb=short -q`
- **期待値**: 25 passed 以上、0 failed

### TC-02 既存テストのリグレッション（Frontend）
- **目的**: npm audit fix による package-lock.json 変更で既存テストが壊れていないことを確認
- **実行**: `docker compose exec frontend npm test -- --watchAll=false`
- **期待値**: 7 passed 以上、0 failed

### TC-03 pre-commit フックの動作確認（正常系）
- **目的**: 追加したフックがすべて実行されること
- **実行**: `pre-commit run --all-files`
- **期待値**: 全フックが pass（Ruff または flake8・bandit・ESLint が実行されたログが出ること）

### TC-03b pre-commit コミットブロック検証（異常系）
- **目的**: lint エラーがある場合に pre-commit がコミットを止めること（AC 第1項の核心）
- **実行**:
  ```bash
  # lint エラーを含むダミーファイルをリポジトリ内に作成して pre-commit を走らせる
  echo "import os,sys,re" > backend/test_lint_dummy.py
  pre-commit run --files backend/test_lint_dummy.py
  EXIT_CODE=$?
  rm backend/test_lint_dummy.py
  echo "exit code: $EXIT_CODE"
  ```
- **期待値**: exit code が非ゼロ（フックがエラーを検出してブロックしたこと）
- **注**: `/tmp/` 配下のファイルは pre-commit の `files: ^backend/` フィルタでスキャン対象外になる可能性があるため、リポジトリ内パスを使用する

### TC-04 CI lint ジョブの構成確認
- **目的**: `pre-commit run --all-files` が CI の backend-lint ジョブに含まれていること
- **実行**: `grep -n "pre-commit" .github/workflows/ci.yml`
- **期待値**: `pre-commit` の記述が ci.yml に存在する

### TC-05 bandit 設定の集約確認
- **目的**: bandit の除外設定が `backend/.bandit`（INI 形式）に存在し、CI の CLI 除外引数が削除されていること
- **実行**:
  ```bash
  grep -A 5 "\[bandit\]" backend/.bandit
  grep "bandit" .github/workflows/ci.yml
  ```
- **期待値**: `backend/.bandit` に `[bandit]` セクションがあり `skips = B101` が含まれる。`ci.yml` の bandit コマンドに `-x` 除外引数がない

### TC-06 pip-audit が requirements-dev.txt に追加されていること
- **実行**: `grep "pip-audit" backend/requirements-dev.txt`
- **期待値**: `pip-audit` の記述が存在する

### TC-07 npm audit critical チェックが CI に追加されていること
- **実行**: `grep -n "npm audit" .github/workflows/ci.yml`
- **期待値**: `npm audit --audit-level=critical` の記述が存在する

### TC-08 ESLint warnings が 0 件であること（pre-commit 追加前提）
- **実行**: `docker compose exec frontend npx eslint src/ --ext .ts,.tsx --max-warnings 0`
- **期待値**: exit code 0（warnings 0件）

### TC-09 コーディング規約冒頭セクションの存在確認
- **実行**:
  ```bash
  grep -n "自動強制範囲" rules/ultimate_django_coding_standards.md
  grep -n "自動強制範囲" rules/react-coding-standards-integrated.md
  ```
- **期待値**: 両ファイルに「自動強制範囲」セクションが存在する

### TC-10 bandit Low 発見対処の確認
- **目的**: B110 が修正され、`watch_errors.py` が `call_command` に置き換えられ、B311 に `# nosec` が付いていること
- **実行**:
  ```bash
  # B110 修正確認（bare except Exception がないこと）
  grep -n "except Exception:" backend/core/enhanced_logging.py
  grep -n "except Exception:" backend/core/management/commands/watch_errors.py
  # subprocess 削除確認（call_command 置き換え後は import subprocess がないこと）
  grep -n "import subprocess" backend/core/management/commands/watch_errors.py
  # call_command 使用確認
  grep -n "call_command" backend/core/management/commands/watch_errors.py
  # B311 nosec コメントの存在確認
  grep -n "nosec B311" backend/studylogs/adaptive_selection.py
  ```
- **期待値**: `except Exception:` が 0件。`import subprocess` が 0件。`call_command` の記述が存在する。`nosec B311` が 3件存在する

### TC-11 pre-commit bandit フック通過確認
- **目的**: bandit フックが Low 発見なしで pass すること
- **実行**:
  ```bash
  pre-commit run bandit --all-files
  ```
- **期待値**: exit code 0（bandit フックが pass）

結果:
- backend: （実施後に記入）
- frontend: （実施後に記入）
