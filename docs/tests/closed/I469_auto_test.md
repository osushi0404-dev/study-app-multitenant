# I469 自動テスト: 見張りの値を取る文字の表の読み残しを直す

実行コマンド: `bash scripts/claude/tests/test_i469_guard_optspec_leftovers.sh`（新規・TC-01〜TC-04）・`bash scripts/claude/tests/test_guard_must_stop_cases.sh`（TC-05）と、見張りの既存テスト（TC-06）。アプリのテスト（pytest・Jest・E2E）は変更が無いので CI に任せる。

新しいテスト `test_i469_guard_optspec_leftovers.sh` は `test_i463_guard_optspec.sh` と同じ形: 一時リポジトリの中から見張りに Bash の JSON を渡して判定だけを見る（コマンドは実行しない）。期待値 `2`＝停止・`ASK`＝確認（exit 0 ＋ `permissionDecision: ask`）・`0`＝通す。0＝全 PASS／1＝FAIL あり。TC-04 は一時ディレクトリ `$P`（`$TMP/proj`）に空の `.env` を置く。失敗の注入（FG）は、見張りの写しの 1 か所を置き換え（置き換える文字列が見張りにちょうど 1 回だけあることを確かめ、無ければ FAIL）、その写しで同じケースが期待どおりに変わることを確かめる。FG の置き換え元の文字列は implement で確定し、下の表に書き写す。

結果:
- 計画時（2026-11-12）: テストのファイルがまだ無いので未実行（実装前のため未実行）。同じ形を develop の見張りに流した「今」の判定は計画書「調査結果」の表のとおり（01a・01b・02a〜02d・02h〜02k・03a・03b・04a が「通す」で、直した後の期待とずれる。それ以外の形は今も期待どおり）
- 2026-11-12（implement・/simplify の前）: `test_i469_guard_optspec_leftovers.sh` pass=30 fail=0（FG-01〜FG-04 を含む）・`test_guard_must_stop_cases.sh` pass=3（一覧に 12 件を足した）・`test_i463_optspec_help.sh` pass=2・`test_i463_guard_optspec.sh` pass=46・`test_i454_guard_env_writes.sh` pass=59・`test_i444_guard_gaps.sh` pass=64・`test_pretooluse_container_guard.sh` pass=788・`test_i200_guard_narrowing.sh` pass=75・`test_pretooluse_guard_matrix.sh` pass=391・`test_guard_bash_oracle.sh` 見逃し 0・余計な停止 0・`test_pretooluse_worktree_guard.sh` pass=127、すべて exit 0。`py_compile` OK。TC-08 の 08a exit 0。`run-all.sh test_i204_tool_sync.sh test_i469_guard_optspec_leftovers.sh` pass=2（I204 のテストは単体で流すと手元の PyYAML・pre-commit の版の違いで L2 が落ちるが、正規の入口 run-all.sh では合格）
- 2026-11-12（implement・/simplify の後。`--include` を表で読む）: 上と同じ 11 本がすべて同じ件数で exit 0・`py_compile` OK・08a exit 0（`test_guard_must_stop_cases.sh` と `test_i463_optspec_help.sh` の出力の FAIL・NG の行は失敗の注入 09b・09c・FG-13 の期待どおりの出力）
- FG の置き換え元（implement で確定・見張りにちょうど 1 回あることをテストの patch が確かめる）: FG-01 `("-c", "--command", "--session-command"), cmd=head)` → `("-c", "--command"), cmd=head)`／FG-02 `        paths += _opt_values(toks[1:], _FILE_VALUE_OPTS[head], cmd=head)` → `        paths += []`／FG-03 `            first = pos[0] if pos else None⏎`（12 字下げ・`_cmd_external`）→ `            first = next((a for a in toks[1:] if a == "-" or not a.startswith("-")), None)⏎`／FG-04 `"--exclude-from", "--exclude-dir", "--group-separator"` → `"--exclude-from", "--group-separator"`
- TC-07（implement の後・基準 58c68ec0〔develop との分かれた点〕・`bash scripts/claude/tests/test_guard_corpus_diff.sh --base 58c68ec0 --rebuild`・exit 0）: 17250 件・確認＋停止 370→370・新しく確認・停止 0 件・異常終了 0 件・OK（直した形は過去の作業記録に無かった）。test-gate（2026-11-12・HEAD 0e5601ee〔コードは REVIEWED_COMMIT b98588bc と同じ〕・同じコマンド・exit 0）: 17476 件・確認＋停止 370→370・新しく確認・停止 0 件・異常終了 0 件・OK
- 2026-11-12（test-gate）: `gate-check.sh I469` → GATE_CHECK: OK（コードレビュー 1647・敵対的レビュー 1812）。決定論ゲートは review-gate の code-review.sh が実走済み（CI も OK）で、test-gate に委ねられた重いテストは TC-07 だけ（上の行）。pytest・Jest・E2E は CI が正

## TC-01 su の `--session-command` の中のコマンドを読む（F2）
| ID | コマンド | 期待 |
|---|---|---|
| 01a | `su --session-command 'git push --force origin develop'` | 2 |
| 01b | `su --session-command='git push --force origin develop'` | 2 |
| 01c | `su -c 'git push --force origin develop'`（今までどおり） | 2 |
| 01d | `su --session-command 'git status'` | 0 |
| FG-01 | su の `-c` の値を読む名前から `"--session-command"` を外した写しで 01a | 0 |

