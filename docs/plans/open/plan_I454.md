# plan_I454: 見張りの環境変数の表示の後退（ps -A e）と書き先の取りこぼしを直す

## 基本情報
- **計画書ID**: plan_I454
- **関連イシュー**: #454
- **Draft PR**: #457
- **作成根拠資料**: docs/issues/open/I454.md（GitHub #454 の本文の写し・正は GitHub）
- **実装後評価**: docs/reviews/open/I454_review.md
- **作成日**: 2026-11-12

## 1. 背景/目的
I444 で見張り（`scripts/claude/hooks/pretooluse_guard.py`）の環境変数の表示の判定をホストとコンテナで 1 か所にまとめ、マージ前の直しで `ps` の誤検出を減らした。その直しの近似（直前の語が - で始まれば値）のため、`ps -A e`・`ps -ef e`（環境変数を丸ごと表示する）が確認にならない後退が出た（台帳 F10・SECURITY=yes）。あわせて、コンテナ内の書き先の取りこぼし（F5）、通す形が書き込みの判定ごと飛ばす作り、書き先の見分け方が 3 つに分かれている作りが残っている。

目的: 環境変数の表示を確認に戻し（最優先）、普通の操作に余計な確認を出さず、手元のファイルへの書き込みの取りこぼしを粗い判定のまま減らす。見張りの行数は増やさない。

## 2. 受け入れ条件
イシュー #454 の受け入れ条件のとおり（下の「6. テスト計画」の表で、どれで確かめるかを対応させる）。

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra:
  - `scripts/claude/hooks/pretooluse_guard.py`（高リスク・敵対的レビューの対象）
  - `scripts/claude/tests/test_i454_guard_env_writes.sh`（新規）
  - `scripts/claude/tests/test_i444_guard_gaps.sh`（失敗の注入の置き換え文字列だけ）
  - `docs/runbooks/danger-ops.md`・`docs/runbooks/worktree.md`（正の関数の名前と代表の形）
  - `docs/reviews/backlog/I444.md`（同梱して直した行を消す）

## 調査結果（2026-11-12）

### 変更前の判定（develop 由来のこのブランチの見張りに Bash の入力を流した結果）
| コマンド | 今 | 望む |
|---|---|---|
| `ps -A e`・`ps -ef e`（ホスト・コンテナ） | 通る | 確認（F10） |
| `ps o etime`・`ps U user` | 確認 | 通る（F11） |
| `declare +x`・`typeset +x` | 通る | 確認（F12） |
| コンテナ内の `cp -vt/app/x /tmp/y` | 通る | 確認（F5） |
| コンテナ内の `cp -t/app/x /tmp/y` | 確認 | 確認（`_opt_values` の付着形で読めている。イシューの記述は誤り） |
| コンテナ内の `sed -i -es/a/b/ /app/x`（式を -e にくっつけた形） | 通る | 確認（F5 と同じ種類の取りこぼし。調べて見つけた） |
| コンテナ内の `install -d /app/newdir` | 通る | 通る（設計確認メモ） |
| コンテナ内の `pytest --junitxml=/app/r.xml -k x` | 通る | 確認（問題 3） |
| コンテナ内の `sh -c "pytest -k delete > /tmp/out.txt"` | 確認（語 delete） | 通る（/tmp/ への書き込みは許す場所。リダイレクトがあると通す形から外れていた） |
| `docker compose exec backend grep -rn foo /app/apps > out.txt`（ホスト側のリダイレクト） | 確認 | 通る（ホストの書き込みをコンテナの書き込みと取り違えていた。下の原因 4） |
| 別ワークツリーへの `cp -vt$W/x`・`--target-directory=$W/x`・`install`・`ln -s`・`rsync` の書き先・`mv $W/x /tmp/y` | 通る | 停止（設計確認メモ） |
| 別ワークツリーの `cp $W/x /tmp/y`・`ln -s $W/x /tmp/y`・`install -d $W/newdir`・`sed -n p $W/x` | 通る | 通る |

### 原因
1. **F10**: `_cmd_external` の `ps` の条件 `not p.startswith("-")` は「直前の語が - で始まれば、その後ろは値」とみなす。`-A`・`-ef` のような値を取らないフラグの後ろの BSD 形式の `e` も値とみなした
2. **F11**: 同じ条件で、`-` の付かない BSD 形式の値を取るオプション（`o`・`U`）の後ろの値（`etime`・`user`）を BSD 形式の e と誤った
3. **F5・sed**: `_opt_values` のまとめ書きは「最後の文字が該当（`-tAc X`）」か「最初の文字が該当（`-cX`）」の 2 つだけを読み、`-vt/app/x`（真ん中の文字の後ろに値）を読めない。`_ctr_write_targets` の sed は「最初の位置引数が式」と決め打ちしていて、式を `-e` にくっつけると最初のファイルを式とみなす
4. **問題 3**: `_analyze` は `_container_safe` が True なら `_container_risky`（語と書き込み）を呼ばない。そのため通す形の分岐ごとに書き込みの除外を抱え、抱え漏れ（`--junitxml=`）は素通りする。また `_container_safe` はリダイレクト（`c["writes"]`）があると通す形から外すので、/tmp/ へのリダイレクトでも語の判定にかかる。さらに、ホスト側のリダイレクト（`docker compose exec … > out.txt`）は、包みを外すときに `writes` だけを消して `write_to` を引き継ぐので、通す形でないコマンドではコンテナの書き込みとして扱われていた
5. **問題 4**: 書き先の見分け方が `_bash_write_targets`（`-t` の完全一致だけ・cp と mv だけ）・`_record_writes`（最後の語だけ）・`_ctr_write_targets`（I444 で `-t`・`mv` の移動元）の 3 つに分かれている

