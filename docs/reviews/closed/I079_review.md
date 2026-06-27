# I079 実装レビュー（案D・実装済み）

- 関連イシュー: #158
- 計画書: docs/plans/open/plan_I079.md
- PR: #159
- 実装コミット: `97134bc`（フック＋settings）/ `42fd991`（docs）

## レビュー対象（案D）
- `.claude/settings.json`: `permissions.allow`（backend/frontend Edit/Write ＋ `bash scripts/claude/*`）、`hooks.PreToolUse` の `Edit|Write` 登録、実効しない高リスク `deny` の撤去、機密 `deny` の維持。
- `scripts/claude/hooks/pretooluse_guard.py`: 高リスク Edit/Write に `permissionDecision: "ask"` を返す判定（既存の危険 bash `exit 2` は維持）。

## レビュー観点（案D）
- [x] allow が計画書 4-1 と一致（過不足・タイポなし）
- [x] フックが高リスク Edit/Write に `ask` を返す（TC-H1）／アプリは素通し（TC-H2）
- [x] フック判定が失敗注入で NG（TC-H3）＝false-green でない
- [x] 危険 bash の `exit 2` ハードブロック維持（TC-H4）
- [x] 既存の機密ファイル deny が維持（TC-A3＝15件）／実効しない高リスク deny は撤去（TC-A4＝0件）
- [x] settings.json が有効な JSON（TC-A1）
- [x] `hooks.PreToolUse` に `Edit|Write` 登録済み
- [x] ワークフローの承認ゲート・計画外変更なし

## 自動テスト結果（案D・/implement 2026-06-27 実測）
- TC-A1 JSON妥当性: **OK**
- TC-A3（機密deny 維持 15件）: **OK**
- TC-A4（実効しない高リスク deny 撤去＝0件）: **OK**
- TC-H1（高リスク11種→ask）: **OK** / TC-H2（アプリ→素通し）: **OK** / 絶対パス・Write も ask: **OK**
- TC-H3（失敗注入で ask 消失）: **OK** / TC-H4（force push→exit 2 維持）: **OK**
- pytest / Jest / E2E: 非該当（アプリコード変更なし）

## 手動テスト結果
- 案D の統合挙動 M1'〜M5'（default モードでの ask 表示確認）は **`/test` で実施予定（⏳）**。フック単体は上記 TC-H で決定論的に検証済み。

## 旧設計（settings `deny`・廃止）の記録 ※現状とは不一致・経緯として保持
- 旧 TC-A2-deny（deny 高リスク群 20件存在）: かつて OK だったが、案Dで該当 deny は**撤去済み（現状0件）**。
- 旧 M2/M3（deny で高リスク編集をブロック）: ❌ FAIL（重複 allow に負け編集が通った）。対照 M_env（`./.env` deny のみ）は OK（ブロック）。
- 根本原因: Edit/Write は allow と deny が重複すると **allow 優先**。→ 案D（フックで ask）へ移行。詳細は plan「重大な発見」。

## 総合判定
✅ **案D 実装済み・自動テスト全 PASS**。残るは `/test` での統合挙動（M1'〜M5'）確認のみ。コードレビュー VERDICT: OK / 高リスク判定: No。
