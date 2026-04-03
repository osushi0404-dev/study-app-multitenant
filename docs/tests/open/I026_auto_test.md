# I026 自動テスト計画

## 対象
AI駆動開発環境・プロセス総合見直し（ドキュメント修正）

## 自動テストの適用可否

本イシューの変更はドキュメント（Markdown ファイル）のみであり、バックエンド・フロントエンドのコード変更を含まない。

**自動テスト（pytest / Jest）: 対象外**

## 代替チェック（CI で自動確認できるもの）

### AC-001: ファイル存在確認

```bash
# 作成・修正対象ファイルが存在するか確認
ls \
  docs/proposals/I026_ai_dev_improvement_proposal.md \
  docs/runbooks/onboarding.md \
  "docs/plans/open/plan_I026_AI駆動開発環境・プロセス総合見直し.md"
```

期待結果: 全ファイルが存在する（exit 0）

### AC-002: 改善項目 G〜J のキーワード存在確認

```bash
# 提案資料に GitHub 未活用機能の記述があるか確認
grep -c "Dependabot" docs/proposals/I026_ai_dev_improvement_proposal.md
grep -c "pull_request_template" docs/proposals/I026_ai_dev_improvement_proposal.md
grep -c "Branch protection" docs/proposals/I026_ai_dev_improvement_proposal.md
grep -c "GitHub Projects" docs/proposals/I026_ai_dev_improvement_proposal.md
```

期待結果: 各コマンドが 1 以上を返す（記述が存在する）

### AC-003: onboarding.md のキーワード確認

```bash
# フロー図・docs 構成・参照先の更新確認
grep -c "plan-issue-review" docs/runbooks/onboarding.md
grep -c "proposals" docs/runbooks/onboarding.md
grep -c "issue-flow.md" docs/runbooks/onboarding.md
```

期待結果: 各コマンドが 1 以上を返す

### AC-004: Markdown リンク切れチェック（任意）

```bash
# markdownlint がある場合
npx markdownlint docs/proposals/I026_ai_dev_improvement_proposal.md docs/runbooks/onboarding.md
```

実施条件: markdownlint が導入済みの場合のみ実施。未導入の場合はスキップ。

---

## 判定

自動テストは適用外。手動テスト（I026_manual_test.md）による確認を合否判定とする。
