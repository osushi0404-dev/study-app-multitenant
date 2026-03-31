---
name: plan-issue-review
description: Review plan and test docs for best practices, security, and modern web dev.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep
---

# /plan-issue-review

前提: /plan-issue 完了・生成ドキュメント作成済み。

1) 対象ドキュメントを読む:
   - docs/issues/open/$ARGUMENTS.md
   - docs/plans/open/$ARGUMENTS_plan.md（または plan_$ARGUMENTS_*.md）
   - docs/tests/open/$ARGUMENTS_manual_test.md
   - docs/tests/open/$ARGUMENTS_auto_test.md

2) ベストプラクティス・セキュリティ・モダン開発観点でレビューし、結果を報告する:
   問題がなければ各観点「問題なし」と記載する。

   **ベストプラクティス:**
   - rules/ultimate_django_coding_standards.md / rules/react-coding-standards-integrated.md の重要原則に反する設計が計画書に含まれていないか
   - 責務分離が適切か（Fat View・Fat Component になる設計になっていないか）
   - テストケースが適切なレベルで書かれているか（ユニット/結合/E2E の使い分け）

   **セキュリティ:**
   - エンドポイントごとの認証・認可要件が計画書に明示されているか
   - 入力検証・サニタイズの実装方針が含まれているか
   - OWASP Top 10 相当のリスク（XSS・CSRF・SQLi・認可不備等）への対策が考慮されているか
   - テストケースに権限外アクセス拒否・不正入力のケースが含まれているか

   **モダンなウェブアプリ開発:**
   - REST API 設計が一貫しているか（HTTPステータスコード・命名規則・レスポンス形式）
   - フロントエンドの状態管理・非同期処理の設計方針が適切か
   - パフォーマンス上の懸念（N+1・ページネーション設計等）が考慮されているか
   - アクセシビリティ要件が必要な場合に含まれているか

   **Claude Code ベストプラクティス（`.claude/skills/` 変更を含む場合のみ）:**
   変更対象に `.claude/skills/` が含まれる場合、以下を確認する（対象外なら「対象外」と記載）:
   - `allowed-tools` で最小権限が設定されているか
   - 副作用のある操作（commit・push・デプロイ等）に `disable-model-invocation: true` が設定されているか
   - `argument-hint` が記載されているか
   - `description` に「いつ使うか」が含まれているか（250文字以内）
   - 指示文に明確な停止条件・完了条件が記載されているか
   - `$ARGUMENTS` 等の変数が一貫して使われているか
   - SKILL.md が 500行以内か（超える場合は supporting files を推奨）
   問題がなければ「問題なし」と記載する。

3) ユーザーへ OK/NG の判断を求める:
   - OK: 「✅ プランレビュー完了。`/implement $ARGUMENTS` を実行してください。」
   - NG: 「❌ レビュー NG。計画書・テスト文書を修正してから `/plan-issue-review $ARGUMENTS` を再実行してください。」
