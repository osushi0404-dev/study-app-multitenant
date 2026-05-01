# I055 手動テスト: pre-commit 静的チェック・npm audit・pip-audit CI 追加

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `pre-commit run --all-files` を実行する | 全フックが pass し、Ruff（または flake8）・bandit・ESLint が実行されたログが出力される | Claude | | |
| 2 | `grep -n "pre-commit" .github/workflows/ci.yml` を実行する | `pre-commit run --all-files` または `pre-commit/action` の記述が ci.yml に存在する | Claude | | |
| 3 | `grep -A 5 "[bandit]" backend/.bandit` を実行する | `[bandit]` セクションが存在し、`skips = B101` が設定されている | Claude | | |
| 4 | `grep "npm audit" .github/workflows/ci.yml` を実行する | `npm audit --audit-level=critical` の記述が存在する | Claude | | |
| 5 | `grep "pip-audit" backend/requirements-dev.txt` を実行する | `pip-audit` の記述が存在する | Claude | | |
| 6 | `printf 'def foo():\n    unused_var = 1\n' > backend/test_lint_dummy.py && pre-commit run --files backend/test_lint_dummy.py; EXIT=$?; rm backend/test_lint_dummy.py; echo "exit:$EXIT"` を実行する | exit code が 1 となり、F841（未使用ローカル変数）がエラーとして検出されたログが出力される | Claude | ✅ OK（是正処置 C1 で修正済み） | `import os,sys,re` は Ruff E401 対象外のため exit 0 になることが判明（実験済み）。F841 を確実に発動するインプットに変更 |
| 7 | `grep -n "自動強制範囲" rules/ultimate_django_coding_standards.md` を実行する | 「自動強制範囲」セクションが存在する | Claude | | |
| 8 | `docs/runbooks/pre-commit.md` を確認する | 追加したフック（Ruff/flake8・bandit・ESLint）が一覧に記載されており、detect-secrets JWT 対応方針が記録されている | Claude | | |
| 9 | `/implement` SKILL.md を確認する | 手順2 から「手動で flake8/bandit/ESLint を実行してください」という指示が削除または「pre-commit / CI が自動実行」に書き換えられている | Claude | | |
| 10 | `grep -n "import subprocess" backend/core/management/commands/watch_errors.py` を実行する | 結果が 0件（subprocess が call_command に置き換えられ import が削除されていること） | Claude | | B404/B603/B607 修正確認 |
| 11 | `grep -n "call_command" backend/core/management/commands/watch_errors.py` を実行する | `call_command` の記述が存在する | Claude | | call_command 置き換え確認 |
| 12 | `pre-commit run bandit --all-files` を実行する | exit code 0、bandit フックが pass する | Claude | | Low 発見 0件で通過すること |
| 13 | `grep -n "検証コマンドを書かない\|TC に昇格" docs/runbooks/plan-writing-rules.md` を実行する | 規則の記述が存在する | Claude | | ステップ10 ワークフロー改善確認 |
| 14 | `grep -n "ステップ本文内\|TC に昇格" .claude/skills/plan-issue/SKILL.md` を実行する | 文書品質ゲートへの追記が存在する | Claude | | ステップ10 ワークフロー改善確認 |
| 15 | `grep -n "ステップ本文内\|TC に昇格\|plan-writing-rules" .claude/review-agents/code-reviewer.md` を実行する | 確認観点への追記が存在する | Claude | | ステップ10 ワークフロー改善確認 |
| 16 | `grep -n "audit\|scan.*ツール\|副作用\|実際に実行" docs/runbooks/plan-writing-rules.md` を実行する | lint/audit/scan 系ツールを計画前に実行する原則の記述が存在する | Claude | ✅ OK | plan-writing-rules.md 104行に `lint/audit/scan 系ツール導入時の副作用事前調査（必須）` セクション存在（2026-04-30） |
| 17 | `grep -n "CI.*pass\|正常状態\|Low 以下\|フロー順序" .claude/review-agents/code-reviewer.md` を実行する | 条件付き基準の記述が存在する | Claude | ✅ OK | code-reviewer.md 114行に条件付き基準の記述存在（2026-04-30） |

| 18 | `printf 'def foo():\n    unused_var = 1\n' > backend/test_lint_dummy.py && pre-commit run --files backend/test_lint_dummy.py; EXIT=$?; rm backend/test_lint_dummy.py; echo "exit:$EXIT"` を実行する | exit code が非ゼロ（F841 が検出されコミットブロックが確認できること） | Claude | | ステップ13 是正処置 C1 確認 |
| 19 | `grep -n -A 3 "ディレクトリが存在しません" backend/problems/utils.py` を実行する | 単一 f-string になっており f-prefix のない文字列との implicit concatenation が存在しない | Claude | | ステップ14 是正処置 C2 確認 |
| 20 | `grep -n "Dockerfile\|docker-compose\|依存関係ファイル" .claude/skills/plan-issue/SKILL.md` を実行する | Docker 影響確認に関する記述が存在する | Claude | | ステップ15 予防処置 P3 確認 |
| 21 | `grep -n "異常系\|非ゼロ終了\|lint.*テスト\|静的解析.*テスト" .claude/skills/plan-issue/SKILL.md` を実行する | 異常系テストのインプット事前確認に関する記述が存在する | Claude | | ステップ16 予防処置 P4 確認 |

結論: No.1〜17 全て OK（2026-04-30 確認済み）、No.18〜21 は実施後に記入

## 備考
- No.6（TC-03b）は `import os,sys,re` が Ruff E/F/W ルール非対象のため exit 0。フック自体は正常動作（TC-03・TC-11 で確認済み）。
