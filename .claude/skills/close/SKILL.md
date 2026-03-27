---
name: close
description: Move docs open→closed and finalize PR description; request merge.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /close

前提: ユーザー検証OK。

0) PR のベースブランチを確認する（必須）:
   ```bash
   gh pr view --json baseRefName --jq '.baseRefName'
   # → "develop" であること。"main" の場合は以下で修正してから続行:
   # gh pr edit <PR番号> --base develop
   ```
1) docs/*/open の対象 I### ファイルを closed へ移動（以下を順番に実行）:
   ```bash
   ISSUE_NUM="###"  # 実際のイシュー番号（3桁）に置き換える

   # イシューファイル（I###.md 形式優先、旧 ###.md 形式にも対応）
   if [ -f "docs/issues/open/I${ISSUE_NUM}.md" ]; then
     mv docs/issues/open/I${ISSUE_NUM}.md docs/issues/closed/
   elif [ -f "docs/issues/open/${ISSUE_NUM}.md" ]; then
     mv docs/issues/open/${ISSUE_NUM}.md docs/issues/closed/
   else
     echo "⚠️ イシューファイルが見つかりません（I${ISSUE_NUM}.md / ${ISSUE_NUM}.md）"
   fi

   # 計画書（複数ある場合もパターンで対応）
   for f in docs/plans/open/I${ISSUE_NUM}_*.md; do
     [ -f "$f" ] && mv "$f" docs/plans/closed/
   done

   # テストケース
   for f in docs/tests/open/I${ISSUE_NUM}_*.md; do
     [ -f "$f" ] && mv "$f" docs/tests/closed/
   done

   # レビュー
   for f in docs/reviews/open/I${ISSUE_NUM}_*.md; do
     [ -f "$f" ] && mv "$f" docs/reviews/closed/
   done
   ```
   移動後、open に残留ファイルがないことを必ず確認:
   ```bash
   ls docs/issues/open/ docs/plans/open/ docs/tests/open/ docs/reviews/open/
   ```
2) PR説明に「目的/変更点/テスト/ロールバック/参照パス」を揃える
3) commit/push して PR を更新
4) PR のベースブランチが `develop` であることを確認・修正:
   ```bash
   gh pr view <PR番号> --json baseRefName -q .baseRefName
   # develop でなければ修正
   gh pr edit <PR番号> --base develop
   ```
5) Draft PRをReadyに切り替え: `gh pr ready <PR番号>`
6) ユーザーへ GitHub 上で Approve & Merge を依頼
