# 計画書: I463 見張りのオプションの値の読み方を、値を取る文字の表で直す

## 基本情報
- **計画書ID**: plan_I463
- **関連イシュー**: #463
- **Draft PR**: #465
- **作成根拠資料**: docs/issues/open/I463.md（起点イシュー・GitHub #463 の本文の写し）
- **実装後評価**: docs/reviews/open/I463_review.md
- **作成日**: 2026-11-12

## 1. 背景/目的
- **背景**: 見張り（`scripts/claude/hooks/pretooluse_guard.py`）は、まとめ書きの短いオプション（`-tAc X`・`-vt/x`・`-Xf/x`）の値を「英字かどうか」で推し量って読む。I454 の fix-loop 2 で読み方を strict（既定）と loose（途中からの候補もすべて）の 2 段にしたが、どの文字が値を取るかを知らないままなので、呼び出し元ごとに誤読が残った（F15・F16・F17・F4・F6・敵対的レビューの Medium・一覧の F14・F18）
- **目的**: 見張りが中を読むコマンドだけに「値を取る短いオプションの文字」の表を持たせ、getopt と同じに読む（grill-me で案 1 に確定）。止める対象（何を確認・停止にするか）は増やさない。あわせて、止めるべき形の一覧を変更前と変更後の見張りに流し、止める判定が減ったら失敗にする仕組み（`guard_corpus_diff.py --cases`）を足す

## 2. 受け入れ条件
イシューの受け入れ条件と同じ（docs/issues/open/I463.md）。
1. F15・F16・F17・F4・F6・F14・F18 と敵対的レビューの Medium の再現の形が期待どおりの判定になり、決定論のテスト（失敗の注入つき）で固定されている → TC-01〜TC-08
2. F2 が再現しないことをテストで固定している → TC-04
3. I454 のテストと見張りの既存テストがすべて合格し、作業記録での判定比較で「新しく確認・停止」が分母の 1% 以内・異常終了 0 件 → TC-10・TC-11
4. 止めるべき形が後退していない（`guard_corpus_diff.py --cases scripts/claude/tests/guard_must_stop_cases.txt` が合格・わざと壊した見張りでは失敗） → TC-09
5. `docs/runbooks/danger-ops.md`「見張りを直したら、コミットの前に流すテスト」に `--cases` のモードが入っている → TC-12

## 3. 影響範囲
| 区分 | 内容 |
|---|---|
| Backend | なし |
| Frontend | なし |
| DB | なし |
| Config/Infra | 見張り（PreToolUse フック）の判定。全ワークツリーの Bash の確認・停止が変わる（読み違いによる誤停止・誤確認が減り、`psql -Xf…`・`grep -ie. .env`・スクリプト名の後ろの `-xcfoo` を新しく止める）。`.claude/settings.json` は変えない |
| ハーネステスト | 新しいテスト 2 本（`test_i463_guard_optspec.sh`・`test_guard_must_stop_cases.sh`）と一覧 1 つ。既存の `test_i454_guard_env_writes.sh`・`test_i444_guard_gaps.sh` の失敗の注入の置き換え元を新しいコードに合わせる |
| 文書 | `docs/runbooks/danger-ops.md`（見張りを直したら流すテスト）・`docs/reviews/backlog/I454.md`・`docs/reviews/backlog/I444.md`（同梱した行を消す） |

P3/P5/P8 影響なし（DB・外部 API・非同期処理・依存ファイルの変更なし）。P6 影響なし（UI なし）。P9 影響なし（個人情報・テナントデータを扱わない）。

## 調査結果

### 環境前提
- 手元にある: `sed`・`grep`・`cp`・`mv`・`install`・`ln`・`su`・`flock`・`script`・`python3`・`rsync`（`which` で確認）。`psql` は手元に無く、コンテナも止まっている（`docker compose ps` が空）。psql の値を取るオプションは PostgreSQL の文書（psql のオプション一覧）に拠る。見張りのテストはコマンドを実行せず JSON を渡して判定だけを見るので、psql・コンテナが無くても流せる
- 各コマンドの値を取る短いオプション（`--help` で 2026-11-12 に確認）: sed `-e -f -l`（`-i` は値をくっつけたときだけ取る `-i[SUFFIX]`）・grep `-e -f -m -d -D -A -B -C`・cp／mv／ln `-S -t`・install `-g -m -o -S -t`・su `-c -g -G -s -w`・flock `-c -E -w`・script `-B -c -E -I -m -O -o -T`。psql（文書）`-c -d -f -F -h -L -o -p -P -R -T -U -v`。python `-c -m -W -X`（`-c`・`-m`・最初の位置引数〔スクリプト名〕で読み終える）。Django の shell `-c -i -v`

### 今の見張りでの再現（2026-11-12・develop の見張り・一時リポジトリに別ワークツリー `$W`。期待値の書き方は 2＝停止・ASK＝確認・0＝通す）
| 指摘 | 形 | 今 | 直した後 |
|---|---|---|---|
| F15 | `python3 $TMP/evil.py -xcfoo`（evil.py は django を import して `User.objects.all().delete()`） | 0 | 2 |
| F15 | `python3 $TMP/evil.py -vc 1` | 0 | 2 |
| F14 | `psql -Umarc drop-test`（`-U` の値の c を `-c` と取り違え、`drop-test` を SQL と読む） | 2 | 0 |
| F16 | `psql -hlocalhost -Ucelery -c 'select 1'` | 0 | 0 |
| F17 | `psql -Xf/tmp/dump.sql`・`$D psql -Xf/tmp/dump.sql` | 0・0 | 2・2 |
| F17 | `grep -ie. .env` | 0 | ASK |
| F2 | `psql -dprofile_db -c "select 1"` | 0 | 0 |
| F4 | `sed -e's/print/log/' $W/file` | 2 | 0 |
| F6 | `$D pytest --cov=/app/apps`・`--ignore=`・`--cov-config=`・`--deselect=` | ASK | 0 |
| 敵対的レビューの Medium | `cp -vt/tmp/d $W/a $W/b` | 2 | 0 |
| I444 F7 | `mv -S $W/sfx /tmp/a /tmp/b`（`-S` の値を移動元と読む） | 2 | 0 |

