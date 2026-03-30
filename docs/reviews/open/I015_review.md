# I015 コードレビュー

## 基本情報
- **イシュー**: I015
- **レビュー対象**: `.claude/skills/code-review/SKILL.md`, `.claude/skills/plan-issue-review/SKILL.md`（新規）, `.claude/skills/plan-issue/SKILL.md`, `.claude/skills/issue-bootstrap/SKILL.md`, `CLAUDE.md`
- **レビュー日**: （実装後に記載）

---

## 受け入れ条件の照合

| # | 受け入れ条件 | 実装状況 | 備考 |
|---|------------|---------|------|
| 1 | `/code-review` にベストプラクティス・セキュリティ・モダン開発観点のチェック項目が追加されている | - | 実装後に確認 |
| 2 | `/plan-issue-review` スキルが新規作成され、計画書・テスト文書を同3観点でレビューする手順が含まれている | - | 実装後に確認 |
| 3 | `/plan-issue-review` でレビュー NG の場合に計画書修正→再実行のフローが明記されている | - | 実装後に確認 |
| 4 | 各観点のチェック項目が具体的（N+1、認証漏れ、OWASP Top 10 等） | - | 実装後に確認 |
| 5 | `/plan-issue` の末尾に `/plan-issue-review` への案内が追加されている | - | 実装後に確認 |
| 6 | `CLAUDE.md` のスキル一覧に `/plan-issue-review` が追加されている | - | 実装後に確認 |
| 7 | `docs/runbooks/workflow.md` のフロー・スキル一覧・フェーズ移行テーブルに `/plan-issue-review` が追加されている | - | 実装後に確認 |
| 8 | `docs/runbooks/workflow.md` のワークフロースキルリストに `/retro` が追加されている | - | 実装後に確認 |
| 9 | `docs/runbooks/issue-flow.md` のフロー図・フェーズ2詳細に `/plan-issue-review` ステップが追加されている | - | 実装後に確認 |
| 10 | `docs/runbooks/issue-flow.md` のフロー図に retro フェーズが追加されている | - | 実装後に確認 |
| 11 | 既存フローを壊していない（ステップ番号の整合性、STOP条件等） | - | 実装後に確認 |
| 12 | `/issue-bootstrap` 採番で I014 の次が I015 と正しく算出される | - | 実装後に確認 |

---

## レビューメモ
（実装後に記載）
