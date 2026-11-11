# I454 自動テスト: 見張りの環境変数の表示の後退（ps -A e）と書き先の取りこぼしを直す

実行コマンド: `bash scripts/claude/tests/test_i454_guard_env_writes.sh`（新規）と、見張りを直したら流すテスト（TC-06）。アプリのテスト（pytest・Jest・E2E）は変更が無いので CI に任せる。

新しいテスト `scripts/claude/tests/test_i454_guard_env_writes.sh` は、見張りに Bash の JSON を渡して判定だけを見る（コマンドは実行しない）。形は `test_i444_guard_gaps.sh` と同じ: 期待値 `2`＝停止・`ASK`＝確認（exit 0 ＋ `permissionDecision: ask`）・`0`＝通す。0＝全 PASS／1＝FAIL あり。失敗の注入（FG）は、見張りの写しの 1 か所を置き換え（置き換える文字列が見張りにちょうど 1 回だけあることを確かめ、無ければ FAIL）、その写しで同じケースが期待どおりに変わることを確かめる。`D='docker compose exec -T backend'`。TC-04 は `test_pretooluse_worktree_guard.sh` と同じく一時リポジトリに別ワークツリー `$W` を作り、一時リポジトリの中から見張りを呼ぶ。

結果:
- 計画時（2026-11-12）: テストのファイルがまだ無いので未実行（実装前のため未実行）。同じケースを見張りの写し（計画書「調査結果」のスパイク）に流し、TC-01〜TC-04 の期待値どおりになることは確かめた。変更前の見張りでは、TC-01 の 01a〜01c・01i・01j が 0、01f・01g が ASK（F11 の誤検出）、TC-02 の 02a・02e が 0、TC-03 の 03a が 0・03e と 03f が ASK（余計な確認）、TC-04 の 04a〜04f が 0（＝今の取りこぼし）
- 2026-11-12（implement・/simplify の後）: `bash scripts/claude/tests/test_i454_guard_env_writes.sh` → pass=44 fail=0（exit 0。FG-01〜FG-04 を含む）。`test_i444_guard_gaps.sh` pass=64・`test_pretooluse_container_guard.sh` pass=788・`test_i200_guard_narrowing.sh` pass=75・`test_pretooluse_guard_matrix.sh` pass=391・`test_guard_bash_oracle.sh` 見逃し 0・余計な停止 0・`test_pretooluse_worktree_guard.sh` pass=127・`test_i182_corpus_base.sh` pass=5、すべて fail=0（exit 0）。`py_compile` OK
- TC-06 の過去の作業コマンドでの比較（implement の後・test-gate で手で流し、ここに件数と中身を書く）: 計画時のスパイク（写しの見張り・15576 件）は新しく確認・停止 4 件・異常終了 0 件・OK（計画書「調査結果」）。implement の後: （未実施）。test-gate: （未実施）

## TC-01 環境変数をまとめて表示する形（F10・F11・F12）
| ID | コマンド | 期待 |
|---|---|---|
| 01a | `ps -A e`（ホスト・値を取らないフラグの後ろの e。F10） | ASK |
| 01b | `ps -ef e`（ホスト） | ASK |
| 01c | `$D ps -A e` | ASK |
| 01d | `ps -o pid e`（値の後ろの e） | ASK |
| 01e | `ps -u root e`（値の語が BSD 形式の値の文字〔t〕で終わる） | ASK |
| 01f | `ps o etime`（BSD 形式の値。F11） | 0 |
| 01g | `ps U user`（F11） | 0 |
| 01h | `ps --sort etime`（長い形の値） | 0 |
| 01i | `declare +x`（F12） | ASK |
| 01j | `typeset +x`（F12） | ASK |
| 01k | `declare +x FOO`（属性を外すだけ・表示ではない） | 0 |
| FG-01 | `not _PS_VALUE_OPT_RE.fullmatch(p)` を `not p.startswith("-")`（I444 の近似）に置き換えた写しで 01a | 0 |
| FG-01b | `all(a.startswith(("-", "+")) for a in toks[1:])` を `all(a.startswith("-") for a in toks[1:])` に置き換えた写しで 01i | 0 |

I444 で固定した形（`ps e`・`ps auxe`・`ps aux e`・`ps -u postgres e`・`export`・`declare -p` は ASK、`ps -C node`・`ps -u postgres`・`ps -p 1 -o etime`・`declare -x FOO=1`・`ps -eo etimes,pcpu,args --sort=-etimes` は 0）は `test_i444_guard_gaps.sh` の TC-01 が確かめる（TC-06）。