- F16 は、偽の候補（`-hlocalhost` → `alhost`）が SQL に混ざっても、今の判定では `select 1` に余計な確認は出なかった（`$D` の形も 0）。置換の印の形（`psql -hlocal$(hostname) -U postgres <<EOF` ＋ `DELETE …`）も 2 で、ヒアドキュメントの SQL は見えていた。原因（偽の候補）は表で消えるので、F16 は「偽の候補が出ない」ことを TC-02 で固定して閉じる
- 止めるべき形で今も止まっているもの（直した後も変えない）: `sed -ie s/a/b/ $W/x`（GNU sed は `-i` に接尾辞 e を付けた形と読む）・`sed -i.bak …`・`grep -f .env x`・`grep -m1 x .env`・`su -lc'git push --force …'`・`flock -w3 /tmp/l -c '…'`・`script -qc '…' /dev/null`・I454 の TC-07（07a〜07i）

### 原因の概要
見張りは「どのオプションが値を取るか」を知らないまま、まとめ書きの値の切れ目を英字かどうかで推し量っている。そのため、値の中の文字（`-Umarc` の c・`-e's/print/…'` の i）をオプションと取り違えたり、逆にくっつけた値（`-Xf/tmp/x`）やスクリプト名の後ろの引数を読み違えたりする。

### 詳細な原因分析
- `_opt_values`（1857 行）は、短いオプションのまとめ書きを「最後の文字が該当」「最初の文字が該当」の 2 形（strict）と、`loose=True` で「英字だけの並びの後の該当の文字から後ろ」を候補にする形で読む。値を取る文字の一覧を持たないので、`-Xf/x`（f が途中）は strict で読めず、`-Umarc`（末尾の c）は strict でも値を取ると見る（F14・F17）
- `_python_code_raw`（1981 行）は `-c` を loose で探すので、スクリプト名の後ろの引数（`-xcfoo`）までオプションとして読み、中身の無害な「コード」を返す（F15）。python はスクリプト名でオプションを読み終える
- `_write_targets`（799 行）の sed の in-place の判定は `_has_short(args, "i")` で、`-e's/print/log/'` の式の i に当たる（F4）。`-t` は strict と loose で 2 回読み、推測があると最後の位置引数も書き先に足す（敵対的レビューの Medium・F18）。mv は `-` で始まらない語をすべて移動元とみなす（I444 F7）
- `_OPT_PATH_RE`（2377 行）は `--rootdir=`・`--confcutdir=` だけを読む指定として除くので、pytest の `--cov=` などの読む指定がコンテナの /tmp/ 以外への書き込みと見なされる（F6）
- I454 の fix-loop は「誤って止める」形だけをテストに足し、「止めるべき」形の後退を版の比較で見つける決定論の仕組みが無かった

### 軽い指摘の一覧（台帳の残り）
`grep -rnF -e "FILE=scripts/claude/hooks/pretooluse_guard.py |" -e "FILE=scripts/claude/tests/guard_corpus_diff.py |" -e "FILE=scripts/claude/tests/test_i454_guard_env_writes.sh |" -e "FILE=docs/runbooks/danger-ops.md |" -e "FILE=- |" docs/reviews/backlog/` で当たった行の扱いは 9. に書く。

## 4. 変更点一覧
| ファイル | 関数・定数 | 変更 |
|---|---|---|
| `scripts/claude/hooks/pretooluse_guard.py` | `_OPTSPEC`・`_OPTSPEC_OPTIONAL`・`_OPTSPEC_STOP`・`_value_opts`（新規） | コマンドごとの値を取る短いオプションの文字と、値を取る長いオプション（`_OPTSPEC_STOP`・`_value_opts` は計画変更記録の /simplify の追加） |
| 同上 | `_django_sub`・`_container_safe`（python -m・psql）・`_wrap_skip`（flock） | 表で読む（計画変更記録の /simplify の追加） |
| 同上 | `_getopt`（新規） | getopt と同じに読み、`([(オプション, 値)], 位置引数)` を返す |
| 同上 | `_opt_values` | `loose` を消し、`cmd` を足す。`cmd` が表にあれば `_getopt` の結果から返す。無ければ今の strict の読み方 |
| 同上 | `_expand`（su・script・flock の `-c`） | `cmd=head` で読む |
| 同上 | `_python_code_raw` | manage.py shell は `cmd="django-shell"`。python は `_getopt("python", …)` の位置引数でスクリプトを決める（`-W`・`-X` を飛ばす手書きの読みを置き換える） |
| 同上 | `_sql_of`・psql の `-f` の判定（`_cmd_danger` 2165 行） | `cmd="psql"` |
| 同上 | `_grep_recursive_secret`・`_cmd_external` の `_PATTERN_FIRST` の判定 | `cmd="grep"`・`cmd=head`（rg・awk は表に無いので今のまま） |
| 同上 | `_write_targets` | sed と cp／mv／install／ln を `_getopt` で読む（rsync は今のまま） |
| 同上 | `_OPT_PATH_RE` | 読む指定の一覧 `_OPT_READ_PATH`（rootdir・confcutdir・cov・cov-config・ignore・ignore-glob・deselect）を除く |
| `scripts/claude/tests/guard_corpus_diff.py` | `main`・`judge`・新規 `run_cases` | `--cases <ファイル>`: 一覧のコマンドを変更前と作業ツリーの見張りに流し、作業ツリーで「通す」・変更前より弱い判定・異常終了があれば exit 1 |
| `scripts/claude/tests/guard_must_stop_cases.txt`（新規） | — | 止めるべき形の一覧（1 行 1 コマンド） |
| `scripts/claude/tests/test_guard_must_stop_cases.sh`（新規） | — | `--cases` を流し、失敗の注入（わざと壊した見張り・通す形を混ぜた一覧）で失敗することも確かめる |
| `scripts/claude/tests/test_i463_guard_optspec.sh`（新規） | — | TC-01〜TC-08 |
| `scripts/claude/tests/test_i454_guard_env_writes.sh` | FG-02・FG-07c・FG-07d | 置き換え元を新しいコードに合わせる（守る形は変えない） |
| `scripts/claude/tests/test_i444_guard_gaps.sh` | FG-02a・FG-02b | 同上 |
| `docs/runbooks/danger-ops.md` | 「見張りを直したら、コミットの前に 3 つのテストを流す」 | 4 つにし、`test_guard_must_stop_cases.sh`（`--cases`）を足す。一覧に止めるべき形を足すのは、見張りで止める形を足したとき・止めるべき形の取りこぼしを直したとき |
| `docs/reviews/backlog/I454.md` | F14・F18 の行 | 消す |
| `docs/reviews/backlog/I444.md` | F7 の行 | 消す |

