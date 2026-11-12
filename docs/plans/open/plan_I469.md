# 計画書: I469 見張りの値を取る文字の表の読み残しを直す

## 基本情報
- **計画書ID**: plan_I469
- **関連イシュー**: #469
- **Draft PR**: #475
- **作成根拠資料**: docs/issues/open/I469.md（起点イシュー・GitHub #469 の本文の写し）
- **実装後評価**: docs/reviews/open/I469_review.md
- **作成日**: 2026-11-12

## 1. 背景/目的
- **背景**: I463 で見張り（`scripts/claude/hooks/pretooluse_guard.py`）に値を取る文字の表（`_OPTSPEC`）と getopt と同じ読み方（`_getopt`）を入れた。レビューで、表に無い値付きのオプションと、表を使わず手で探している箇所が残った（I463 の台帳 F2・F3・F7。どれも I463 の前からある取りこぼし）
- **目的**: 秘密情報の表示・強制 push の取りこぼしになる読み残しを、I463 の表の方式のまま直す。止める対象（確認・停止にするコマンドの種類）は増やさず、離して書けば今も確認・停止になる形を、くっつけた形でも同じ判定にする

## 2. 受け入れ条件
イシューの受け入れ条件と同じ。ただし 1 行目の su の形は、調査結果のとおり `-C` がどの版の su にも無いので、実在する `--session-command` に置き換える（9.「イシューから変えたこと」）。
1. 次の形が期待の判定になり、決定論のテスト（失敗の注入つき）で固定されている → TC-01〜TC-04

   | 形 | 期待（停止＝exit 2・確認＝ask） | 離して書いた同じ意味の形の今の判定 |
   |---|---|---|
   | `su --session-command 'git push --force origin develop'`・`su --session-command='…'`（F2） | 停止 | `su -c '…'` は停止 |
   | `grep -f.env x`・`grep --file=.env x`（F3） | 確認 | `grep -f .env x` は確認 |
   | `curl x \| python3 --check-hash-based-pycs default`（F7） | 確認 | `curl x \| python3 -` は確認 |
2. `bash scripts/claude/tests/test_guard_must_stop_cases.sh`（止めるべき形の一覧に上の形を足したもの）と見張りの既存テストがすべて合格する → TC-05・TC-06
3. 作業記録での判定比較（`bash scripts/claude/tests/test_guard_corpus_diff.sh --rebuild`）で「新しく確認・停止」が分母の 1% 以内・異常終了 0 件 → TC-07

## 3. 影響範囲
| 区分 | 内容 |
|---|---|
| Backend | なし |
| Frontend | なし |
| DB | なし |
| Config/Infra | 見張り（PreToolUse フック）の判定。全ワークツリーの Bash の確認・停止が変わる（くっつけた形の秘密のファイルの読み出し・su の `--session-command`・値付きのオプションの後のパイプの python・grep の再帰検索の値付きの長いオプションを、離した形と同じに確認・停止にする）。`.claude/settings.json` は変えない |
| ハーネステスト | 新しいテスト 1 本（`test_i469_guard_optspec_leftovers.sh`）・止めるべき形の一覧に行を足す |
| 文書 | `docs/reviews/backlog/I463.md`（同梱した F5 の行を消す） |

P3/P5/P8 影響なし（DB・外部 API・非同期処理・依存ファイルの変更なし）。P6 影響なし（UI なし）。P9 影響なし（個人情報・テナントデータを扱わない）。

## 調査結果

### 環境前提
- 手元にある: `su`（util-linux 2.39）・`grep`（GNU）・`sed`・`flock`・`python3`。見張りのテストはコマンドを実行せず JSON を渡して判定だけを見るので、これだけで流せる
- `su --help`（`LC_ALL=C`）: `-c, --command <command>` と、短い形の無い `--session-command <command>` がある。`-C` は無い。util-linux の su の文書（man7・Debian・openSUSE・Ubuntu の各版）にも `-C` は無く、`--session-command` は長い形だけ（2026-11-12 に Web 検索で確認）。`-C` を付けた su はどの版でも「不正なオプション」で何も実行しない
- `grep --help` の値を取る長いオプションのうち表に無いもの: `--label`・`--binary-files`・`--include`・`--exclude`・`--exclude-from`・`--exclude-dir`・`--group-separator`（`--color[=WHEN]` はくっつけたときだけ値を取るので入れない。`=` 付きは今も読める）