### 案の写しでのスパイク（リポジトリをスクラッチパッドに複製した写し。リポジトリのファイルは変えていない）
5-1〜5-4 を写しに当てて流した:
- 上の表の「望む」がすべて成り立つ（TC-01〜TC-04 のケースを写しの見張りに流した）
- 既存のテスト: `test_pretooluse_container_guard.sh` pass=788・`test_i200_guard_narrowing.sh` pass=75・`test_pretooluse_guard_matrix.sh` pass=391・`test_guard_bash_oracle.sh` 見逃し 0・余計な停止 0・`test_i182_corpus_base.sh` pass=5・`test_pretooluse_worktree_guard.sh` pass=126、すべて fail=0（変更前と同じ数）。`test_i444_guard_gaps.sh` は pass=60 fail=4 で、4 件はどれも失敗の注入の置き換え文字列が見張りから消えた「置き換え NOPATCH」（判定のケースの FAIL は 0）→ 5-5 で合わせる
- 行数: `git diff --numstat` で `60 83`（差し引き −23）
- 過去の作業コマンド: 下の「過去の作業コマンドでの比較」

### 過去の作業コマンドでの比較
`guard_corpus_diff.py --base HEAD --guard <写しの見張り>`（作業記録 15576 件）: 確認＋停止 362（2.32%）→ 358（2.30%）・新しく確認・停止 4 件（0.03%・上限 156 件）・異常終了 0 件・OK。変わった 12 件の中身（スクラッチパッドの比較用スクリプトで全件を出した）:
- 停止→（新しく停止）2 件: `mv <harness-2 のワークツリー>/e2e/tests/tmp-*.spec.ts … /tmp/claude…`（別ワークツリーのファイルを動かす＝移動元が消える。設計確認メモで止めると決めた形。比較はこのワークツリーから流すので harness-2 は別ワークツリーになる。harness-2 のセッションで打った元のコマンドなら自分のワークツリーで止まらない）
- 通る→確認 2 件: `pytest … --rootdir=/app -c /app/pytest.ini`（`--opt=/絶対パス` の値が読む場所でも当たる。5-4 の粗い判定の余計な確認。2 件とも同じ時期の敵対的テストの作業）
- 確認→通る 8 件: すべて `docker compose exec … > $D/probe.txt` のように、ホスト側のスクラッチパッドへ書き出すリダイレクト。変更前は、包みを外すときに `write_to` を引き継ぎ、ホストの書き込みをコンテナの /tmp/ 以外への書き込みと取り違えて確認にしていた（原因 4）。語の理由が出ていたものは無い（同じ 8 件を変更前の見張りに流し直し、理由が書き込みだけであることを確かめた）
- `_opt_values` の読み方の変更（5-2）で判定が変わったものは無い（上の 12 件のどれも `_opt_values` の呼び出し元〔コード・SQL・grep のパターン・docker inspect の書式〕の形ではない）

### 既存のテスト
- 計画時（2026-11-12・変更前）: 上の 6 本と `test_i444_guard_gaps.sh` pass=64 はすべて fail=0（写しの基準として同じ環境で流した）

### 環境前提
- `python3`・`bash`・`git` はホストにある（上のスパイクで使用）。手動テストの docker は存在しないサービス名で流すので、コンテナが無くても判定は変わらない

## 4. 変更点一覧
| ファイル | 関数・定数 | 変更 |
|---|---|---|
| `scripts/claude/hooks/pretooluse_guard.py` | `_PS_VALUE_OPT_RE`（新規）・`_cmd_external` | 5-1 |
| 同上 | `_opt_values` | 5-2: まとめ書きの真ん中の文字の後ろの値（`-vt/x`）を読む |
| 同上 | `_COPY_CMDS`・`_write_targets`（新規）・`_bash_write_targets`・`_has_write_intent`・`_record_writes`・`_ctr_write_targets`（削除） | 5-3 |
| 同上 | `_container_risky`・`_container_safe`・`_analyze`・`_new_cmd`・`_raw_commands`・`_expand`（`writes` を消す・包みを外すときに `write_to` も消す） | 5-4 |
| `scripts/claude/tests/test_i454_guard_env_writes.sh` | 新規 | TC-01〜TC-04 |
| `scripts/claude/tests/test_i444_guard_gaps.sh` | FG-01・FG-01b・FG-02a・FG-02b の置き換え文字列 | 5-5（TC-05） |
| `docs/runbooks/danger-ops.md` | 「見張りの扱い」の 4. | 5-6 |
| `docs/runbooks/worktree.md` | §9「技術強制済み（I095）」 | 5-6 |
| `docs/reviews/backlog/I444.md` | F11・F12・F13 の行 | 消す |

## 5. 実装手順

