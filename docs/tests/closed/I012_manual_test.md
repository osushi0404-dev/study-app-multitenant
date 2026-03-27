# I012 手動テスト: クローズ済みイシューファイルの open フォルダ残留対応

| No | 手順 | 期待結果 | 実結果 | 備考 |
|---:|------|----------|--------|------|
| 1 | `ls docs/issues/open/` を実行 | 006.md, 007.md, 010.md, 011.md が存在しない（012.md のみ） |  |  |
| 2 | `ls docs/plans/open/` を実行 | I006_plan.md, I010_plan.md, I011_plan.md が存在しない（I012_plan.md のみ） |  |  |
| 3 | `ls docs/tests/open/` を実行 | I006_*, I010_*, I011_* が存在しない（I012_* のみ） |  |  |
| 4 | `ls docs/reviews/open/` を実行 | I006_review.md, I010_review.md, I011_review.md が存在しない（I012_review.md のみ） |  |  |
| 5 | `ls docs/issues/closed/` を実行 | 006.md, 007.md, 010.md, 011.md が存在する（削除されていない） |  |  |
| 6 | `cat .claude/settings.json` で allow セクションを確認 | `Bash(mv docs/*/open/* docs/*/closed/)` と `Bash(rm docs/*/open/*)` が含まれている |  |  |
| 7 | `cat .claude/skills/close/SKILL.md` のステップ1を確認 | `mv` コマンドがファイル種別ごとに具体的に記載されている |  |  |

結論: OK / NG