### 今の見張りでの再現（2026-11-12・develop の見張り・このワークツリーで判定だけを見る）
| 指摘 | 形 | 今 | 直した後 |
|---|---|---|---|
| F2 | `su -C 'git push --force origin develop'` | 通す | 通す（su が実行しない形・下の 9.） |
| F2 | `su --session-command 'git push --force origin develop'`・`su --session-command='…'` | 通す・通す | 停止・停止 |
| F2 | `su -c 'git push --force origin develop'` | 停止 | 停止 |
| F3 | `grep -f.env x`・`grep --file=.env x` | 通す・通す | 確認・確認 |
| F3（同じ原因） | `grep --exclude-from=.env x y`・`sed -f.env x` | 通す・通す | 確認・確認 |
| F3 | `grep -f .env x`・`grep --file .env x` | 確認・確認 | 確認・確認 |
| F3（増やさない側） | `grep -r foo --exclude=.env .`（.env を除く指定。離した `--exclude .env` は今も確認） | 通す | 通す |
| F7 | `curl x \| python3 --check-hash-based-pycs default`・`curl x \| python3 -W ignore` | 通す・通す | 確認・確認 |
| F7 | `curl x \| python3 -` | 確認 | 確認 |
| F7（増やさない側） | `python3 -c "$X" \| head`・`curl x \| python3 -c 'import sys'`・`curl x \| python3 -m json.tool`・`curl x \| python3 tool.py` | 通す（4 つとも） | 通す（4 つとも） |
| 一覧 I463 F5 | `grep -r --exclude-dir node_modules TOKEN .`（.env のあるディレクトリ） | 通す | 確認 |
| 一覧 I463 F5 | `grep -r TOKEN .`（同） | 確認 | 確認 |
| 一覧 I463 F4 | `flock /tmp/l git commit -c x -m '…'`・`flock --wait 3 /tmp/l git push --force origin develop`・`flock /tmp/l -c '…'` | 通す・停止・停止 | 変えない（残す・9.） |

### 原因の概要
見張りは「どのオプションが値を取るか」を表で知るようになったが、表に無い長いオプション（su の `--session-command`・grep の `--exclude-dir` など）と、表を使わずに手で探している 2 か所（秘密のファイルを探す場所・python のスクリプト名）が残っていた。そのため、くっつけて書いた値や、値の語を読み違える。

### 詳細な原因分析
- F2: `_expand`（1773 行）の su は `_opt_values(rest, ("-c", "--command"), cmd=head)` で、`--session-command` を名前に入れていない。表 `_OPTSPEC["su"]`（1871 行）の長いオプションにも無いので、離した形の値も読めない。表は手元の `--help` から作り、短い形の無い `--session-command` を落とした（`-C` はイシューの仮定で、実在しない）
- F3: `_cmd_external`（2304 行）の秘密のファイルを探す `paths` は「`-` で始まらない語」だけ。値をくっつけた `-f.env`・`--file=.env` は `-` で始まるので落ちる。I463 は止める側を減らさないためにここを表に替えなかった（I463 の計画書 9.）
- F7: `_cmd_external`（2298 行）の python の `first` は「`-` か `-` で始まらない最初の語」で、表を使わない。値を取るオプションの値（`--check-hash-based-pycs default` の default・`-W ignore` の ignore）をスクリプト名と読み、パイプの中身をコードとして実行する形を見逃す
- 一覧 I463 F5: `_grep_recursive_secret`（2240 行）は `_getopt("grep", …)` で読むが、表に `--exclude-dir` などが無いので、その値を検索語と読み、本当の検索語をディレクトリと読む

