# I058 自動テスト: plan-issue-review・code-review のオーケストレーションをシェルスクリプト化する

## テストケース

### TC-01 スクリプトファイルの存在と実行権限
- **目的**: 両スクリプトが存在し実行権限があること
- **実行**:
  ```bash
  test -x scripts/claude/plan-issue-review.sh && echo "PASS plan-review" || echo "FAIL plan-review"
  test -x scripts/claude/code-review.sh && echo "PASS code-review" || echo "FAIL code-review"
  ```
- **期待値**: 両方 PASS

### TC-02 bash 構文チェック
- **目的**: スクリプトが構文エラーなく解析できること
- **実行**:
  ```bash
  bash -n scripts/claude/plan-issue-review.sh && echo "PASS plan-review" || echo "FAIL plan-review"
  bash -n scripts/claude/code-review.sh && echo "PASS code-review" || echo "FAIL code-review"
  ```
- **期待値**: 両方 PASS

### TC-03 出力正規化コードの存在
- **目的**: 末尾スペース除去の正規化処理がスクリプトに含まれること
- **実行**:
  ```bash
  grep -qF "REVIEW_CLEAN" scripts/claude/plan-issue-review.sh && echo "PASS" || echo "FAIL"
  grep -qF "REVIEW_CLEAN" scripts/claude/code-review.sh && echo "PASS" || echo "FAIL"
  ```
- **期待値**: 両方 PASS

### TC-04 CI タイムアウト設定
- **目的**: code-review.sh に 600 秒タイムアウトが設定されていること
- **実行**:
  ```bash
  grep -q "TIMEOUT=600" scripts/claude/code-review.sh && echo "PASS" || echo "FAIL"
  ```
- **期待値**: PASS

### TC-05 `claude -p` の使用確認（agentId 非混入の保証）
- **目的**: Agent ツールではなく `claude -p` を使用していること
- **実行**:
  ```bash
  grep -qF "claude -p" scripts/claude/plan-issue-review.sh && echo "PASS" || echo "FAIL"
  grep -qF "claude -p" scripts/claude/code-review.sh && echo "PASS" || echo "FAIL"
  ```
- **期待値**: 両方 PASS

### TC-06 スキルラッパーの内容確認
- **目的**: スキルファイルがスクリプトを呼び出す形式になっていること
- **実行**:
  ```bash
  grep -q "plan-issue-review.sh" .claude/skills/plan-issue-review/SKILL.md && echo "PASS" || echo "FAIL"
  grep -q "code-review.sh" .claude/skills/code-review/SKILL.md && echo "PASS" || echo "FAIL"
  ```
- **期待値**: 両方 PASS

### TC-07 plan-issue-review.sh の差し戻し判定パターン（判定フィールド限定）
- **目的**: 「判定:」フィールドを含む行のみにマッチするパターンが使用されていること（レビュー本文中の単独「差し戻し」誤検知防止・reviewer 出力フォーマット揺れへの耐性）
- **実行**:
  ```bash
  grep -qF 'grep -qE "判定:.*差し戻し"' scripts/claude/plan-issue-review.sh && echo "PASS" || echo "FAIL"
  ```
- **期待値**: PASS

### TC-08 code-review.sh の Blocker/High 判定パターン（行頭アンカー）
- **目的**: テーブル第1列のみにマッチする grep パターンが使用されていること（受け入れ条件テーブル等からの誤検知防止）
- **実行**:
  ```bash
  grep -qF 'grep -qE "^\| Blocker \|"' scripts/claude/code-review.sh && echo "PASS" || echo "FAIL"
  grep -qF 'grep -qE "^\| High \|"' scripts/claude/code-review.sh && echo "PASS" || echo "FAIL"
  ```
- **期待値**: 両方 PASS

### TC-09 code-review.sh の gh pr checks set -e 保護
- **目的**: `gh pr checks` の非ゼロ exit code で `set -euo pipefail` によりスクリプトが即終了しないこと
- **実行**:
  ```bash
  grep -qF "gh pr checks" scripts/claude/code-review.sh && \
  grep -qF "|| true" scripts/claude/code-review.sh && echo "PASS" || echo "FAIL"
  ```
- **期待値**: PASS

### TC-10 `--allowedTools` 設定の確認（plan-issue-review.sh）
- **目的**: plan-issue-review.sh の `claude -p` 呼び出しに `--allowedTools "Read,Grep,Glob"` が設定されていること
- **実行**:
  ```bash
  grep -qF '--allowedTools "Read,Grep,Glob"' scripts/claude/plan-issue-review.sh && echo "PASS" || echo "FAIL"
  ```
- **期待値**: PASS

### TC-11 `--allowedTools` 設定の確認（code-review.sh）
- **目的**: code-review.sh の `claude -p` 呼び出しに `--allowedTools "Read,Grep,Glob"` が設定されていること
- **実行**:
  ```bash
  grep -qF '--allowedTools "Read,Grep,Glob"' scripts/claude/code-review.sh && echo "PASS" || echo "FAIL"
  ```
- **期待値**: PASS

## 各 TC 実行結果

| TC | 結果 | 備考 |
|----|------|------|
| TC-01 | PASS | |
| TC-02 | PASS | |
| TC-03 | PASS | |
| TC-04 | PASS | |
| TC-05 | PASS | |
| TC-06 | PASS | |
| TC-07 | PASS | |
| TC-08 | PASS | |
| TC-09 | PASS | |
| TC-10 | | ステップ5実装後に実施 |
| TC-11 | | ステップ5実装後に実施 |
