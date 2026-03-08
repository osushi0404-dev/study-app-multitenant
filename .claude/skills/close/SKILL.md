---
name: close
description: Create closeout, move work item open→closed, finalize PR; request merge.
argument-hint: "[issue_number]"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /close

## 引数

`$ARGUMENTS` = GitHub Issue番号（例: `8`）

## 前提

ユーザー検証 OK 済み。

## 手順

### 1. 90_closeout.md を作成

`docs/work/templates/90_closeout.md` をベースに
`docs/work/open/$ARGUMENTS/90_closeout.md` を作成する。

記載内容:
- 達成した内容の要約
- 変更ファイル一覧（`git diff --name-only develop...HEAD`）
- 自動テスト・手動テストの最終結果
- GH Issue / PR / RID のリンク

### 2. フォルダを open → closed に移動

```bash
bash scripts/move_work_item.sh $ARGUMENTS
```

（`90_closeout.md` が存在しない場合はスクリプトがエラーで停止する）

### 3. 索引を再生成

```bash
python3 scripts/build_indices.py
```

### 4. PR 説明を整備

PR description に以下を揃える:
- 目的 / 変更点 / テスト結果 / ロールバック手順 / 参照パス

### 5. コミット & プッシュ

```bash
git add docs/work/closed/$ARGUMENTS/ docs/indices/
git commit -m "docs: close work item #$ARGUMENTS"
git push
```

### 6. マージ依頼

ユーザーへ GitHub 上で **Approve & Merge** を依頼する。
