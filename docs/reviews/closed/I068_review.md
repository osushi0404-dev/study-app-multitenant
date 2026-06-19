# I068 レビュー記録

- **関連計画書**: docs/plans/open/plan_I068.md
- **関連イシュー**: #140 / **Draft PR**: #142

## レビュー対象
- `scripts/claude/check-memo-body-paths.sh`（新規・P3 決定論ゲート）
- `.claude/skills/grill-me/SKILL.md`（P3 実行 do）
- `docs/runbooks/plan-writing-rules.md`（P2 拡張・P1 do）
- `.claude/review-agents/plan-reviewer.md`（P1/P2 gate・P3 backstop）
- `.claude/review-agents/code-reviewer.md`（P1 gate）

## レビュー観点
- 受け入れ条件（P1/P2/P3 の do＋gate＋P3 スクリプト＋I067 逆引き）を満たすか
- P3 スクリプトの引数検証・read-only（パストラバーサル防止）が実装されているか
- P3 の誤検出（意図的除外・バックティック無し・glob）がソフト警告として許容範囲か
- P3 が P2 の決定論的インスタンスとして一本化され、重複していないか
- 新規スクリプトが shellcheck を通るか
- セキュリティ影響（app/依存変更なし・read-only）の妥当性

## plan-issue-review 記録
- 実行: 2026-06-19 / レビューファイル: `docs/reviews/I068_plan_review_20260619_0938.md`
- **VERDICT: OK**（高リスク判定: No）→ `/implement I068` 可
- 指摘 5 件すべて計画書/テスト文書に反映済み:
  - W1+Info2: 終了コード規約を 0=整合/1=不一致/2=実行不可（不正引数・未検出）に明確化。TC-E の期待値（exit 2・対象外ファイル非出力）を補完
  - W2: 計画書 §5 ステップ5 の TC 参照を TC-E・M → **TC-N（実イシュー ドッグフード）** に訂正
  - W3: auto_test ヘッダー・計画書 §6 を **TC-A〜TC-N** に統一
  - Info1: P3-b/c・P2-a/b・P1-a/b の具体文言案を計画書 §5 に追記（TC grep キーワードと整合）

## /test 記録
- 実行: 2026-06-19（計画駆動経路）
- 自動テスト（正＝auto_test.md TC-A〜N）: **PASS=15 / FAIL=0**。既定 pytest/Jest/E2E は **非該当**（app コード変更なし）
- 手動テスト No.1〜4（Claude）: すべて OK（誤検出レビュー・I067 逆引き実証・P2 整合・P3↔P2 一本化）
- 手動テスト No.5（Human）: gate 文言の明確性 最終サインオフをユーザーに依頼中

## code-review 記録
- 実行: 2026-06-19 / レビューファイル: `docs/reviews/I068_code_review_20260619_1017.md`
- **VERDICT: OK**（高リスク判定: No）。受け入れ条件 1〜4 すべて ✅
- **AC4 検出ログ（参照）**: I067 の 3 件を新ルール/ゲートに当てはめた検出ログは `docs/tests/open/I068_manual_test.md` No.1（I067 の brace-glob を advisory 検出）・No.2（W2 を再現しゲートが retro/close 未反映を exit 1 で検出）に記録。
- Low 指摘 3 件の対応（いずれも Low のため CI で十分・再レビュー不要）:
  - Low①（運用性）: git リポジトリ外で exit 128 になり 0/1/2 規約から外れる → `git rev-parse … || exit 2` で決定論化（`/tmp` 実行で exit 2 を確認）
  - Low②（BP）: メモにパス無し時の早期 return を追加（空文字を comm に渡さない・意図明確化）
  - Low③（P4）: 本記録に AC4 検出ログの参照先を明記（上記）
- 修正後 回帰: スクリプト TC PASS=7 FAIL=0・shellcheck Pass
