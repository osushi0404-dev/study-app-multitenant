---
name: issue-bootstrap
description: Bootstrap a Work Item for a GitHub Issue. Supports two modes.
argument-hint: "[title] or [github_issue_number]"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /issue-bootstrap

## モード判定

引数（`$ARGUMENTS`）が数字のみ → **Mode B**（既存 GH Issue のローカル化）
引数がテキスト　　　　　　　　→ **Mode A**（新規 GH Issue 作成）

```bash
if [[ "$ARGUMENTS" =~ ^[0-9]+$ ]]; then
  MODE="B"
  ISSUE_NUM="$ARGUMENTS"
else
  MODE="A"
  TITLE="$ARGUMENTS"
fi
```

---

## Mode A: 新規 GH Issue を作成してブートストラップ

### 1. GH Issue 作成（番号確定）
```bash
ISSUE_URL=$(gh issue create \
  --title "$TITLE" \
  --body "作業開始。詳細は 00_issue.md に記載します。" \
  --label "enhancement")
ISSUE_NUM=$(echo "$ISSUE_URL" | grep -o '[0-9]*$')
echo "GH Issue #$ISSUE_NUM を作成しました"
```

### 2. Work Item フォルダ作成 & 00_issue.md 生成
```bash
mkdir -p docs/work/open/$ISSUE_NUM

# GH Issue の内容を取得して 00_issue.md に書き込む
gh issue view $ISSUE_NUM --json number,title,body \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'''---
github_issue_number: {d['number']}
title: \"{d['title']}\"
state: open
branch: feature/I{d['number']}-{slug}
created_at: $(date +%Y-%m-%d)
---

# Issue #{d['number']}: {d['title']}

{d['body']}
''')
" > docs/work/open/$ISSUE_NUM/00_issue.md
```

（`{slug}` はタイトルをケバブケース英語化したもの、最大 5 単語）

### 3. ブランチ作成
```bash
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-40)
git checkout develop
git pull origin develop
git checkout -b feature/I${ISSUE_NUM}-${SLUG}
```

### 4. コミット & プッシュ
```bash
git add docs/work/open/$ISSUE_NUM/00_issue.md
git commit -m "docs: bootstrap work item for issue #$ISSUE_NUM"
git push -u origin feature/I${ISSUE_NUM}-${SLUG}
```

### 5. Draft PR 作成
```bash
gh pr create \
  --title "feat: I${ISSUE_NUM} ${TITLE}" \
  --body "## 概要
Issue #${ISSUE_NUM} の対応。

## 関連イシュー
Closes #${ISSUE_NUM}" \
  --draft \
  --base develop
```

### 6. 報告
```
✅ Work Item を作成しました: Issue #$ISSUE_NUM
📂 フォルダ: docs/work/open/$ISSUE_NUM/
🌿 ブランチ: feature/I$ISSUE_NUM-$SLUG
🔗 GH Issue: $ISSUE_URL
📋 Draft PR: [PR URL]

次のステップ: /plan $ISSUE_NUM
```

---

## Mode B: 既存 GH Issue をローカル化

### 1. GH Issue 情報取得
```bash
gh issue view $ISSUE_NUM --json number,title,body,state
```

### 2. Work Item フォルダ作成 & 00_issue.md 生成
```bash
mkdir -p docs/work/open/$ISSUE_NUM
# Mode A と同様に gh issue view の内容から 00_issue.md を生成
```

既にフォルダが存在する場合はエラーを出して停止する（上書き禁止）:
```bash
if [ -d "docs/work/open/$ISSUE_NUM" ] || [ -d "docs/work/closed/$ISSUE_NUM" ]; then
  echo "ERROR: Work Item $ISSUE_NUM already exists. Aborting."
  exit 1
fi
```

### 3. ブランチ作成
```bash
# GH Issue のタイトルからスラッグを生成
TITLE=$(gh issue view $ISSUE_NUM --json title -q .title)
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-40)
git checkout develop
git pull origin develop
git checkout -b feature/I${ISSUE_NUM}-${SLUG}
```

### 4. コミット & プッシュ & Draft PR 作成
Mode A の Step 4〜5 と同様。

### 5. 報告（Mode B）
```
✅ 既存イシュー #$ISSUE_NUM をローカル化しました
📂 フォルダ: docs/work/open/$ISSUE_NUM/
🌿 ブランチ: feature/I$ISSUE_NUM-$SLUG
📋 Draft PR: [PR URL]

次のステップ: /plan $ISSUE_NUM
```

---

## 詳細ルール
- `docs/runbooks/issue-flow.md`
- `docs/runbooks/workflow.md`
