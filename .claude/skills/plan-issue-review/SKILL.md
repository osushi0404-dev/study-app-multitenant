---
name: plan-issue-review
description: Review plan and test docs for best practices, security, and modern web dev.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Edit, Glob, Grep
---

# /plan-issue-review

前提: /plan-issue 完了・生成ドキュメント作成済み。

1) 対象ドキュメントを読む:
   - docs/issues/open/$ARGUMENTS.md
   - docs/plans/open/plan_$ARGUMENTS.md
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

   **レビュー指摘一覧（全観点チェック後に出力）:**
   発見した指摘を以下のテーブル形式でまとめて出力する。指摘がなければ「指摘なし」と記載する。
   ```
   ## レビュー指摘一覧
   | 重大度 | 観点 | 指摘内容 | 該当箇所 | 対応 |
   |--------|------|---------|---------|------|
   | Blocker | セキュリティ | 認可チェックが計画書に明示されていない | API設計 | 実装前に修正必須 |
   | High    | BP   | Fat View になる設計 | ... | 当該PRで修正推奨 |
   | Medium  | モダン | ページネーション未考慮 | ... | チケット化推奨 |
   | Low     | BP   | 変数名の微妙なズレ | ... | 改善提案 |
   ```
   重大度の定義:
   - **Blocker**: 次工程へ進めない（認可漏れ・要件未達・設計上の重大リスク等）
   - **High**: 原則として修正してから進める（運用事故・重大不具合の高リスク）
   - **Medium**: 当該PRでの修正推奨（難しければチケット化して期限を切る）
   - **Low**: 改善提案（今回見送りの場合は理由を残す）

   **高リスク判定（全観点チェック後に出力）:**
   以下の条件に1つでも直接該当する場合、高リスク: Yes と判定する。
   - 認証・認可・ロール変更
   - マルチテナント境界変更
   - 管理画面追加・変更
   - ファイルアップロード/ダウンロード
   - 外部公開API追加・変更
   - Webhook・外部API連携
   - 個人情報・機微情報の新規取り扱い
   - DBスキーマ重要変更
   - 既存事故の再発リスクが高い変更
   - 画面制御していてもAPI直叩きで事故りうる変更

   判定結果を以下の形式で出力する:
   ```
   ## 高リスク判定
   判定: Yes / No
   該当条件: [リスト、なければ「なし」]
   推奨: （Yes の場合）`/implement` 前に `/security-review $ARGUMENTS` を実行してください。
        （No の場合）そのまま `/implement $ARGUMENTS` へ進めてください。
   ```

3) レビュー指摘一覧の重大度に基づいて判定し、対応する:

   - **Blocker あり**: ⛔ STOP。以下を出力して停止する。
     「Blocker が残っています。修正後に `/plan-issue-review $ARGUMENTS` を再実行してください。」
     `/implement` は案内しない。

   - **Blocker なし・High あり**: ❌ レビュー NG。High 以上の指摘を修正することを推奨する。
     - **Edit/Write で修正できる問題**（記述の追加・補足・誤字等）: ユーザーに依頼せず自分で修正し、コミットしてからレビューを再実行する
     - **設計判断が必要な問題**（スコープ変更・方針転換・トレードオフの選択等）: 選択肢を提示してユーザーに確認を求め、承認後に修正する
     - 自己修正した場合: 修正内容を説明してからレビューを再実行する

   - **Blocker・High なし**: ✅ プランレビュー完了。
     高リスク判定 Yes の場合: 「`/security-review $ARGUMENTS` を実行してから `/implement $ARGUMENTS` へ進めてください。」
     高リスク判定 No の場合: 「`/implement $ARGUMENTS` を実行してください。」