### 5-1. ps の値を取るオプションを読み、BSD 形式の e を確認に戻す（F10・F11）・`declare +x`（F12）
**方針**: 「直前の語が - で始まる」の近似をやめ、「直前の語が `ps` の値を取るオプション」のときだけ値として読み飛ばす。粗い判定にとどめる（I179 の教訓）: procps の値を取る短いオプション（`-C -G -g -O -o -p -q -s -t -U -u`。まとめ書きの最後〔`-eo`〕も）、BSD 形式の値を取る 1 文字（`O o p q t U`）、長い形（`--sort` など）。BSD 形式のまとめ書き（`axo`）は、値の語（`root`）と見分けられないので見ない（`ps axo etime` は確認になる＝安全側）。`declare`／`typeset` は `+` で始まるオプションだけの形も表示とみなす。

```python
# ps の値を取るオプション（procps: -C -G -g -O -o -p -q -s -t -U -u とまとめ書きの最後〔-eo〕／BSD 形式の 1 文字 O o p q t U
# 〔axo のようなまとめ書きは値の語〈root〉と見分けられないので見ない〕／長い形）
_PS_VALUE_OPT_RE = re.compile(r"-[A-Za-z]*[CGOUgopqstu]|[OUopqt]|--(sort|format|pid|ppid|user|group|tty|sid|cols|rows)")
...
            or (head == "ps" and any(re.fullmatch(r"[A-Za-z]*e[A-Za-z]*", a) and not _PS_VALUE_OPT_RE.fullmatch(p)
                                     for p, a in zip(toks, toks[1:]))) \
            or (head in ("export", "declare", "typeset")
                and (all(a.startswith(("-", "+")) for a in toks[1:]) or any(a in ("-p", "-px", "-xp") for a in toks[1:]))):
```
コメントの「-C node・-o etime のようなオプションの値は見ない」を「値を取るオプション〔-C node・-o etime・o etime・--sort etime〕の値は見ない・I454」にする。
→ TC-01（I444 で固定した形は TC-05 の `test_i444_guard_gaps.sh`）

### 5-2. `_opt_values` のまとめ書きを getopt と同じに読む（F5）
**方針**: まとめ書き（`-` 1 つの後ろに英字が続く語）は、英字だけの並びの後の最初の該当の文字から後ろが値、無ければ次の語（getopt と同じ）。今の 2 つの形（`-tAc X`・`-cX`）はこの規則に含まれるので、他の呼び出し元の読み方は変わらない（既存のテストの全件一致で確かめた・調査結果）。

```python
        if t.startswith("-") and not t.startswith("--") and len(t) > 2:
            body = t[1:]
            k = next((j for j, ch in enumerate(body) if ch in shorts and (j == 0 or body[:j].isalpha())), None)
            if k is not None and (body[k + 1:] or i + 1 < len(toks)):
                vals.append(body[k + 1:] or toks[i + 1])   # -cX・-vtX（付着形）／-tAc X
                i += 1 if body[k + 1:] else 2
                continue
        i += 1
```
docstring に「`-vtX`」と「英字だけの並びの後の最初の該当の文字から後ろが値（無ければ次の語。getopt と同じ・I454）」を足す。
→ TC-02 の 02a・FG-02

### 5-3. 書き先の見分け方を 1 つの関数にまとめる（問題 4・設計確認メモ）
**方針**: リダイレクト以外の書き先を出す `_write_targets(toks)` を 1 つ作り、別ワークツリーの停止（`_bash_write_targets`・絶対パスだけ）・未カバーの警告（`_has_write_intent`）・同じコマンドの中で書くファイルの記録（`_record_writes`）・コンテナの /tmp/ 以外の判定（`_container_risky`）が使う。中身は I444 の `_ctr_write_targets` に、sed の式をオプションで渡す形と `install -d` を足したもの。`_ctr_write_targets` は消す。

```python
_COPY_CMDS = ("cp", "mv", "install", "ln", "rsync")


def _write_targets(toks: list) -> list:
    """リダイレクト以外でファイルに書き込むコマンドの書き先（I454: 別ワークツリーの停止・同じコマンドの中で書くファイルの記録・
    コンテナの /tmp/ 以外の判定で共通）。tee・sed -i（-e／-f で式を渡すときは位置引数がすべてファイル）・cp／mv／install／ln／
    rsync の書き先（最後の位置引数か -t／--target-directory。-vt/x のようなまとめ書きも）と mv の移動元。install -d は作るだけ。"""
    if not toks:
        return []
    head, args = os.path.basename(toks[0]), toks[1:]
    pos = [a for a in args if not a.startswith("-")]
    if head == "tee":
        return pos
    if head == "sed":
        expr = _opt_values(args, ("-e", "-f", "--expression", "--file"))
        files = [a for a in pos if a not in expr]
        return (files if expr else files[1:]) if _has_short(args, "i", "--in-place") else []
    if head not in _COPY_CMDS or (head == "install" and _has_short(args, "d", "--directory")):
        return []
    tdir = _opt_values(args, ("-t", "--target-directory")) if head != "rsync" else []   # rsync の -t は時刻を保つ
    if head == "mv":                           # 移動元も消える（I444）
        return tdir + pos
    return tdir or (pos[-1:] if len(pos) >= 2 else [])
```
- `_bash_write_targets`: コマンド別の宛先の部分（tee・cp／mv・sed の 17 行）を `targets += _write_targets(toks)` の 1 行にする。リダイレクトの読み取りと「絶対パスだけ」は変えない。これで停止（exit 2）は `install`・`ln`・`rsync` の書き先・`--target-directory=`・くっつけた `-t`・`mv` の移動元に広がる（設計確認メモ）。sed は「位置引数すべて」から「式を除いたファイル」に変わるが、絶対パスだけを見るので、止める形は減らない（式は `/` で始まる場合〔`sed -i '/^#/d' f`〕だけ絶対パスに見えていた。止める理由にはならない）
- `_has_write_intent`: リダイレクトと `_write_targets(toks)` が空でないことで判定する（3 行にまとまる）
- `_record_writes`: `targets = c["write_to"] + (コピー系なら位置引数すべて、それ以外は _write_targets(toks))`。コピー系（`_COPY_CMDS`）は、元の名前で書く形（`cp a /dir/`・`cp -t /dir a`）のために位置引数をすべて記録する（書く中身は見えない＝None。判定では「中身を確かめられない」で確認側に倒れる。今は最後の語だけを記録していて、`cp -t /tmp/d /tmp/x.sh && bash /tmp/d/x.sh` の x.sh を記録しない）
→ TC-02・TC-04・FG-04

