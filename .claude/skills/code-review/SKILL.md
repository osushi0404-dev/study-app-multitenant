---
name: code-review
description: Verify CI passes and review implementation against acceptance criteria.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Glob, Grep
---

# /code-review

前提: /implement 完了・push 済み。

1) CI 確認:
   ```bash
   gh pr checks [PR番号]
   ```
   - 全ジョブ pass: 手順 2) へ
   - pending: 数分待って再確認してから手順 2) へ
   - 失敗あり: STOP。失敗ジョブのログを確認して報告し、修正後に再 push するよう案内する。

2) 計画書・イシューの受け入れ条件を読む:
   - docs/issues/open/$ARGUMENTS.md
   - docs/plans/open/plan_$ARGUMENTS.md

3) 実装差分を確認:
   ```bash
   git diff origin/develop...HEAD --name-only
   git diff origin/develop...HEAD
   ```

4) 各受け入れ条件について実装との照合を行い、結果を以下の形式で報告:
   ```
   ## コードレビュー結果
   | # | 受け入れ条件 | 実装状況 | 重大度 | 備考 |
   |---|------------|---------|--------|------|
   | 1 | ...        | ✅ 実装済み / ⚠️ 一部不足 / ❌ 未実装 | - / Blocker / High / Medium / Low | ... |
   ```
   実装状況が ✅ の場合、重大度列は「-」とする。

5) コードの品質・ロジック上の問題があれば重大度を付けて追記する

6) ベストプラクティス・セキュリティ・モダン開発観点のレビュー:
   実装差分を以下の観点で確認し、問題があれば重大度（Blocker/High/Medium/Low）を付けて報告する。問題がなければ「問題なし」と記載する。

   重大度の定義:
   - **Blocker**: 次工程へ進めない（認可漏れ・要件未達・重大セキュリティ欠陥等）
   - **High**: 原則として修正してから進める（運用事故・重大不具合の高リスク）
   - **Medium**: 当該PRでの修正推奨（難しければチケット化して期限を切る）
   - **Low**: 改善提案（今回見送りの場合は理由を残す）

   **ベストプラクティス:**
   - rules/ultimate_django_coding_standards.md（Backend）/ rules/react-coding-standards-integrated.md（Frontend）の重要原則との重大な逸脱がないか
   - 責務分離が適切か（Fat View・Fat Component になっていないか）
   - 重複・冗長なコードが生まれていないか

   **セキュリティ:**
   - 認証・認可チェックの漏れ（未認証アクセス可能なエンドポイント、権限外操作の許容）
   - 入力検証・サニタイズ漏れ（シリアライザ/フォームによる検証があるか）
   - SQLインジェクション・XSS・CSRF 等 OWASP Top 10 相当のリスク
   - 秘密情報（APIキー・パスワード）のハードコードや意図しない露出
   - 過剰な権限付与・情報過多なレスポンス

   **モダンなウェブアプリ開発:**
   - REST API 設計の一貫性（HTTPステータスコード・命名規則・レスポンス形式）
   - 非同期処理・エラーハンドリングが適切に実装されているか
   - パフォーマンス上の明らかな問題（N+1 クエリ、不要な全件取得、未ページネーション）
   - アクセシビリティ（Frontend: aria属性・セマンティックHTML・キーボード操作）

   **P3. データ整合性・変更安全性:**
   変更対象に DB・マイグレーション・API が含まれる場合に確認する（含まれない場合は「対象外」と記載）:
   - DB制約（NOT NULL・UNIQUE・FK・CHECK）が実装に反映されているか
   - アプリ側バリデーションとDB制約の責務分担が計画書の設計方針通りか
   - トランザクション境界が適切に実装されているか
   - 冪等性が必要な処理に二重送信対策が実装されているか
   - 同時更新・競合更新・排他制御が考慮されているか
   - マイグレーション手順が安全か（ロールバック可能か）
   - 後方互換性を壊す変更になっていないか
   - ForeignKey 削除時の挙動（CASCADE/PROTECT/SET_NULL）が意図と一致しているか
   - インデックス設計が適切か（必要なインデックスがあるか、過剰・不足がないか）

   **P5. 運用性・障害対応性:**
   - ログが構造化され原因追跡に必要な情報を持っているか（request_id・user_id・tenant_id）
   - タイムアウト・リトライ・フォールバックが計画書の方針通りに実装されているか
   - 外部API・非同期ジョブ・バッチ失敗時の扱いが実装されているか
   - 切り戻ししやすい実装になっているか
   - Runbook・管理者向け導線が必要な箇所で実装されているか
   - 新機能の監視項目・アラートが定義通りに実装されているか

   **P8. コスト・保守負荷:**
   - 要件規模に対して過剰な構成を採用していないか
   - 長期保守で属人化しやすい実装になっていないか（複雑すぎる処理・マジックナンバー等）
   - 監視・テスト・デプロイ・リリース運用の維持コストが増加していないか
   - ドキュメント（README・APIドキュメント・Runbook）の更新が必要な箇所で更新されているか

7) 指摘の重大度に基づいて判定する:

   - **Blocker あり**: ⛔ STOP。以下を出力して停止する。
     「Blocker が残っています。`/fix-loop $ARGUMENTS` で修正後、`/code-review $ARGUMENTS` を再実行してください。」
     `/test` は案内しない。

   - **Blocker なし・High あり**: ❌ レビュー NG。
     「`/fix-loop $ARGUMENTS` を実行してください。fix-loop 完了後は `/code-review $ARGUMENTS` に戻ってください。」

   - **Blocker・High なし**: ✅ コードレビュー完了。
     「`/test $ARGUMENTS` を実行してください。」
