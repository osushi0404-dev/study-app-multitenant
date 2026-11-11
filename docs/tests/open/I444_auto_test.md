# I444 自動テスト: 見張りに残る役目の取りこぼしを塞ぎ、許可リストと手順書の写しを整理する

実行コマンド: `bash scripts/claude/tests/test_i444_guard_gaps.sh`（新規）と、見張りを直したら流すテスト（TC-06）。アプリのテスト（pytest・Jest・E2E）は変更が無いので CI に任せる。

新しいテスト `scripts/claude/tests/test_i444_guard_gaps.sh` は、見張りに Bash の JSON を渡して判定だけを見る（コマンドは実行しない）。期待値: `2`＝停止・`ASK`＝確認（exit 0 ＋ `permissionDecision: ask`）・`0`＝通す。0＝全 PASS／1＝FAIL あり。失敗の注入（FG）は、見張りの写しの 1 行を置き換え（置き換える行が見張りにちょうど 1 回だけあることを確かめ、無ければ FAIL）、その写しで同じケースが期待どおりに変わることを確かめる。`D='docker compose exec -T backend'`。

結果:
- 計画時（2026-11-11）: すべて実装前のため未実行（テストのファイルがまだ無い）。同じケースを見張りの写し（計画書「調査結果」のスパイク `g_proto.py`）に流し、TC-01〜TC-04 の期待値どおりになることは確かめた。変更前の見張りでは TC-01・TC-02 の ASK のケースが 0（＝今の取りこぼし）、TC-03 は 2、TC-04 は 0

## TC-01 環境変数をまとめて表示する形は確認（ホストとコンテナ）
| ID | コマンド | 期待 |
|---|---|---|
| 01a | `$D export` | ASK |
| 01b | `$D declare` | ASK |
| 01c | `$D typeset` | ASK |
| 01d | `$D env -0` | ASK |
| 01e | `$D env -u X` | ASK |
| 01f | `$D env FOO=1` | ASK |
| 01g | `$D ps auxe` | ASK |
| 01h | `export`（ホスト） | ASK |
| 01i | `env -u X`（ホスト） | ASK |
| 01j | `set`（ホスト） | ASK |
| 01k | `declare -p`（ホスト） | ASK |
| 01l | `ps e`（ホスト） | ASK |
| 01m | `$D export FOO=1` | 0 |
| 01n | `$D declare -i x=1` | 0 |
| 01o | `set -euo pipefail`（ホスト） | 0 |
| 01p | `ps aux`（ホスト） | 0 |
| 01q | `ps -eo etimes,pcpu,args --sort=-etimes`（ホスト） | 0 |
| 01r | `env FOO=1 python3 -V`（ホスト） | 0 |
| FG-01 | `_cmd_external` の新しい判定の下の `r.append("環境変数（秘密情報を含む）の表示")` を `pass` に置き換えた写しで 01a | 0 |

## TC-02 コンテナの /tmp/ 以外への書き込み（書き先の指定・移動元）は確認
| ID | コマンド | 期待 |
|---|---|---|
| 02a | `$D cp -t /app/x /tmp/y` | ASK |
| 02b | `$D cp --target-directory=/app/x /tmp/y` | ASK |
| 02c | `$D cp -vt /app/x /tmp/y` | ASK |
| 02d | `$D mv /app/x /tmp/y` | ASK |
| 02e | `$D mv /tmp/a /tmp/b` | 0 |
| 02f | `$D cp /app/a /tmp/b` | 0 |
| 02g | `$D cp -t /tmp/d /app/a` | 0 |
| FG-02a | `_ctr_write_targets` の `tdir = _opt_values(toks[1:], ("-t", "--target-directory"))` を `tdir = []` に置き換えた写しで 02a | 0 |
| FG-02b | `_ctr_write_targets` の `return tdir + pos` を `return pos[-1:]` に置き換えた写しで 02d | 0 |

