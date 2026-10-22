# I182 レビュー: 「GitHub から復旧できる」前提が成り立たない操作を防ぐ（秘密情報の push など）

## 基本情報
- **関連イシュー**: #307（docs/issues/open/I182.md）
- **計画書**: docs/plans/open/plan_I182.md
- **Draft PR**: #308
- **テスト文書**: docs/tests/open/I182_auto_test.md・docs/tests/open/I182_manual_test.md

## レビュー対象
| 計画 | 対象ファイル | 内容 |
|------|-------------|------|
| 4-1 | `scripts/claude/tests/guard_corpus_diff.py` | 比べる相手を develop との分かれた点にする（`base_rev()`） |
| 4-2 | `scripts/claude/hooks/pretooluse_guard.py` | 最上位の包み・時間 20 秒／メモリ 512MB（`RLIMIT_DATA`）の上限・失敗は確認 |
| 4-3 | `scripts/claude/hooks/pretooluse_guard.py` | `--no-verify` の停止・リモートブランチの削除の確認・ワークフロー／検査設定の Edit/Write の確認 |
| 4-4 | `scripts/claude/tests/test_i182_secret_gates.sh`（新規） | CI の detect-secrets が外されていないことのテスト（N・D・E 群も同じファイル） |
| 4-9 | `.github/workflows/ci.yml`・`.github/workflows/e2e.yml` | 最上位に `permissions: contents: read`（/security-review で追加） |
| 4-5 | `.claude/settings.json`・`scripts/claude/tests/test_settings_permissions.sh` | ask から rm・mv・cp・chmod・chown を外し allow へ |
| 4-6 | `docs/runbooks/danger-ops.md` | 復旧できる範囲・漏れたときの手順・見張りの扱いの追記 |
| 4-7 | `docs/runbooks/review-rules.md`・`docs/runbooks/worktree.md`・`docs/issues/open/I181.md`（ローカル）・`test_pretooluse_guard_matrix.sh` | レビュー観点・前提の参照・I181 の注記・マトリクスの 3 行 |
| テスト | `test_i182_corpus_base.sh`・`test_i182_guard_failsafe.sh`・`test_i182_docs.sh`（新規） | B・F・DOC 群 |

## レビューの重さ（イシュー「制約・引き継ぎ情報」）
秘密情報の push と GitHub Actions に関わる変更（4-3 の `--no-verify`・ワークフローの確認、4-4、4-9）は「GitHub が最後の守り」の対象外。この範囲は敵対的レビューを 1 周・時間上限付きで回す。それ以外（4-1・4-2・4-5〜4-7）は決定論ゲートが緑で基本レビューが OK なら先へ進む。

## 実装後評価
（/code-review・/test の後に記入）
