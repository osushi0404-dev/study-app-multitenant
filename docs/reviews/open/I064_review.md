# I064 レビュー: レビュー命名・状態管理規約の一本化（reviewXXX → IXXX_review）

## 変更概要
- レビュー/計画書ヘッダの命名・状態管理規約を、旧系統（`reviewXXX` 通し番号・`_post` 別ファイル・`in_progress` 状態）から新系統（`IXXX_review.md` / `IXXX_{code,plan,issue}_review_<ts>.md`・open/closed の2状態）へ一本化する。

## 変更点
- `docs/runbooks/review-rules.md`: 命名・状態・採番の新系統是正、`_post` 通し番号採番フローの簡素化、`review001〜003` 履歴注記。命名無関係部分（A/B/C/D・準拠チェックリスト）は保持。
- `docs/runbooks/plan-writing-rules.md`: ヘッダ基本情報ブロック（L177-183）を是正（`作成根拠資料`/`実装後評価`/`Draft PR`）。
- `docs/runbooks/issue-flow.md`: 計画書命名 L241 を `plan_I###.md` に、close グロブ L347/L365 を `plan_IXXX*.md` に是正。

## 影響範囲
- Backend/Frontend/DB/Config: Config（runbook ドキュメント規約のみ）。コード・DB・依存・スクリプト・スキル・テンプレートの変更なし。

## テスト結果
- 自動: ✅ 全 PASS（`docs/tests/open/I064_auto_test.md` TC-01〜08・TC-07b/TC-02b、2026-06-15 実行）
- 手動: 通読確認は `/test` 時に実施予定（`docs/tests/open/I064_manual_test.md`・Claude 実施項目のみ）

## 計画との差分
- あり（軽微）: 計画策定時に `issue-flow.md` の close 用グロブ L347/L365 を新旧両対応 `plan_IXXX*.md` へ是正するスコープ追加をユーザー承認のうえ反映（イシュー実装対象表も更新済み）。
- 参照健全性メモ: `review-rules.md` 末尾の `docs/reviews/README.md` 参照は I064 以前から壊れたリンク。命名規約と無関係のため本イシューでは原文保持（フォローアップ候補）。

## ロールバック
- `git checkout -- docs/runbooks/{review-rules,plan-writing-rules,issue-flow}.md` で復元、または PR を revert。コード/DB 変更がないため再起動・マイグレーション不要。
