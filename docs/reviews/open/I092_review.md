# I092 レビュー: worktree ベースの並行トラック運用を runbook 化

## レビュー対象
- `docs/runbooks/worktree.md`（新規作成）
- `CLAUDE.md`（「0. 参照先」運用・ルール: に worktree.md 参照 1 行追加）
- 計画書 `docs/plans/open/plan_I092.md`
- テスト文書 `docs/tests/open/I092_auto_test.md` / `I092_manual_test.md`

## 変更概要
- worktree 並行トラック運用の手順を runbook 化（ベースブランチ選択・トラック/ブランチ設計・独立セッション起動・**Docker Compose 前提のセットアップ**・**並行実行のポート衝突**・共有/非共有・採番一貫性・セッション間引き継ぎ原則・現構成の参考例）。
- ※初回グリルの venv/pip/npm・SQLite ロック前提を docker-compose.yml 実査で是正（Docker/Postgres/固定ポート衝突へ）。
- CLAUDE.md の参照先に 1 行追加（実体は runbook、CLAUDE.md にはルールを増やさない方針に準拠）。

## 影響範囲
- Backend/Frontend/DB: なし
- Config/Infra: `docs/runbooks/worktree.md`（新規）・`CLAUDE.md`（参照 1 行）

## レビュー観点（実装後に確認）
- [ ] AC 全項目を満たす（自動 TC-A1〜A13 が ALL PASS）
- [ ] 再発防止: ベースブランチ＝develop・main を使わない旨が runbook に明記（TC-A3）
- [ ] **Docker 整合**: セットアップが `docker compose up -d`+`.env` コピーで、venv/pip/npm 手順が無い（TC-A6）。dev DB=Postgres・node_modules はコンテナ管理と記載（TC-A7）
- [ ] **並行衝突**: ホスト固定ポート衝突・`COMPOSE_PROJECT_NAME` が記載（TC-A13）
- [ ] CLAUDE.md 参照行のリンク切れ 0（TC-A11）・挿入位置＝workflow.md の直後（TC-A10）
- [ ] 手順本文が一般表現＋参考例の 2 層（TC-A12）／固有値が参考表に隔離
- [ ] 計画書に無い実装・仕様追加が入っていない（docs 2 ファイルのみの変更）
- [ ] 設計確認メモ（/grill-me）の確定値と runbook 記載が矛盾しない（wt-app 新設なし・アプリ開発=study-app-multitenant・Docker 前提の是正が反映済み）

## 敵対的検証（計画段階・独立サブエージェント）
Docker 前提の是正が正しいかを独立サブエージェントに「合格を反証せよ」で検証させ、自己再実証した:
- **主張 6 件すべて HOLDS**: DB=Postgres（settings.py:91・compose db 5432）／固定ポート衝突／project 名は dir 名で自動分離（トップレベル `name:` 無し・`container_name:` 無し・override 無し）／node_modules は匿名ボリューム＋Dockerfile.dev で `npm install`／backend `.env` は gitignore+env_file（`required: false`）／CLAUDE.md 運用フロー行は先頭。
- **追加検出 4 精緻化（反映済み）**: (A) 既定 up 衝突ポートは 5432/6379/8000/3000（nginx は production profile で対象外・自己確認）／(B) `.env` 欠落は `required: false` で静かに insecure 既定起動（settings.py:17,94・自己確認）→ 警告明記＋TC-A14／(C) `COMPOSE_PROJECT_NAME` の global export 禁止／(D) 削除時 `docker compose down -v` で volume 回収。

## テスト結果
- 自動: 実装前 false-green 検証済み（RED→フィクスチャ GREEN で全 TC(A1〜A14) の反転を実証）。実装後 `/test` で ALL PASS を記録予定。
- 手動: `/test` でユーザー確認（No.6 の可読性のみ Human）。

## セキュリティ影響
- なし（コード変更なし。docs 追加のみ）。

## 計画との差分
- （実装後に記入）

## ロールバック
- `git` で worktree.md 追加・CLAUDE.md 差分を復元可能。破壊的操作なし。