## 5. 実装手順

### ステップ 1: 値を取る文字の表と getopt の読み方（見張りの読み方を一度に置き換える）
**修正方針**: 表にあるコマンドは、getopt と同じに「まとめ書きの文字を左から見て、値を取る文字に当たったら、残りの文字（無ければ次の語）を値にして読み終える」。表に無いコマンドは今の strict の読み方のまま（loose は消す。loose を使っていた呼び出し元はすべて表のコマンドになる）。
```python
# I463: 見張りが中を読むコマンドの「値を取る短いオプションの文字」と「値を取る長いオプション」（各コマンドの --help・
# psql は PostgreSQL の文書。2026-11-12 に確認）。まとめ書き（-tAc X・-vt/x・-Xf/x）を getopt と同じに読む。
# 表に無いコマンドは _opt_values の既定（-c X・-cX・まとめ書きの最後）のまま。止める対象は変えない（読み違いを減らすだけ）
_CP_LONG = ("--target-directory", "--suffix")
_OPTSPEC = {
    "psql": ("cdfFhLopPRTUv", ("--command", "--dbname", "--file", "--field-separator", "--host", "--log-file",
                               "--output", "--port", "--pset", "--record-separator", "--table-attr", "--username",
                               "--variable")),
    "python": ("cmWX", ()),                      # -c・-m・最初の位置引数（スクリプト名）で読み終える
    "django-shell": ("civ", ("--command", "--interface", "--settings", "--pythonpath", "--verbosity")),
    "sed": ("efl", ("--expression", "--file", "--line-length")),
    "grep": ("ABCDdefm", ("--regexp", "--file", "--max-count", "--directories", "--devices",
                          "--before-context", "--after-context", "--context")),
    "cp": ("St", _CP_LONG), "mv": ("St", _CP_LONG), "ln": ("St", _CP_LONG),
    "install": ("gmoSt", _CP_LONG + ("--group", "--mode", "--owner")),
    "su": ("cgGsw", ("--command", "--group", "--supp-group", "--shell", "--whitelist-environment")),
    "flock": ("cEw", ("--command", "--timeout", "--conflict-exit-code")),
    "script": ("BcEImOoT", ("--command", "--log-in", "--log-out", "--log-io", "--log-timing", "--logging-format",
                            "--echo", "--output-limit")),
}
_OPTSPEC_OPTIONAL = {"sed": "i"}   # 値をくっつけたときだけ取る（sed -i.bak・sed -ie は接尾辞 e）

def _getopt(cmd: str, args: list) -> tuple:
    """args を getopt と同じに読み、([(オプション, 値 or None)], 位置引数) を返す（I463）。オプションは "-c"・"--command" の形。
    GNU と同じく位置引数の後ろのオプションも読む。python だけは -c・-m・最初の位置引数で読み終える（後ろはスクリプトの引数）。"""
    short, longs = _OPTSPEC[cmd]
    optional = _OPTSPEC_OPTIONAL.get(cmd, "")
    opts, pos, i = [], [], 0
    while i < len(args):
        a = args[i]
        if a == "--":
            return opts, pos + args[i + 1:]
        if a.startswith("--"):
            name, eq, val = a.partition("=")
            if not eq and name in longs and i + 1 < len(args):
                i, val = i + 1, args[i + 1]
            opts.append((name, val if (eq or name in longs) else None))
        elif a.startswith("-") and a != "-":
            body = a[1:]
            for j, ch in enumerate(body):
                if ch in short or ch in optional:
                    val = body[j + 1:] or None
                    if val is None and ch in short and i + 1 < len(args):
                        i, val = i + 1, args[i + 1]
                    opts.append(("-" + ch, val))
                    break
                opts.append(("-" + ch, None))
        else:
            pos.append(a)
            if cmd == "python":
                return opts, pos + args[i + 1:]
        if cmd == "python" and opts and opts[-1][0] in ("-c", "-m"):
            return opts, pos + args[i + 1:]
        i += 1
    return opts, pos

def _opt_values(toks: list, names: tuple, cmd: str = "") -> list:
    """toks の中の names の値をすべて返す。cmd が _OPTSPEC にあれば getopt と同じに読む（I463）。
    無ければ `-c X`・`-cX`・`-tAc X`（まとめ書きの最後）・`--command X`・`--command=X` を読む（値を取る文字を知らないので
    まとめ書きの途中の文字は読まない）。"""
    if cmd in _OPTSPEC:
        return [v for n, v in _getopt(cmd, toks)[0] if n in names and v is not None]
    ...（今の strict の読み方。loose の 2 行を消す）
```
- 呼び出し元の置き換え（4. の表のとおり）:
  - `_expand`: `flock_cmd = _opt_values(rest, ("-c", "--command"), cmd="flock") if head == "flock" else []`・su／script は `cmd=head`
  - `_python_code_raw`: shell は `_opt_values(dj[1], ("-c", "--command"), cmd="django-shell")`。python は `opts, pos = _getopt("python", rest)` とし、`codes = [v for n, v in opts if n == "-c" and v is not None]`・`-m` があれば False・`first = pos[0] if pos else None`（`-W`・`-X` を飛ばす手書きの while を消す）・`pos and pos[0].endswith(".py")` でファイルを読む
  - `_sql_of`: `sqls = _opt_values(args, ("-c", "--command"), cmd="psql")`（ヒアドキュメント・here-string と合わせて見るのは今のまま）。psql の `-f`: `_opt_values(toks[1:], ("-f", "--file"), cmd="psql")`
  - `_grep_recursive_secret`: `cmd="grep"`。`_cmd_external`: `_opt_values(toks[1:], ("-e", "-f", "--regexp", "--file"), cmd=head)`。秘密のファイルを探す `paths`（`-` で始まらない語すべて）は今のまま（`grep -f .env x` の `.env` を落とさないため。位置引数だけに絞ると止める側が減る）
  - `_write_targets`:
    ```python
    if head == "sed":
        opts, pos = _getopt("sed", args)
        names = {n for n, _v in opts}
        if not names & {"-i", "--in-place"}:
            return []
        return pos if names & {"-e", "-f", "--expression", "--file"} else pos[1:]   # -e／-f があれば位置引数はすべてファイル
    if head not in _COPY_CMDS:
        return []
    if head == "rsync":                        # rsync の -t は時刻を保つ。値を取る文字は表に入れない（今のまま）
        pos = [a for a in args if not a.startswith("-")]
        return pos[-1:] if len(pos) >= 2 else []
    opts, pos = _getopt(head, args)
    if head == "install" and {n for n, _v in opts} & {"-d", "--directory"}:
        return []                              # install -d は作るだけ
    tdir = [v for n, v in opts if n in ("-t", "--target-directory") and v]
    if head == "mv":                           # 移動元も消える（I444）
        return tdir + pos
    return tdir or (pos[-1:] if len(pos) >= 2 else [])
    ```