### 軽い指摘の一覧（台帳の残り）
`grep -rnF -e "FILE=scripts/claude/hooks/pretooluse_guard.py |" -e "FILE=scripts/claude/tests/guard_must_stop_cases.txt |" -e "FILE=docs/reviews/backlog/I463.md |" -e "FILE=- |" docs/reviews/backlog/` で当たった行の扱いは 9. に書く。

## 4. 変更点一覧
| ファイル | 関数・定数 | 変更 |
|---|---|---|
| `scripts/claude/hooks/pretooluse_guard.py` | `_OPTSPEC["su"]` | 長いオプションに `--session-command` を足す |
| 同上 | `_expand`（su・script） | `-c` の値を読む名前に `--session-command` を足す |
| 同上 | `_OPTSPEC["grep"]` | 長いオプションに `--label`・`--binary-files`・`--include`・`--exclude`・`--exclude-from`・`--exclude-dir`・`--group-separator` を足す（一覧 I463 F5） |
| 同上 | `_FILE_VALUE_OPTS`（新規）・`_cmd_external` の `paths` | 中身を読むファイルを値に取るオプション（grep `-f`・`--file`・`--exclude-from`、sed `-f`・`--file`）の値を、表で読んで `paths` に足す（今の `-` で始まらない語は残す） |
| 同上 | `_cmd_external` の python の `script_arg` | `_getopt("python", …)` で読み、`-c`・`-m` があるか、最初の位置引数が `-`・`/dev/`・`/proc/` 以外ならスクリプトを指定した形とする |
| `scripts/claude/tests/test_i469_guard_optspec_leftovers.sh`（新規） | — | TC-01〜TC-04 |
| `scripts/claude/tests/guard_must_stop_cases.txt` | — | 止めるべき形を足す（TC-05） |
| `docs/reviews/backlog/I463.md` | F5 の行 | 消す |

`scripts/claude/tests/test_i463_optspec_help.sh`（表と `--help` の突き合わせ）は変えない。短いオプションの文字を変えないので、版の違いで落ちる心配が無い（イシューの実装対象の 4 行目は、`-C` を足す前提だったので不要になった）。

## 5. 実装手順

### ステップ 1: python のスクリプト名を表で読む（F7）
**修正方針**: パイプの受け手の python が「実行するものを指定した形」かを、`_python_code_raw` と同じ `_getopt("python", …)` で読む。`-c`・`-m` は実行するものを指定した形（パイプの中身はデータ）として今と同じ判定にし、値を取るオプションの値をスクリプト名と読まないようにする。
```python
        # 実行するものを指定した python（スクリプト名・-c・-m）では、パイプで流れるのはデータでコードではない。
        # 値を取るオプション（-W ignore・--check-hash-based-pycs default）の値はスクリプト名ではない（表で読む・I469 F7）。
        # ただし `python - 引数` と `python /dev/stdin` は標準入力（パイプの中身）をコードとして実行する
        script_arg = False
        if _PYTHON_RE.match(head) and not dj:
            opts, pos = _getopt("python", toks[1:])
            first = pos[0] if pos else None
            script_arg = any(n in ("-c", "-m") for n, _v in opts) \
                or (first is not None and first != "-" and not first.startswith(("/dev/", "/proc/")))
        if not f[0] and c["piped"] and not c["compose"] and not script_arg:
            r.append("パイプで流し込むコード（中身が見えない）")
```
- → TC-03 参照
- 依存: なし（最初に行う。止める側が新しく増える形〔`python3 -W ignore` など〕の量がこのイシューの未知のリスクなので先に置き、TC-07 で量を測る）

