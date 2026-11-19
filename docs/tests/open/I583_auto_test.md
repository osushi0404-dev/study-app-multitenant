# I583 自動テスト: 番号のテストを本物のリポジトリの記録に頼らない形にする

実行コマンド（例）: `bash scripts/claude/tests/test_i569_issue_number_digits.sh`

結果:
- harness: 2026-11-19 implement で実行・pass=84 fail=0

## テストケース
| TC | 対象 | 期待値（合格=exit 0） |
|---|---|---|
| TC-A1 | `bash scripts/claude/tests/test_i569_issue_number_digits.sh` | exit 0・最後の行が `pass=<N> fail=0`。中の TC-02・TC-03・TC-05・TC-10・TC-11・FG-05〜FG-08 がすべて PASS（下の表） |

テストファイルの中のケース（計画書 4 節）:
| ケース | 確かめること | 期待 |
|---|---|---|
| TC-02 | 一時のリポジトリで `gate-check.sh I1000`（`GATE_BASE=HEAD`） | exit 1 かつ `GATE_CHECK: FAIL REASON=missing` の行 → YES |
| TC-03 | 一時のリポジトリで `adversarial-review.sh I1000`（差し替えの `claude`） | exit 2 かつ `ADVERSARIAL_ERROR: FILES` の行 → YES |
| TC-05 | 一時のリポジトリで `check-manual-test-executor.sh I1000` | exit 2 かつ `判定できない: I1000_manual_test.md がありません` → YES |
| TC-10 | TC-02〜TC-05 の後の印 | `$TMP/claude_called` が無い |
| FG-05 | `GATE_CHECK_LIB` を無いパスにした TC-02 の判定 | NO（読み込みの失敗で終わる） |
| FG-06 | I1000 のイシューファイルと計画書をコミットした一時のリポジトリでの TC-03 の判定 | NO、かつ `$TMP/claude_called` ができる |
| FG-07 | git の外のフォルダから起動した TC-05 の判定 | NO（git の外で終わる） |
| TC-11 | `GIT_DIR`・`GIT_WORK_TREE` をおとりの一時のリポジトリに向けたまま `iso_repo` と `tgit add/commit` を流す（F1） | おとりのコミット数が 1 のまま、作ったリポジトリのコミット数が 2（init と add・commit の分） → YES |
| FG-08 | 前置き `NOGIT` を付けない git で TC-11 と同じことをする | NO（おとりにコミットが入る） |

結果（実装後に記入）:
- TC-A1: 2026-11-19 implement で実行・exit 0（pass=84 fail=0。TC-02・TC-03・TC-05・TC-10・FG-05〜FG-07 すべて PASS）

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i569_issue_number_digits.sh
```

## 実行記録
- 2026-11-19 test-gate: 決定論ゲート `bash scripts/claude/tests/test_i569_issue_number_digits.sh` は review-gate（code-review.sh）が実走済み。heavy の委譲なし。test-gate で手元の流し直しはしない（CI が正・CI_WAIT: OK）
