# I430 自動テスト: サンドボックスを土台にした見張りの組み直しと許可の設定の整理

実行コマンド（例）: `bash scripts/claude/tests/run-all.sh`（CI の Harness Tests が全部を流す。手元では下の決定論ゲートの関係するテストだけ）

結果:
- 2026-11-13 実装前の基準: TC-01〜TC-07 の 11 本を `bash scripts/claude/tests/run-all.sh <11 本>` で流し、`run-all: pass=11 fail=0`（変更前の見張り・設定）
- 2026-11-13 実装後（/simplify の後・コミット後）: TC-01〜TC-07 と、見張りに触れるそのほかのテスト（i197・wt_lifecycle・i182_secret_gates・guard_corpus_diff）の 19 本を `run-all.sh` で流し、`run-all: pass=19 fail=0`。TC-08 は exit 0（2,929 行）・TC-10〜TC-12 は exit 0。TC-09（全体）は CI で確かめる
- TC-01 の FG: 足したサンドボックスの決まり・deny の 12 件（S16〜S22b）は、壊した写しでそれぞれ不合格になった（`pass=32 fail=0`）
- 実行記録（test-gate・2026-11-13）: `bash scripts/claude/gate-check.sh I430` → `GATE_CHECK: OK`。test-gate に回された重いテストは無し（コードレビューの記録に「委譲」の行が無い）。TC-08 `bash -c 'test "$(wc -l < scripts/claude/hooks/pretooluse_guard.py)" -le 3050'` → exit 0（2,929 行）。TC-09（run-all 全体）は CI の Harness Tests が success（review-gate の `CI_WAIT: OK`・2 回）
- backend: 対象外（コードの変更なし）
- frontend: 対象外（コードの変更なし）

## テストケース

| TC | 対象 | 確かめること | 合否の判定 | FG（失敗の注入） | 結果 |
|---|---|---|---|---|---|
| TC-01 | `scripts/claude/tests/test_settings_permissions.sh` | 見張りを呼ぶ PreToolUse フックが 3 つ。`sandbox.enabled`=true・`allowUnsandboxedCommands`=false・`failIfUnavailable`=true・`filesystem.denyWrite` に `.claude/worktrees`・`filesystem.denyRead` に `~/.config/github-app`・`excludedCommands` に一般のインタプリタ・シェル（`bash *`・`sh *`・`python3 *`・`python *`・`node *`・`env *`・`*`）が無い・deny に `Bash(gh pr checkout *)`・`Bash(gh co *)` がある | exit 0 | テストの中で設定の写しを壊す（`enabled` を false・`allowUnsandboxedCommands` を true・`failIfUnavailable` を消す・`denyWrite` から `.claude/worktrees` を消す・`denyRead` から App の鍵を消す・`excludedCommands` に `bash *`／`sh *`／`python3 *`／`*` を足す・deny から 2 行を消す）と、それぞれ不合格になる（テストの中の `ck`） | 実装前のため未実行 |
| TC-02 | `scripts/claude/tests/test_pretooluse_worktree_guard.sh` | Edit／Write の別ワークツリー・primary への書き込みが今までどおり止まる（G01）。合否はこの Edit／Write の例が全部通ること（Bash の例を消したことは、計画 4-6 のとおりレビューで差分を見る） | exit 0 | 既存の FG（見張りの判定を外した写しで不合格）をそのまま使う | 実装前のため未実行 |
| TC-03 | `scripts/claude/tests/test_pretooluse_push_guard.sh` | force・`--no-verify`・リモートの削除・`--mirror`/`--all` が今までどおり止まる・確認になる | exit 0 | 既存の FG | 実装前のため未実行 |
| TC-04 | `scripts/claude/tests/test_guard_must_stop_cases.sh` | 止めるべき形の一覧（消した判定の行を除いたもの）で、変更前より弱い判定が無い | exit 0 | 既存の FG | 実装前のため未実行 |
| TC-05 | `scripts/claude/tests/test_pretooluse_guard_matrix.sh` | 危険な操作 × 書き方の総当たりで、残す判定の素通しが無い | exit 0 | 既存の FG | 実装前のため未実行 |
| TC-06 | `scripts/claude/tests/test_guard_bash_oracle.sh` | 本物の bash との突き合わせで、残す判定の素通しが無い | exit 0 | 既存の FG | 実装前のため未実行 |
| TC-07 | `scripts/claude/tests/test_pretooluse_container_guard.sh`・`test_pretooluse_checkout_guard.sh`・`test_i182_guard_failsafe.sh`・`test_i200_guard_narrowing.sh`・`test_i187_mcp_filename_guard.sh`・`test_i444_guard_gaps.sh`・`test_i454_guard_env_writes.sh`・`test_i463_guard_optspec.sh`・`test_i469_guard_optspec_leftovers.sh` | 残す判定（コンテナ・未コミットの変更の取り消し・見張りの失敗・Playwright の書き先・書き先とオプションの表の共有の関数）の振る舞いが変わらない | exit 0 | 既存の FG | 2026-11-13 実装前: 前の 5 本は基準で合格（下の結果）。後ろの 4 本は計画レビューの Warning で足した（実装の中で流す） |
| TC-08 | `scripts/claude/hooks/pretooluse_guard.py` の行数 | 3,050 行以下（AC3） | `bash -c 'test "$(wc -l < scripts/claude/hooks/pretooluse_guard.py)" -le 3050'` が exit 0 | 目標を 3,880（今の行数より 1 小さい 3,879）にすると今の見張りで不合格になる（`bash -c 'test "$(wc -l < scripts/claude/hooks/pretooluse_guard.py)" -le 3879'` が今は exit 1） | 2026-11-13 実装前: 本体 exit 1（3,880 行・期待どおり不合格）・FG（上限 3,879）exit 1。実装後に本体が exit 0 になることを確かめる |
| TC-09 | `bash scripts/claude/tests/run-all.sh` | ハーネスのテストが全部合格（AC7） | CI の Harness Tests が success | — | CI で確かめる |
| TC-10 | `.claude/settings.json`・見張りの構文 | JSON として読める・見張りがコンパイルできる | `python3 -m json.tool` と `python3 -m py_compile` が exit 0 | — | 2026-11-13 実装前: どちらも exit 0（変更前の基準）。実装後に流し直す |
| TC-11 | `docs/runbooks/danger-ops.md` | 「見張りに判定を足すときの決まり」の小節がある（AC6） | `grep -q` が exit 0 | 見出しの無い写しで不合格（`grep -q` が exit 1） | 2026-11-13 実装前: exit 1（まだ無い＝FG の確かめを兼ねる）。実装後に exit 0 を確かめる |
| TC-12 | `docs/runbooks/plan-writing-rules.md` | 「見張り（`pretooluse_guard.py`）に判定を足す計画」の小節がある（AC6） | `grep -q` が exit 0 | 同上 | 2026-11-13 実装前: exit 1（同上） |

