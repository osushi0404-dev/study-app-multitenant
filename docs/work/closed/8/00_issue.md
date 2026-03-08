---
github_issue_number: 8
title: "docs: Work Item を GitHub Issue番号で統一し docs/work に集約"
state: open
branch: feature/I8-docs-work-restructure
created_at: 2026-03-03
---

# Issue #8: docs/work ディレクトリ再構成

## 概要

バイブコーディング運用の成果物（issue/plan/tests/review/closeout）を
**「1 GitHub Issue = 1 フォルダ」**に集約する。

- 主キー：GitHub Issue番号
- 成果物ルート：`docs/work/{open|closed}/{issue_number}/`
- 状態遷移：フォルダ単位で移動（`open/` → `closed/`）
- Review：通し番号（RID）を維持しつつ、Issue/Plan/PR に確実に紐づく形で保存

## 背景 / 課題

現状は成果物が `docs/issues`, `docs/plans`, `docs/tests`, `docs/reviews` に分散し、
同一作業の追跡・状態移動（open→closed）で漏れが起きやすい。
ローカル採番（XXX / IXXX 等）と GitHub Issue番号が一致しておらず、管理上の主キーが曖昧。

## 目的

1. GitHub Issue番号を管理上の主キーに統一
2. 成果物を `docs/work/**/{issue}/` に集約し、探索コストと移動漏れを排除
3. skills / CI / templates / runbooks を新構成に合わせて整合させる
4. 旧構成からの移行手段（スクリプト + 手順）を用意する

## 受け入れ条件（Acceptance Criteria）

- [ ] `docs/work/{open|closed}/{issue}/` が運用の唯一の成果物ルートになっている
- [ ] `/issue-bootstrap` で Work Item が新構成に作成される（タイトル指定・GH番号指定の両モード対応）
- [ ] `/plan` が `10_plan.md`, `20_test_auto.md`, `21_test_manual.md`, `30_review_*.md` を新構成に作成する
- [ ] `/implement` が計画承認ゲートを守りつつ新構成に記録を残す
- [ ] `/close` が `90_closeout.md` を完成させ、フォルダを `closed/` に移動できる
- [N/A] CI（plan-gate）— GitHub 無料プランのため Actions 未使用
- [ ] `issue-bootstrap` が2モード対応している（タイトル指定 / GH Issue番号指定）
- [ ] runbooks と CLAUDE.md の記述が新構成と矛盾しない

## 関連ドキュメント

- `.tmp/directory-restructure/restructure-policy_B.md`
- `.tmp/directory-restructure/restructure-directory-map_B.md`