### 5-4. 危ない語の理由と書き込みの理由を分け、通す形でも /tmp/ 以外への書き込みを見る（問題 3）
**方針**: `_container_risky` が書き込みの理由を先に、常に見る。`_container_safe` は危ない語の理由だけを打ち消す。書き込みの理由は、リダイレクト（`write_to`）・`_write_targets`・`--opt=/絶対パス` の形のオプションの値（`--junitxml=/app/r.xml` のように、通す形の道具が書き出し先を値で受ける形。粗い判定で、`--opt /path` の離した形は見ない）。

```python
def _container_risky(c: dict, text: str) -> list:
    """I200: コンテナ内の単純コマンドを確認にする理由（無ければ []）。環境変数の表示は _cmd_external が見る（I444）。
    /tmp/ 以外へ書き込むとき（リダイレクト・_write_targets・`--opt=/絶対パス` の値）は常に確認（I454）。危ない語が当たっても
    通す形（_container_safe）でなければ、コマンドの語・ヒアドキュメント・here-string・読める Python コードの危ない語も見る。
    パイプ・標準入力・読みきれない書き方では、流し込まれる中身が見えないので、コマンド全体の文字列も見る。"""
    reasons = []
    vals = [a.split("=", 1)[1] for a in c["toks"][1:] if re.match(r"--[\w-]+=/", a)]   # pytest --junitxml=/app/r.xml
    if any(not _in_scratch(t) for t in c["write_to"] + _write_targets(c["toks"]) + vals):
        reasons.append("コンテナの /tmp/ 以外への書き込み")
    if _container_safe(c):
        return reasons
    （語の判定は今のまま）
    found = _risky_words("\n".join(parts))
    return reasons + (["危ない語: " + "・".join(found)] if found else [])
```
- `_analyze`: `if c["compose"] and not d and not e and not _container_safe(c):` を `if c["compose"] and not d and not e:` にする（コメントも直す）
- `_container_safe`: 前提の条件から `c["writes"]` を外す（リダイレクトの書き込みは `_container_risky` が常に見るため。/tmp/ へのリダイレクトなら通す形のまま通る）。docstring の最後を「打ち消すのは危ない語の理由だけで、/tmp/ 以外への書き込みは _container_risky が常に見る（I454）」にする。分岐ごとの書き込みの除外（`--fix`・`--basetemp`・`ruff format`・psql の `-o`・`sort -o`）は残す（離した形の値〔`--basetemp /app/x`・`-o /app/x`〕は上の書き込みの理由では見えないため。消すと確認を外す範囲が広がる）
- `writes` のフラグを消す（`_new_cmd`・`_raw_commands`。使うのは `_container_safe` だけだった）。`_expand` で docker の包みを外すときは、`writes=False` の代わりに `write_to=[]` にする（ホスト側のリダイレクトはコンテナ内の書き込みではない、という今のコメントどおりにする）
→ TC-03・FG-03

### 5-5. I444 のテストの失敗の注入を新しいコードに合わせる
`test_i444_guard_gaps.sh` の置き換え文字列を、守る形を変えずに新しいコードに合わせる:
- FG-01: `and (all(a.startswith("-") for a in toks[1:]) …` の 2 行 → `and (all(a.startswith(("-", "+")) for a in toks[1:]) …` の 2 行（後ろの `r.append(...)` を `pass` にする置き換えはそのまま）
- FG-01b: ` and not p.startswith("-")` を消す → ` and not _PS_VALUE_OPT_RE.fullmatch(p)` を消す（01u `ps -C node` が ASK になる）
- FG-02a: `_opt_values(toks[1:], ("-t", "--target-directory")) if head != "rsync" else []` → `_opt_values(args, ("-t", "--target-directory")) if head != "rsync" else []`
- FG-02b: `            return tdir + pos`（12 字下げ）→ `        return tdir + pos`（8 字下げ）
→ TC-05

