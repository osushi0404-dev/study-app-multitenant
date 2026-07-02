# I097 レビュー記録

- **関連**: docs/plans/open/plan_I097.md / docs/issues/open/I097.md（#183, PR #187）
- **レビュー対象**:
  - docker-compose.yml（db/redis/backend/frontend の ports 変数化・nginx 対象外）
  - ポート変数の runbook 文書化（`.env.example` は deny ガードにより取り止め・worktree.md §6 / common-commands.md へ集約）
  - scripts/claude/wt-new.sh（--port-offset・自動割当・衝突 fail・直下 .env 生成）
  - scripts/claude/tests/test_wt_port_offset.sh（新規・決定論①＋false-green 注入）
  - scripts/claude/tests/test_compose_ports.sh（新規・決定論②・docker 任意 SKIP）
  - docs/runbooks/worktree.md §6・docs/runbooks/common-commands.md

## レビュー観点（実装後に埋める）
- [ ] AC1: 変数未設定時に現行ポート（5432/6379/8000/3000）で起動（後方互換）
- [ ] AC2: 自動割当・`--port-offset` 上書き・衝突 fail
- [ ] AC3: 2 オフセットの publish ポートが非衝突（決定論テスト②）
- [ ] AC4: COMPOSE_PROJECT_NAME による分離維持
- [ ] AC5: 決定論テスト①②が green（docker 無しは②SKIP）
- [ ] AC6: worktree.md §6 更新
- [ ] AC7: 既存 test_wt_lifecycle.sh が 55/55 のまま
- [ ] false-green 検証: 衝突/重複系 TC が失敗注入で NG になることを確認
- [ ] nginx が対象外のまま（80/443 変数化されていない）
- [ ] root `.env` が gitignore・ポート変数は runbook に文書化（`.env.example` 不採用）
- [ ] 生成 `.env` に `COMPOSE_PROJECT_NAME` が混入しない（TC-P9・AC4）
- [ ] worktree.md §3 の wt-new コマンド例に `--port-offset` が追記（TC-DOC1・W1）
- [ ] wt-new.sh の `usage()`・冒頭コメント・§6 コメントが stale でない（W2）
- [ ] plan-review 指摘（W1/W2/W3/W4/I1/I2）の反映確認

## 自動テスト結果（実装後に記入）
- test_wt_port_offset.sh:
- test_compose_ports.sh:
- test_wt_lifecycle.sh（回帰）:

## 指摘事項
- plan-review（20260702_2215）: Warning 4・Info 2 → 実装前に計画/テスト文書へ反映済み（W1〜W4/I1/I2）。
- code-review（20260702_2319）: FINAL VERDICT OK・高リスク No・AC1〜AC7 全て ✅。
  - Medium 1 件（W2 残件）: `wt-new.sh` の `--up` インラインコメントが旧理由（§6 ポート衝突）のまま未更新 → コメント文のみ修正（ロジック不変・機械的修正のため CI で担保・再レビュー不要）。

## 総評
決定論テスト（34+13）＋回帰（55）が全 green、false-green 注入も実施。AC は独立 code-review で全件 ✅。残る Medium はコメント整合のみで対応済み。
