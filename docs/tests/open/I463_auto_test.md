# I463 自動テスト: 見張りのオプションの値の読み方を、値を取る文字の表で直す

実行コマンド: `bash scripts/claude/tests/test_i463_guard_optspec.sh`（新規・TC-01〜TC-08）・`bash scripts/claude/tests/test_guard_must_stop_cases.sh`（新規・TC-09）と、見張りの既存テスト（TC-10）。アプリのテスト（pytest・Jest・E2E）は変更が無いので CI に任せる。

新しいテスト `test_i463_guard_optspec.sh` は `test_i454_guard_env_writes.sh` と同じ形: 一時リポジトリ（今のワークツリーの代役）に別ワークツリー `$W` を作り、一時リポジトリの中から見張りに Bash の JSON を渡して判定だけを見る（コマンドは実行しない）。期待値 `2`＝停止・`ASK`＝確認（exit 0 ＋ `permissionDecision: ask`）・`0`＝通す。0＝全 PASS／1＝FAIL あり。`D='docker compose exec -T backend'`。`$TMP/evil.py` は `import django`・`from apps.users.models import User`・`User.objects.all().delete()` の 3 行（ホストの python でもアプリを import するので危険操作を判定する）。失敗の注入（FG）は、見張りの写しの 1 か所を置き換え（置き換える文字列が見張りにちょうど 1 回だけあることを確かめ、無ければ FAIL）、その写しで同じケースが期待どおりに変わることを確かめる。FG の置き換え元の文字列は実装で決まるので、implement で下の表に書き写す（意図は表に書いたとおり）。

結果:
- 計画時（2026-11-12）: テストのファイルがまだ無いので未実行（実装前のため未実行）。同じ形を develop の見張りに流した「今」の判定は計画書「調査結果」の表のとおり（01a・01b が 0、02a が 2、03a・03b・03c が 0、05a が 2、06a〜06d が ASK、07a・07f が 2）。直した後の期待とずれる形がこのイシューの対象で、それ以外の形は今も期待どおり

## TC-01 python はスクリプト名でオプションを読み終える（F15）
| ID | コマンド | 期待 |
|---|---|---|
| 01a | `python3 $TMP/evil.py -xcfoo`（スクリプトの引数の c を `-c` と読まない） | 2 |
| 01b | `python3 $TMP/evil.py -vc 1` | 2 |
| 01c | `python3 $TMP/evil.py`（今までどおり） | 2 |
| 01d | `python3 -Xdev $TMP/evil.py`（`-X` の値を飛ばしてスクリプトを読む） | 2 |
| 01e | `python3 -c 'print(1)' $TMP/evil.py`（コードは `-c`。後ろはスクリプトの引数） | 0 |
| 01f | `$D python manage.py shell -c 'from apps.users.models import User; User.objects.all().delete()'` | 2 |
| FG-01 | `_getopt` の python の「位置引数で読み終える」行を消した写しで 01a | 0 |

## TC-02 psql の値の中の文字を `-c` と読まない（F14・F16）
| ID | コマンド | 期待 |
|---|---|---|
| 02a | `psql -Umarc drop-test`（`-U` の値の c。F14） | 0 |
| 02b | `psql -hlocalhost -Ucelery -c 'select 1'`（偽の候補 `alhost` が SQL に混ざらない。F16） | 0 |
| 02c | `psql -Umarc mydb -c 'DELETE FROM users'` | 2 |
| 02d | `psql -hlocal$(hostname) -U postgres <<EOF` ＋ `DELETE FROM users;` ＋ `EOF`（置換の印のある値でもヒアドキュメントの SQL を見る。F16） | 2 |
| FG-02 | `_OPTSPEC` の psql の文字から `U` を消した写し（`-U` の値を読まない）で 02a | 2 |

## TC-03 まとめ書きの途中の値を読む（F17）
| ID | コマンド | 期待 |
|---|---|---|
| 03a | `psql -Xf/tmp/dump.sql` | 2 |
| 03b | `$D psql -Xf/tmp/dump.sql` | 2 |
| 03c | `grep -ie. .env`（`-e` の値は `.`、`.env` は読むファイル） | ASK |
| 03d | `grep -f .env x`（パターンを .env から読む。今までどおり） | ASK |
| 03e | `grep -m1 x .env`（今までどおり） | ASK |
| 03f | `grep -ie. README.md` | 0 |
| FG-03 | psql の `-f` の判定の `cmd="psql"` を外した写し（表を使わない読み方）で 03a | 0 |

## TC-04 psql の `-d` の値の f を `-f` と読まない（F2）
| ID | コマンド | 期待 |
|---|---|---|
| 04a | `psql -dprofile_db -c "select 1"` | 0 |
| 04b | `$D psql -dprofile_db -c "select 1"` | 0 |

## TC-05 sed の in-place の判定（F4）
| ID | コマンド | 期待 |
|---|---|---|
| 05a | `sed -e's/print/log/' $W/x`（式の i を `-i` と読まない） | 0 |
| 05b | `sed -ie s/a/b/ $W/x`（GNU sed は接尾辞 e の `-i`。今までどおり） | 2 |
| 05c | `sed -i.bak s/a/b/ $W/x` | 2 |
| 05d | `sed --in-place=.bak -e s/a/b/ $W/x` | 2 |
| 05e | `sed -n -f $W/x /tmp/y`（スクリプトを読むだけ） | 0 |
| FG-05 | `_write_targets` の sed の in-place の判定を `_has_short(args, "i", "--in-place")`（今の作り）に戻した写しで 05a | 2 |

