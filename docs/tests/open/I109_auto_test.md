# I109 自動テスト: 依存脆弱性ドリフトの定期検知（scheduled 監査＋自動起票）

実行コマンド:
```bash
bash scripts/claude/tests/test_i109_dependency_audit.sh
```

結果:
- backend: 対象外（アプリコード変更なし・pytest 不要）
- frontend: 対象外（アプリコード変更なし・Jest 不要）
- 決定論ゲート: **実行済み（2026-07-15・RESULT: OK・16/16 項目 OK・exit 0）**。TDD Red（実装前・全16項目 NG・exit 1）→ Green（実装後・全 OK）を確認

## テストケース

### TC-01: workflow / スクリプトの静的不変条件（test_i109_dependency_audit.sh 内）
| 検証項目 | 判定方法 | 期待値 |
|---------|---------|--------|
| workflow YAML 構文 | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/dependency-audit.yml'))"` | 例外なし（exit 0） |
| cron 値 | `grep -qF "cron: '0 22 * * *'"` | ヒット（exit 0） |
| 監査対象の固定 | `grep -qF "ref: develop"` | ヒット |
| backend 監査コマンドの CI 同一性（**ペア検証**） | `grep -qF "pip-audit -r requirements.txt"` を `dependency-audit.yml` と `.github/workflows/ci.yml` の**両方**に対して実行 | 両方ヒット（ci.yml 側が将来変更されると fail し乖離を検知） |
| frontend 監査コマンドの CI 同一性（**ペア検証**） | `grep -qF -- "--audit-level=critical --omit=dev"` を `dependency-audit.yml` と `.github/workflows/ci.yml` の**両方**に対して実行 | 両方ヒット（同上） |
| GITHUB_TOKEN 最小権限 | `grep -qF "issues: write"` と `grep -qF "contents: read"` | 両方ヒット |
| 手動トリガー | `grep -qF "workflow_dispatch"` | ヒット |
| テスト用 simulate 分岐の存在 | `grep -qF "inputs.simulate_failure"` | ヒット（実監査コマンドの存在検証と併せて、simulate 分岐が実監査を置換していないことを担保） |
| 起票スクリプト構文 | `bash -n scripts/claude/dependency-audit-issue.sh` | exit 0 |
| スクリプト合計判定 | test_i109_dependency_audit.sh 全体 | **exit 0・NG 行 0 件** |

### TC-02: false-green 注入検証（実装ステップ3 で 1 回実施・結果をここに記録）
**方式**: 実ファイルは一切改変しない。workflow / スクリプトを**一時ディレクトリにコピーして壊し**、テストスクリプトの検証対象を環境変数 `I109_TEST_WF` / `I109_TEST_SCRIPT` でそのコピーに差し替えて実行する（git restore 等による戻し作業自体を不要にする）。

| 手順 | 期待値 |
|------|--------|
| workflow の一時コピーの cron 行を `'0 23 * * *'` へ書き換え → `I109_TEST_WF=<コピー> bash scripts/claude/tests/test_i109_dependency_audit.sh` | テストが **NG 行を出力し非ゼロ終了**（壊れた状態を合格させない） |
| `dependency-audit-issue.sh` の一時コピーから `gh issue comment` 分岐を削除 → `I109_TEST_SCRIPT=<コピー> bash scripts/claude/tests/test_i109_dependency_audit.sh` | テストが **非ゼロ終了** |

実施記録（2026-07-15 実施・実ファイル無改変）:
- 注入1: 一時コピーの cron を `'0 23 * * *'` に改変 → `NG: cron 値` を出力し **exit 1**（検知 OK）
- 注入2: 一時コピーの `gh issue comment` 呼び出しを no-op に置換 → `NG: 重複防止B` を出力し **exit 1**（検知 OK）
- 判定: 本テストは false-green ではない（壊れた状態を確実に不合格にする）

### TC-03: 重複防止ロジックの分岐検証（gh スタブ・test_i109_dependency_audit.sh 内）
gh コマンドを PATH 差し替えのスタブ（応答固定・呼び出しログ記録）に置き換えて `dependency-audit-issue.sh backend <ダミー出力>` を実行する。

| ケース | スタブ応答（gh issue list --jq 結果） | 期待値 |
|--------|----------------------------------|--------|
| A: 既存 open イシューなし | 空文字 | 呼び出しログに `issue create` が **1 回**・`issue comment` が **0 回** |
| B: 既存 open イシュー #42 あり | `42` | 呼び出しログに `issue comment 42` が **1 回**・`issue create` が **0 回** |
| C: KIND 不正（`badkind`） | — | **exit 2**（許可リスト検証） |

対応任意指摘の見送り記録（plan review Info-2）: schedule 実行時に `inputs.simulate_failure` が空文字になり通常監査が走る経路の専用 TC は追加しない。`[ "" = "backend" ]` が不成立なのは bash の自明動作であり、workflow YAML 側の分岐存在は TC-01 の不変条件（simulate 分岐と実監査コマンドの両方の存在検証）でカバーされるため。

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
