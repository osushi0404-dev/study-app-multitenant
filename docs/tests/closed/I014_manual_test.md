# I014 手動テスト計画

## テスト対象
- `/implement` スキルの動作変更確認
- `/code-review` スキルの新規動作確認
- `/test` スキルの新規動作確認
- `workflow.md` フロー定義の確認

## 手動テスト項目

| # | 確認内容 | 操作手順 | 期待結果 |
|---|---------|---------|---------|
| 1 | `/implement` が自動テストを実行しない | 任意のイシューで `/implement` を実行 | 自動テスト（pytest/Jest）が実行されず、push 後に `/code-review` を案内して停止する |
| 2 | `/code-review` が CI 確認から開始する | `/code-review I###` を実行 | `gh pr checks` を実行し CI 結果を確認してからレビューに進む |
| 3 | `/code-review` が受け入れ条件を照合する | CI pass 状態で `/code-review I###` を実行 | 計画書の受け入れ条件と実装差分を照合し、表形式で結果を報告する |
| 4 | `/test` が自動テストを実行する | `/test I###` を実行 | pytest + Jest が実行され、結果が報告される |
| 5 | `/test` が手動テスト確認を提示する | 自動テスト pass 後 | 手動テスト確認テーブルが提示されユーザー OK/NG 待ちになる |
| 6 | `workflow.md` が新フローを反映している | `docs/runbooks/workflow.md` を確認 | implement → code-review → test → close のフローが定義されている |
| 7 | `/close` スキルが変更されていない | `/close` の SKILL.md を確認 | 既存の close スキルの手順に変更がないこと |

## テスト結果
- 実施日: 未実施
- 結果: 未実施