## TC-02 コンテナの /tmp/ 以外への書き込み（くっつけた -t・sed の式の付着形）
| ID | コマンド | 期待 |
|---|---|---|
| 02a | `$D cp -vt/app/x /tmp/y` | ASK |
| 02b | `$D cp -t/app/x /tmp/y` | ASK |
| 02c | `$D install -d /app/newdir`（作るだけ・設計確認メモ） | 0 |
| 02d | `$D cp -vt/tmp/x /app/y`（書き先は /tmp/） | 0 |
| 02e | `$D sed -i -es/a/b/ /app/x`（式を -e にくっつけた形） | ASK |
| 02f | `$D sed -i -e s/a/b/ /tmp/x`（式の語は書き先ではない） | 0 |
| 02g | `$D install -m 644 /tmp/a /app/b` | ASK |
| FG-02 | `_opt_values` の `(j == 0 or body[:j].isalpha())` を `j == 0` に置き換えた写しで 02a | 0 |

## TC-03 通す形でも /tmp/ 以外への書き込みは確認（危ない語の理由と書き込みの理由を分ける）
| ID | コマンド | 期待 |
|---|---|---|
| 03a | `$D pytest --junitxml=/app/r.xml -k x` | ASK |
| 03b | `$D pytest --junitxml=/tmp/r.xml -k delete` | 0 |
| 03c | `$D pytest -k delete` | 0 |
| 03d | `$D sh -c "pytest -k delete > /app/out.txt"`（コンテナの中のリダイレクト） | ASK |
| 03e | `$D sh -c "pytest -k delete > /tmp/out.txt"`（通す形の /tmp/ へのリダイレクト。変更前は語で ASK） | 0 |
| 03f | `$D grep -rn foo /app/apps > out.txt`（ホスト側のリダイレクトはコンテナの書き込みではない） | 0 |
| FG-03 | `_container_risky` の書き込みの判定 `if any(not _in_scratch(t) for t in c["write_to"] + _write_targets(c["toks"]) + vals):` を `if not _container_safe(c) and any(not _in_scratch(t) for t in c["write_to"] + _write_targets(c["toks"]) + vals):` に置き換えた写し（＝通す形なら書き込みの判定も飛ばす・変更前の作り）で 03a | 0 |

## TC-04 別ワークツリーへの書き込みの停止（書き先の見分け方を 1 つに）
| ID | コマンド | 期待 |
|---|---|---|
| 04a | `cp -vt$W/x /tmp/y` | 2 |
| 04b | `cp --target-directory=$W/x /tmp/y` | 2 |
| 04c | `install /tmp/y $W/x` | 2 |
| 04d | `ln -s /tmp/y $W/x` | 2 |
| 04e | `rsync -a /tmp/y $W/x` | 2 |
| 04f | `mv $W/x /tmp/y`（移動元が消える） | 2 |
| 04g | `cp /tmp/y $W/x`（今までどおり） | 2 |
| 04h | `cp -t $W/x /tmp/y`（今までどおり） | 2 |
| 04i | `sed -i s/a/b/ $W/x`（今までどおり） | 2 |
| 04j | `tee $W/x`（今までどおり） | 2 |
| 04k | `echo x > $W/x`（今までどおり） | 2 |
| 04l | `cp $W/x /tmp/y`（読むだけ） | 0 |
| 04m | `ln -s $W/x /tmp/y`（リンク先として指すだけ） | 0 |
| 04n | `install -d $W/newdir`（作るだけ・設計確認メモ） | 0 |
| 04o | `sed -n p $W/x`（読むだけ） | 0 |
| FG-04 | `_bash_write_targets` の `        targets += _write_targets(toks)` の行の右辺を `[]` に置き換えた写しで 04a | 0 |

## TC-05 I444 のテストの失敗の注入を新しいコードに合わせる
`test_i444_guard_gaps.sh` の FG-01・FG-01b・FG-02a・FG-02b は、置き換える文字列が見張りから消える（5-1・5-2）ので「置き換え NOPATCH」で FAIL になる。置き換える文字列を新しいコードに合わせる（守る形は変えない）。
| ID | 確かめ | 期待 |
|---|---|---|
| 05a | `bash scripts/claude/tests/test_i444_guard_gaps.sh` | exit 0（NOPATCH の FAIL が無い） |

## TC-06 見張りを直したら流すテストと既存のテスト
- 下の決定論ゲートのすべてが exit 0
- `bash scripts/claude/tests/test_guard_corpus_diff.sh --rebuild` を、implement の後と test-gate で上限なしで手で流す（数分かかり、決定論ゲートの 1 行 120 秒に収まらないため、ゲートに置かない・I444 の fix-loop 1）。「OK: 新しく確認・停止 N 件」を出し、N は記録の 1% 以内・異常終了 0 件。出た件数と中身をこの文書の結果の欄に書く

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i454_guard_env_writes.sh
bash scripts/claude/tests/test_i444_guard_gaps.sh
bash scripts/claude/tests/test_pretooluse_container_guard.sh
bash scripts/claude/tests/test_i200_guard_narrowing.sh
bash scripts/claude/tests/test_pretooluse_guard_matrix.sh
bash scripts/claude/tests/test_guard_bash_oracle.sh
bash scripts/claude/tests/test_pretooluse_worktree_guard.sh
bash scripts/claude/tests/test_i182_corpus_base.sh
python3 -m py_compile scripts/claude/hooks/pretooluse_guard.py
```
