---
name: plan
description: Create plan + tests + review docs for an issue. No code changes.
argument-hint: "[issue_number]"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /plan

## 引数

`$ARGUMENTS` = GitHub Issue番号（例: `8`）

## 必読

```bash
cat docs/work/open/$ARGUMENTS/00_issue.md
cat docs/runbooks/plan-writing-rules.md
cat rules/ultimate_django_coding_standards.md      # バックエンド変更がある場合
cat rules/react-coding-standards-integrated.md     # フロントエンド変更がある場合
```

## RID 採番

```bash
python3 -c "
import json
with open('docs/indices/review_seq.json') as f:
    d = json.load(f)
rid = f\"R{d['next']:05d}\"
d['next'] += 1
with open('docs/indices/review_seq.json', 'w') as f:
    json.dump(d, f, indent=2)
print(rid)
"
```

## 生成物（`docs/work/open/$ARGUMENTS/` 配下）

```
10_plan.md           ← 計画書（承認ゲート）
20_test_auto.md      ← 自動テスト
21_test_manual.md    ← 手動テスト
30_review_{RID}.md   ← レビュー枠（上記で採番した RID を使用）
```

テンプレートは `docs/work/templates/` から参照する。

## 禁止

- コード変更（承認前の Edit/Write/MultiEdit 開始は禁止）
- 旧ディレクトリ（廃止済み）への書き込み

## 完了

「承認ポイント」を提示して停止する:

```
📋 計画書を作成しました: docs/work/open/$ARGUMENTS/10_plan.md

⏸️ 承認待ち中: 実際の修正作業は開始しません
✅ 承認いただけましたら「OK」または「承認」とお答えください
❌ 修正が必要でしたら具体的な指示をお願いします
```
