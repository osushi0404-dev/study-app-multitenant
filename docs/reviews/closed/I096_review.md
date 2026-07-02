# I096 レビュー: worktree lifecycle スクリプト（作成・撤去）で foot-gun を機械化

## 基本情報
- **関連イシュー**: #182
- **対象計画書**: docs/plans/open/plan_I096.md
- **Draft PR**: #186
- **作成日**: 2026-07-02

## レビュー目的
worktree の作成・撤去 lifecycle をスクリプト化し、`worktree.md` が警告する foot-gun（main 基点の空ツリー・`.env` 欠落の静かな insecure 起動・volume 漏れ・`COMPOSE_PROJECT_NAME` 分離崩壊）を機械化で不可能化する実装が、計画書どおり・誤停止なく・回帰なく行われたかを検証する。重点:
- `wt-new`: origin/develop 基点固定・`.env` コピー検証（欠落で停止）・`--up` opt-in・引数検証・衝突事前検査・base=primary 親導出
- `wt-remove`: `DANGER_OK=1` ゲート（未設定で `down -v` 非実行）・`down -v`→`remove` 順序・未コミット/未 push 中止・primary 保護
- 決定論テストが false-green でない（ゲート/検証を外すと振る舞いが反転する）こと
- `.env` を中身を読まずに扱う（deny リスト・I095 横断ガードと非衝突）こと

## 期待する成果
- AC 全項目を満たす
- 自動テスト（`test_wt_lifecycle.sh`）ALL PASS ＋ 決定論ゲート exit 0
- 手動テスト（Claude 実施のファイル・構文・runbook 確認）OK

## 変更概要
`scripts/claude/wt-new.sh` / `wt-remove.sh` を新規追加し、worktree lifecycle の foot-gun を機械化。`test_wt_lifecycle.sh`（temp repo + docker スタブ）で決定論検証。`worktree.md` §3/§5 をスクリプト利用手順に更新（手動は fallback 保持）。

## 変更点
- `scripts/claude/wt-new.sh`（新規）
- `scripts/claude/wt-remove.sh`（新規）
- `scripts/claude/tests/test_wt_lifecycle.sh`（新規）
- `docs/runbooks/worktree.md`（§3/§5 更新）

## 影響範囲
- Backend/Frontend/DB: なし
- Config/Infra: 上記 4 ファイル

## 実装結果評価
- 計画書 §4-1/§4-2/§4-3/§4-4 のとおり実装。TDD（Red: 43 fail → Green: 55 PASS）で進行。
- plan-review 指摘（W1 CWD 内側ガード・W2 `--env-source` 値検査・W4 down 失敗案内・Info6 未コミットチェックの fail-safe）を実装に反映し、TC-R7/N10/R8 で回帰検証。
- code-review（VERDICT: OK・高リスク No）の Low 指摘（恒真な `SRC_ROOT` 非空チェック）を修正済み。

## テスト結果
- 自動: `test_wt_lifecycle.sh` **55/55 PASS**（2026-07-02）。決定論ゲート 5/5 exit=0（lifecycle test・`bash -n` wt-new/wt-remove・runbook grep wt-new/wt-remove）。pytest/Jest/E2E は非該当（アプリコード変更なし）。false-green 注入 TC-FG1/FG2 で否定・停止ガードの実効性を反証。
- 手動: `I096_manual_test.md` 全 6 項目 Claude 実施・**OK**（ファイル存在/実行ビット・`bash -n`・テスト全 PASS・no-arg Usage・runbook §3/§5・DANGER_OK/未 push 実装確認）。Human 専用項目なし。
- pre-commit（shellcheck 含む）PASS。code-review VERDICT: OK。

## 計画との差分
- なし（plan-review・code-review 指摘反映はいずれも計画書へ同時更新済みのため計画一致）。SRC_ROOT の e2e 導出を `cd/pwd` から `dirname` 二重に簡素化（SC2015 回避・plan §4-1 へ同時反映）。

## ロールバック
- 新規 3 ファイルを削除し `worktree.md` §3/§5 の追記を revert すれば従来の手動運用に戻る（DB・外部状態の永続変更なし・テストは temp repo と docker スタブのみ）。