### 5-6. 手順書の正の関数の名前と代表の形を直す
- `danger-ops.md`「見張りの扱い」の 4.: 書き込みの文の「形の正は `_ctr_write_targets`」を「形の正は `_write_targets` と `_container_risky`」にし（`--opt=/絶対パス` の値は `_container_risky` が見るため）、「書き先と移動元」の後ろに「・`--opt=/絶対パス` の値」を足す。「危ない語が当たっても通す形」の文の後ろに「（通す形でも、/tmp/ 以外への書き込みは確認・I454）」を足す
- `worktree.md` §9「技術強制済み（I095）」: 「Bash 書込（代表: リダイレクト・`tee`・`cp`/`mv` の宛先・`sed -i`。形の正は見張りの `_bash_write_targets`）」を「Bash 書込（代表: リダイレクト・`tee`・`sed -i`・`cp`/`mv`/`install`/`ln`/`rsync` の書き先と `mv` の移動元。形の正は見張りの `_write_targets`〔`_bash_write_targets` が絶対パスだけを見る〕）」にする
→ M-04

### ステップの順と依存
1. 5-2（`_opt_values`。5-3 が使う）→ 5-3 → 5-4（5-3 の `_write_targets` を使う）
2. 5-1 は独立（いつでもよい）
3. 5-5・新しいテスト（TC-01〜TC-05）・5-6・一覧の行を消す・行数（M-03）と TC-06

## 6. テスト計画
- 自動: `docs/tests/open/I454_auto_test.md`。新しい `scripts/claude/tests/test_i454_guard_env_writes.sh` が見張りに JSON を渡して判定だけを見る（コマンドは実行しない）。失敗の注入は見張りの写しを一部書き換えて行う（`test_i444_guard_gaps.sh` と同じ方法）。TC-04 は一時リポジトリに別ワークツリーを作る（`test_pretooluse_worktree_guard.sh` と同じ方法）。テストのレベルは見張りの単体（判定関数を通した入出力）だけ。アプリのテスト（pytest・Jest・E2E）は変更が無いので CI に任せる
- 手動（Claude）: `docs/tests/open/I454_manual_test.md`。`check-permission-prompt.sh` で、承認の仕組み全体（settings.json の allow と見張り）での出方を確かめる。行数・手順書と見張りの突き合わせ

| 受け入れ条件 | 確かめ |
|---|---|
| `ps -A e`・`ps -ef e` が確認・I444 で固定した形は確認／通るのまま | TC-01・TC-05（`test_i444_guard_gaps.sh` の TC-01）・M-02 |
| `cp -vt/app/x`・`cp -t/app/x` が確認・`install -d /app/newdir` は通る | TC-02 |
| 通す形でも /tmp/ 以外へ書くものが確認・`pytest -k delete` などは通る | TC-03・M-01・M-02・`test_i444_guard_gaps.sh` の TC-04 |
| 書き先の抽出が 1 つ・別ワークツリーの停止が新しく止める形と今までどおり止める形 | TC-04 |
| 過去の作業コマンドでの比較が 1% 以内・異常終了 0 | TC-06 |
| 見張りの行数を差し引きで増やさない | M-03 |
| 既存のハーネステスト・CI が pass | TC-06・CI |

## 7. ロールバック
PR を revert する（見張り・テスト・手順書だけ。データの変更なし）。見張りが起動できなくなったときは、ユーザーが端末で `! git restore scripts/claude/hooks/pretooluse_guard.py`（`danger-ops.md` の「見張りが失敗したとき」）。

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| `_opt_values` の読み方を変えて、他の呼び出し元（`python -c`・`psql -c`・`grep -e`・`docker inspect -f` など）の値の読み方が変わる | 今の 2 つの形は新しい規則に含まれる（5-2）。変わるのは真ん中の文字の後ろに値がある形だけで、どの呼び出し元でも getopt と同じ読み方に近づく。既存の 6 本のテスト（matrix・oracle を含む）と corpus diff の全件で確かめる（調査結果・TC-06） |
| 別ワークツリーの停止が広がり、普通の作業が止まる | 広がるのは別ワークツリーへの書き込みと移動元だけ（設計確認メモ）。別ワークツリーから読むだけの形（`cp $W/x /tmp/y`・`ln -s $W/x`）は通る（TC-04 の対照）。corpus diff の「新しく停止」を見る |
| 書き込みの理由を通す形にも当てて、普通のテスト・lint に確認が増える | 見るのは /tmp/ 以外への書き込みだけ。`--opt=/絶対パス` は粗い判定で、読む場所を値で渡す形（`--rootdir=/app`）にも当たる（スパイクの corpus diff で 2 件・15576 件中）。読む場所のオプションの一覧で除くのは粗い判定の方針に合わないので、確認のままにする。件数は TC-06 で見て 1% 以内 |
| `writes` を消し、包みを外すときに `write_to` を消して、コンテナの中の書き込みを見落とす | 消すのはホスト側のリダイレクト（docker の外）だけ。コンテナの中のリダイレクト（`sh -c "… > /app/x"`）は中のコマンドの `write_to` に入る（TC-03 の 03d） |
| 読み解きの例外で見張りが止まる | 変えるのは判定の関数だけで、読み解き（`_raw_commands` の区切り）は変えない。matrix・oracle・corpus diff（異常終了は 1 件でも不合格）を流す（TC-06） |

