# I080 実装後レビュー

- **対象イシュー**: docs/issues/open/I080.md（#160）
- **計画書**: docs/plans/open/plan_I080.md
- **Draft PR**: #165

## レビュー対象（実装物）
1. `.claude/settings.json` — allow に `Bash(git push)`・`Bash(git push *)` 追加、ask から `Bash(git push *)` 撤去、deny 維持
2. `scripts/claude/hooks/pretooluse_guard.py` — `_current_branch`/`_norm_push_dest`/`_push_protected_target` 追加、protected/HEAD push 判定の置換、`--all`/`--mirror` 追加
3. `scripts/claude/tests/test_pretooluse_push_guard.sh`（新規） — 決定論テスト（TC-P/false-green）
4. `docs/claude-code-structure.md` — フック/権限説明の同期

## レビュー観点チェックリスト
- [ ] **要件適合**: イシュー AC を全て満たす（settings の allow/ask/deny・フックの全宛先形 block・DANGER_OK escape・FP 解消・`--all`/`--mirror`・doc 同期）
- [ ] **protected 検出の網羅性**: 明示名・引数なし(保護ブランチ上)・refspec・`+develop`・`refs/heads/`・`HEAD:refs/heads/main`・`--all`/`--mirror` が全て exit 2（TC-P で固定）
- [ ] **danger-op モデル**: protected 宛先 push が `if not danger_ok:` 内＝`DANGER_OK=1` で exit 0（無条件化していない）。release/hotfix のローカル push 経路が壊れていない
- [ ] **誤検知ゼロ**: feature 上の素 push・`<src>:<feature>`・`develop-fix`/`main-backup` 宛先が exit 0
- [ ] **false-green でない**: TC-FALSEGREEN（判定関数無効化で protected が素通り／実体で block）の差分を確認済み
- [ ] **回帰なし**: 既存 `test_pretooluse_checkout_guard.sh` が 14/14 維持
- [ ] **権限レイヤー実証**: ステップ1ゲート（プレーン default 新規セッション）で安全 push 無確認・未承認 protected push が deny・DANGER_OK で escape 到達を確認（M1〜M3）
- [ ] **セキュリティ**: `allow: git push *` 緩和がフック＋deny で二重担保。subprocess はリスト引数（shell=False）。fail-open は既存方針と一貫
- [ ] **設計品質**: ヘルパ分割・`PROTECTED_BRANCHES` 定数化・正規化関数への集約。アンチパターン無し
- [ ] **コマンド衛生（I081 gate）**: 実装/検証手順に不要な複合化・パイプ・未コミットファイルへの checkout/restore が無い
- [ ] **doc 同期**: `claude-code-structure.md` の `git push *`(ask→allow)・protected danger-op 化が反映、追記にイシュー番号なし
- [ ] **計画一致**: 計画書記載外の変更が無い（`git diff --name-only` が影響範囲の4ファイルのみ）

## 判定
（実装・テスト完了後に追記）