- → TC-01〜TC-05・TC-07・TC-08・TC-10 参照
- 依存: なし（最初に行う。読み方の置き換えがこのイシューの未知のリスク〔今のテストのどれかが後退する〕なので先に置く）

### ステップ 2: 読む指定を書き込みと見なさない（F6）
**修正方針**: pytest の読む指定（測る範囲・設定・除く対象）を、コンテナの /tmp/ 以外への書き込みの判定から外す。書き出し先の指定（`--junitxml=`・`--basetemp=` など）は今のまま確認にする。
```python
# 書き出し先を値で受ける形（pytest --junitxml=/app/r.xml）。粗い判定で、よく使う読む場所の指定だけ除く（I454・I463）
_OPT_READ_PATH = ("rootdir", "confcutdir", "cov", "cov-config", "ignore", "ignore-glob", "deselect")
_OPT_PATH_RE = re.compile(r"--(?!(?:" + "|".join(map(re.escape, _OPT_READ_PATH)) + r")=)[\w-]+=/")
```
- → TC-06 参照
- 依存: ステップ 1 と並行可

### ステップ 3: 止めるべき形の一覧で版を比べる（予防策）
**修正方針**: `guard_corpus_diff.py` に `--cases <ファイル>` を足す。作業記録を使わないので CI でも流せる。一時リポジトリに別ワークツリーを作り、一覧の `{W}` をそのパスに置き換え、一時リポジトリの中から変更前（`--base`。既定は今と同じ `base_rev` の決め方）と作業ツリー（または `--guard`）の見張りで判定する。判定の強さは 通す＜確認＜停止。次のどれかがあれば exit 1 にし、その行を出す:
- 作業ツリーで「通す」（一覧は止めるべき形だけなので、通すなら一覧か見張りの誤り）
- 作業ツリーの判定が変更前より弱い（停止→確認を含む）
- 作業ツリーで異常終了（exit 0・2 以外）
変更前の見張りを取り出せないとき（比べる相手が無い）は SKIP にせず、作業ツリーの判定だけで上の 1 つ目と 3 つ目を見て、「変更前より弱いかは見られない」と出力する。
一覧の書き方: 1 行 1 コマンド。空行と `#` で始まる行は飛ばす。`⏎` は改行（ヒアドキュメント）に、`{W}` は別ワークツリーのパスに置き換える（`guard_corpus_diff.py` の出力の書き方と同じ）。
- 一覧 `scripts/claude/tests/guard_must_stop_cases.txt` の中身（最初）: I454 の TC-07 のうち止める形（07a〜07d・07f〜07i）・TC-04 の 04a〜04k・TC-01 の 01a〜01e・01i・01j と、本イシューの止める形（TC-01 は 01f だけ。01a〜01d は evil.py のファイルが要るため、本イシューのテストで見る）・TC-02 の 02c・02d・TC-03 の 03a〜03e・TC-05 の 05b〜05d・TC-07 の 07c〜07e・TC-08 の 08a〜08d）
- `scripts/claude/tests/test_guard_must_stop_cases.sh`: 3 つを確かめる。①`guard_corpus_diff.py --cases <一覧>` が exit 0 ②`_cmd_danger` の `r.append("destructive SQL requires DANGER_OK=1")` を `pass` に置き換えた見張りの写しを `--guard` に渡すと exit 1 ③一覧に `echo hi` を足した写しを渡すと exit 1
- → TC-09 参照
- 依存: ステップ 1・2 の後（一覧の期待はステップ 1・2 の後の判定）

