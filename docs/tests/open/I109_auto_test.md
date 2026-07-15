# I109 自動テスト: 依存脆弱性ドリフトの定期検知（scheduled 監査＋自動起票）

実行コマンド:
```bash
bash scripts/claude/tests/test_i109_dependency_audit.sh
```

結果:
- backend: 対象外（アプリコード変更なし・pytest 不要）
- frontend: 対象外（アプリコード変更なし・Jest 不要）
- 決定論ゲート: 未実行（実装ステップ3 で実行・記録する）

## テストケース

### TC-01: workflow / スクリプトの静的不変条件（test_i109_dependency_audit.sh 内）
| 検証項目 | 判定方法 | 期待値 |
|---------|---------|--------|
| workflow YAML 構文 | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/dependency-audit.yml'))"` | 例外なし（exit 0） |
| cron 値 | `grep -qF "cron: '0 22 * * *'"` | ヒット（exit 0） |
| 監査対象の固定 | `grep -qF "ref: develop"` | ヒット |
| backend 監査コマンドの CI 同一性 | `grep -qF "pip-audit -r requirements.txt"` | ヒット |
| frontend 監査コマンドの CI 同一性 | `grep -qF -- "--audit-level=critical --omit=dev"` | ヒット |
| GITHUB_TOKEN 最小権限 | `grep -qF "issues: write"` と `grep -qF "contents: read"` | 両方ヒット |
| 手動トリガー | `grep -qF "workflow_dispatch"` | ヒット |
| 起票スクリプト構文 | `bash -n scripts/claude/dependency-audit-issue.sh` | exit 0 |
| スクリプト合計判定 | test_i109_dependency_audit.sh 全体 | **exit 0・NG 行 0 件** |

### TC-02: false-green 注入検証（実装ステップ3 で 1 回実施・結果をここに記録）
| 手順 | 期待値 |
|------|--------|
| workflow の cron 行を一時的に `'0 23 * * *'` へ書き換え → TC-01 のテストスクリプトを実行 → 元に戻す | テストが **NG 行を出力し非ゼロ終了**（壊れた状態を合格させない） |
| `dependency-audit-issue.sh` の `gh issue comment` 分岐を一時的に削除 → TC-03 相当の分岐検証を実行 → 元に戻す | テストが **非ゼロ終了** |

実施記録: （実装時に記入）

### TC-03: 重複防止ロジックの分岐検証（gh スタブ・test_i109_dependency_audit.sh 内）
gh コマンドを PATH 差し替えのスタブ（応答固定・呼び出しログ記録）に置き換えて `dependency-audit-issue.sh backend <ダミー出力>` を実行する。

| ケース | スタブ応答（gh issue list --jq 結果） | 期待値 |
|--------|----------------------------------|--------|
| A: 既存 open イシューなし | 空文字 | 呼び出しログに `issue create` が **1 回**・`issue comment` が **0 回** |
| B: 既存 open イシュー #42 あり | `42` | 呼び出しログに `issue comment 42` が **1 回**・`issue create` が **0 回** |
| C: KIND 不正（`badkind`） | — | **exit 2**（許可リスト検証） |

### TC-04: runbook / CLAUDE.md 整合
| 検証項目 | 判定方法 | 期待値 |
|---------|---------|--------|
| runbook 実在 | `test -f docs/runbooks/dependency-audit.md` | exit 0 |
| CLAUDE.md 参照行 | `grep -qF "docs/runbooks/dependency-audit.md" CLAUDE.md` | ヒット |
| 起票 body の runbook 参照実在性 | スクリプト内の参照パスが実在（TC-01 のスクリプトに含める） | exit 0 |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i109_dependency_audit.sh
```
