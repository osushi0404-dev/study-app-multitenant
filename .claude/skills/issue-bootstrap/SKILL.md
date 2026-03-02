---
name: issue-bootstrap
description: Create issue doc, create issue branch, create draft PR.
argument-hint: "[title]"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /issue-bootstrap

## 自動実行フロー（必須）

### 1. リポジトリ確認
```bash
git rev-parse --show-toplevel
git branch --show-current
```

### 2. イシュー番号の採番
open / in_progress / closed の全ディレクトリから最大番号を取得：
```bash
LAST_NUM=$(ls docs/issues/open/*.md docs/issues/in_progress/*.md docs/issues/closed/*.md 2>/dev/null | grep -o '[0-9]\+\.md' | sed 's/\.md//' | sort -n | tail -1)
if [ -z "$LAST_NUM" ]; then
  ISSUE_NUM="001"
else
  NEXT_NUM=$((LAST_NUM + 1))
  ISSUE_NUM=$(printf "%03d" $NEXT_NUM)
fi
echo "次のイシュー番号: $ISSUE_NUM"
```

**重要**: closedディレクトリも必ず確認すること。

### 3. イシューファイル作成
```bash
cp docs/issues/templates/issue_template.md docs/issues/open/${ISSUE_NUM}.md
# 内容を編集（タイトル、概要等をユーザーの指示に基づいて記載）
```

### 4. ブランチ作成（必須）
developブランチをベースにfeatureブランチを作成：
```bash
git checkout develop
git pull origin develop  # リモートがある場合
git checkout -b feature/I${ISSUE_NUM}-[概要を英語化したもの]
```

**ブランチ命名規則**:
- フォーマット: `feature/I{イシュー番号3桁}-{概要を英語化してケバブケース}`
- 例: `feature/I030-media-asset-models`

**概要の英語化ルール**:
- 日本語の概要をシンプルな英語に変換
- スペースは`-`（ハイフン）に変換
- 最大5単語程度に要約

### 5. ドキュメントをコミット・プッシュ
```bash
git add docs/issues/open/${ISSUE_NUM}.md
git commit -m "docs: create issue I${ISSUE_NUM}"
git push -u origin feature/I${ISSUE_NUM}-[概要]
```

### 6. GitHubイシューの登録（必須）
```bash
gh issue create \
  --title "I${ISSUE_NUM}: [イシュータイトル]" \
  --body "$(cat docs/issues/open/${ISSUE_NUM}.md)" \
  --label "[種別に応じたラベル]"
```

**ラベル設定**:
- Bug → `bug`
- Feature → `enhancement`
- Documentation → `documentation`
- Refactoring → `refactoring`

### 7. Draft PR作成
```bash
gh pr create \
  --title "feat: I${ISSUE_NUM} [イシュータイトル]" \
  --body "## 概要\nI${ISSUE_NUM}: [概要]\n\n## 関連イシュー\nCloses #[GitHubイシュー番号]" \
  --draft \
  --base develop
```

### 8. ユーザーへの報告
```
✅ イシュー I${ISSUE_NUM} を作成しました: [タイトル]
📂 ファイル: docs/issues/open/${ISSUE_NUM}.md
🌿 ブランチ: feature/I${ISSUE_NUM}-[概要]
🔗 GitHubイシュー: [GitHubイシューURL]
📋 Draft PR: [PR URL]

このブランチで作業を開始します。
次のステップ: /plan I${ISSUE_NUM} で計画書を作成してください。
```

## 詳細ルール
詳細なイシュー作成フロー・ブランチ戦略・クローズ手順は以下を参照：
- `docs/runbooks/issue-flow.md`
- `docs/runbooks/workflow.md`
