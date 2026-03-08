---
github_issue_number: 10
title: "CLAUDE.md の完全移行 — GitHub Actions ワークフローによる自動化"
state: open
branch: feature/I10-claude-md-migration-github-actions
created_at: 2026-03-09
---

# Issue #10: CLAUDE.md の完全移行 — GitHub Actions ワークフローによる自動化

## 背景

現在 CLAUDE.md にはプロジェクト運用ルールが集約されているが、
GitHub Actions ワークフローを活用することで一部の運用を自動化・
外部化できる可能性がある。

また、有料プラン（GitHub Team / Pro）でのみ利用可能な機能と
無料プランで実現できる機能の整理が必要。

## 目的

1. CLAUDE.md の内容を docs/runbooks/ 配下へ完全移行（CLAUDE.md はポインタのみ）
2. GitHub Actions ワークフローで自動化できる運用の洗い出しと実装
3. 無料プラン制限の確認と、セルフホストランナー等の代替案の検討

## 調査済み事項（issue-bootstrap 時点）

### 有料プランが必要な機能

| 機能 | 必要プラン |
|------|-----------|
| Environment required reviewers（承認ゲート） | GitHub Team（Org）/ GitHub Pro（個人） |
| プライベートリポジトリの Actions 分数（2,000分/月超） | 有料課金 or 停止 |

### 無料プランで使える機能

- `.github/workflows/*.yml` でのワークフロー定義
- `claude-code-action`（Anthropic 公式）の実行（APIキーあれば）
- ブランチ保護ルール（required status checks, PR reviews）
- セルフホストランナー（分数制限なし）

## リポジトリ情報

- オーナー: `osushi0404-dev`（Organization）
- 可視性: Private
- 現在の GitHub Actions ワークフロー: なし（.github/workflows/ 未作成）