### ステップ 2: くっつけた値の秘密のファイルを読む（F3）
**修正方針**: 中身を読むファイルを値に取るオプションだけを表で読み、その値を `paths` に足す。今の「`-` で始まらない語」は残すので、止める側は減らない。除く指定（`--exclude=.env`）やパターン（`-e.env`）の値は足さない（止める対象を増やさない）。
```python
# 中身を読むファイルを値に取るオプション（I469 F3）。くっつけた値（grep -f.env・--file=.env）も、離した形と同じに秘密のファイルを探す
_FILE_VALUE_OPTS = {"grep": ("-f", "--file", "--exclude-from"), "sed": ("-f", "--file")}
...
    paths = [a for a in toks[1:] if not a.startswith("-")]
    if head in _PATTERN_FIRST and not _opt_values(toks[1:], ("-e", "-f", "--regexp", "--file"), cmd=head):
        paths = paths[1:]
    if head in _FILE_VALUE_OPTS:
        paths += _opt_values(toks[1:], _FILE_VALUE_OPTS[head], cmd=head)
```
- → TC-02 参照
- 依存: ステップ 3 の grep の表の `--exclude-from`（離した `--exclude-from .env` を値として読む）とあわせて行う

### ステップ 3: 表に無い値付きの長いオプションを足す（F2・一覧 I463 F5）
**修正方針**: su に `--session-command`、grep に値を取る長いオプションを足し、su の `-c` の値を読む名前に `--session-command` を足す。短いオプションの文字は変えない。
```python
    "grep": ("ABCDdefm", ("--regexp", "--file", "--max-count", "--directories", "--devices",
                          "--before-context", "--after-context", "--context", "--label", "--binary-files",
                          "--include", "--exclude", "--exclude-from", "--exclude-dir", "--group-separator")),
    "su": ("cgGsw", ("--command", "--session-command", "--group", "--supp-group", "--shell",
                     "--whitelist-environment")),
...
    if head in ("su", "script"):
        return [e for s in _opt_values(rest, ("-c", "--command", "--session-command"), cmd=head) for e in sub(s)] \
            or [dict(c, toks=toks)]
```
- script の表には `--session-command` が無いので、script では `=` を付けた形しか値にならない（script にそのオプションは無く、判定は今と変わらない）
- → TC-01・TC-04 参照
- 依存: なし（ステップ 1 と並行可）

### ステップ 4: テストと一覧
- 失敗の注入（FG-01〜FG-04）の置き換え元の文字列を、ステップ 1〜3 の実装の直後に確定し、見張りにちょうど 1 回あることを確かめて `docs/tests/open/I469_auto_test.md` の表に書き写す
- `scripts/claude/tests/test_i469_guard_optspec_leftovers.sh` を作る（形は `test_i463_guard_optspec.sh` と同じ: 一時リポジトリの中から見張りを呼ぶ・`ck`／`fg`。TC-04 は一時ディレクトリ `$TMP/proj` に空の `.env` を置く）→ TC-01〜TC-04
- `scripts/claude/tests/guard_must_stop_cases.txt` に止めるべき形を足す（`.env` の有無によらない形だけ。一覧は空の一時リポジトリで判定するため・一覧 I463 F6）→ TC-05
- `docs/reviews/backlog/I463.md` の F5 の行を消す → TC-08
- 依存: ステップ 1〜3 の後

## 6. テスト計画
- 自動（決定論）: `docs/tests/open/I469_auto_test.md` の TC-01〜TC-06・TC-08。テストのレベルは、見張りに Bash の JSON を渡して判定だけを見る結合テスト（コマンドは実行しない）。取りこぼしの再発防止テストとして、止めるべき形と、止める対象を増やさない形（除く指定・`-c`・`-m`・スクリプト名）の両方向を固定し、失敗の注入（FG）を付ける
- 重いテスト（test-gate で手で流す）: TC-07 作業記録での判定比較（数分かかり、決定論ゲートの 1 行 120 秒に収まらない）
- 手動: `docs/tests/open/I469_manual_test.md`（Claude が `check-permission-prompt.sh` で、くっつけた形の秘密のファイルの読み出しに承認画面が出ることを確かめる）
- 認可・テナント境界: 該当なし（アプリのコードを変えない）
- pytest・Jest・E2E: 変更が無いので CI に任せる（手元で流し直さない）