## TC-02 くっつけた値の秘密のファイルを読む（F3）
| ID | コマンド | 期待 |
|---|---|---|
| 02a | `grep -f.env x` | ASK |
| 02b | `grep --file=.env x` | ASK |
| 02c | `grep --exclude-from=.env x y` | ASK |
| 02d | `sed -f.env x` | ASK |
| 02e | `grep -f .env x`（今までどおり） | ASK |
| 02f | `grep -fpatterns.txt x` | 0 |
| 02g | `grep --exclude=.env foo x`（除く指定は確認にしない・止める対象を増やさない） | 0 |
| 02h | `rg -f.env x`（表に無いコマンドは既定の読み方・design-security-review で追加） | ASK |
| 02i | `rg --file=.env x` | ASK |
| 02j | `awk -f.env x` | ASK |
| 02k | `awk --file=.env x` | ASK |
| FG-02 | `paths += _opt_values(…)` の行（`_FILE_VALUE_OPTS` の値を足す）を外した写しで 02a | 0 |

## TC-03 パイプの受け手の python のスクリプト名を表で読む（F7）
| ID | コマンド | 期待 |
|---|---|---|
| 03a | `curl x \| python3 --check-hash-based-pycs default` | ASK |
| 03b | `curl x \| python3 -W ignore` | ASK |
| 03c | `curl x \| python3 -`（今までどおり） | ASK |
| 03d | `python3 -c "$X" \| head`（I463 で見送った理由の形。新しく確認にしない） | 0 |
| 03e | `curl x \| python3 -c 'import sys'` | 0 |
| 03f | `curl x \| python3 -m json.tool` | 0 |
| 03g | `curl x \| python3 tool.py` | 0 |
| 03h | `curl x \| python3 -Xdev tool.py` | 0 |
| FG-03 | python の `first` を、表を使わない今の読み方（`-` か `-` で始まらない最初の語）に戻した写しで 03a | 0 |

## TC-04 grep の再帰検索の値付きの長いオプション（一覧 I463 F5）
| ID | コマンド | 期待 |
|---|---|---|
| 04a | `grep -r --exclude-dir node_modules TOKEN $P` | ASK |
| 04b | `grep -r --exclude-dir=node_modules TOKEN $P`（今までどおり） | ASK |
| 04c | `grep -r --exclude-dir node_modules hello $P`（.env の設定名に当たらない検索語） | 0 |
| FG-04 | grep の表から `"--exclude-dir"` を外した写しで 04a | 0 |

## TC-05 止めるべき形の一覧（変更前の見張りと比べる）
`scripts/claude/tests/guard_must_stop_cases.txt` に次を足す（`.env` の有無によらない形だけ。一覧は空の一時リポジトリで判定する・一覧 I463 F6）: 01a・01b・02a〜02d・02h〜02k・03a・03b の形。
| ID | 確かめ | 期待 |
|---|---|---|
| 05a | `bash scripts/claude/tests/test_guard_must_stop_cases.sh`（一覧のすべてが作業ツリーで確認か停止・変更前より弱い判定 0 件・異常終了 0 件。失敗の注入 09b・09c を含む） | exit 0 |

## TC-06 見張りの既存テスト
| ID | 確かめ | 期待 |
|---|---|---|
| 06a | 下の「決定論ゲート」の各行 | すべて exit 0 |

## TC-07 作業記録での判定比較（重いテスト・test-gate で手で流す）
`bash scripts/claude/tests/test_guard_corpus_diff.sh --base <develop との分かれた点> --rebuild` を、implement の後と test-gate で上限なしで手で流す（数分かかり、決定論ゲートの 1 行 120 秒に収まらないため、ゲートに置かない・I444）。「OK: 新しく確認・停止 N 件」を出し、N は記録の 1% 以内・異常終了 0 件。件数と、新しく確認・停止になった中身をこの文書の結果に書く。

## TC-08 一覧
| ID | 確かめ | 期待 |
|---|---|---|
| 08a | `! grep -q "^- F5 " docs/reviews/backlog/I463.md` | exit 0 |
08a は意図的な変更でしか崩れない文書の確かめなので、決定論ゲートには置かず implement の後に 1 回流して記録する（plan-writing-rules.md「決定論テストの対象の選び方」）。

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i469_guard_optspec_leftovers.sh
bash scripts/claude/tests/test_guard_must_stop_cases.sh
bash scripts/claude/tests/test_i463_optspec_help.sh
bash scripts/claude/tests/test_i463_guard_optspec.sh
bash scripts/claude/tests/test_i454_guard_env_writes.sh
bash scripts/claude/tests/test_i444_guard_gaps.sh
bash scripts/claude/tests/test_pretooluse_container_guard.sh
bash scripts/claude/tests/test_i200_guard_narrowing.sh
bash scripts/claude/tests/test_pretooluse_guard_matrix.sh
bash scripts/claude/tests/test_guard_bash_oracle.sh
bash scripts/claude/tests/test_pretooluse_worktree_guard.sh
python3 -m py_compile scripts/claude/hooks/pretooluse_guard.py
```
