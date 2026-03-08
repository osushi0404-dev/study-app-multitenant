---
github_issue_number: {ISSUE_NUMBER}
rid: {RID}
closed_at: {DATE}
pr: #{PR_NUMBER}
---

# 完了サマリ — Issue #{ISSUE_NUMBER}: {TITLE}

## 成果

{達成した内容の要約}

## 変更ファイル

```
{git diff --name-only の出力}
```

## テスト結果

- 自動テスト: OK / NG
- 手動テスト: OK / NG

## 関連リンク

- GH Issue: #{ISSUE_NUMBER}
- PR: #{PR_NUMBER}
- レビュー: {RID}

## 成果物一覧

```
docs/work/closed/{ISSUE_NUMBER}/
  00_issue.md
  10_plan.md
  20_test_auto.md
  21_test_manual.md
  30_review_{RID}.md
  90_closeout.md  ← このファイル
```
