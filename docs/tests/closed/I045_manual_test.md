# I045 手動テスト

## 対象
- `.claude/skills/plan-issue-review/SKILL.md`
- `.claude/skills/code-review/SKILL.md`

## テストケース

| No | 確認内容 | 操作手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|---------|---------|---------|--------|--------|------|
| 1 | plan-issue-review に P3 セクションが存在する | SKILL.md を開き「P3. データ整合性・変更安全性」を検索 | セクションが存在し、設計段階の確認項目（DB制約・トランザクション・冪等性・FK削除挙動等）が列挙されている | Claude | OK | grep 結果: 50行目にヒット |
| 2 | plan-issue-review に P5 セクションが存在する | SKILL.md を開き「P5. 運用性・障害対応性」を検索 | セクションが存在し、設計段階の確認項目（ログ設計・タイムアウト・Feature Flag 等）が列挙されている | Claude | OK | grep 結果: 64行目にヒット |
| 3 | plan-issue-review に P8 セクションが存在する | SKILL.md を開き「P8. コスト・保守負荷」を検索 | セクションが存在し、設計段階の確認項目（コスト・属人化・維持コスト等）が列挙されている | Claude | OK | grep 結果: 74行目にヒット |
| 4 | code-review に P3 セクションが存在する | SKILL.md を開き「P3. データ整合性・変更安全性」を検索 | セクションが存在し、実装段階の確認項目（DB制約の実装確認・トランザクション実装確認等）が列挙されている | Claude | OK | grep 結果: 69行目にヒット |
| 5 | code-review に P5 セクションが存在する | SKILL.md を開き「P5. 運用性・障害対応性」を検索 | セクションが存在し、実装段階の確認項目（ログ実装確認・フォールバック実装確認等）が列挙されている | Claude | OK | grep 結果: 81行目にヒット |
| 6 | code-review に P8 セクションが存在する | SKILL.md を開き「P8. コスト・保守負荷」を検索 | セクションが存在し、実装段階の確認項目（過剰構成・属人化リスク等）が列挙されている | Claude | OK | grep 結果: 89行目にヒット |
| 7 | plan-issue-review が 500 行以内 | `wc -l .claude/skills/plan-issue-review/SKILL.md` を実行 | 500 以下の行数が表示される | Claude | OK | 136行 |
| 8 | code-review が 500 行以内 | `wc -l .claude/skills/code-review/SKILL.md` を実行 | 500 以下の行数が表示される | Claude | OK | 105行 |
| 9 | 既存セクション（ベストプラクティス等）が変更されていない | git diff で変更差分を確認 | 既存の「ベストプラクティス」「セキュリティ」「モダン開発」の記述が変更されていない | Claude | OK | 削除行に既存セクションの変更なし |
| 10 | plan-issue-review の配置順序が正しい | SKILL.md のセクション順を確認 | Claude Code BP → P3 → P5 → P8 → レビュー指摘一覧 の順になっている | Claude | OK | grep -n 結果で順序確認済み |
| 11 | code-review の配置順序が正しい | SKILL.md のセクション順を確認 | モダン開発 → P3 → P5 → P8 → 判定（step 7）の順になっている | Claude | OK | grep -n 結果で順序確認済み |
