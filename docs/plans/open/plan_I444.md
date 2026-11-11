# plan_I444: 見張りに残る役目の取りこぼしを塞ぎ、許可リストと手順書の写しを整理する

## 基本情報
- **計画書ID**: plan_I444
- **関連イシュー**: #444
- **Draft PR**: #451
- **作成根拠資料**: docs/issues/open/I444.md（GitHub #444 の本文の写し・正は GitHub）
- **実装後評価**: docs/reviews/open/I444_review.md
- **作成日**: 2026-11-11

## 1. 背景/目的
I200 で見張り（`scripts/claude/hooks/pretooluse_guard.py`）の確認を (A) GitHub の破壊・(B) 復旧できない状態・(C) 秘密や個人情報の流出だけに絞った。そのレビューで、(B)・(C) に当たるのに確認にならない形（環境変数の表示・コンテナ内の書き込み先）と、作りの重複（許可リストと語の判定の二重化・`ps` の e の判定が 2 か所）、手順書の写しのずれが残った。

目的: #430 の後も見張りに残る役目について、取りこぼしを塞ぎ、確認の基準（手順書）と見張りの実物を一致させる。見張りの行数は増やさない。

## 2. 受け入れ条件
イシュー #444 の受け入れ条件のとおり（下の「6. テスト計画」の表で、どれで確かめるかを対応させる）。

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra:
  - `scripts/claude/hooks/pretooluse_guard.py`（高リスク・敵対的レビューの対象）
  - `scripts/claude/tests/guard_corpus_diff.py`（見張りを直したら流すテストの 1 つ。ワークツリーで SKIP になる不具合を直す）
  - `scripts/claude/tests/test_i444_guard_gaps.sh`（新規）
  - `docs/runbooks/danger-ops.md`・`docs/runbooks/worktree.md`
  - `docs/reviews/backlog/I200.md`・`docs/reviews/backlog/I219.md`・`docs/reviews/backlog/I224.md`（同梱して直した行を消す）

## 調査結果（2026-11-11）

### 0. 対象の確かめ（#430 との関係）
- #430 は OPEN（2026-11-11）。その計画書はまだ無い
- 1〜5 はどれも `docker compose exec|run` の中の判定（1・2・4）か、ホスト・コンテナ共通の SQL の判定（3）か、手順書（5）。#430 の本文は「docker はサンドボックスの外に出す見込み」としており（サンドボックスは docker のソケットを通すと中のコマンドを見られない）、コンテナの中のコマンドの判定はサンドボックスでは止まらない。→ 1〜5 はすべて「見張りの役目」として扱う（対象外にした項目は無い）
- #430 と同時に進む場合は、先にマージしたほうに後のほうが合わせる（イシューの制約のとおり）。許可リストの整理はこのイシューが持つ

### 今の見張りの判定（develop 757828f0 の見張りに Bash の入力を流した結果。/grill-me の設計確認メモと同じ）
| コマンド | 今 | 望む |
|---|---|---|
| コンテナ内の引数なしの `export`・`declare`・`typeset` | 通る | 確認 |
| コンテナ内の `env -u X`・`env FOO=1`（コマンドを包まない env） | 通る | 確認 |
| コンテナ内の `env -0`・引数なしの `env` | 確認（`_cmd_external`） | 確認（変えない） |
| コンテナ内の `cp -t /app/x /tmp/y`・`cp --target-directory=/app/x /tmp/y`・`mv /app/x /tmp/y` | 通る | 確認 |
| コンテナ内・ホストの `psql -c "UPDATE users SET ..."`（WHERE なし）・`DELETE FROM users` | 停止（exit 2） | 停止（変えない・テストで固定） |
| WHERE ありの UPDATE | 通る | 通る |
| `pytest -k delete` | 通る（許可リスト） | 通る |

- 原因（1）: 環境変数の表示の判定が 2 か所にある。`_cmd_external`（ホストとコンテナ共通・`printenv` と「位置引数の無い env」）と、`_container_risky`（コンテナだけ・`ps` の BSD 形式の e・`len(toks) == 1` の env／set・`export`／`declare`／`typeset` の `-p`／`-x`）。どちらも「引数なしの export」と「値を取るオプション（`-u X`）・代入（`FOO=1`）つきの env」を見ない。見張りの読み解きは、コマンドを包む env（`env -u X python -V`）を外して中のコマンドにするので、読み解きの後に先頭に残った `env` は、どんな引数でも「環境変数の表示」である（スクラッチパッドの `toks.py` で確かめた: `env -u X python -V` → `['python', '-V']`、`env -u X` → `['env', '-u', 'X']`）
- 原因（2）: `_ctr_write_targets`（2403 行）は `cp`／`mv`／`install`／`ln`／`rsync` の最後の位置引数しか見ない。`-t <dir>`・`--target-directory=<dir>` の書き先と、`mv` の移動元（移動で消える）を見ない。一方、別ワークツリーへの書き込みの判定 `_bash_write_targets`（765 行）は `-t` を見ている（作りが 3 つに分かれている: `_bash_write_targets`・`_record_writes`・`_ctr_write_targets`）
- 3: `_sql_is_destructive`（1908 行）が psql の `-c` の SQL に当たっている。直しは不要で、テストで固定するだけ（既存の `test_i200_guard_narrowing.sh` の 02g2・02g3 は DELETE だけで、UPDATE は無い）

