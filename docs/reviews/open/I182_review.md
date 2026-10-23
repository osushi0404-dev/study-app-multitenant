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
| 4-2 | `scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json` | 最上位の包み（例外は確認）・メモリ 512MB（`RLIMIT_DATA`）の上限。時間 20 秒と異常終了は公式の `timeout`＋`onFailure: "block"`（計画変更記録 1） |
| 4-3 | `scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json` | `--no-verify` の停止・リモートブランチの削除の確認（見張り）。ワークフロー／検査設定／高リスクファイルの Edit/Write の確認は settings.json の `ask` へ移し、見張りの `_check_edit_write` を削除（計画変更記録 1） |
| 4-4 | `scripts/claude/tests/test_i182_secret_gates.sh`（新規） | CI の detect-secrets が外されていないことのテスト（N・D・E 群も同じファイル） |
| 4-9 | `.github/workflows/ci.yml`・`.github/workflows/e2e.yml` | 最上位に `permissions: contents: read`（/security-review で追加） |
| 4-5 | `.claude/settings.json`・`scripts/claude/tests/test_settings_permissions.sh` | ask から rm・mv・cp・chmod・chown を外し allow へ |
| 4-6 | `docs/runbooks/danger-ops.md` | 復旧できる範囲・漏れたときの手順・見張りの扱いの追記 |
| 4-7 | `docs/runbooks/review-rules.md`・`docs/runbooks/worktree.md`・`docs/issues/open/I181.md`（ローカル）・`test_pretooluse_guard_matrix.sh` | レビュー観点・前提の参照・I181 の注記・マトリクスの 3 行 |
| 計画変更記録 3 | `.secrets.baseline` | `ci.yml` の行ずれに伴う `line_number` の自動更新のみ（新しい検出なし） |
| 計画変更記録 2 | `scripts/claude/tests/test_pretooluse_container_guard.sh` | 安全網の差し替え値に `remote_ask` を追加（結果の形を合わせるだけ） |
| テスト | `test_i182_corpus_base.sh`・`test_i182_guard_failsafe.sh`・`test_i182_docs.sh`（新規） | B・F・DOC 群 |

## レビューの重さ（イシュー「制約・引き継ぎ情報」）
秘密情報の push と GitHub Actions に関わる変更（4-3 の `--no-verify`・ワークフローの確認、4-4、4-9）は「GitHub が最後の守り」の対象外。この範囲は敵対的レビューを 1 周・時間上限付きで回す。それ以外（4-1・4-2・4-5〜4-7）は決定論ゲートが緑で基本レビューが OK なら先へ進む。

## /code-review の CI ゲートでの停止（2026-10-23）
- `bash scripts/claude/code-review.sh I182` が CI ゲートで停止: `Backend Lint & Security` の `pip-audit -r requirements.txt` が失敗（CI run 39856491985）。原因は I182 と無関係の新しい脆弱性で、`djangorestframework 3.18.0` に CVE-2026-114136・114137・114138（修正版 3.18.2）。I182 の変更（ハーネス・ワークフローの `permissions`）は関係しない（同じ run のほかの 5 件と E2E は成功）。
- ユーザー判断: 別イシュー（track:app）で DRF を 3.18.2 に更新して先にマージし、I182 はそれを取り込んで CI を緑にしてから `/code-review I182` をやり直す。起票コマンドは `/issue-bootstrap djangorestframework を 3.18.0 から 3.18.2 に更新する — …（track:app）`。
- 根本の是正（既存の脆弱性で無関係な PR が全面停止しない PR ゲート）は I152（#268）。

## /code-review のやり直し（2026-10-24）
- I183（PR #310）マージ後に develop を取り込み（d5934f4）、CI 6 件すべて pass。基本レビュー OK（`docs/reviews/I182_code_review_20261024_0134.md`・高リスク YES）
- 敵対的レビュー（Actions・秘密情報の範囲だけ・1 周・3 体）: High 1・Medium 3 を修正（a843b9f）、Low 4 は処遇を確定（2 件は I152 に同梱・c73e317）。`docs/reviews/I182_adversarial_review_20261024_0149.md`・VERDICT: OK

## 実装後評価
- /test（2026-10-24）: 自動テストはすべて fail=0（内訳は `docs/tests/open/I182_auto_test.md`「実装後」）・c73e317 の CI 6 件 pass。手動の Claude 実施分（No.3・3b・4・5・6）はすべて OK。Human 実施分（No.1・2）はユーザー確認待ち
