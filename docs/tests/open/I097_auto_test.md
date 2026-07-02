# I097 自動テスト（決定論）

- **関連**: docs/plans/open/plan_I097.md / docs/issues/open/I097.md（#183, PR #187）
- **実行**:
  - `bash scripts/claude/tests/test_wt_port_offset.sh`（docker 非依存）
  - `bash scripts/claude/tests/test_compose_ports.sh`（docker 任意・非在時 SKIP）
  - 回帰: `bash scripts/claude/tests/test_wt_lifecycle.sh`（55/55 維持）

隔離方針は既存 `test_wt_lifecycle.sh` を踏襲（temp bare origin + clone、docker は不使用または `docker compose config` のみ）。

---

## A. wt-new オフセット/衝突ロジック（test_wt_port_offset.sh・docker 不要）

| TC | 前提/操作 | 期待結果 |
|----|-----------|----------|
| TC-P1 | 既存 worktree 無し（primary のみ）で `wt-new app 101 x`（--port-offset 無し） | exit 0。生成された `wt-app/.env` に `BACKEND_PORT=8010` `DB_PORT=5442` `REDIS_PORT=6389` `FRONTEND_PORT=3010`（自動 offset=10） |
| TC-P2 | `wt-new app 102 x --port-offset 20` | exit 0。`wt-app/.env` に `DB_PORT=5452` `REDIS_PORT=6399` `BACKEND_PORT=8020` `FRONTEND_PORT=3020` |
| TC-P3 | 既存 worktree の `.env` に `BACKEND_PORT=8010` 等がある状態で `--port-offset 10` を指定 | exit 2。メッセージに「ポートが既存 worktree と衝突」。新 worktree 非作成 |
| TC-P4 | 既存 worktree が offset=10 を使用中、`wt-new app 104 x`（自動割当） | exit 0。新 `.env` は offset=20（`BACKEND_PORT=8020`）＝使用済みを避ける |
| TC-P5 | `wt-new app 105 x --port-offset abc`（非整数） | exit 2。メッセージに「--port-offset は数字」。非作成 |
| TC-P6 | `--port-offset 0` を明示（primary 既定ポートと同値） | exit 2（衝突検出が primary の既定ポートと衝突を検知）。非作成 |
| TC-P7 | `.env.example` の存在と内容 | `.env.example` が存在し `DB_PORT=5432` `REDIS_PORT=6379` `BACKEND_PORT=8000` `FRONTEND_PORT=3000` を含む |
| TC-P8（回帰） | `wt-new` 実行後、backend/.env コピー・基点 origin/develop 等の既存挙動 | 既存どおり（`test_wt_lifecycle.sh` 55/55 維持で担保。本ファイルでは新 `.env` 生成が既存挙動を壊さないことを確認） |

### false-green 注入（test_wt_port_offset.sh 内）
| TC | 操作 | 期待結果 |
|----|------|----------|
| TC-FG-P1 | 衝突検出ガードを sed で無効化した wt-new 複製に対し TC-P3 と同条件を実行 | 衝突しても worktree が作成される（＝実体の停止要因が衝突ガードである反証）。注入前は TC-P3 が exit 2 になることと対で false-green でないことを担保 |

---

## B. compose レンダリング（test_compose_ports.sh・docker 任意）

冒頭で `command -v docker` && `docker compose version` を確認し、不可なら `SKIP`（exit 0）。実 `docker-compose.yml` を対象に `docker compose config` をレンダリングして publish ポートを検証する。

| TC | 前提/操作 | 期待結果 |
|----|-----------|----------|
| TC-D1 | `.env` 無し（変数未設定）で `docker compose config` | published に `5432` `6379` `8000` `3000` が現れる（後方互換・AC1） |
| TC-D2 | 一時 `.env`（offset=10: `BACKEND_PORT=8010` 等）を与えて `docker compose config` | published が `5442` `6389` `8010` `3010` に変わる |
| TC-D3 | offset=10 と offset=20 の 2 レンダリング結果の publish ポート集合を結合 | 重複ポートが 0 件（AC3・同時 up 非衝突の立証）。**自己検証**: 同一 offset 同士を結合すると重複が検出されテストが FAIL することを確認（false-green 防止） |
| TC-D4 | nginx が対象外であること | `docker compose config`（既定・profile 無し）に nginx が現れない（production profile のため）。nginx の 80/443 が変数化されていないことを確認 |

---

## C. runbook 整合（test_wt_port_offset.sh 末尾 or 目視）

| TC | 検証 | 期待結果 |
|----|------|----------|
| TC-DOC1 | `docs/runbooks/worktree.md` §6 | 「同時起動」「BACKEND_PORT」等ポート変数への言及があり、「1 スタックずつ」のみの旧記述が残っていない |
| TC-DOC2 | `docs/runbooks/common-commands.md` | ポート変数・同時 up 手順への言及がある |

---

## 実行結果（実装後に記入）
- test_wt_port_offset.sh: （未実施）
- test_compose_ports.sh: （未実施）
- test_wt_lifecycle.sh（回帰）: baseline 55/55（実装後に再実行して記入）