### 許可リスト（`_container_safe`・2520〜2630 行の 111 行）を消したら何が変わるか（スパイク）
見張りの写し（スクラッチパッドの `g_nosafe.py`。`_container_safe` の先頭で `return False`）で測った:
- `test_pretooluse_container_guard.sh`: 788 件のうち 12 件が 0→ASK。中身は 3 種類だけ: (a) 中身が見えて安全な Python に語がある（`dict.update`・`cache.delete`・`os.environ.setdefault`・パスワード再設定の確定 API。S47・P13・P16・P43・P44・P65・P77・P90）、(b) 読み取りの SQL の文字列に語がある（P29 `select 'drop'`）、(c) ローカル宛ての curl（P30・P54・P74）
- `test_i200_guard_narrowing.sh`: 75 件すべて変わらない
- `pytest -k delete`・`npx playwright test --grep delete`・`npx jest src/password`・`ruff check .../password_reset.py` は ASK になる（引数のテスト名・ファイル名の語）
- 過去の作業コマンド（`guard_corpus_diff.py --guard`・3701 件）: 新しく確認 18 件（0.49%）。うち許可リストが効いていたのは `pip show openai`・`pip index versions openai`・`curl localhost`・`manage.py shell` の中の `'password'`・`manage.py check --deploy` など
→ 全部を消すと、受け入れ条件の「`pytest -k delete` などが今までどおり通る」を満たせない。許可リストは「危ない語が引数に出やすいが、(A)〜(C) を起こさない形」だけに縮める（5-4）。残りの分岐（`redis-cli`・`celery`・`sed -n`・`find`・`sort`・`uniq`・`echo`／`printf`・`node`・`ps`・読み取りのコマンドの一覧 `_SAFE_READ_CMDS`・パイプの受け手の一覧 `_PIPE_FILTERS`・`migrate`・`makemigrations`）は、引数に語が出にくく、出たとき（例 `grep -rn token /app`・`redis-cli GET token:x`）は (C) に当たりうるので確認でよい

### 案の写しでのスパイク（5-1・5-2・5-4 を当てた写し `g_proto.py`。リポジトリのファイルは変えていない）
- 行数: 3856 → 3811（−45。計画レビューの指摘でパイプの受け手と ruff format の条件を戻した後）
- `test_pretooluse_container_guard.sh` pass=788 fail=0・`test_i200_guard_narrowing.sh` pass=75 fail=0・`test_pretooluse_guard_matrix.sh` pass=391 fail=0
- 上の表の「望む」がすべて成り立つ。`pytest -k delete`・`manage.py test ...test_delete`・`npx playwright test --grep delete`・`pip show openai`・`ruff check .../password_reset.py` は 0、`grep -rn token /app/apps` は ASK。ホストの `export`・`env -u X`・`set`・`declare -p`・`ps auxe` は ASK、`ps aux`・`set -euo pipefail`・`env FOO=1 python -V` は 0
- 過去の作業コマンド（3701 件）: 確認＋停止 135 → 140、新しく確認 5 件（0.14%・上限 1%＝37 件）、新しく停止 0 件。5 件の中身: `manage.py check --deploy` に `SECRET_KEY=$(python -c "import secrets…")` を渡す形（語 `secret`。確認でよい）・celery の `inspect` を含む長い 1 行が 3 件（許可リストから celery を外したため。同じ日の 1 回の作業）・ホストの `ps -eo etimes,pcpu,args`（`-o` の値の `etimes` の e を BSD 形式の e と誤った。今のコンテナの判定と同じ誤り）。最後の 1 件を受けて、`ps` の e は「最初の引数が英字だけで e を含む」（`ps e`・`ps auxe`・`ps axe -o pid`）に絞った（5-1）。絞った写しで既存の 3 つのテストと上のケースを流し直し、すべて同じ結果・`ps -eo etimes,…` は 0 になった。絞った後の過去の作業コマンドでの件数は TC-06 で測り直す（見込み 4 件）

### 見張りを直したら流すテストの 1 つが、ワークツリーで黙って SKIP になる
- `bash scripts/claude/tests/test_guard_corpus_diff.sh` はこのワークツリーで「SKIP: 作業記録が無い環境です（CI 等）」を出して exit 0 になった
- 原因: `guard_corpus_diff.py` の `_project_dir()` は作業記録のフォルダ名を「パスの `/` を `-` に」で作るが、Claude Code は英数字以外（`.` を含む）をすべて `-` にする。ワークツリー（`.claude/worktrees/<名前>`）では `.` が残るのでフォルダが見つからない（実物は `~/.claude/projects/-mnt-c-app-study-app-multitenant--claude-worktrees-harness-1`）。キャッシュの名前もワークツリーの名前（`harness-1.json`）になり、primary の記録を使わない
- ハーネスの作業はワークツリーで行う（`docs/runbooks/worktree.md`）ので、「見張りを直したら 3 つのテストを流す」の 1 つが実質効いていない。このイシューの確かめ（新しく確認になる件数）にも要るので同梱する（5-6）。計画時の測定は、primary のキャッシュを `~/.cache/claude-guard-corpus/harness-1.json` に写して行った

### 手順書の写し
- `danger-ops.md` 4.（29 行）は、書き込みの種類（「`cp`／`mv`／`install`／`ln`／`rsync` の書き先」）と環境変数の表示の形を言葉で列挙している。実物より広い約束（F11）で、見張りを変えるたびにずれる（F13）
- `danger-ops.md` 3.（28 行）の「引数なしの `env`」も、5-1 の後は実物と食い違う
- `danger-ops.md` 37 行の「rebase の前に commit・push しておけば」は、push の時点の決まり（`docs/runbooks/workflow.md`「GitHub への書き込みの時点」）と合わない（I224 の一覧 F8）
- `worktree.md` §9（244 行）は「読み取りの git の打ち切りは SIGTERM」と書くが、実物（`sessionstart_context.py` の `_run`）は読み取りをすぐ打ち切り（SIGKILL）、SIGTERM の後に待つのは fetch・merge だけ（I219 の一覧 F1）
- `worktree.md` §9（246 行）は別ワークツリーへの Bash の書き込みの形を列挙している（今は `_bash_write_targets` と一致）。写しを持たない形に直す

