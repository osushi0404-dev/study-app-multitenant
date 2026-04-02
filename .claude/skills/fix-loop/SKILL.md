---
name: fix-loop
description: When NG or tests fail: record facts, propose delta plan, get approval, fix, re-test.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /fix-loop

1) 失敗内容を「再現手順 / 期待値 / 実際値 / ログ」に分解して報告
2) 根本原因を調査・分析して報告（なぜ失敗したか）
   - セキュリティ観点も確認する（認証・認可の欠落、インジェクション、XSS、機密データ露出等に該当しないか）
3) 対応方法を複数案提示。各案に以下の軸でメリット・デメリットを添える:
   - セキュリティ影響（OWASP Top 10 関連リスクの有無、Django / React セキュリティガイドライン準拠）
   - ベストプラクティス適合（フレームワーク推奨パターン・コーディング規約との整合性）
   - 保守性・拡張性
   - リスク・副作用
4) 承認待ちで停止（ユーザーが案を選択）
5) 選択された案で修正
6) 自動テスト・リント・セキュリティスキャンを実行:
   - Backend: pytest / flake8（全エラー修正）/ bandit（MEDIUM 以上を修正対象。LOW は # nosec で抑制・理由記載必須）
   - Frontend: Jest / ESLint（error を修正対象、warning は記録）/ npm audit（high/critical を修正対象、moderate は記録・期限設定）
   - 成功（修正対象の警告・エラーなし）: 手順 7) へ
   - 失敗: 手順 1) に戻る（ループ）
7) 再発防止記録を docs/tests/open/$ARGUMENTS_auto_test.md に追記:
   - なぜ失敗したか
   - 何を変えたか
   - セキュリティ上の考慮点（該当する場合）
   - 次回どう防ぐか
