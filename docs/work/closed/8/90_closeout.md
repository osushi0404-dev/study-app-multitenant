---
github_issue_number: 8
rid: R00001
closed_at: 2026-03-08
pr: "#9"
---

# 完了サマリ — Issue #8: docs/work ディレクトリ再構成

## 成果

- `docs/work/{open|closed}/{issue}/` を成果物の唯一のルートとして確立
- `issue-bootstrap` スキルを2モード対応に変更（Mode A: タイトル指定 / Mode B: GH番号指定）
- 全5スキルのパスを新構成に更新
- `scripts/build_indices.py` と `move_work_item.sh` を新設
- 旧ディレクトリ（`docs/issues/`, `docs/plans/`, `docs/tests/`, `docs/reviews/`）を DEPRECATED 化
- CI gate は GitHub 無料プランのため除外（N/A）

## 変更ファイル

```
.claude/skills/close/SKILL.md
.claude/skills/fix-loop/SKILL.md
.claude/skills/implement/SKILL.md
.claude/skills/issue-bootstrap/SKILL.md
.claude/skills/plan/SKILL.md
CLAUDE.md
docs/indices/REVIEW_INDEX.md
docs/indices/WORK_INDEX.md
docs/indices/review_seq.json
docs/issues/DEPRECATED.md
docs/plans/DEPRECATED.md
docs/reviews/DEPRECATED.md
docs/runbooks/issue-flow.md
docs/runbooks/plan-writing-rules.md
docs/runbooks/workflow.md
docs/tests/DEPRECATED.md
docs/work/closed/.gitkeep
docs/work/open/.gitkeep
docs/work/templates/（7種）
scripts/build_indices.py
scripts/move_work_item.sh
```

## テスト結果

- 自動テスト T01〜T05, T07〜T08: OK
- T06（CI）: N/A（GitHub 無料プランのため）
- 手動テスト: 次回イシュー時に実地確認

## 関連リンク

- GH Issue: #8
- PR: #9
- レビュー: R00001

## 成果物一覧

```
docs/work/closed/8/
  00_issue.md
  10_plan.md
  20_test_auto.md
  21_test_manual.md
  30_review_R00001.md
  90_closeout.md  ← このファイル
```