### 既存のテスト
- 計画時（2026-11-11・変更前）: `test_pretooluse_container_guard.sh` pass=788・`test_i200_guard_narrowing.sh` pass=75・`test_pretooluse_guard_matrix.sh` pass=391、すべて fail=0（上のスパイクの基準として同じ環境で流した）

### 環境前提
- `python3`・`bash`・`git` はホストにある（上のスパイクで使用）。docker は手動テスト M-01・M-02 で使うが、コンテナが無くても、存在しないサービス名で流すので判定は変わらない（下の手動テスト）

## 4. 変更点一覧
| ファイル | 関数・定数 | 変更 |
|---|---|---|
| `scripts/claude/hooks/pretooluse_guard.py` | `_cmd_external`（2255 行付近） | 5-1: 環境変数の表示の判定を 1 か所にまとめ、ホストとコンテナの両方に当てる |
| 同上 | `_container_risky`（2368 行） | 5-1: 環境変数の表示の判定を消す（`_cmd_external` に移す）・docstring を直す |
| 同上 | `_ctr_write_targets`（2403 行） | 5-2: `-t`・`--target-directory`・`mv` の移動元 |
| 同上 | `_container_safe`（2520 行）・`_SAFE_READ_CMDS`・`_PIPE_FILTERS`・`_SAFE_REDIS`（1277〜1282 行） | 5-4: 許可リストを縮め、使わなくなった定数を消す |
| `scripts/claude/tests/guard_corpus_diff.py` | `_project_dir`・`build_corpus`・`main` | 5-6: primary とすべてのワークツリーの作業記録を読む |
| `scripts/claude/tests/test_i444_guard_gaps.sh` | 新規 | 5-1〜5-4・5-6 の確かめ（失敗の注入つき）。→ TC-01〜TC-05 |
| `docs/runbooks/danger-ops.md` | 「見張りの扱い」の 3.・4.・「見張りが判定しないもの」 | 5-5 |
| `docs/runbooks/worktree.md` | §9 | 5-5 |
| `docs/reviews/backlog/I200.md`・`I219.md`・`I224.md` | 同梱した行 | 消す（行が無くなったファイルは消す） |

`test_pretooluse_container_guard.sh`・`test_i200_guard_narrowing.sh` は変えない（スパイクで全件そのまま通る。期待値の整理は不要だった）。

## 5. 実装手順

### 5-1. 環境変数の表示の判定を 1 か所にまとめる（1・(C)）
**方針**: 「環境変数をまとめて表示する形」の判定を `_cmd_external` の 1 か所に寄せ、ホストとコンテナの両方に当てる。ホストの環境（Claude Code を動かすシェル）にも鍵が入りうるので、ホストの `printenv` がすでに確認なのと同じ扱いにする。読み解きの後に先頭に残った `env` は、引数によらず表示（コマンドを包む env は読み解きで外れるため・調査結果）。

```python
    # 環境変数をまとめて表示する形（I444。ホストとコンテナで同じ）。env はコマンドを包むときは読み解きで外れるので、
    # 先頭に残った env は引数によらず表示（env -u X・env FOO=1・env -0）。ps は BSD 形式の e（最初の引数が英字だけ）
    if head in ("printenv", "env") or (head == "set" and len(toks) == 1) \
            or (head == "ps" and any(re.fullmatch(r"[A-Za-z]*e[A-Za-z]*", a) for a in toks[1:])) \
            or (head in ("export", "declare", "typeset")
                and (all(a.startswith("-") for a in toks[1:]) or any(a in ("-p", "-x", "-px", "-xp") for a in toks[1:]))):
        r.append("環境変数（秘密情報を含む）の表示")
```
`_container_risky` の同じ判定（2389〜2394 行）と、そのためだけの `head` の変数を消す。docstring の「許可リストに入らない」を「危ない語が当たっても通す形（`_container_safe`）に入らない」に直す。
→ TC-01

### 5-2. コンテナ内の書き先に `-t`・`--target-directory`・`mv` の移動元を入れる（2・(B)）
**方針**: 粗い判定にとどめる（I179 の教訓）。`-t` の値は既存の `_opt_values`（`-t X`・`-tX`・`-vt X`・`--target-directory=X` を読む）で取る。`mv` は移動元も消えるので、位置引数をすべて書き先として扱う。

```python
    if head in ("cp", "mv", "install", "ln", "rsync"):
        tdir = _opt_values(toks[1:], ("-t", "--target-directory")) if head != "rsync" else []   # rsync の -t は時刻を保つ
        if head == "mv":                       # 移動元も消える（I444）
            return tdir + pos
        return tdir or pos[-1:] if len(pos) >= 2 or tdir else []
```
`_bash_write_targets`（別ワークツリーへの書き込みの停止）と `_record_writes` は変えない（範囲の外・停止の判定を広げない）。
→ TC-02

### 5-3. psql の WHERE なしの UPDATE（3・(B)）
見張りは変えない。コンテナ内・ホストの両方で停止になることをテストで固定する。
→ TC-03

