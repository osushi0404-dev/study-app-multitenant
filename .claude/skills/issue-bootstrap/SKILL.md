---
name: issue-bootstrap
description: Create issue doc and GitHub Issue only. Branch creation is handled by /plan-issue.
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
ファイルシステムと git 履歴の両方から最大番号を取得する：
```bash
# ファイルシステム上の番号（I###.md / ###.md 両方に対応）
FS_MAX=$(find docs/issues -name "*.md" 2>/dev/null | grep -oP '\d+(?=\.md)' | sort -n | tail -1)
# git 履歴上の番号（削除済みファイルも含む）
GIT_MAX=$(git log --all --oneline -- "docs/issues/**" | grep -oP 'I0*\d+' | grep -oP '\d+' | sort -n | tail -1)
# 大きい方を採用（$((10#...)) で8進数誤解釈を防ぐ）
FS_NUM=$((10#${FS_MAX:-0}))
GIT_NUM=$((10#${GIT_MAX:-0}))
if [ "$FS_NUM" -gt "$GIT_NUM" ]; then
  LAST_NUM=$FS_NUM
else
  LAST_NUM=$GIT_NUM
fi
if [ "$LAST_NUM" -eq 0 ]; then
  ISSUE_NUM="001"
else
  NEXT_NUM=$((LAST_NUM + 1))
  ISSUE_NUM=$(printf "%03d" $NEXT_NUM)
fi
echo "次のイシュー番号: $ISSUE_NUM"
```

**重要**: ファイルシステムだけでなく git 履歴も必ず確認すること（closed から削除されたイシューも番号として使用済み）。

### 3. イシューファイル作成

**イシューファイル名形式**: `I${ISSUE_NUM}.md`（概要なし、例: `I039.md`）

作成前に同名ファイルが存在しないことを確認する:
```bash
if [ -f "docs/issues/open/I${ISSUE_NUM}.md" ]; then
  echo "⚠️ docs/issues/open/I${ISSUE_NUM}.md が既に存在します。上書きしません。採番を再確認してください。"
  exit 1
fi
cp docs/issues/templates/issue_template.md docs/issues/open/I${ISSUE_NUM}.md
# 内容を編集（タイトル、概要等をユーザーの指示に基づいて記載）
```

### 4. GitHubイシューの登録（必須）
```bash
gh issue create \
  --title "I${ISSUE_NUM}: [イシュータイトル]" \
  --body "$(cat docs/issues/open/I${ISSUE_NUM}.md)" \
  --label "[種別に応じたラベル]"
```

**ラベル設定**:
- Bug → `bug`
- Feature → `enhancement`
- Documentation → `documentation`
- Refactoring → `refactoring`

### 5. イシューファイルに GitHub Issue 番号を記録
GitHub Issue 作成後、返却された Issue URL から番号を取得してイシューファイルに追記する:
```bash
# gh issue create の出力から番号を取得（例: https://github.com/org/repo/issues/62 → #62）
GITHUB_ISSUE_NUM=$(gh issue list --state open --limit 1 --json number --jq '.[0].number')
# イシューファイルの「## 関連資料」セクションに追記
# 例: sed -i を使って「## 関連資料」の次の行に挿入するか、
#     Edit ツールで直接 「- GitHub Issue: #XX」 を追記する
```

記録フォーマット（`## 関連資料` セクションに追記）:
```
- GitHub Issue: #XX
```

### 6. ユーザーへの報告
```
✅ イシュー I${ISSUE_NUM} を作成しました: [タイトル]
📂 ファイル: docs/issues/open/I${ISSUE_NUM}.md
🔗 GitHubイシュー: [GitHubイシューURL]

⚠️ ブランチはまだ作成されていません。
次のステップ: /plan-issue I${ISSUE_NUM} でブランチ作成・計画書作成を行ってください。
```

## 詳細ルール
詳細なイシュー作成フロー・ブランチ戦略・クローズ手順は以下を参照：
- `docs/runbooks/issue-flow.md`
- `docs/runbooks/workflow.md`
