# I054 手動テスト: サブエージェントレビューと差し戻しファースト原則の導入

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `.claude/review-agents/plan-reviewer.md` が存在するか確認 | ファイルが存在する | Claude | OK | |
| 2 | `.claude/review-agents/code-reviewer.md` が存在するか確認 | ファイルが存在する | Claude | OK | |
| 3 | `plan-reviewer.md` の冒頭に `<instructions>` XML デリミタブロックが含まれているか確認 | `<instructions>` タグが存在する | Claude | OK | |
| 4 | `plan-reviewer.md` に 3 段階重大度（Blocker/Warning/Info）の定義が含まれているか確認 | 3 段階が明記されている | Claude | OK | |
| 5 | `plan-issue-review/SKILL.md` のフロントマターに `disable-model-invocation: false` が設定されているか確認 | `false` になっている | Claude | OK | |
| 6 | `plan-issue-review/SKILL.md` の `allowed-tools` に `Agent, Edit, Bash` が含まれているか確認 | 3 ツールが含まれている | Claude | OK | |
| 7 | `plan-issue-review/SKILL.md` に「サブエージェントには Edit・Bash を渡さない」旨の記述があるか確認 | `allowed_tools: [Read, Glob, Grep]`（Edit・Bash 除外）が明記されている | Claude | OK | |
| 8 | `code-review/SKILL.md` のフロントマターに `disable-model-invocation: false` が設定されているか確認 | `false` になっている | Claude | OK | |
| 9 | `plan-issue-review/SKILL.md` に `$(cat [ファイルパス])` 経由の `gh pr review` 投稿が記述されているか確認 | `cat` 経由が明記されている | Claude | OK | |
| 10 | `plan-issue-review/SKILL.md` に `--body` への直書き禁止が明記されているか確認 | 禁止が明記されている | Claude | OK | |
| 11 | `plan-issue-review/SKILL.md` で `gh pr review` 失敗時にノンブロッキング処理（エラー報告して継続）が記述されているか確認 | ノンブロッキング処理が明記されている | Claude | OK | |
| 12 | `plan-issue-review/SKILL.md` で Agent 呼び出し時のモデルに `claude-sonnet-4-6` が指定されているか確認 | モデルが指定されている | Claude | OK | |
| 13 | `plan-issue-review/SKILL.md` で Agent の `allowed_tools` に `Edit`・`Bash` が含まれていないか確認 | サブエージェントの allowed_tools は `Read, Glob, Grep` のみ | Claude | OK | |
| 14 | `grill-me/SKILL.md` に具体化追求ルールが追加されているか確認 | 「動詞止まり」「方向性のみ」への追加質問ルールが存在する | Claude | OK | |
| 15 | `plan-issue/SKILL.md` に文書品質ゲート（6 項目チェックリスト）が追加されているか確認 | 6 項目のチェックリストが存在する | Claude | OK | |
| 16 | `retro/SKILL.md` に指示ファイルメンテナンス確認項目が追加されているか確認 | `plan-reviewer.md`/`code-reviewer.md` の見直し観点が存在する | Claude | OK | |
| 17 | `docs/tests/templates/auto_test_template.md` に品質基準コメントが追加されているか確認 | コメントブロックが存在する | Claude | OK | |
| 18 | `docs/tests/templates/manual_test_template.md` に「実施者」列と品質基準コメントが追加されているか確認 | 列とコメントが存在する | Claude | OK | |
| 19 | 実際に `/plan-issue-review I054` を実行し、サブエージェントが起動されることを確認 | Agent ツールが呼び出されるログが出力される | Human | | 実装完了後に実施 |
| 20 | `/plan-issue-review I054` 実行後、`docs/reviews/` にタイムスタンプ付きレビューファイルが作成されることを確認 | `I054_plan_review_YYYYMMDD_HHMM.md` が存在する | Human | | 実装完了後に実施 |
| 21 | `/plan-issue-review I054` 実行後、GitHub PR #113 にコメントが投稿されることを確認 | PR タイムライン上にレビューコメントが表示される | Human | | 実装完了後に実施 |
| 22 | PR コメントの内容がローカルの `docs/reviews/` ファイルと一致することを確認 | 内容が完全一致（verbatim） | Human | | 実装完了後に実施 |

結論: OK / NG