### 5-4. 許可リストを「危ない語が当たっても通す形」だけに縮める（4）
**方針**: 許可リストを消して語と書き込み先の判定に一本化する案は、`pytest -k delete` などテスト名・ファイル名・中身の見えるコードに語が出る普通の操作が確認になる（調査結果）。そこで、許可リストの役目を「引数に危ない語が出やすいが、(A)〜(C) を起こさない形」に限り、それ以外の分岐を消す。残す形と理由:
- テスト・lint・型検査（`pytest`・`flake8`・`bandit`・`pip-audit`・`mypy`・`eslint`・`tsc`・`jest`・`python -m pytest|flake8|mypy`・`npm test`・`npm run lint|test`・`npx tsc|eslint|jest`・e2e の `npx playwright test`・`ruff check`・`ruff format --check|--diff`）: 引数がテスト名・ファイル名。`--fix`・`--unsafe-fixes`・`--basetemp` があるときは外す（今と同じ）。`ruff format` は書き換えないとき（`--check`・`--diff`）だけ（今と同じ）
- パイプの受け手の読むだけの絞り込み（`_PIPE_FILTERS`: `grep`・`head`・`tail`・`wc`・`sort`・`cut`・`tr`・`jq`・`uniq`・`cat`。書き出す `sort -o`・`uniq IN OUT` は外す）: `sh -c "pytest -k delete | tail -20"` のように、パイプで受けると前のコマンドの語も見るため（今と同じ）
- 依存の情報（`pip freeze|list|show|check`・`pip index versions`・`npm ls|outdated|view`・`npm audit`〔`fix` なし〕）: 引数がパッケージ名（`openai` 等）
- 読み取りの `manage.py`（`_SAFE_MANAGE`）・中身が見えて危険のない Python（`_code_safe`）・読み取りの SQL（`psql`・`dbshell` の `_sql_is_safe_read`）・ローカル宛ての curl（今の分岐のまま）
- 前提の条件（読みきれない書き方・here-string・書き込み・ヒアドキュメント〔psql・python 以外〕のときは外す）は今のまま

消す分岐: `redis-cli`・`celery`・パイプで受けない `sed -n`・`find`・`sort`・`uniq`・`echo`／`printf`・`node --version`・`ps`・`_SAFE_READ_CMDS`・`migrate`・`makemigrations`・`pip --version`・`npm run build|typecheck`・`npm --version`。これらは語が無ければ今までどおり通る（`_container_risky` が何も返さないため）。語があるときだけ確認になる。使わなくなった定数 `_SAFE_READ_CMDS`・`_SAFE_REDIS` を消す（他で使っていないことを grep で確かめた）。`_PIPE_FILTERS` は残す。

```python
def _container_safe(c: dict) -> bool:
    """I444: 危ない語が当たっても通す docker compose exec|run の中の形（引数に語が出やすい、(A)〜(C) を起こさない操作）。
    テスト・lint・依存の情報・読み取りの manage.py・中身が見えて危険のない Python・読み取りの SQL・ローカル宛ての curl。
    これ以外は _container_risky（危ない語・/tmp/ 以外への書き込み）と _cmd_external（環境変数の表示など）だけで決まる。"""
    toks = c["toks"]
    if c["note"] or c["herestr"] is not None or c["writes"] or not toks:
        return False
    head, rest = os.path.basename(toks[0]), toks[1:]
    if c["piped"]:                             # パイプの受け手は読むだけの絞り込みだけ（pytest … | tail）
        return head in _PIPE_FILTERS and not (head == "sort" and any(a.startswith(("-o", "--output")) for a in rest)) \
            and not (head == "uniq" and len([a for a in rest if not a.startswith("-")]) > 1)
    dj = _django_sub(toks)
    if dj:
        if dj[0] == "dbshell":
            sql = _sql_of(c)
            return sql is not None and _sql_is_safe_read(sql)
        return _code_safe(c) if dj[0] == "shell" else dj[0] in _SAFE_MANAGE
    if c["heredoc"] is not None and head != "psql" and not _PYTHON_RE.match(head):
        return False
    fix = any(a.startswith(("--fix", "--unsafe-fixes", "--basetemp")) for a in rest)
    if head in ("pytest", "flake8", "bandit", "pip-audit", "mypy", "eslint", "tsc", "jest"):
        return not fix
    if head == "ruff":                         # format は書き換えないとき（--check・--diff）だけ
        return (rest[:1] == ["check"] and not fix) or (rest[:1] == ["format"] and ("--check" in rest or "--diff" in rest))
    if _PYTHON_RE.match(head):
        （今の -m の前のオプションを読み飛ばす部分と -m pytest|flake8|mypy・--version／-V はそのまま）
        return _code_safe(c)
    if head == "pip":
        return rest[:1] in (["freeze"], ["list"], ["show"], ["check"]) or rest[:2] == ["index", "versions"]
    if head == "npm":
        return rest[:1] in (["test"], ["ls"], ["outdated"], ["view"]) or rest[:2] in (["run", "lint"], ["run", "test"]) \
            or (rest[:1] == ["audit"] and "fix" not in rest)
    （npx・psql・curl の分岐は今のまま。npx の "--fix" not in rest は fix に置き換える）
    return False
```
`_analyze` の呼び出し（2668 行）は変えない。
→ TC-04