## 9. 確定事項と自律判断
### イシューに明記されていること
- F10 を最優先で直す・1〜4 の範囲・粗い判定にとどめる・脅威モデルは「事故」（I200・I179）
- 設計確認メモ（2026-11-12）: 書き先の見分け方を 1 つにまとめ、別ワークツリーの停止を広げる。コンテナ内のくっつけた `-t` は確認、`install -d` は確認・停止にしない
- 受け入れ条件の各項目（corpus diff 1% 以内・行数を差し引きで増やさない）

### Claude が技術的に決めたこと
- 5-1: `ps` は値を取るオプションの一覧で読む（「直前の語が - で始まる」の近似は F10 を生んだ。一覧は procps の値を取る短いオプションと BSD 形式の 1 文字・長い形。BSD 形式のまとめ書きは値の語と見分けられないので見ない＝確認側に倒れる）。F11（`ps o etime`・`ps U user`）は同じ一覧で直る
- 5-2: `-vt/x` の読み取りは `_opt_values` を getopt と同じ規則にして直す（書き先の関数の中で別に読むより、他の呼び出し元〔`grep -ve`・`python -Bc`〕も同じ規則でそろう。行数も減る）
- 5-3: 共通の関数は I444 の `_ctr_write_targets` を土台にする（`-t`・`--target-directory`・`mv` の移動元・rsync の `-t` の扱いが一番そろっているため）。sed の式をオプションで渡す形（`-es/a/b/`）は、調べて見つけた同じ種類の取りこぼしなので足す
- 5-3: `_record_writes` はコピー系の位置引数もすべて記録する（元の名前で書く形があるため。記録が増えると「中身を確かめられない」で確認側に倒れるだけ）
- 5-4: 書き込みの理由に `--opt=/絶対パス` の値を足す（受け入れ条件の `--junitxml=/app/r.xml` を、分岐ごとの除外を増やさずに捕まえるため）。分岐ごとの書き込みの除外は、離した形の値が見えないので残す（消すと確認を外す範囲が広がる）
- 5-4: ホスト側のリダイレクトを包みを外すときに消す（今のコメントどおりの動きに直す。I444 までは `writes` だけを消していて、通す形でないコマンドではホストの書き込みでコンテナの確認が出ていた。確認が減る方向で、ホストの書き込み先は別ワークツリーの停止が今までどおり見る）
- テストは新しいファイル `test_i454_guard_env_writes.sh` に置き、`test_i444_guard_gaps.sh` は失敗の注入の置き換え文字列だけを直す（I444 の守る形を変えないため）
- 一覧 `docs/reviews/backlog/I444.md` F11: 同梱 — 5-1 の同じ一覧で直る
- 一覧 `docs/reviews/backlog/I444.md` F12: 同梱 — 5-1 で `+` を足す（1 か所）
- 一覧 `docs/reviews/backlog/I444.md` F13: 同梱 — TC-01 の 01a〜01c（`ps -A e` を固定）
- 一覧 `docs/reviews/backlog/I444.md` F7（`mv -S .bak` の値を書き先とみなす）: 残す — 余計な確認になるのはコンテナの中で `-S` の値を離して書くときだけで、停止の判定は絶対パスだけなので影響しない。直すには mv の値を取るオプションの一覧が要り、粗い判定の方針に合わない
- 一覧 `docs/reviews/backlog/I444.md` F2・F6・F8・F9: 対象外 — 実装対象のファイル（`guard_corpus_diff.py`・`test_guard_corpus_diff.sh`）に当たらない
- 一覧 `docs/reviews/backlog/I200.md` F5（語の後ろの切れ目）: 残す — I444 で「残す」と決めた理由（語形の取りこぼしで (C) を弱める）のまま
- 一覧 `docs/reviews/backlog/I224.md` F9・`docs/reviews/backlog/I223.md` B1〜B4（`FILE=-`）: 残す — このイシューの範囲と関係が無い（受け入れ条件の実測・bot の停止中の作業）