## 7. ロールバック
`git revert` で見張りとテストを戻す（データ・設定の変更なし）。見張りが壊れて止まり続けるときは、このブランチのコミットを戻せば元の判定に戻る（`docs/runbooks/danger-ops.md` の「見張りが起動できない」ときの `! git restore`）。

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| python の読み方の変更で、パイプの python の確認が増えすぎる（`python3 -W ignore` など、今は通る形が確認になる） | `-c`・`-m`・スクリプト名は今と同じに通す（TC-03 の 03d〜03h）。量は TC-07（作業記録の 1% 以内） |
| 表に足した長いオプションの値を読み飛ばすことで、止める側が減る（その値に止めるべき語があった場合） | 足すのは `--help` で値を取ると書かれたものだけ。`paths` は今の「`-` で始まらない語」を残す。後退は TC-05（止めるべき形の一覧の版比較）・TC-06（既存テスト全件）で見る |
| `_FILE_VALUE_OPTS` を広げすぎて、除く指定（`--exclude=.env`）まで確認になる | 中身を読むオプションだけに絞る。TC-02 の 02g で「確認にならない」を固定 |
| su の `-C` を止めないこと | どの版の su にも無く、su が何も実行しない（調査結果）。表に入れると「`--help` に無い文字を表に入れない」（I463 の設計レビューの禁止事項）に反する |

## 9. 確定事項と自律判断
### イシューに明記されていること
- I463 の方式（値を取る文字の表で読む・表に無いコマンドは今の読み方・止める対象は増やさない）を引き継ぐ
- F2・F3・F7 を直す。「止める対象は増やさない」は規則を増やさない意味で、離して書けば今も確認・停止になる形を、くっつけた形でも同じ判定にするのは含む。誤った確認の増加は作業記録の判定比較の 1% 以内
- 一覧 `docs/reviews/backlog/I463.md` のうち実装対象のファイルに当たり小さく直せるものは計画で決める

### イシューから変えたこと（受け入れ条件の su の形）
- イシューの受け入れ条件 1 行目の `su -C '…'` を `su --session-command '…'`・`su --session-command='…'` に置き換えた — `-C` はどの版の su にも無く（手元の `--help`・各版の文書）、`su -C` は何も実行しない。イシューが守りたいもの（su で包んだ強制 push を `-c` と同じに止める）は、実在する `--session-command` で満たす。止める対象・規則は変わらず、価値判断ではなく事実の訂正なので、止めずに決めた（レビュー文書の自律判断の記録に書く）

### Claude が技術的に決めたこと（理由）
- F7: python の `-c`・`-m` は「実行するものを指定した形」として通す（今と同じ） — パイプの中身はコードとして実行されない。表に替えたときに `python3 -c "$X" | …` が新しく確認になる（I463 で見送った理由）のは、`-c` を位置引数の有無だけで見るのをやめれば起きない
- F3: `paths` に足すのは中身を読むファイルを値に取るオプション（grep `-f`・`--file`・`--exclude-from`、sed `-f`・`--file`）だけ — すべての値を足すと、離した形で今は通るくっつけた除く指定（`--exclude=.env`）やパターン（`-e.env`）まで確認になり、イシューの意味の範囲を超えて確認が増える
- F3 を grep・sed に限る — `_SECRET_READERS` のうち表にある（値を取る文字を読める）コマンドは grep・sed・cp で、cp に中身を読むファイルを値に取るオプションは無い
- F2: su の表に `-C` を入れない（上の「イシューから変えたこと」）。`test_i463_optspec_help.sh` は短いオプションの文字を変えないので直さない
- 一覧の行の扱い:
  - 一覧 docs/reviews/backlog/I463.md F5: 同梱 — grep の表に長いオプションを足すだけで、`grep -r --exclude-dir node_modules TOKEN .` の秘密の表示の取りこぼしが直る（TC-04）。F3 と同じ「表に無い値付きのオプション」の残り
  - 一覧 docs/reviews/backlog/I463.md F4: 残す — 読みすぎ（flock の中のコマンドの `-c` を flock の値と読む）で、止める側に倒れるだけ。秘密・push の取りこぼしにならない。flock を位置引数で読み終えるには `flock <file> -c` の扱いを別に書く必要があり、I463 で見送ったのと同じ理由で小さくない
  - 一覧 docs/reviews/backlog/I454.md F5・F7・F8・F9: 残す — 書き先の判定・rsync・ps の話で、値を取る文字の表の読み残しとは別の直し
  - 一覧 docs/reviews/backlog/I200.md F5: 残す — 危ない語の判定の話（#430 の範囲）
  - 一覧 docs/reviews/backlog/I224.md F9・I223.md B1〜B4（`FILE=-`）: 残す — 本イシューと関係が無い
  - 一覧 docs/reviews/backlog/I463.md F6・F8・F9: 実装対象のファイル（`guard_corpus_diff.py`・`test_i463_optspec_help.sh`）に当たらないので拾わない（残る）