### 5-5. 手順書は分類と代表だけを書き、細かい列挙は見張りを正にする（5）
- `danger-ops.md`「見張りの扱い」の 3.: 「引数なしの `env`」を「環境変数をまとめて表示する形（代表: `printenv`・コマンドを包まない `env`・引数なしの `export`。ホストとコンテナで同じ。形の正は `_cmd_external`）」にする
- 同 4.: 次の形に書き直す（列挙をやめる）
  - 「危ない語が当たっても通す形」（テスト・lint・依存の情報・読み取りの `manage.py`・中身が見えて危険のない Python・読み取りの SQL・ローカル宛ての `curl`。形の正は `_container_safe`）は通す
  - それ以外は、危ない語があるか、コンテナの `/tmp/` 以外へ書き込む（リダイレクトと、ファイルを書く・移すコマンドの書き先と移動元。代表 `tee`・`sed -i`・`cp`・`mv`。`..` はそろえてから見る。形の正は `_ctr_write_targets`）ときだけ確認し、それ以外は通す。環境変数の表示は 3. のとおり
  - `docker compose cp`・素の `docker exec|run` の文は今のまま
- 同「見張りが判定しないもの」の「push していない手元の変更は rebase の前に commit・push しておけば `git reflog` と GitHub から戻せる」を「rebase の前に commit しておけば `git reflog` から戻せる（push 済みなら GitHub からも）」にする（I224 の一覧 F8）
- `worktree.md` §9 の「ロックを残さない（I219）」の打ち切りの文を、実物どおり「読み取りの git はロックを取らないのですぐ打ち切る。必須のロックを取る fetch・merge だけ、SIGTERM で打ち切って少し待ち（git が自分で `.lock` を片付ける）、それでも終わらなければ SIGKILL」にする（I219 の一覧 F1）
- `worktree.md` §9 の「技術強制済み（I095）」の Bash の書き込みの列挙を「Bash の書き込み（代表: リダイレクト・`tee`・`cp`／`mv` の書き先・`sed -i`。形の正は `_bash_write_targets`）」にする
→ M-04

### 5-6. corpus diff を primary とすべてのワークツリーの作業記録で動かす
**方針**: 作業記録のフォルダ名は Claude Code と同じく英数字以外を `-` にし、primary（`git rev-parse --path-format=absolute --git-common-dir` の親）のフォルダと、その下のワークツリー（`<primary のフォルダ名>--claude-worktrees-*`）を読む。キャッシュの名前も primary の名前にそろえ、どのワークツリーからでも同じ記録を使う。

```python
_COMMON = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                         capture_output=True, text=True, cwd=REPO or None).stdout.strip()
PRIMARY = os.path.dirname(_COMMON) if _COMMON else REPO


def _project_dirs(primary: str = PRIMARY) -> list:
    """primary とそのワークツリーの作業記録のフォルダ（Claude Code は英数字以外を - にした名前で置く）。"""
    base = os.path.expanduser("~/.claude/projects/" + re.sub(r"[^A-Za-z0-9]", "-", primary))
    return [d for d in [base] + sorted(glob.glob(base + "--claude-worktrees-*")) if os.path.isdir(d)]
```
`REPO` は今と同じ（呼び出したフォルダの `git rev-parse --show-toplevel`。`test_guard_corpus_diff.sh` はリポジトリの中から呼ぶ）。`_COMMON` も `REPO` のフォルダで求め、git が失敗して空なら `PRIMARY = REPO` に落とす（今の動きと同じ名前で探し、見つからなければ今までどおり SKIP）。作業記録のフォルダが 1 つも無い環境（CI）は `_project_dirs()` が空になり、今までどおり「SKIP: 作業記録が無い環境です」で exit 0（TC-05b）。`build_corpus` は `_project_dirs()` の各フォルダを読む。`main` の「作業記録が無い環境」の判定は `not _project_dirs()`、キャッシュの名前は `os.path.basename(PRIMARY)`。`base_rev` と判定の部分は変えない。
→ TC-05

### ステップの順と依存
1. 5-6（corpus diff。後の確かめに使うので先に）→ TC-05
2. 5-1・5-2（独立・どちらが先でもよい）→ TC-01・TC-02、5-3 → TC-03
3. 5-4（5-1 の後。`ps` の e の判定を `_cmd_external` に移してから許可リストの `ps` を消す）→ TC-04
4. 行数と 3 つのテスト（TC-06）、5-5 の手順書（M-04）、一覧の行を消す

## 6. テスト計画
- 自動: `docs/tests/open/I444_auto_test.md`。新しい `scripts/claude/tests/test_i444_guard_gaps.sh` が見張りに JSON を渡して判定だけを見る（コマンドは実行しない）。失敗の注入は見張りの写しを一部書き換えて行う（`test_i200_guard_narrowing.sh` と同じ方法）。テストのレベルは見張りの単体（判定関数を通した入出力）だけ。アプリのテスト（pytest・Jest・E2E）は変更が無いので CI に任せる
- 手動（Claude）: `docs/tests/open/I444_manual_test.md`。`check-permission-prompt.sh` で、承認の仕組み全体（settings.json の allow と見張り）での出方を確かめる。手順書と見張りの突き合わせ

| 受け入れ条件 | 確かめ |
|---|---|
| 1〜5 の「見張りの役目か」の判定と根拠 | 調査結果「0. 対象の確かめ」（計画レビュー） |
| `export`・`declare`・`typeset`（引数なし）・`env -0`・`env -u X` が確認 | TC-01・M-02 |
| `cp -t`・`--target-directory=`・`mv` の移動元が確認 | TC-02・M-02 |
| psql の WHERE なしの UPDATE が停止（コンテナ内・ホスト） | TC-03 |
| 許可リストの扱いが計画どおり・I200 の普通の操作が確認なしで通る | TC-04・M-01 |
| `danger-ops.md` 4.・`worktree.md` §9 が実物と食い違わない | M-04 |
| 見張りの行数が増えていない | M-03 |
| 既存のハーネステスト・CI が pass | TC-06・CI |

