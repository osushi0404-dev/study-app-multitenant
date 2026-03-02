# Migration MANIFEST

PR1-PR3 で追加・更新したファイル一覧。

## ディレクトリ構造

```
docs/
  runbooks/
    legacy/            # PR3 で原本CLAUDE.mdを格納
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
    CLAUDE_original.md # PR3 で固定（上書き禁止）
    migration_map.yml  # PR3 で作成
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

### PR3: chore/claude-migration-content
#### 新規追加
- `docs/migration/CLAUDE_original.md`（原本固定・上書き禁止）
- `docs/migration/migration_map.yml`（原本→移植先の対応表）
- `docs/runbooks/legacy/CLAUDE.md.20260302`（原本のlegacyコピー）
- `docs/runbooks/issue-flow.md`（NEW: イシューフロー・採番ルール・統合フロー）
- `docs/runbooks/ux-rules.md`（NEW: UX重視の設計・実装ルール）
- `docs/runbooks/backend-check.md`（NEW: DB整合性・API統合テスト・要件適合性）
- `docs/runbooks/review-rules.md`（NEW: 文書間関係性・対応結果レビュー）
- `docs/runbooks/template-sync.md`（NEW: テンプレートファイル同期必須ルール）

#### 更新（内容拡充）
- `CLAUDE.md`（短いインデックスへ置き換え・詳細はrunbooks/skills参照）
- `docs/runbooks/workflow.md`（Claude Code実行ルール・承認ワークフロー・ブランチ戦略追記）
- `docs/runbooks/plan-writing-rules.md`（計画書作成詳細・一致性保証ルール追記）
- `docs/runbooks/common-commands.md`（エラー調査手順・API endpoints・注意事項追記）
- `.claude/skills/issue-bootstrap/SKILL.md`（採番・ブランチ作成・GitHub登録の詳細フロー追記）

### PR4: chore/claude-migration-verify（予定）
- `scripts/migration_verify/verify.sh` 他
- `docs/migration/reports/` 配下のレポート群
