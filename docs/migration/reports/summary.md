# 移行検証レポート

- **実行日時**: 2026-03-02 16:02:05
- **総合判定**: NG

## チェック結果

| チェック項目 | 件数 | 判定 |
|-------------|------|------|
| atomic_lines 総数 | 571 行 | — |
| 未一致行（移植漏れ） | 114 件 | ❌ NG |
| 参照切れ | 0 件 | ✅ OK |
| Skill lint エラー | 0 件 | ✅ OK |
| シークレット検出 | 0 件 | ✅ OK |

## 詳細レポート

- 未一致一覧: `docs/migration/reports/migration_report.json`
- 原本行リスト: `docs/migration/reports/atomic_lines.txt`
- 参照切れ: `docs/migration/reports/broken_references.txt`
- Skill lint: `docs/migration/reports/skills_lint_report.json`
- シークレット: `docs/migration/reports/secrets_scan_report.txt`

## 再実行コマンド

```bash
bash scripts/migration_verify/verify.sh
```

## 次のアクション

❌ NG のため、このPRはマージしないでください。
PR3（chore/claude-migration-content）へ戻り、以下を修正してください:

- 移植漏れ 114 件: `docs/migration/reports/migration_report.json` の `unmatched` を参照
