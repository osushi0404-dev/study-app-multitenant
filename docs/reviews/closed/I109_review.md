# I109 レビュー: 依存脆弱性ドリフトの定期検知（scheduled 監査＋自動起票）

## 基本情報
- **対象計画書**: docs/plans/open/plan_I109.md
- **関連イシュー**: #205（docs/issues/open/I109.md）
- **Draft PR**: #211

## レビュー目的
- scheduled 監査が PR ゲート（ci.yml）と判定一貫（同一ツール・同一条件）であること
- 検知 → 自動起票 → 重複防止 → 運用導線（runbook）が自己完結で機能すること
- default branch 切替（前提ゲート）と Phase B（マージ後 live 検証）の順序特例が記録どおり実施されること

## 期待する成果
- 依存の新規 CVE を最大 24 時間で検知し、PR 契機の一斉 CI ブロック（I108 型）を予防する仕組みが稼働する
- 検知時の対応がイシュー起票（GitHub のみ）→ /issue-bootstrap の 2 段階運用として runbook 化される

## 変更概要
- 依存脆弱性ドリフトの定期検知を導入。scheduled workflow（毎日 JST 7:00）が develop を PR ゲートと同一条件で監査し、fail 時に GitHub イシューを自動起票（種別ごと open 最大 1 本・既存はコメント追記）する。検知後はイシューを見た人が /issue-bootstrap でローカル起票する 2 段階運用。

## 変更点
- `.github/workflows/dependency-audit.yml` 新規（cron `0 22 * * *` UTC・workflow_dispatch＋simulate_failure 入力・`ref: develop` 固定・`permissions: contents: read, issues: write`）
- `scripts/claude/dependency-audit-issue.sh` 新規（起票/重複防止。タイトル固定プレフィックス前方一致・`--limit 50`）
- `scripts/claude/tests/test_i109_dependency_audit.sh` 新規（決定論ゲート: YAML 構文・不変条件・ci.yml とのペア検証・gh スタブ分岐検証。false-green 注入検証済み）
- `docs/runbooks/dependency-audit.md` 新規＋ `CLAUDE.md` 参照 1 行
- リポジトリ設定: default branch main → develop（オーナー実施・M2 で機械確認）・ラベル `dependency-audit` 作成（M3 で確認）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.github/workflows/dependency-audit.yml`・`scripts/claude/dependency-audit-issue.sh`・`scripts/claude/tests/test_i109_dependency_audit.sh`・`docs/runbooks/dependency-audit.md`・`CLAUDE.md`（1 行）・リポジトリ設定（default branch / ラベル）

## 実装結果評価
- 計画書 4-1〜4-5 のとおり実装（TDD: Red 全16項目NG → Green 全OK）。plan-issue-review 指摘（CI ペア検証・false-green 一時コピー方式・--limit 明示）と code-review 指摘（omission-lint 文書構造・M3 記録・runbook 補足 1 行）を反映済み。
- 品質: pre-commit（shellcheck・check yaml）pass。code-review 最終 VERDICT: OK（I109_code_review_20260715_1856.md・高リスク判定 No）。

## テスト結果
- 自動: `test_i109_dependency_audit.sh` **exit 0（16/16 OK）**（実装時・/test 時の 2 回実行）。false-green 注入検証 2 件とも NG 検知（auto_test.md TC-02 実施記録参照）。pytest / Jest / E2E は非該当（アプリコード変更なし・PR CI では全 6 チェック pass）。
- 手動: Phase A（M1〜M4）**全 OK**（default branch=develop 機械確認・ラベル存在・PR CI 全 pass）。Phase B（M5〜M9・workflow_dispatch live 検証）は順序特例により **develop マージ後にクローズ処理内で実施予定**（未実施）。

## 計画との差分
- なし（実装ファイル・コマンド・値はすべて計画書どおり。レビュー指摘による文書・テスト構造の改善のみで、機能仕様の変更なし）

## ロールバック
- 追加ファイル群の削除（revert 1 コミット）＋ラベル削除（任意）＋ default branch 復帰（オーナー操作・任意）
