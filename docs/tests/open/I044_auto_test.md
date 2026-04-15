# I044 自動テスト仕様書

## 概要
`/security-review` スキル新設・`/retro` 更新・`workflow.md` 更新のファイル存在・内容確認テスト。
バックエンド・フロントエンドのコード変更なし。

## テスト一覧

| No | テスト内容 | 確認コマンド / 方法 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|-----------|-------------------|---------|--------|--------|------|
| 1 | security-review/SKILL.md が存在する | ファイルパス確認 | ファイルが存在する | Claude | | |
| 2 | フロントマター: `name: security-review` が含まれる | Grep | ヒットする | Claude | | |
| 3 | フロントマター: `disable-model-invocation: true` が含まれる | Grep | ヒットする | Claude | | |
| 4 | フロントマター: `argument-hint` が含まれる | Grep | ヒットする | Claude | | |
| 5 | フロントマター: `allowed-tools` に Read/Glob/Grep/Edit が含まれる | Grep | 4ツールすべてヒット | Claude | | |
| 6 | SKILL.md が 500 行以内である | wc -l | 500 行以下 | Claude | | |
| 7 | SKILL.md に「Blocker」という文字列が含まれる（重大度区分） | Grep | ヒットする | Claude | | |
| 8 | SKILL.md に「セキュリティレビュー結果」という文字列が含まれる（追記手順） | Grep | ヒットする | Claude | | |
| 9 | SKILL.md に「/implement」の案内を停止する条件が含まれる | Grep | STOP または停止条件の記述がヒットする | Claude | | |
| 10 | retro/SKILL.md に「残余リスク処遇」が含まれる | Grep | ヒットする | Claude | | |
| 11 | retro/SKILL.md に「設計ルール昇格」が含まれる | Grep | ヒットする | Claude | | |
| 12 | workflow.md に「security-review」が含まれる（スキル一覧） | Grep | ヒットする | Claude | | |
| 13 | workflow.md に「高リスク判定 Yes」の案内が含まれる | Grep | ヒットする | Claude | | |
| 14 | workflow.md の移行テーブルに「security-review」のケースが含まれる | Grep | ヒットする | Claude | | |
