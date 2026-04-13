# I043 自動テスト計画: レビュースキルに停止条件・重大度区分・高リスク判定を追加する

## 方針

スキルファイル（`.claude/skills/**/*.md`）はドキュメントであり、自動テスト対象外。

Backend・Frontend・DB の変更はないため、pytest・Jest は実行不要。

## CI 確認

PR の lint / format / typecheck / build は通常通り CI で確認する。
スキルファイルは YAML チェック（pre-commit hook）が通ることで品質を担保する。
