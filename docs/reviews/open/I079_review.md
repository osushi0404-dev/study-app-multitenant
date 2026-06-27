# I079 実装レビュー（記入用）

- 関連イシュー: #158
- 計画書: docs/plans/open/plan_I079.md
- PR: #159

## レビュー対象
`.claude/settings.json` の `permissions`（allow へコードパス＋`bash scripts/claude/*`、deny へ高リスク群10種×Write/Edit）。

## レビュー観点
- [ ] allow/deny エントリが計画書 4-1/4-2 と完全一致（過不足・タイポなし）
- [ ] deny が broad allow に優先する挙動を実セッションで確認した（M2/M3/M4 OK）
- [ ] アプリソース編集が無確認になることを確認した（M1 OK）
- [ ] 既存の機密ファイル deny が維持されている（TC-A3 / M5 OK）
- [ ] settings.json が有効な JSON（TC-A1 OK）
- [ ] ワークフローの承認ゲート（`/implement` 等）に変更がない
- [ ] 計画外の変更（他の allow/ask/deny エントリの増減）がない

## 自動テスト結果（2026-06-27 /test 実行）
- TC-A1 JSON妥当性: **OK**
- TC-A2-allow（allow 5系統）: **OK (5/5)**
- TC-A2-deny（deny 高リスク群 20）: **OK (20/20)**
- TC-A3（機密deny env/secrets/pem/key 15）: **OK (15/15)**
- pytest / Jest / E2E: 非該当（アプリコード変更なし）

## 手動テスト結果（2026-06-27 default モード実測）
- M1（backend ソース編集）: ✅ OK（allow 効く）
- M2（backend/Dockerfile・deny）: ❌ **FAIL**（ブロックされず編集成功）
- M3（migrations・deny）: ❌ **FAIL**（同上）
- M_env 対照（`./.env` Read・deny のみ）: ✅ OK（ブロック）
- 根本原因: Edit/Write は allow と deny が重複すると **allow 優先**。高リスク群は broad allow 配下のため deny で保護できない。詳細は plan「重大な発見」。

## 総合判定
❌ **NG（旧設計）→ 案D を採用して再設計**。
- 旧設計（settings `deny` で高リスク保護）は挙動レベルで未達（M2/M3 FAIL）。
- **採用方針 = 案D**: 高リスク Edit/Write の保護を **PreToolUse フック（`pretooluse_guard.py`）** に移管（決定論的・失敗注入でテスト可能・fail-safe）。broad allow は維持。機密 deny は settings 側で実効のため据え置き。
- 詳細は plan「重大な発見」「§4〜§9」、テストは TC-H1〜H3（フック単体）。実装後に M1'〜M5' で統合挙動を再検証する。
- ※ 現時点は**資料更新のみ・未実装/未コミット**。