### ステップ 4: 既存のテストの失敗の注入を新しいコードに合わせる
**修正方針**: `test_i454_guard_env_writes.sh` の FG-02・FG-07c・FG-07d、`test_i444_guard_gaps.sh` の FG-02a・FG-02b は、置き換え元（`loose=True`・`guess`・`T = (…)`・`return tdir + guess + pos`）がステップ 1 で消えて「置き換え NOPATCH」で FAIL になる。それぞれ同じ守り（くっつけた -t を読む・まとめ書きの値を読む・sed の式を読む・mv の移動元）を外す置き換えに変える（守る形・期待値は変えない）。FG-07a（`parts = sqls + …`）は置き換え元が残るので変えない。
- → TC-10 参照
- 依存: ステップ 1 の後

### ステップ 5: 新しいテストと手順書・一覧
- 失敗の注入（FG-01〜FG-07）の置き換え元の文字列を、ステップ 1・2 の実装の直後に確定し、見張りにちょうど 1 回あることを確かめて `docs/tests/open/I463_auto_test.md` の表に書き写す
- `scripts/claude/tests/test_i463_guard_optspec.sh` を作る（形は `test_i454_guard_env_writes.sh` と同じ: 一時リポジトリに別ワークツリー `$W`・evil.py を置く・`ck`／`fg`）→ TC-01〜TC-08
- `docs/runbooks/danger-ops.md` 34 行を「4 つのテスト」にし、`bash scripts/claude/tests/test_guard_must_stop_cases.sh`（止めるべき形の一覧で、変更前の見張りより止める判定が弱くなっていないか。CI でも流れる）を足す。一覧に足すとき（見張りで止める形を足した・止めるべき形の取りこぼしを直した）も 1 文で書く → TC-12
- `docs/reviews/backlog/I454.md` の F14・F18、`docs/reviews/backlog/I444.md` の F7 の行を消す → TC-12
- 依存: ステップ 1〜4 の後

## 6. テスト計画
- 自動（決定論）: `docs/tests/open/I463_auto_test.md` の TC-01〜TC-10・TC-12。テストのレベルは、見張りに Bash の JSON を渡して判定だけを見る結合テスト（コマンドは実行しない）。読み違いの再発防止テストとして、誤って止める形と止めるべき形の両方向を固定し、失敗の注入（FG）を付ける
- 重いテスト（test-gate で手で流す）: TC-11 作業記録での判定比較（数分かかり、決定論ゲートの 1 行 120 秒に収まらない）
- 手動: `docs/tests/open/I463_manual_test.md`（Claude が `check-permission-prompt.sh` で、直した形に承認画面が出ないこと・書き出しの形に出ることを確かめる）
- 認可・テナント境界: 該当なし（アプリのコードを変えない）
- pytest・Jest・E2E: 変更が無いので CI に任せる（手元で流し直さない）

## 7. ロールバック
`git revert` で見張りとテストを戻す（データ・設定の変更なし）。見張りが壊れて止まり続けるときは、`.claude/settings.json` を変えずに、このブランチのコミットを戻せば元の判定に戻る。

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| 表の文字の誤り（値を取らない文字を値ありとすると、後ろの文字を読まず止める側が減る） | 表は `--help`・公式文書から写した（調査結果）。止めるべき形の一覧（TC-09）と既存テストの全件（TC-10）で、変更前より弱い判定が無いことを確かめる |
| getopt の読み方の取り違え（`--` の後・`-` 単体・python の読み終わり） | TC-01（python）・TC-05（sed の `-i` の接尾辞）・TC-08（su・flock・script）で固定 |
| 位置引数だけに絞ったせいで秘密のファイルを落とす（`grep -f .env x`） | `paths` は今のまま `-` で始まらない語すべて（ステップ 1）。TC-03 の 03d・一覧に入れる |
| `--cases` が CI で比べる相手を作れない | CI は `fetch-depth: 0` で `origin/develop` がある（ci.yml 157 行）。比べる相手が無ければ SKIP ではなく、作業ツリーの判定だけで「通す」の行を失敗にする（変更前より弱いかは見られないと出力する） |
| 誤停止の増加 | TC-11（作業記録の 1% 以内・異常終了 0 件） |

## 9. 確定事項と自律判断
### イシューに明記されていること
- 案 1（値を取る文字の表・getopt と同じ読み方）・表にないコマンドは今の読み方・止める対象は増やさない（設計確認メモ）
- 予防策を採る: `guard_corpus_diff.py --cases <ファイル>`・`scripts/claude/tests/guard_must_stop_cases.txt`・danger-ops.md の見張りを直したら流すテストに入れる
- F14・F18 は同梱。#430 より先に行う