## 7. ロールバック
PR を revert する（見張り・テスト・手順書・corpus diff だけ。データの変更なし）。見張りが起動できなくなったときは、ユーザーが端末で `! git restore scripts/claude/hooks/pretooluse_guard.py`（`danger-ops.md` の「見張りが失敗したとき」）。

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| 許可リストを縮めて、普通の操作に確認が増える | 残す形は過去の作業コマンドで語が当たったものから選んだ（調査結果）。corpus diff で新しく確認になる件数を測り、1% 以内（TC-06）。増えた形は計画変更記録に書く |
| 許可リストを縮めて、(A)〜(C) の操作が通るようになる | 縮めると「通す」が減るだけで、増える方向の変更は無い（許可リストは確認を外す側の仕組み）。5-4 で `--fix` などの外す条件は今のまま残す |
| ホストの `export`・`set`・`declare -p`・`ps e` が新しく確認になり、普通の作業が止まる | どれも環境変数を表示する形で (C) に当たる。ホストで普通に使う `set -euo pipefail`・`export FOO=1`・`ps aux`・`env FOO=1 cmd` は通る（スパイク・TC-01 の対照）。corpus diff で件数を見る |
| `mv` の位置引数をすべて書き先にして、`/tmp/` の中の移動まで確認になる | `/tmp/` の中どうし（`mv /tmp/a /tmp/b`）は通る（TC-02 の対照） |
| 読み解きの例外で見張りが止まる | 変えるのは判定の関数だけで読み解きは変えない。matrix・oracle・corpus diff（異常終了は 1 件でも不合格）を流す（TC-06） |
| corpus diff の直しで、別のリポジトリの記録を読む | フォルダ名は primary の絶対パスから作り、`--claude-worktrees-` の下だけを足す |

## 9. 確定事項と自律判断
### イシューに明記されていること
- 1〜5 の範囲・脅威モデルは「事故」・粗い判定にとどめる・精密な判定は作り込まない（I200 の決定）
- 受け入れ条件の各項目（psql は停止・I200 の普通の操作は通る・行数を差し引きで増やさない）
- 設計確認メモ（2026-11-11）: #430 は OPEN・3 は確かめ済みでテストで固定だけ・4 は計画で決める・F5・F7・F8 は計画で決める

### Claude が技術的に決めたこと
- 0: #430 は終わっていないので、1〜5 はすべて見張りの役目として扱う（docker のコンテナの中はサンドボックスの外・調査結果）
- 4: 許可リストは消さずに縮める（全部消すと `pytest -k delete` が確認になり受け入れ条件を満たせない・調査結果のスパイク）。残す形は「引数に危ない語が出やすいが (A)〜(C) を起こさない」もの
- 1: 環境変数の表示の判定はホストとコンテナで 1 か所にまとめ、ホストにも当てる（ホストの `printenv` がすでに確認であることとそろえる・`ps` の e の判定の重複を消す）。イシューの受け入れ条件はコンテナだけだが、ホストにも当てる方が (C) の基準と一致する
- 2: 書き先の直しはコンテナの判定（`_ctr_write_targets`）だけ。別ワークツリーの停止（`_bash_write_targets`）は広げない（範囲の外）
- テストは新しいファイル `test_i444_guard_gaps.sh` に置く（イシューの実装対象は既存の 2 つのテストの直しを挙げていたが、スパイクで既存の期待値は 1 件も変わらないと分かったため、変えない）
- 5-6: corpus diff の直しを同梱する（見張りを直したら流すテストがワークツリーで黙って SKIP になり、このイシューの確かめにも要る。決定論テストは「気づきにくく被害が大きい」に当たる: SKIP は exit 0 で気づけない）
- 行数: スパイクで −45 行（受け入れ条件を満たす見込み）。テストのファイルは数えない（受け入れ条件は見張りの行数）
- 一覧 `docs/reviews/backlog/I200.md` F5: 残す — 語の後ろにも切れ目を求めると `secrets`・`deleted`・`tokens` のような語形を取りこぼし、(C) を弱める。粗い判定にとどめる方針（I200）に反する。過去の作業コマンドの「新しく確認」にも、この形（識別子の一部に当たる）は出ていない
- 一覧 `docs/reviews/backlog/I200.md` F9: 同梱 — 5-2 で直す
- 一覧 `docs/reviews/backlog/I200.md` F11: 同梱 — 5-2 で実物を手順書に合わせ、5-5 で手順書を代表と正の場所だけにする
- 一覧 `docs/reviews/backlog/I200.md` F13: 同梱 — 5-5（写しを持たない形にする。手順書の中身を確かめるテストは足さない〔写しのテストになるため・plan-writing-rules.md「決定論テストの対象の選び方」〕）
- 一覧 `docs/reviews/backlog/I200.md` F7（`check-permission-prompt.sh`）: 残す — 見張りの外のファイル。確かめの道具の中だけの話で、このイシューの範囲と失敗の影響が違う
- 台帳 `docs/reviews/closed/I200_code_review_20261030_0008.md` の F8（`sessionstart_context.py` の時間の見積もり）: 対応不要 — I219 で時間の見積もりの仕組みを作り直し、一覧から消えている（I219 の計画書の自律判断）
- 一覧 `docs/reviews/backlog/I219.md` F1: 同梱 — 5-5 で `worktree.md` §9 を直す（このイシューで §9 を触るため）
- 一覧 `docs/reviews/backlog/I224.md` F8: 同梱 — 5-5 で `danger-ops.md` の該当の文を直す（このイシューで同じ節を触るため）
- 一覧 `docs/reviews/backlog/I224.md` F9・`docs/reviews/backlog/I223.md` B1〜B4（`FILE=-`）: 残す — このイシューの範囲と関係が無い（受け入れ条件の実測・bot の停止中の作業）