### チェック
- 要件適合性: 受け入れ条件の範囲内。調べて見つけた sed の式の付着形（5-3）とホスト側のリダイレクトの取り違え（5-4）は、同じ書き先の判定の取りこぼし・誤りで、問題 2・3 の根本原因の範囲。マルチテナント・ステータス遷移は該当なし
- セキュリティ: 秘密情報（環境変数）の表示が確認に戻る（F10）・手元のファイルの上書きと別ワークツリーへの書き込みを見る範囲が広がる方向。確認が減るのは、値を取るオプションの値（F11）・/tmp/ へのリダイレクト・ホスト側のリダイレクト・`install -d` だけで、どれも (A)〜(C) に当たらない。入力の検証・認証・OWASP・依存の追加は該当なし（Python の標準ライブラリだけ）。bandit・npm audit の対象外（`scripts/` は bandit の対象外・依存の変更なし）
- テスト計画: 再発防止のテスト（TC-01〜TC-04・失敗の注入つき）あり。F10 は I444 で検知できなかった（F13）ので、`ps -A e` を直接固定する。テストのレベルは見張りの単体と、承認の仕組み全体（M-01・M-02）
- P3/P5/P8 影響なし（DB・外部 API・非同期・新しいインフラ・依存の変更なし）
- P6 影響なし（UI・データ量の懸念なし）
- P9 影響なし（個人情報・テナントデータを扱わない）
- 設計品質: 書き先の見分け方の重複（3 つ）を 1 つにし、許可リストの役目（語の理由だけを打ち消す）と作りを一致させる方向。定数は見張りの中の名前つきの定数（`_PS_VALUE_OPT_RE`・`_COPY_CMDS`）
- 守る対象と最後の守り（ローカルの見張りは GitHub を最後の守りとして最小限にする方針・I179）: 環境変数の表示（F10）は秘密情報が作業記録に出る＝GitHub からは取り消せない例外なので、見張りで確認する。別ワークツリーへの書き込みの停止は、push 前の他トラックの未コミットの変更を壊す事故（GitHub からは戻せない）を止めるもので、I095 からの既存の役目を同じ単純な規則（絶対パスだけ）のまま書き方の取りこぼしを減らすだけ。コンテナの /tmp/ 以外への書き込みも、手元の未コミットのファイルの上書きが対象。どれも判定は粗い規則にとどめ、新しい種類の判定は足さない
- 高リスクの見込み: 見張り（`path_risk_trigger` の集合）を変えるので高リスク。計画レビューの判定に従う
- 要件・基本設計・UI/UX の価値判断で仮定したものは無い（止める範囲を広げることと `install -d` の扱いは設計確認メモで決まっている。それ以外は確認を出す基準〔(A)〜(C)〕に沿った当てはめ）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | (C) ホスト・コンテナの環境変数をまとめて表示する形（`ps -A e`・`ps -ef e`・`ps -o pid e`・`ps -u root e`・`declare +x` と、I444 で固定した `ps e`・`ps aux e`・引数なしの `export`・`declare -p`）が確認になり、値を取るオプションの値（`ps -C node`・`ps o etime`・`ps --sort etime`）と代入（`declare -x FOO=1`）は通る（TC-01・FG-01・FG-01b・`test_i444_guard_gaps.sh` の TC-01） |
| V2 | 1 | 読んで可 | (B) コンテナの /tmp/ 以外への書き込み（くっつけた `-t`・`sed -i -es…`・`install`・通す形の `--opt=/絶対パス`・コンテナの中のリダイレクト）が確認になり、/tmp/ の中・ホスト側のリダイレクト・`install -d` は通る（TC-02・TC-03・FG-02・FG-03） |
| V3 | 2 | 読んで可 | 別ワークツリーへの書き込みの停止が、新しい形（`install`・`ln`・`rsync` の書き先・`--target-directory=`・くっつけた `-t`・`mv` の移動元）で止まり、今までの形（`cp`・`cp -t`・`sed -i`・`tee`・リダイレクト）も止まる。別ワークツリーから読むだけの形は通る（TC-04・FG-04・`test_pretooluse_worktree_guard.sh`） |
| V4 | 2 | 読んで可 | `_opt_values` の読み方の変更で、他の呼び出し元（コードの読み取り・SQL・grep のパターン・docker inspect の書式）が今より取りこぼさない（既存の 6 本のテストの全件一致・corpus diff の「確認→通る」がホスト側のリダイレクトの 8 件だけ〔調査結果〕） |
| V5 | 3 | 読んで可 | 普通の操作: `pytest -k delete` などの通す形と、/tmp/ へのリダイレクトが通る（TC-03・M-01・`test_i444_guard_gaps.sh` の TC-04・`test_i200_guard_narrowing.sh`） |

## 計画変更記録
- 1（plan-review・2026-11-12・計画レビュー 1 は HIGHRISK・Warning 3・Info 2）: 9.「チェック」に守る対象と最後の守りを書いた／FG-03 の置き換え後の式を全文で書いた／auto_test の結果の欄に TC-06 の記録の行を用意した。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）
- 2（implement・/simplify の 4 観点の指摘）: `_record_writes` はコピー系なら位置引数だけ、それ以外は `_write_targets` にした（二重に記録していた）／`_write_targets` の sed は `-i` が無ければ先に返す形にした／`_opt_values` の値を 1 回だけ求める形にした／`--opt=/絶対パス` の正規表現を名前つきの定数 `_OPT_PATH_RE` にし、コンテナの判定だけが足すこと（停止の範囲は広げない）を `_write_targets` の docstring に書いた／`_PS_VALUE_OPT_RE` のコメントから文字の写しを外した。見送り: `--opt=/絶対パス` を `_write_targets` に入れる案（別ワークツリーの停止が設計確認メモの範囲を越えて広がる）・`ps` の値の判定を `_opt_values` で読む案（BSD 形式の 1 文字は正規表現が要り、短くならない）・テストの補助関数の共通化（既存のテストと同じ自己完結の形）。手順書の 4. の正の関数は `_write_targets` と `_container_risky` にした（`--opt=/絶対パス` の値は `_container_risky` が見るため・5-6 を合わせた）。見張りの行数は `65 84`（差し引き −19）。計画レビューのやり直し: 不要（整理だけで、方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261112_0215 判定: ✅ 完了（高リスク）](../../reviews/I454_plan_review_20261112_0215.md)

## セキュリティレビュー結果

**実施日**: 2026-11-12

