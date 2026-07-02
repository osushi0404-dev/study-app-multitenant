# I097 レビュー記録

- **関連**: docs/plans/open/plan_I097.md / docs/issues/open/I097.md（#183, PR #187）
- **レビュー対象**:
  - docker-compose.yml（db/redis/backend/frontend の ports 変数化・nginx 対象外）
  - .env.example（新規・追跡・4 変数と既定値・オフセット規約）
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
- [ ] root `.env` が gitignore・`.env.example` のみ追跡

## 自動テスト結果（実装後に記入）
- test_wt_port_offset.sh:
- test_compose_ports.sh:
- test_wt_lifecycle.sh（回帰）:

## 指摘事項
（実装・レビュー時に記入）

## 総評
（実装・レビュー時に記入）