## TC-06 読む指定を書き込みと見なさない（F6）
| ID | コマンド | 期待 |
|---|---|---|
| 06a | `$D pytest --cov=/app/apps` | 0 |
| 06b | `$D pytest --ignore=/app/apps/x` | 0 |
| 06c | `$D pytest --cov-config=/app/.coveragerc` | 0 |
| 06d | `$D pytest --deselect=/app/apps/t.py::test_a` | 0 |
| 06e | `$D pytest --basetemp=/app/tmp`（書き出し先・今までどおり） | ASK |
| 06f | `$D pytest --junitxml=/app/r.xml -k x`（今までどおり） | ASK |
| FG-06 | `_OPT_READ_PATH` から `"cov", ` を消した写しで 06a | ASK |

## TC-07 cp／mv の書き先と移動元（敵対的レビューの Medium・F18・I444 F7）
| ID | コマンド | 期待 |
|---|---|---|
| 07a | `cp -vt/tmp/d $W/a $W/b`（くっつけた -t と複数の読み元） | 0 |
| 07b | `cp -t /tmp/d $W/a $W/b`（今までどおり） | 0 |
| 07c | `cp -vt$W/d /tmp/a /tmp/b` | 2 |
| 07d | `mv -vt/tmp/d $W/a`（移動元が消える） | 2 |
| 07e | `install -m644 /tmp/a $W/b` | 2 |
| 07f | `mv -S $W/sfx /tmp/a /tmp/b`（`-S` の値は移動元ではない。I444 F7） | 0 |
| FG-07 | `_write_targets` の `return tdir or (pos[-1:] if len(pos) >= 2 else [])` を `return tdir + pos[-1:]`（-t があっても最後の位置引数を足す・今の作り）に置き換えた写しで 07a | 2 |

## TC-08 シェルを包むコマンドの `-c`（su・flock・script）
| ID | コマンド | 期待 |
|---|---|---|
| 08a | `su -lc'git push --force origin develop'` | 2 |
| 08b | `su -s/bin/bash -c 'git push --force origin develop'` | 2 |
| 08c | `flock -w3 /tmp/l -c 'git push --force origin develop'` | 2 |
| 08d | `script -qc 'git push --force origin develop' /dev/null` | 2 |

## TC-09 止めるべき形の一覧で版を比べる（予防策）
| ID | 確かめ | 期待 |
|---|---|---|
| 09a | `python3 scripts/claude/tests/guard_corpus_diff.py --cases scripts/claude/tests/guard_must_stop_cases.txt` | exit 0（一覧のすべてが作業ツリーで確認か停止・変更前より弱い判定 0 件・異常終了 0 件） |
| 09b（FG） | `_cmd_danger` の `r.append("destructive SQL requires DANGER_OK=1")` を `pass` に置き換えた見張りの写しを `--guard` に渡す | exit 1（変更前より弱い判定があると出す） |
| 09c（FG） | 一覧に `echo hi` を足した写しを `--cases` に渡す | exit 1（作業ツリーで通す形があると出す） |
`bash scripts/claude/tests/test_guard_must_stop_cases.sh` が 09a〜09c をまとめて確かめ、すべて期待どおりなら exit 0。

## TC-10 見張りの既存テスト（失敗の注入の置き換え元を新しいコードに合わせる）
`test_i454_guard_env_writes.sh` の FG-02・FG-07c・FG-07d と `test_i444_guard_gaps.sh` の FG-02a・FG-02b は、置き換え元がステップ 1 で消えるので、同じ守りを外す新しい置き換えに変える（期待値・守る形は変えない）。
| ID | 確かめ | 期待 |
|---|---|---|
| 10a | 下の「決定論ゲート」の各行 | すべて exit 0 |

## TC-11 作業記録での判定比較（重いテスト・test-gate で手で流す）
`bash scripts/claude/tests/test_guard_corpus_diff.sh --base <develop との分かれた点> --rebuild` を、implement の後と test-gate で上限なしで手で流す（数分かかり、決定論ゲートの 1 行 120 秒に収まらないため、ゲートに置かない・I444）。「OK: 新しく確認・停止 N 件」を出し、N は記録の 1% 以内・異常終了 0 件。件数と、新しく確認・停止になった中身をこの文書の結果に書く。

## TC-12 手順書と一覧
| ID | 確かめ | 期待 |
|---|---|---|
| 12a | `grep -q "test_guard_must_stop_cases.sh" docs/runbooks/danger-ops.md` | exit 0 |
| 12b | `! grep -q "^- F14 " docs/reviews/backlog/I454.md` | exit 0 |
| 12c | `! grep -q "^- F18 " docs/reviews/backlog/I454.md` | exit 0 |
| 12d | `! grep -q "^- F7 " docs/reviews/backlog/I444.md` | exit 0 |
12a〜12d は意図的な変更でしか崩れない文書の確かめなので、決定論ゲートには置かず implement の後に 1 回流して記録する（plan-writing-rules.md「決定論テストの対象の選び方」）。

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i463_guard_optspec.sh
bash scripts/claude/tests/test_guard_must_stop_cases.sh
bash scripts/claude/tests/test_i454_guard_env_writes.sh
bash scripts/claude/tests/test_i444_guard_gaps.sh
bash scripts/claude/tests/test_pretooluse_container_guard.sh
bash scripts/claude/tests/test_i200_guard_narrowing.sh
bash scripts/claude/tests/test_pretooluse_guard_matrix.sh
bash scripts/claude/tests/test_guard_bash_oracle.sh
bash scripts/claude/tests/test_pretooluse_worktree_guard.sh
bash scripts/claude/tests/test_i182_corpus_base.sh
python3 -m py_compile scripts/claude/hooks/pretooluse_guard.py scripts/claude/tests/guard_corpus_diff.py
```