### チェック
- 要件適合性: 受け入れ条件の範囲内。ホストへの環境変数の表示の確認（5-1）と corpus diff の直し（5-6）は範囲を少し広げるが、どちらも確認を出す基準（(C)）と見張りを直したときの決まりに沿うもの。マルチテナント・ステータス遷移は該当なし
- セキュリティ: 秘密情報（環境変数）の表示と、手元のファイルの上書きが確認になる方向の変更。許可リストを縮めるのは確認を外す範囲を狭めるだけ。入力の検証・認証・OWASP・依存の追加は該当なし（ハーネスの Python の標準ライブラリだけ）。bandit・npm audit の対象外（`scripts/` は bandit の対象外・依存の変更なし）
- テスト計画: 再発防止のテスト（TC-01〜TC-03・失敗の注入つき）あり。テストのレベルは見張りの単体と、承認の仕組み全体（M-01・M-02）
- P3/P5/P8 影響なし（DB・外部 API・非同期・新しいインフラ・依存の変更なし）
- P6 影響なし（UI・データ量の懸念なし）
- P9 影響なし（個人情報・テナントデータを扱わない。corpus diff の作業記録はリポジトリの外〔本人だけが読める権限〕のまま）
- 設計品質: 判定の重複（環境変数の表示・`ps` の e・許可リストと語の判定）を減らす方向。定数は見張りの中の名前つきの定数のまま
- 高リスクの見込み: 見張り（`path_risk_trigger` の集合）を変えるので高リスク。計画レビューの判定に従う
- 要件・基本設計・UI/UX の価値判断で仮定したものは無い（確認を出す基準〔(A)〜(C)〕は I200 で決まっていて、それに沿って当てはめただけ）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | (C) コンテナ内・ホストの、環境変数をまとめて表示する形（引数なしの `export`・`declare`・`typeset`・`set`、コマンドを包まない `env`、`ps` の e）が確認になり、`set -euo pipefail`・`export FOO=1`・`env FOO=1 cmd`・`ps aux`・`ps -eo etimes,args` は通る（TC-01・FG-01） |
| V2 | 1 | 読んで可 | (B) コンテナ内の `/tmp/` 以外への書き込み（`-t`・`--target-directory=`・`mv` の移動元）が確認になり、`/tmp/` の中どうしは通る（TC-02・FG-02） |
| V3 | 2 | 読んで可 | (B) 許可リストを縮めた後も、停止（2）の判定は 1 件も通る側に変わらない（既存の 2 つのテストの期待値を変えない・matrix・corpus diff の「新しく停止」と「停止→通る」） |
| V4 | 3 | 読んで可 | 普通の操作: I200 の普通の操作（`test_i200_guard_narrowing.sh` の TC-01）と `pytest -k delete` などが通る（TC-04・M-01） |
| V5 | 3 | 読んで可 | 手順書: `danger-ops.md` 3.・4. と `worktree.md` §9 が、見張りの実物（`_cmd_external`・`_container_safe`・`_ctr_write_targets`・`_bash_write_targets`）と `sessionstart_context.py` の `_run` に食い違わない（M-04） |

## 計画変更記録
- 1（plan-review・2026-11-11・計画レビュー 1 は BLOCKER 1・Warning 4・Info 2）: 「必ず確かめる項目」の観点を 1〜3 の番号にした（Blocker）／許可リストのパイプの受け手（`_PIPE_FILTERS`）を残した（`sh -c "pytest -k delete | tail -20"` が確認になるため。`-o`・`--output` は外す）／`ruff` は `check` と `format --check|--diff` だけにした（今と同じ）／TC-01 に包む env の対照（`env -u X python -V` → 0）・TC-04 にパイプの対照・TC-05 に作業記録が無い環境の SKIP を足した／5-6 の git の呼び出しの場所と失敗時の落ち先を書いた／M-03 をパイプなしの 1 コマンド（`git diff --numstat`）にした。写しで流し直し、既存の 3 つのテストは全件そのまま・行数は 3811（−45）。計画レビューのやり直し: 要（Blocker のため）
- 2（plan-review・2026-11-11・計画レビュー 2 は HIGHRISK・Warning 3・Info 2）: 5-2 で `rsync` は `-t` を書き先として読まない（`rsync -t` は時刻を保つオプションで値を取らないため、`rsync -avt /tmp/a /app/b` の書き先を見落とす）。TC-02 に `mv -t`・`install -t`・`rsync -avt` を足した／M-03 は出力の数値を実結果に書いて比べる形にした／5-4 の擬似コードの「今のまま」の部分は、実装時に今のコード（2551〜2575 行の python・npx・psql・curl の分岐）をそのまま移し、ヒアドキュメントの条件は `redis-cli` を外して `psql` と python だけにする（TC-04 と既存のテストの全件一致で確かめる）。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）
- 3（implement・/simplify の 4 観点の指摘）: (a) パイプの受け手の書き出しの除外を今と同じ `sort -o`・`uniq IN OUT` だけに戻した（全部の受け手に `-o` を当てると `grep -o` が確認になる・TC-04 04o）／(b) `ps` の e は「- の無い英字だけの引数のどれか」にした（`toks[1]` だけだと旧コンテナの判定より狭く `ps aux e` が通る・TC-01 01t。`ps -eo etimes,pcpu,args` はカンマを含むので今までどおり通る）／(c) `_ctr_write_targets` の式を 2 行に分けた・古いコメント 3 か所を「危ない語が当たっても通す形」にそろえた・corpus diff の git の呼び出しを 1 回にまとめた・FG-04 の置き換えを 1 行にした。見送り: 書き先の抽出 3 つ（`_bash_write_targets`・`_record_writes`・`_ctr_write_targets`）の共通化と、「通す形なら書き込みの判定ごと飛ばす」構造（例 `pytest --junitxml=/app/r.xml` が通る・今もそう）は、止める範囲を広げる・範囲を越えるので retro で扱う／テストの python の起動回数・`_env_dump` への切り出しは、既存のテストの形とそろえるため見送り。計画レビューのやり直し: 不要（(a)(b) は今の動きに合わせる側の直しで、方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261111_1824 判定: ✅ 完了](../../reviews/I444_plan_review_20261111_1824.md)
- [20261111_1819 判定: 差し戻し（Blocker 1件）](../../reviews/I444_plan_review_20261111_1819.md)

