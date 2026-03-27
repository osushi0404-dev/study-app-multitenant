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
1) docs/*/open の対象 I### ファイルを closed へ移動
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
