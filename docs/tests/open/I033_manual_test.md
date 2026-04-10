# I033 手動テスト: GitHub Projects カンバンと Milestones（Phase 1〜3）の設定

| No | 手順 | 期待結果 | 実結果 | 備考 |
|---:|------|----------|--------|------|
| 1 | GitHub リポジトリの Issues → Milestones を開く | Phase 1・Phase 2・Phase 3 の 3件が表示される | OK | CLI 確認済み |
| 2 | Phase 1 Milestone を開く | I028（#58）・I029（#60）が紐づいている | OK | CLI 確認済み |
| 3 | Phase 2 Milestone を開く | I030（#71）・I031（#69）・I032（#73）・I033（#76）・I034（#78） が紐づいている | OK | CLI 確認済み |
| 4 | Phase 3 Milestone を開く | I035（#79）・I036（#80） が紐づいている | OK | CLI 確認済み |
| 5 | GitHub Projects タブを開く | "AI Dev Improvement（Phase 1〜3）" ボードが存在する | OK | CLI 確認済み（Project #1） |
| 6 | Projects ボードを開く | I028〜I036 の全 Issue（9件）が登録されている | OK | totalCount: 9 確認済み |
| 7 | I034.md を確認 | `## 関連資料` に `- GitHub Issue: #78` が追記されている | OK | |
| 8 | I035.md を確認 | `## 関連資料` に `- GitHub Issue: #79` が追記されている | OK | |
| 9 | I036.md を確認 | `## 関連資料` に `- GitHub Issue: #80` が追記されている | OK | |

結論: OK（2026-04-11）