## TC-03 psql の WHERE なしの UPDATE は停止（コンテナ内・ホスト）
| ID | コマンド | 期待 |
|---|---|---|
| 03a | `docker compose exec -T db psql -U postgres -c 'UPDATE users SET is_active=false'` | 2 |
| 03b | `psql -U postgres -h localhost -c 'UPDATE users SET is_active=false'` | 2 |
| 03c | `docker compose exec -T db psql -U postgres -c 'UPDATE users SET is_active=false WHERE id=1'` | 0 |
| FG-03 | `_sql_is_destructive` の `if re.search(r"\bupdate\b", s) and re.search(r"\bset\b", s) and not has_where:` を `if False:` に置き換えた写しで 03a | 0 |

## TC-04 危ない語が当たっても通す形（許可リストを縮めた後も I200 の普通の操作は通る）
| ID | コマンド | 期待 |
|---|---|---|
| 04a | `$D pytest -k delete` | 0 |
| 04b | `$D python -m pytest -k delete` | 0 |
| 04c | `$D python manage.py test apps.problems.tests.test_delete` | 0 |
| 04d | `docker compose run --rm e2e npx playwright test --grep delete` | 0 |
| 04e | `docker compose exec -T frontend npx jest src/password` | 0 |
| 04f | `$D ruff check apps/accounts/password_reset.py` | 0 |
| 04g | `$D pip show openai` | 0 |
| 04h | `$D python manage.py shell -c "from rest_framework.test import APIClient; APIClient().post('/api/auth/password-reset-confirm/', {})"` | 0 |
| 04i | `docker compose exec -T db psql -U postgres -c "select 'drop' as x"` | 0 |
| 04j | `$D curl -fsS http://localhost:8000/health/` | 0 |
| FG-04 | `_container_safe` の docstring の直後に `return False` を差し込んだ写しで 04a | ASK |

I200 の普通の操作（I166 の形・`seed_e2e`・`psql select`・`manage.py check` など）は `test_i200_guard_narrowing.sh` の TC-01 が確かめる（TC-06）。

## TC-05 corpus diff が primary とワークツリーの作業記録を見つける
一時の `HOME` に `~/.claude/projects/-x-app-y`・`-x-app-y--claude-worktrees-w1`・`-x-app-yz`（別のリポジトリ）を作り、`guard_corpus_diff.py` を読み込んで `_project_dirs("/x/app.y")` を呼ぶ。
| ID | 確かめ | 期待 |
|---|---|---|
| 05a | 返るフォルダ | `-x-app-y` と `-x-app-y--claude-worktrees-w1` の 2 つだけ（この順） |
| FG-05 | `re.sub(r"[^A-Za-z0-9]", "-", primary)` を `primary.replace("/", "-")` に置き換えた写しで 05a | 空（`.` が残るので見つからない）→ 05a の比較が不一致 |

## TC-06 見張りを直したら流すテストと既存のテスト
- 下の決定論ゲートのすべてが exit 0
- `test_guard_corpus_diff.sh` は SKIP ではなく「OK: 新しく確認・停止 N 件」を出す（5-6 の後はワークツリーでも作業記録を読む）。N は 37 件（1%）以内。新しく停止は 0 件。出た件数と中身を計画変更記録に書く（計画時の見込み 4 件）

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i444_guard_gaps.sh
bash scripts/claude/tests/test_pretooluse_container_guard.sh
bash scripts/claude/tests/test_i200_guard_narrowing.sh
bash scripts/claude/tests/test_pretooluse_guard_matrix.sh
bash scripts/claude/tests/test_guard_bash_oracle.sh
bash scripts/claude/tests/test_guard_corpus_diff.sh
bash scripts/claude/tests/test_i182_corpus_base.sh
python3 -m py_compile scripts/claude/hooks/pretooluse_guard.py
python3 -m py_compile scripts/claude/tests/guard_corpus_diff.py
```