### 要件適合性・業務ロジック
- 受け入れ条件の範囲を超える仕様の追加は無い。新しく確認・停止になる形は、どれも離して書けば今も確認・停止になる形（`grep -f .env x`・`su -c '…'`・`curl x | python3 -`・`grep -r TOKEN .`）と同じ意味の形だけ
- マルチテナント・ステータス遷移: 該当なし

### セキュリティ・ベストプラクティス
- 見張りは秘密情報の表示（`grep -f.env`・`grep -r --exclude-dir …`）・強制 push（`su --session-command`）・中身の見えないコードの流し込み（パイプの python）の取りこぼしを塞ぐ側に変わる（3 件とも SECURITY=yes）。止める側の後退は TC-05・TC-06 で決定論で確かめる
- 入力（コマンド文字列）は見張りの中で読むだけで実行しない
- 認証・認可・機密データの扱い・OWASP・依存ライブラリ: 変更なし（セキュリティ影響はハーネスの見張りの判定だけ）。bandit／npm audit の対象のアプリのコードは変えない
- 脅威モデルは「普通の書き方の事故」（わざと抜ける書き方は対象外・danger-ops.md）

### 設計品質
- 表（`_OPTSPEC`・`_FILE_VALUE_OPTS`）は 1 か所に置き、呼び出し元はコマンド名を渡すだけ。python のスクリプト名の読み方は `_python_code_raw` と同じ `_getopt` にそろえ、読み方を 2 通りにしない
- 例外処理: `_getopt` は例外を出さない（今のまま）。見張り全体の例外の扱いは今のまま

### 設計判断の区別
| 判断 | 区別 |
|---|---|
| I463 の方式・止める対象を増やさない・1% 以内 | イシューに明記 |
| su は `-C` でなく `--session-command`（受け入れ条件の形の訂正） | 仮定で決めた（事実の訂正・技術） |
| python の `-c`・`-m` を通す | 仮定で決めた（技術） |
| `_FILE_VALUE_OPTS` の範囲（中身を読むオプションだけ・grep と sed） | 仮定で決めた（技術） |
| 一覧の行の同梱・残す | 仮定で決めた（技術） |
価値判断（要件・UI）に当たる仮定は無い。

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | 取りこぼしが直っている: 受け入れ条件 1 の形と、同じ原因の `grep --exclude-from=.env x y`・`sed -f.env x`・`curl x \| python3 -W ignore`・`grep -r --exclude-dir node_modules TOKEN <.env のあるディレクトリ>` が確認・停止になる（TC-01〜TC-04） |
| V2 | 1 | 実験必須 | 止める側の後退が無い: 止めるべき形の一覧（TC-05）と既存の見張りのテスト全件（TC-06）が、変更前と同じかより強い判定になる。`paths` の「`-` で始まらない語」を残している（`grep -f .env x` が確認のまま） |
| V3 | 3 | 実験必須 | 止める対象を増やさない: `grep --exclude=.env foo x`・`python3 -c "$X" \| head`・`curl x \| python3 -m json.tool`・`curl x \| python3 tool.py` が通るまま（TC-02 の 02g・TC-03）。作業記録の比較（TC-07）で新しく確認・停止が 1% 以内 |

## 計画変更記録
（なし）
