---
name: issue-bootstrap
description: Create issue doc, create issue branch, create draft PR.
argument-hint: "[title]"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /issue-bootstrap

1) リポジトリ直下であることを確認（git rev-parse --show-toplevel）
2) docs/issues/open と closed を走査し、次の I### を採番
3) docs/issues/open/I###_<slug>.md を templates から生成
4) ブランチ issue/I### を作成して checkout
5) ドキュメントだけ commit → push（develop/mainへ直 push しない）
6) 可能なら gh で draft PR を作成（base=develop）
