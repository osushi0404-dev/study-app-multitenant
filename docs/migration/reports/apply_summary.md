# Apply Summary — claude hardening pack

- **Applied**: 2026-03-01
- **Source**: `_imports/claude_hardening_pack_with_install.zip`
- **Branch**: `chore/claude-pack-apply`

## 追加ファイル（Allowlist内）

| ファイル | 備考 |
|---------|------|
| `.claude/settings.json` | フック設定・権限設定 |
| `.claude/skills/issue-bootstrap/SKILL.md` | スキル: イシューブートストラップ |
| `.claude/skills/plan/SKILL.md` | スキル: 計画書作成 |
| `.claude/skills/implement/SKILL.md` | スキル: 実装 |
| `.claude/skills/fix-loop/SKILL.md` | スキル: 修正ループ |
| `.claude/skills/close/SKILL.md` | スキル: クローズ |
| `docs/runbooks/workflow.md` | ワークフロー定義 |
| `docs/runbooks/danger-ops.md` | 危険操作ガード |
| `docs/runbooks/plan-writing-rules.md` | 計画書記述ルール |
| `docs/runbooks/common-commands.md` | よく使うコマンド集 |
| `scripts/claude/hooks/pretooluse_guard.py` | `.claude/settings.json` のPreToolUseフックが参照するガードスクリプト |
| `.gitignore` | `settings.local.json`・`.tmp/`・`_imports/` をgit管理外に除外 |

## Allowlist外（未配置）

| ファイル | 理由 |
|---------|------|
| `CLAUDE.md` | Allowlist外のためPR3（Migration）で対応 |
| `MANIFEST.md` | Allowlist外のためPR2（Scaffold）で対応 |
| `INSTALL.md` | 作業用ドキュメント・配置不要 |
| `docs/issues/templates/` | PR2（Scaffold）で対応 |
| `docs/plans/templates/` | PR2（Scaffold）で対応 |
| `docs/tests/templates/` | PR2（Scaffold）で対応 |
| `docs/reviews/templates/` | PR2（Scaffold）で対応 |
| `.github/workflows/plan-gate.yml` | PATのworkflowスコープ不足のため除外（後で対応） |

## Allowlist外差分（作業用ファイル）
- `claude.mdの完全移行/` — 手順書・ZIP置き場（git管理外）