### Claude が技術的に決めたこと（理由）
- 表に入れるコマンドは、今 `loose` を使う呼び出し元と、F17 の読み違いが出る呼び出し元（psql・python・Django の shell・sed・grep・cp・mv・ln・install・su・flock・script）だけ。rsync は値を取る文字が多く、`-t` が書き先でないので入れない（今のまま） — 表を小さく保ち、事故の例のあるコマンドだけにする（I179 の粗い判定の方針）
- `loose` は消す — 使っていた呼び出し元がすべて表のコマンドになり、2 つの読み方を残す理由が無くなる（F18 の根治）
- 秘密のファイルを探す `paths` は位置引数に絞らない — 絞ると `grep -f .env x` が通るようになり、止める側が減る
- python の位置引数より後ろはスクリプトの引数として読まない — python 自身の読み方と同じ（F15 の根治）
- `--cases` は作業記録を使わず CI でも流す（`test_guard_must_stop_cases.sh` を run-all に入れる）— 数十件で数十秒に収まる。後退は気づきにくく被害が大きい（plan-writing-rules.md「決定論テストの対象の選び方」に当たる）
- `--cases` の合否に「作業ツリーで通す」も入れる — 一覧の誤り（止めるべきでない形を入れた）と、変更前から後退していた形を両方見つける
- F16 は現象が再現しないので、原因（偽の候補）が出ないことの固定で閉じる（調査結果）
- 一覧の行の扱い:
  - 一覧 docs/reviews/backlog/I454.md F14: 同梱 — 表で `-Umarc` の c を値と読まなくなる（TC-02）
  - 一覧 docs/reviews/backlog/I454.md F18: 同梱 — `_write_targets` の `_opt_values` の 2 回の呼び出しが `_getopt` 1 回になる
  - 一覧 docs/reviews/backlog/I444.md F7: 同梱 — 表で mv の `-S` の値を移動元と読まなくなる（TC-07 の 07f）
  - 一覧 docs/reviews/backlog/I454.md F5: 残す — 未カバー警告の判定（`_has_write_intent`）の話で、読み方の表とは別の直しになる
  - 一覧 docs/reviews/backlog/I454.md F7: 残す — rsync は表に入れない（上の理由）
  - 一覧 docs/reviews/backlog/I454.md F8: 残す — ps の BSD 形式は getopt で読めない。確認側に倒れるだけ
  - 一覧 docs/reviews/backlog/I454.md F9: 残す — `_record_writes` の書き先の記録の話で、読み方の表とは別
  - 一覧 docs/reviews/backlog/I444.md F2: 残す — `--cases` はキャッシュを使わず、作業記録の比較は `--rebuild` で流す（TC-11）。キャッシュの古さの直しは別の直し
  - 一覧 docs/reviews/backlog/I444.md F6: 残す — git の版の話で、本イシューと関係が無い
  - 一覧 docs/reviews/backlog/I200.md F5: 残す — 危ない語の判定の話（#430 の範囲）
  - 一覧 docs/reviews/backlog/I224.md F9・I223.md B1〜B4（`FILE=-`）: 残す — 本イシューと関係が無い

### 要件適合性・業務ロジック
- 受け入れ条件の範囲を超える仕様の追加は無い（止める対象は増やさず、読み違いを直すだけ。新しく止まる形〔`psql -Xf…`・`grep -ie. .env`・スクリプト名の後ろの `-xcfoo`〕は、離して書けば今も止まる形）
- マルチテナント・ステータス遷移: 該当なし

### セキュリティ・ベストプラクティス
- 見張りは秘密情報の表示（`grep -ie. .env`）と破壊的 SQL の流し込み（`psql -Xf…`）の取りこぼしを塞ぐ側に変わる（F15・F17 は SECURITY=yes）。止める側の後退は TC-09・TC-10 で決定論で確かめる
- 入力（コマンド文字列）は見張りの中で読むだけで実行しない。`--cases` は一時ディレクトリの中で見張りを呼ぶだけで、一覧のコマンドを実行しない
- 認証・認可・機密データの扱い・OWASP・依存ライブラリ: 変更なし（セキュリティ影響はハーネスの見張りの判定だけ）。bandit／npm audit の対象のアプリのコードは変えない
- 脅威モデルは「普通の書き方の事故」（わざと抜ける書き方は対象外・danger-ops.md）

### 設計品質
- 定数（表）は 1 か所に置き、呼び出し元は `cmd` を渡すだけ。値が無いときは None とし、`_opt_values` は None を返さない（今と同じ）
- 例外処理: `_getopt` は例外を出さない（添字は長さを確かめてから読む）。見張り全体の例外の扱いは今のまま

### 設計判断の区別
| 判断 | 区別 |
|---|---|
| 案 1・止める対象を増やさない・#430 より先 | イシューに明記 |
| 予防策の形（`--cases`・一覧のファイル名・danger-ops.md） | イシューに明記 |
| 表に入れるコマンドと文字・rsync を入れない | 仮定で決めた（技術） |
| `loose` を消す | 仮定で決めた（技術） |
| `paths` を絞らない | 仮定で決めた（技術） |
| `--cases` の合否の決め方・CI で流す | 仮定で決めた（技術） |
| 一覧の行の同梱・残す | 仮定で決めた（技術） |
価値判断（要件・UI）に当たる仮定は無い。

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 表の文字の正しさ: `_OPTSPEC` の各コマンドの値を取る文字・長いオプションが、そのコマンドの `--help`（psql は PostgreSQL の文書）と一致する。値を取らない文字を値ありとしていない（後ろの文字を読まず止める側が減る）。手元にあるコマンドは `--help` と突き合わせる（TC-13 が決定論で突き合わせる・FG-13 つき。python の値を取る長いオプションは TC-01 の 01g） |
| V2 | 2 | 実験必須 | 位置引数より後ろの読み方: python は `-c`・`-m`・スクリプト名で読み終え、後ろの `-xcfoo` を読まない（TC-01）。ほかのコマンドは GNU と同じく位置引数の後ろのオプションも読み（`psql mydb -c 'DELETE …'`）、`--` の後は位置引数になる。`-` 単体は位置引数 |
| V3 | 1 | 実験必須 | 止める側の後退が無い: 止めるべき形の一覧（TC-09）・I454 の TC-07・既存の見張りのテスト全件（TC-10）が、変更前と同じかより強い判定になる。秘密のファイルを探す `paths` を位置引数に絞っていない（`grep -f .env x` が確認のまま・TC-03 の 03d） |
| V4 | 3 | 読んで可 | 普通の操作: 読む指定（`--cov=` など）・読むだけの sed・cp の形が通り、作業記録の比較（TC-11）で新しく確認・停止が 1% 以内 |