- `test_pretooluse_gh_pr_guard.sh` は消す（G33〜G35 だけを見るテスト・計画 4-6）
- TC-02〜TC-07 で期待値を消すのは、消した判定（D1〜D3）の分だけ。残す判定の期待値が落ちたら見張りを直す（計画 4-6）
- `test_guard_corpus_diff.sh`（手元の作業記録で、新しく確認・停止になったものが 1% を超えないか）は、判定を消すだけで増えないので、見張りを直したときの手順（danger-ops.md）どおり手元で流す

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_settings_permissions.sh
bash scripts/claude/tests/test_pretooluse_worktree_guard.sh
bash scripts/claude/tests/test_pretooluse_push_guard.sh
bash scripts/claude/tests/test_guard_must_stop_cases.sh
bash scripts/claude/tests/test_pretooluse_guard_matrix.sh
bash scripts/claude/tests/test_guard_bash_oracle.sh
bash scripts/claude/tests/test_pretooluse_container_guard.sh
bash scripts/claude/tests/test_pretooluse_checkout_guard.sh
bash scripts/claude/tests/test_i182_guard_failsafe.sh
bash scripts/claude/tests/test_i200_guard_narrowing.sh
bash scripts/claude/tests/test_i187_mcp_filename_guard.sh
bash scripts/claude/tests/test_i444_guard_gaps.sh
bash scripts/claude/tests/test_i454_guard_env_writes.sh
bash scripts/claude/tests/test_i463_guard_optspec.sh
bash scripts/claude/tests/test_i469_guard_optspec_leftovers.sh
python3 -m json.tool .claude/settings.json
python3 -m py_compile scripts/claude/hooks/pretooluse_guard.py
grep -q 見張りに判定を足すときの決まり docs/runbooks/danger-ops.md
grep -q 判定を足す計画 docs/runbooks/plan-writing-rules.md
```
