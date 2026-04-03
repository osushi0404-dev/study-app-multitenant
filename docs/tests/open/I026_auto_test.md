# I026 自動テスト計画

## 対象
AI駆動開発環境・プロセス総合見直し（ドキュメント修正）

## 自動テストの適用可否

本イシューの変更はドキュメント（Markdown ファイル）のみであり、バックエンド・フロントエンドのコード変更を含まない。

**自動テスト（pytest / Jest）: 対象外**

## 代替チェック（CI で自動確認できるもの）

### AC-001: Markdown リンク切れチェック（任意）

```bash
# markdownlint がある場合
npx markdownlint docs/runbooks/workflow.md docs/runbooks/issue-flow.md
```

実施条件: markdownlint が導入済みの場合のみ実施。未導入の場合はスキップ。

### AC-002: ファイル存在確認

```bash
# 修正対象ファイルが存在するか確認
ls docs/runbooks/issue-flow.md docs/runbooks/workflow.md docs/plans/open/plan_I026_AI駆動開発環境・プロセス総合見直し.md
```

期待結果: 全ファイルが存在する（exit 0）

---

## 判定

自動テストは適用外。手動テスト（I026_manual_test.md）による確認を合否判定とする。