## セキュリティレビュー結果

**実施日**: 2026-11-11

アプリ（backend・frontend）のコード変更なし。対象はハーネスの見張り（`pretooluse_guard.py`）・corpus diff・手順書。認証・認可・マルチテナント・入力検証（HTTP）・OWASP のアプリ側・ファイルのアップロード・依存の追加は該当なし。見張りの脅威モデルは「事故」（意図的な回避は対象外・`danger-ops.md`）。

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | 機密情報 | 許可リストを縮める（5-4）ときに、残す形の条件を書き写し損ねると、確認を外す範囲が今より広がる（例: `ruff format` の書き換え・パイプの受け手の `-o`・`npx` の `--fix`） | 必須: 残す分岐は今のコードの条件をそのまま移す（計画変更記録 1・2）。既存の 2 つのテストの期待値を 1 件も変えない（V3）。許可リストは確認を外す側だけの仕組みで、停止（2）の判定は `_cmd_danger` が先に行う（`_analyze` の `not d and not e` は変えない） |
| Medium | 機密情報 | 環境変数の表示の判定を `_container_risky` から `_cmd_external` に移す（5-1）ときに、どちらにも無い形が出る（移し損ね） | 必須: 移す前の形（`ps` の BSD 形式の e・引数なしの env／set・`export`／`declare`／`typeset` の `-p`／`-x`）をすべて新しい判定が含む（TC-01 の 01a〜01l・既存の FG-01o・FG-01p） |
| Low | 機密情報 | corpus diff（5-6）が primary とすべてのワークツリーの作業記録を読み、キャッシュに入れる。作業のコマンドには秘密が含まれうる | 必須: キャッシュは今のまま `~/.cache/claude-guard-corpus/`（0700）・ファイルは 0600 で作り、リポジトリに入れない。読むのは primary の絶対パスから作ったフォルダとその `--claude-worktrees-` の下だけ（別のリポジトリの記録を読まない・TC-05a の `-x-app-yz`） |
| Low | セキュリティ設定ミス | 見張りの判定の関数を変えて、例外や異常終了で見張りが素通しになる | 必須: 読み解きは変えない。matrix・oracle・corpus diff（異常終了は 1 件でも不合格）を流す（TC-06）。例外時は既存の `_fail_safe`（危ない語があれば確認） |
| Low | 外部通信 | なし（外部への送信の判定〔`_cmd_external` の送信系〕は変えない） | — |
| Low | 依存ライブラリ | なし（標準ライブラリだけ） | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | Bash（コンテナ内） | Claude（auto mode） | `docker compose exec backend export`・`env -u X` などで backend/.env の鍵を作業記録に表示する（事故） | 確認になる | Yes: TC-01 | Yes: M-02 | 意図的な回避（`sh -c "$(echo ZXhwb3J0 \| base64 -d)"` 等）は対象外 | Medium |
| 2 | Bash（ホスト） | Claude | ホストの `export`・`declare -p`・`set`・`ps e` で Claude Code のシェルの環境（鍵を含みうる）を表示する | 確認になる | Yes: TC-01 01h〜01l | Yes: M-02（`ps e -p 999999`） | 同上 | Low |
| 3 | Bash（コンテナ内） | Claude | `cp -t /app/…`・`mv /app/x /tmp/y` で手元のファイル（bind mount）を上書き・移動して消す | 確認になる | Yes: TC-02 | Yes: M-02 | 書き方の網羅は粗い（`install -D` 等の珍しい形は対象外・I179 の教訓） | Low |
| 4 | Bash（コンテナ内・ホスト） | Claude | `psql -c "UPDATE users SET …"`（WHERE なし）で dev DB を大量更新する | 停止になる | Yes: TC-03 | No | SQL を変数・ファイル経由で渡す形は既存のとおり（`psql -f` は停止） | Low |
| 5 | Bash（コンテナ内） | Claude | 許可リストに残した形（テスト・lint・依存の情報・読み取りの SQL・ローカル宛ての curl）に危ない操作を紛れ込ませる（例 `pytest --basetemp=/app`・`ruff format`・`… \| sort -o /app/x`） | 書き換える・外へ送る形は許可リストから外れ、語の判定・書き込み先の判定にかかる | Yes: TC-04 04l・04n・既存の container_guard | No | 許可リストの形の引数にコードを渡す意図的な形は対象外 | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 2件 | 1件 |
| Low     | 4件 | 4件 |

### 残余リスク処遇
（retro 段階で決定する）
