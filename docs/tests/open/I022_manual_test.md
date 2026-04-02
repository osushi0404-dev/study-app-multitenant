# I022 手動テスト: onboarding ドキュメント追加

| No | 手順 | 期待結果 | 実結果 | 備考 |
|---:|------|----------|--------|------|
| 1 | `docs/runbooks/onboarding.md` が存在することを確認 | ファイルが存在する | | |
| 2 | スキル一覧テーブルの各スキル名が `.claude/skills/` のディレクトリ名と一致することを確認 | 全スキルが一致 | | |
| 3 | CI 内容（flake8・bandit・pytest・tsc・ESLint・Jest）が `.github/workflows/ci.yml` と一致することを確認 | 全項目が一致 | | |
| 4 | ブランチ戦略の記載が `docs/runbooks/workflow.md` と矛盾しないことを確認 | 矛盾なし | | |
| 5 | ドキュメント構成（`open/closed/templates`）が実際のディレクトリ構成と一致することを確認 | 一致 | | |
| 6 | 参照先リンク（runbooks・rules）のファイルパスが実在することを確認 | 全パスが存在する | | |

結論: OK / NG
