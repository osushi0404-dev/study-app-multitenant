# Migration MANIFEST

PR2（Scaffold）で追加したファイル一覧。

## ディレクトリ構造

```
docs/
  runbooks/
    legacy/            # PR0/PR3 で原本CLAUDE.mdを格納予定
  issues/
    templates/
      issue_template.md
  plans/
    templates/
      plan_template.md
  tests/
    templates/
      manual_test_template.md
      auto_test_template.md
  reviews/
    templates/
      review_template.md
  migration/
    MANIFEST.md        # このファイル
    reports/
      apply_summary.md  # PR1 で生成済み
scripts/
  migration_verify/    # PR4（Verify）でスクリプトを配置予定
```

## PR別ファイル追加履歴

### PR1: chore/claude-pack-apply
- `.claude/settings.json`
- `.claude/skills/issue-bootstrap/SKILL.md`
- `.claude/skills/plan/SKILL.md`
- `.claude/skills/implement/SKILL.md`
- `.claude/skills/fix-loop/SKILL.md`
- `.claude/skills/close/SKILL.md`
- `docs/runbooks/workflow.md`
- `docs/runbooks/danger-ops.md`
- `docs/runbooks/plan-writing-rules.md`
- `docs/runbooks/common-commands.md`
- `scripts/claude/hooks/pretooluse_guard.py`
- `.gitignore`
- `docs/migration/reports/apply_summary.md`

### PR2: chore/claude-migration-scaffold
- `docs/runbooks/legacy/.gitkeep`
- `docs/issues/templates/issue_template.md`
- `docs/plans/templates/plan_template.md`
- `docs/tests/templates/manual_test_template.md`
- `docs/tests/templates/auto_test_template.md`
- `docs/reviews/templates/review_template.md`
- `scripts/migration_verify/.gitkeep`
- `docs/migration/MANIFEST.md`

### PR3: chore/claude-migration-content（予定）
- `docs/migration/CLAUDE_original.md`
- `docs/migration/migration_map.yml`
- runbooks/skills への本文移植

### PR4: chore/claude-migration-verify（予定）
- `scripts/migration_verify/verify.sh` 他
- `docs/migration/reports/` 配下のレポート群
