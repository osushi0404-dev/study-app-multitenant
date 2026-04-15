# I046 手動テスト

## テスト対象
- `.claude/skills/plan-issue-review/SKILL.md`
- `.claude/skills/code-review/SKILL.md`

---

## テストケース

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | plan-issue-review/SKILL.md を読み、P1 セクション「要件適合性・業務ロジックの正しさ」が存在するか確認 | セクションが存在し、受け入れ条件超えの仕様追加確認・マルチテナント制約確認・エッジケース確認等の項目が含まれる | Claude | | |
| 2 | plan-issue-review/SKILL.md を読み、P1 セクションが「ベストプラクティス」セクションの前に配置されているか確認 | P1 セクションが ベストプラクティス より先に現れる | Claude | | |
| 3 | plan-issue-review/SKILL.md を読み、P4 セクション「テスト妥当性・回帰防止」が存在するか確認 | セクションが存在し、再発防止テスト・実装詳細非依存・認可テスト確認の3項目が含まれる | Claude | | |
| 4 | plan-issue-review/SKILL.md を読み、セキュリティ セクションに SSRF・Path Traversal・Open Redirect が追記されているか確認 | OWASP 行に SSRF・Path Traversal・Open Redirect が含まれる | Claude | | |
| 5 | plan-issue-review/SKILL.md を読み、セキュリティ セクションに JWT/セッション・レート制限・監査ログ・Cookie/CORS が追加されているか確認 | 4項目すべてが含まれる | Claude | | |
| 6 | plan-issue-review/SKILL.md を読み、モダン セクションにローディング状態・破壊的操作確認導線・キャッシュ戦略の3項目が追加されているか確認 | 3項目すべてが含まれる | Claude | | |
| 7 | plan-issue-review/SKILL.md を読み、ベストプラクティス セクションに null 扱い・例外処理・ハードコード禁止・アンチパターンの4項目が追加されているか確認 | 4項目すべてが含まれる | Claude | | |
| 8 | plan-issue-review/SKILL.md を読み、P1・P4 セクションの末尾に「問題がなければ「問題なし」と記載する。」が含まれるか確認 | 両セクションとも末尾に該当テキストがある | Claude | | |
| 9 | plan-issue-review/SKILL.md の行数を確認 | 500 行以内 | Claude | | |
| 10 | code-review/SKILL.md を読み、P1 セクション「要件適合性・業務ロジックの正しさ」が存在するか確認 | セクションが存在し、仕様追加検出・マルチテナント制約・エッジケース確認等の項目が含まれる | Claude | | |
| 11 | code-review/SKILL.md を読み、P1 セクションが「ベストプラクティス」セクションの前に配置されているか確認 | P1 セクションが ベストプラクティス より先に現れる | Claude | | |
| 12 | code-review/SKILL.md を読み、P4 セクション「テスト妥当性・回帰防止」が存在するか確認 | セクションが存在し、再発防止テスト・非実装詳細依存・モック過多・認可テストの4項目が含まれる | Claude | | |
| 13 | code-review/SKILL.md を読み、P4 セクションが「モダンなウェブアプリ開発」と「P3」の間に配置されているか確認 | P4 がモダンセクションの直後、P3 の直前に現れる | Claude | | |
| 14 | code-review/SKILL.md を読み、セキュリティ セクションに SSRF・Path Traversal・Open Redirect が追記されているか確認 | OWASP 行に SSRF・Path Traversal・Open Redirect が含まれる | Claude | | |
| 15 | code-review/SKILL.md を読み、セキュリティ セクションに JWT/セッション・レート制限・監査ログ・Cookie/CORS が追加されているか確認 | 4項目すべてが含まれる | Claude | | |
| 16 | code-review/SKILL.md を読み、モダン セクションにローディング状態・破壊的操作・エラーメッセージの3項目が追加されているか確認 | 3項目すべてが含まれる | Claude | | |
| 17 | code-review/SKILL.md を読み、ベストプラクティス セクションに null 扱い・例外処理統一・ハードコード禁止・アンチパターンの4項目が追加されているか確認 | 4項目すべてが含まれる | Claude | | |
| 18 | code-review/SKILL.md の行数を確認 | 500 行以内 | Claude | | |
| 19 | P3・P5・P8 セクション（I045 追加分）が変更されていないか確認（両ファイル） | I045 で追加した内容がそのまま残っている | Claude | | |
