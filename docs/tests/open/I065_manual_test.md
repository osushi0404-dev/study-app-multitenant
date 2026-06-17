# I065 手動テスト

- **関連イシュー**: #131
- **計画書**: docs/plans/open/plan_I065.md
- **対象**: `.claude/skills/close/SKILL.md` の回収手順 / 遡及整理結果

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 実装後、`.claude/skills/close/SKILL.md` の step 1 を目視で読み、回収手順が既存の open→closed 移動の後段に自然に組み込まれているか確認 | 回収手順が step 1 末尾にあり、`ISSUE_NUM` の3桁バリデーション配下で動く（手順の前後関係が破綻していない） | Claude | 未実行 | Read で確認可 |
| 2 | 遡及整理後、`git log --oneline --follow docs/reviews/closed/I055_code_review_20260430_1012.md` 等で移動が履歴保持（rename）されているか確認 | `git mv` による rename として履歴が追跡でき、内容は消失していない | Claude | 未実行 | Bash で確認可 |
| 3 | 将来いずれかの open issue（例 I066）を実際に `/close` する際、当該 issue の timestamped 記録が直下から消え `closed/` に現れ、plan の `## レビュー結果` リンクがクリックで開けることをブラウザ/エディタで確認 | 直下に当該 issue の記録が残らず `closed/` に移動。plan 内リンクがリンク切れせず開ける | Human | 未実行 | 実 `/close` 実走時に観察（本イシュー完了の必須条件ではない・回帰観察） |

> No.1/No.2 は実装後に Claude が自動実行して記入する。No.3 は実 `/close` のタイミングで Human が観察する回帰確認（本イシューのマージ可否はブロックしない）。
