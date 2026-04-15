# 手動テスト: I047 計画書作成・実装スキルを8観点フレームワークに整合させる

## テスト方針

スキルファイル・Runbook の Markdown 変更のため、自動テストは存在しない。
以下の目視確認で受け入れ条件を検証する。

---

## テストケース

| No | 確認対象 | 確認手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|----------|----------|----------|--------|--------|------|
| 1 | grill-me P8（必須確認） | `.claude/skills/grill-me/SKILL.md` の「必須確認」セクションを読む | 「コスト・保守負荷が妥当か（インフラコスト・運用者の手作業増加・属人化リスク・長期維持コスト・過剰構成）」に相当する項目が存在する | Claude | OK | |
| 2 | grill-me P3（質問観点） | `.claude/skills/grill-me/SKILL.md` の「質問の観点（該当する場合のみ）」を読む | 「データ整合性設計（DB変更がある場合）」に相当する項目が存在する | Claude | OK | |
| 3 | grill-me P5（質問観点） | `.claude/skills/grill-me/SKILL.md` の「質問の観点（該当する場合のみ）」を読む | 「運用設計（外部API・非同期処理・バッチがある場合）」に相当する項目が存在する | Claude | OK | |
| 4 | plan-writing-rules セクション10 | `docs/runbooks/plan-writing-rules.md` を読む | セクション10「データ整合性設計（DB変更がある場合のみ）」が追加されており、DB制約・トランザクション・マイグレーションの記載がある | Claude | OK | |
| 5 | plan-writing-rules セクション11 | `docs/runbooks/plan-writing-rules.md` を読む | セクション11「運用設計（外部API・非同期処理・バッチがある場合のみ）」が追加されており、ログ・タイムアウト・Feature Flag の記載がある | Claude | OK | |
| 6 | plan-writing-rules セクション12 | `docs/runbooks/plan-writing-rules.md` を読む | セクション12「コスト・保守見積もり（該当する場合のみ）」が追加されており、インフラコスト・属人化リスクの記載がある | Claude | OK | |
| 7 | plan-issue P3/P5/P8 チェック | `.claude/skills/plan-issue/SKILL.md` を読む | 「データ整合性・運用性・コスト設計チェック（該当する場合）」ブロックが、セキュリティチェックの後に存在する | Claude | OK | |
| 8 | implement P3/P5 チェック | `.claude/skills/implement/SKILL.md` を読む | 「P3・P5 実装確認チェック（該当する場合）」ブロックが、TDD サイクルと step 1 の間に存在する | Claude | OK | |
| 9 | 既存内容との重複なし | 各ファイルの追加箇所と既存内容を照合する | 追加した確認項目が既存の確認項目と実質的に重複していない | Claude | OK | grill-me P5 と既存「フォールバック方針」は ops-facing vs user-facing で分離。他も観点・粒度が異なり重複なし |
| 10 | I046 レビュー観点との対応 | I045/I046 の plan-issue-review・code-review の P3/P5/P8 確認項目と本変更の内容を照合する | 上流で確認した観点が下流レビューでも同じ言葉・分類で参照できる | Claude | OK | P3/P5/P8 全観点で上流（grill-me/plan-issue/implement）と下流（plan-issue-review/code-review）が同用語でカバー |
