---
name: issue-bootstrap
description: Create issue doc, run issue-review (self-completeness), then register GitHub Issue. Branch creation is handled by /plan-issue.
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

### 3.5 自己完結度レビュー（必須・ソフト警告）

GitHub 登録（step 4）の前に、issue-review サブエージェントでイシュー内容をレビューする:
```bash
bash scripts/claude/issue-review.sh "I${ISSUE_NUM}"
```

- レビュー結果（自己完結判定＝`十分`/`要補足`、未記入セクション、内容指摘）をユーザーに提示する。
- これは**ソフト警告**であり、登録（step 4 以降）を**ブロックしない**。情報が本当に未確定なら「未特定・grill-me で確認」と明記して進めてよい。
- `claude -p` が利用できない等で結果が得られない場合もフローは継続する（`issue-review.sh` が非ブロックで `exit 0` する）。
- 「未特定・grill-me で確認」「未定・grill-me で確認」「未特定」のプレースホルダが明記されている項目は未記入扱いにしない。
- 実行後、出力中の `## 判定: 十分/要補足` を読み取り、step 6 の報告分岐（A=要補足／B=十分）の判断に使う。

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

step 3.5 の issue-review 判定に応じて次ステップ案内を出し分ける。

**(A) 判定=`要補足` / 「未特定・未定」プレースホルダが残っている場合**:
```
✅ イシュー I${ISSUE_NUM} を作成しました: [タイトル]
📂 ファイル: docs/issues/open/I${ISSUE_NUM}.md
🔗 GitHubイシュー: [GitHubイシューURL]

⚠️ 未確定のセクションがあります: [未記入/プレースホルダのセクション名一覧]
⚠️ ブランチはまだ作成されていません。
次のステップ:
  👉 未確定の設計を詰めるため `/grill-me I${ISSUE_NUM}` を実行してください（推奨）。
  👉 詰め終わったら `/plan-issue I${ISSUE_NUM}` でブランチ作成・計画書作成を行ってください。
```

**(B) 判定=`十分`（重要セクションが具体的に記入済み・プレースホルダなし）の場合**:
```
✅ イシュー I${ISSUE_NUM} を作成しました: [タイトル]
📂 ファイル: docs/issues/open/I${ISSUE_NUM}.md
🔗 GitHubイシュー: [GitHubイシューURL]

✅ イシューは自己完結しています（現状の問題・根本原因・解決方針・実装対象が記入済み）。
⚠️ ブランチはまだ作成されていません。
次のステップ:
  👉 設計上の疑問がなければ `/grill-me` はスキップして `/plan-issue I${ISSUE_NUM}` に直接進めます。
  👉 念のため設計を確認したい場合は `/grill-me I${ISSUE_NUM}` を実行してください。
```

## 詳細ルール
詳細なイシュー作成フロー・ブランチ戦略・クローズ手順は以下を参照：
- `docs/runbooks/issue-flow.md`
- `docs/runbooks/workflow.md`
