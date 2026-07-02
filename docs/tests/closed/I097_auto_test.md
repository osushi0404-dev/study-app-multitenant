# I097 自動テスト（決定論）

- **関連**: docs/plans/open/plan_I097.md / docs/issues/open/I097.md（#183, PR #187）
- **実行**:
  - `bash scripts/claude/tests/test_wt_port_offset.sh`（docker 非依存）
  - `bash scripts/claude/tests/test_compose_ports.sh`（docker 任意・非在時 SKIP）
  - 回帰: `bash scripts/claude/tests/test_wt_lifecycle.sh`（55/55 維持）

隔離方針は既存 `test_wt_lifecycle.sh` を踏襲（temp bare origin + clone、docker は不使用または `docker compose config` のみ）。

**実装メモ（隔離環境・I1）**: `test_wt_port_offset.sh` の `new_env()` は temp repo の `.gitignore` に `.env` / `*.env` を含め、実 `.gitignore` と揃える。これにより wt-new が生成する root `.env` が untracked/dirty 扱いにならず実運用と同じ挙動で検証できる。**既存 `test_wt_lifecycle.sh` も同様に fixture の `.gitignore` へ `.env`/`*.env` を追加**（追加しないと生成 `.env` が dirty 扱いになり wt-remove テストが誤 abort する＝実装時に検出・修正）。テスト内容・形式は不変。

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
| TC-P7 | ポート変数の runbook 文書化（`.env.example` は deny ガードにより取り止め） | `docs/runbooks/worktree.md` または `common-commands.md` に 4 変数（`DB_PORT`/`REDIS_PORT`/`BACKEND_PORT`/`FRONTEND_PORT`）と STEP=10 の記載がある（TC-DOC で機械検証） |
| TC-P9（COMPOSE_PROJECT_NAME 不在・W3/AC4） | TC-P1/TC-P2 で生成された `wt-app/.env` を検査 | 生成 `.env` に `COMPOSE_PROJECT_NAME` が**含まれない**（`grep -q 'COMPOSE_PROJECT_NAME' → 非ヒット`）。分離は既定（ディレクトリ名）に委ね、`.env` へ混入させない設計を機械保証（AC4） |
| TC-P8（回帰・W4 具体化） | `wt-new app 108 x`（自動割当）実行後の既存挙動 | exit 0 かつ ①`wt-app/backend/.env` が primary の `backend/.env` と一致（`cmp -s`＝`SECRET=stub` コピー済）②基点が origin/develop（`only-develop-file.txt` 在・`only-main-file.txt` 無）③新 root `.env` 生成が上記を壊さない |

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
| TC-DOC1 | `docs/runbooks/worktree.md` §6 + §3 | ①§6 に「同時起動」「BACKEND_PORT」等ポート変数への言及があり「1 スタックずつ」のみの旧記述が残っていない ②§3 の wt-new コマンド例に `--port-offset` が含まれる（W1・引数パリティの機械検証） |
| TC-DOC2 | `docs/runbooks/common-commands.md` | ポート変数・同時 up 手順への言及がある |

---

## 実行結果（2026-07-02 実装時）
- test_wt_port_offset.sh: **pass=34 fail=0**（TC-P1〜P9・P5b・FG-P1・DOC1a〜e）
- test_compose_ports.sh: **pass=13 fail=0**（TC-D1〜D4・自己検証含む。docker compose v5.1.0 で実行）
- test_wt_lifecycle.sh（回帰）: **pass=55 fail=0**（fixture の `.gitignore` 整合後・baseline 維持）