## 計画変更記録
- plan-review 1224 の Warning への対応（方式・範囲・受け入れ条件は変えない・再レビューは Blocker の直しで行う）: TC-12b を 3 つの `! grep -q` に分けた／FG の置き換え元は implement の最初に確定して auto_test.md に書く（ステップ 5 に明記）／長いオプションの省略形・表にない値付きの長いオプションは、脅威モデル（普通の書き方の事故）の範囲外として許容し、後退は TC-09 で見る
- plan-review 1226 の Warning への対応（同上・再レビューしない）: psql の表の根拠は PostgreSQL 15 の psql の文書（docker-compose.yml の db は `postgres:15-alpine`）。手元に psql が無く `--help` と突き合わせられないので、V1 の psql は文書と、TC-09・TC-10 の後退検知で見る。コンテナを起こせたら implement で `docker compose exec -T db psql --help` と突き合わせ、結果を auto_test.md に書く
- implement（2026-11-12）: ステップ 4 の失敗の注入の直し
  - 計画書の記載: 「FG-02・FG-07c・FG-07d、FG-02a・FG-02b を直す。FG-07a は置き換え元が残るので変えない」
  - 採った方法: FG-07b（install -d の判定）も置き換え元が消えたので直した。FG-07a は置き換え元は残るが、偽の `-c` が出なくなったので 07a（`psql -hlocalhost … <<EOF`）では写しでも 2 のまま差が出ず FAIL になった。流す形を、本物の `-c` とヒアドキュメントを併せた `psql -Umarc -c 'select 1' <<EOF` ＋ `DELETE …` に替えた（守る形〔-c があってもヒアドキュメントの SQL を見る〕は同じ）。FG-07d は sed の表から e を外すと `-nes…` の e が値なしの `-e` として残り差が出ないので、「-e／-f があれば位置引数はすべてファイル」の行を外す置き換えにした
  - 理由: どれも守る形・期待値は変えず、置き換え元を新しいコードに合わせただけ
  - 計画レビューのやり直し: 不要（テストの置き換え元の追従だけで、方式・範囲・受け入れ条件を変えない）
- implement（2026-11-12）: `guard_corpus_diff.py` の比べる相手の決め方を `base_source` に切り出し、作業記録のモードと `--cases` で共用した（同じ決め方を 2 か所に書かない）。計画レビューのやり直し: 不要（ステップ 3 の範囲の中の整理）
- implement（2026-11-12・/simplify の 4 体の指摘）: 同じコマンドを表と手書きの 2 通りで読む残りを表にそろえた（止める対象は増やさない・読み違いを減らすだけ）
  - 計画書の記載: 変更点一覧の呼び出し元（`_expand`・`_python_code_raw`・`_sql_of`・psql の `-f`・`_grep_recursive_secret` のパターン・`_cmd_external` のパターン・`_write_targets`）
  - 採った方法: ①`_getopt` の `cmd == "python"` の決め打ちを表 `_OPTSPEC_STOP = {"python": "cm"}` にした ②`_django_sub`（`python -m django`）と `_container_safe` の `python -m pytest` の判定の -W・-X 等を飛ばす手書きの一覧を `_getopt("python", …)` にした ③`_container_safe` の psql の読むだけの判定（`-o`・`-L`・`-f`）に `cmd="psql"` を付けた ④`_grep_recursive_secret` の `-r` の有無・ディレクトリも `_getopt("grep", …)` で読む（`-m 5` の 5 をディレクトリと見ない） ⑤`_wrap_skip` の flock の値を取るオプションを `_value_opts("flock")`（表から作る）にした ⑥`guard_corpus_diff.py` の 2 つのモードで同じだった「変更前の写しを書いて両方を判定」を `judge_both` にまとめ、`base_source` の戻り値で `a.base` を書き換えないようにした ⑦`test_guard_must_stop_cases.sh` の 09b は DELETE の行だけ、09c は `echo hi` だけを流す（見張りの起動を約 280 回→約 100 回）
  - 見送り: `_cmd_external` の python の `first`（`python3 -c "$X" | …` で表に替えると新しく確認が出る＝止める側が増える）・`git commit` の読み方（`_commit_no_verify`）を表に寄せる（このイシューの差分の外）・`_record_writes`（一覧 I454 F9 に残す）・flock を位置引数で読み終える（`flock /tmp/l -c …` の -c を読まなくなる）
  - 理由: どれも同じ根本原因（コマンドごとの読み方が 2 通りある）の残りで、表に寄せると読み方が 1 つになる。止める対象は増えない（①〜⑤は読み違いが減るだけ）
  - 計画レビューのやり直し: 不要（方式〔値を取る文字の表で読む〕・範囲・受け入れ条件は同じ。呼び出し元を表にそろえる追加だけ）
- review-gate（2026-11-12・敵対的レビュー 1319 が V1 を「未検証〔実験必須を読んで確認しただけ〕」で HIGH）: 表と `--help` を突き合わせる決定論の TC-13（`test_i463_optspec_help.sh`・FG-13 つき）を足し、V1 の確かめ方を「読んで可」に下げた。TC-13 で script の `-t`（`-t[<file>]`）がくっつけたときだけ値を取ると分かったので `_OPTSPEC_OPTIONAL` に足した。あわせてコードレビュー 1303 の F1（python の値を取る長いオプション `--check-hash-based-pycs` が表に無く、値をスクリプト名と読んで後ろの `-c` を見なくなる後退・SECURITY=yes）を表に足して直し、TC-01 の 01g と止めるべき形の一覧に入れた。方式・範囲・受け入れ条件は変えないので計画レビューは通り直さない
- implement（2026-11-12）: psql のコンテナは止まっていて起こしていない（`docker compose ps` が空）。psql の表は PostgreSQL 15 の文書のまま（V1 の psql は TC-09・TC-10 の後退検知で見る）