アプリ（backend・frontend）のコード変更なし。対象はハーネスの見張り（`pretooluse_guard.py`）・そのテスト・手順書。認証・認可・マルチテナント・入力検証（HTTP）・OWASP のアプリ側・ファイルのアップロード・外部通信・依存の追加は該当なし。見張りの脅威モデルは「事故」（意図的な回避は対象外・`danger-ops.md`）。

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | 機密情報 | `_PS_VALUE_OPT_RE`（5-1）に値を取らないオプションを誤って入れると、その後ろの BSD 形式の `e` を値とみなし、環境変数の表示を取りこぼす（F10 と同じ種類の後退）。逆に値を取るオプションを入れ忘れても、確認が増えるだけ（安全側） | 必須: 一覧は procps と BSD 形式の「値を取る」オプションだけにする（`-A`・`-e`・`-f`・`a`・`u`・`x` のような値を取らないものを入れない）。BSD 形式のまとめ書きは入れない（値の語〈`root`〉と見分けられない）。値を取らないフラグの後ろ（`ps -A e`・`ps -ef e`）と値の語が値の文字で終わる形（`ps -u root e`）を TC-01 と FG-01 で固定 |
| Medium | 機密情報 | `_opt_values` の読み方の変更（5-2）で、`python -c`・`psql -c`・`grep -e`・`docker inspect -f` などの値の読み方が変わり、コード・SQL・パターンの判定を取りこぼす | 必須: 今の 2 つの形（`-tAc X`・`-cX`）の読み方を変えない（新しい規則に含まれる）。変わるのは真ん中の文字の後ろに値がある形だけ（getopt と同じになる）。既存の matrix・oracle・container_guard・i200 の全件一致と corpus diff の「確認→通る」の中身で確かめる（調査結果で確認済み・TC-06） |
| Medium | 機密情報 | 通す形でリダイレクトを許す（5-4 で `c["writes"]` を外す）ことで、通す形の出力（テストの出力に秘密が出る場合など）を /tmp/ に書けるようになる | 必須: 許すのは /tmp/ の中だけ（/tmp/ 以外は書き込みの理由で確認）。通す形の役目（(A)〜(C) を起こさない操作）は変えない。標準入力（`c["stdin"]`）・here-string・読めない書き方の前提の条件は外さない |
| Low | セキュリティ設定ミス | 別ワークツリーの停止（exit 2・`DANGER_OK` でも外れない）を広げ（5-3）、普通の作業が止まって回避できない | 必須: 広がるのは別ワークツリーの中への書き込みと移動元だけ（絶対パスだけを見る今の規則のまま）。読むだけの形（`cp $W/x /tmp/y`・`ln -s $W/x`）と `install -d` は通す（TC-04 の対照）。corpus diff の「新しく停止」を見る（スパイクで 2 件・どちらも別ワークツリーのファイルの移動） |
| Low | セキュリティ設定ミス | 包みを外すときに `write_to` を消す（5-4）ことで、コンテナの中の書き込みを見落とす | 必須: 消すのは docker の外（ホスト側）のリダイレクトだけ。コンテナの中のリダイレクト（`sh -c "… > /app/x"`）は中のコマンドの `write_to` に入る（TC-03 の 03d・03f） |
| Low | セキュリティ設定ミス | 判定の関数を変えて、例外や異常終了で見張りが素通しになる | 必須: 読み解き（`_raw_commands` の区切り）は変えない。matrix・oracle・corpus diff（異常終了は 1 件でも不合格）を流す（TC-06）。例外時は既存の `_fail_safe`（危ない語があれば確認） |
| Low | 外部通信 | なし（外部への送信の判定は変えない） | — |
| Low | 依存ライブラリ | なし（標準ライブラリだけ） | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | Bash（ホスト・コンテナ） | Claude（auto mode） | `ps -A e`・`ps -ef e` で Claude Code のシェル・コンテナの環境（鍵を含みうる）を作業記録に表示する（事故） | 確認になる | Yes: TC-01・FG-01 | Yes: M-02 | 値を取るオプションの値に見える語の後ろに置く意図的な形は対象外。BSD 形式のまとめ書き（`ps axo etime`）は確認側 | Medium |
| 2 | Bash（コンテナ内） | Claude | `cp -vt/app/x …`・`sed -i -es/a/b/ /app/x`・`install … /app/x` で手元のファイル（bind mount）を上書きする | 確認になる | Yes: TC-02・FG-02 | Yes: M-02（`cp -vt/app/x`） | 書き方の網羅は粗い（値を離した `--junitxml /app/x` などは対象外・I179 の教訓） | Low |
| 3 | Bash（コンテナ内） | Claude | 通す形（`pytest`）に書き出し先のオプション（`--junitxml=/app/r.xml`）を付けて手元のファイルを上書きする | 確認になる | Yes: TC-03・FG-03 | Yes: M-02 | 離した形（`--junitxml /app/r.xml`）は分岐ごとの除外が無い限り通る（粗い判定） | Low |
| 4 | Bash（ホスト） | Claude | `install`・`ln -s`・`rsync`・`cp -vt…`・`mv $W/x …` で別トラックのワークツリーのファイルを書き換える・消す | 停止になる | Yes: TC-04・FG-04 | No | 相対パス・変数越しの宛先は今までどおり対象外（警告だけ） | Low |
| 5 | Bash（コンテナ内） | Claude | `_opt_values` の読み方の変化で `python -c`・`psql -c` の中身の判定を取りこぼす | 今と同じか、より多く読む | Yes: 既存の matrix・oracle・container_guard（TC-06） | No | getopt と違う独自の書き方は対象外 | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 3件 | 1件 |
| Low     | 5件 | 4件 |

### 残余リスク処遇
（retro 段階で決定する）