## レビュー結果
- [20261112_1226 判定: ✅ 完了](../../reviews/I463_plan_review_20261112_1226.md)
- [20261112_1224 判定: 差し戻し（Blocker 1件）](../../reviews/I463_plan_review_20261112_1224.md)

## セキュリティレビュー結果

**実施日**: 2026-11-12

バックエンド・フロントエンドのコード変更なし（アプリの認証・認可・モデル・URL は読む対象なし）。対象はハーネスの見張り（PreToolUse フック）の判定と、そのテストの道具。脅威モデルは「普通の書き方の事故」（わざと抜ける書き方は対象外・danger-ops.md）。

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | 入力検証（見張りが読むコマンド文字列） | `_OPTSPEC` に値を取らない文字を値ありとして入れると、その文字の後ろのまとめ書き（例: `-Xc'DELETE …'` の c）を読まなくなり、破壊的 SQL・別ワークツリーへの書き込みの停止が減る | 禁止: `--help`・公式文書に無い文字を表に入れない。必須: TC-09（止めるべき形の一覧で変更前より弱い判定 0 件）・TC-10（既存の見張りのテスト全件）・必ず確かめる項目 V1 |
| Medium | 機密情報 | 秘密のファイルを探す `paths` を getopt の位置引数に絞ると、`grep -f .env x`（パターンを .env から読む）の確認が消える | 禁止: `_cmd_external` の `paths` を位置引数に絞らない（今のまま `-` で始まらない語すべて）。必須: TC-03 の 03d・一覧に入れる |
| Medium | 入力検証 | python の読み終わり（`-c`・`-m`・スクリプト名）を他のコマンドに広げると、`psql mydb -c 'DELETE …'` のような位置引数の後ろの `-c` を読まなくなる | 必須: 読み終わりは python だけ（`_getopt` の `cmd == "python"`）。TC-02 の 02c・必ず確かめる項目 V2 |
| Low | セキュリティ設定ミス | `--cases` は比べる相手（変更前の見張り）が無いと後退を見られない | 必須: 相手が無くても SKIP にせず、作業ツリーで「通す」の行を失敗にする（ステップ 3） |
| Low | ファイル操作 | `--cases` が一覧のコマンドを実行してしまう | 禁止: 一覧のコマンドを実行しない。見張りに JSON を渡して終了コードと出力を見るだけ（`judge` と同じ）。一時ディレクトリの中で呼ぶ |
| — | 認証・認可・マルチテナント・OWASP（XSS・CSRF・IDOR）・外部通信・依存ライブラリ | なし（アプリのコード・依存の変更なし。`--cases` は外部と通信しない） | — |

### 攻撃シナリオレビュー

入口はアプリの API ではなく、Claude が Bash で打つコマンド（見張りが判定する）。想定する「攻撃」は、普通の書き方の事故で危ない操作が見張りを素通りすること。

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | Bash（psql） | Claude（作業者） | `psql -Xf/tmp/dump.sql`・`psql -tAc'DELETE …'`・ヒアドキュメントの `DELETE` | 流し込み・破壊的 SQL は停止（DANGER_OK） | Yes: TC-02・TC-03・一覧（07a・07b・07f） | No | 長いオプションの省略形（`--fi=/x`）は読まない（脅威モデルの範囲外） | Medium |
| 2 | Bash（python） | Claude | アプリを import して消すスクリプトを、引数付き（`-xcfoo`）で実行 | スクリプトの中身を読み、危険操作は停止 | Yes: TC-01 | No | スクリプトのファイルが読めない（大きい・無い）ときは今までどおり「中身の見えないコード」の扱い | Medium |
| 3 | Bash（grep・cat 等） | Claude | `grep -ie. .env`・`grep -f .env x` で秘密のファイルを読む | 確認になる | Yes: TC-03・一覧 | No | 表に無い読み方（rg・awk のまとめ書き）は今のまま | Medium |
| 4 | Bash（sed・cp・mv・install・ln） | Claude | 別ワークツリーへの書き込み・移動（`sed -ie …`・`cp -vt$W/d …`・`mv -vt/tmp/d $W/a`） | 停止（DANGER_OK でも外れない） | Yes: TC-05・TC-07・一覧（I454 の 04a〜04k） | No | rsync は表に入れない（今のまま） | Medium |
| 5 | Bash（su・flock・script） | Claude | `su -lc'git push --force …'` などシェルを包む形 | 中のコマンドを読み、停止 | Yes: TC-08・一覧 | No | なし | Low |
| 6 | Bash（コンテナの pytest） | Claude | `--basetemp=/app/…`・`--junitxml=/app/…` で bind mount の先に書く | 確認になる（読む指定の除外を書き出しに広げない） | Yes: TC-06 の 06e・06f・M-02 | Yes: M-01・M-02（承認画面の出方） | `--cov-report=xml:/app/…` は `=/` で始まらず元から読まない（今のまま・範囲外） | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 3件 | 4件 |
| Low     | 2件 | 2件 |

### 残余リスク処遇
（retro・2026-11-12）
- 設計レビューの Medium 3 件: すべて TC で防御済み（TC-03 の 03d・TC-02 の 02c・TC-09・TC-10・TC-13）
- 受け入れる残り: 長いオプションの省略形（`--fi=/x`）・rsync を表に入れない・`--cov-report=xml:/app/…`（元から読まない）・表に無い値付きの長いオプション（grep `--exclude-dir` など）— 脅威モデル（普通の書き方の事故）の範囲外か変更前と同じ。秘密に関わる読み残し（su `-C`・`grep -f.env`／`--file=.env`・python のスクリプト名の探し方）は I469（#469）で扱う
