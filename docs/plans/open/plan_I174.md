# I174 計画書: 確認が必要な操作の見直し（docker compose exec 等の一律確認をやめ、コンテナ内の危険操作だけを見張りで止める）

## 基本情報
- **計画書ID**: plan_I174
- **関連イシュー**: #292
- **Draft PR**: #293
- **作成根拠資料**: docs/issues/open/I174.md（起点イシュー・設計確認メモ 7 回分を含む）
- **実装後評価**: docs/reviews/open/I174_review.md
- **作成日**: 2026-10-16
- **ブランチ**: `feature/I174-guard-based-permission-review`（`origin/develop` から分岐）
- **作業場所**: primary checkout（`/mnt/c/app/study-app-multitenant`）。track:harness だが、wt-harness は I146 で使用中のため例外（2026-10-16 ユーザー決定）
- **マージ順の制約**: I146（#260）のマージ後にマージする（ステップ 6）
- **テストの件数の正本**: `docs/tests/open/I174_auto_test.md` の「TC 一覧」と「実施記録」（本書の各節に書いた件数は、その時点の値）

## 0. 設計変更（2026-10-16・敵対的レビュー第 1 周の後・ユーザー決定）

敵対的レビュー第 1 周（`docs/reviews/I174_adversarial_review_20261016_1745.md`）で Critical 1・High 約 10 が出た。原因は「危険なものを列挙して止める（列挙外は素通し）」方式そのもので、ask を外した結果、列挙の漏れがそのまま確認なしで通る。ユーザーの決定で、**コンテナ内の操作は「安全と確かめられたものだけ通し、それ以外は人の確認」（許可リスト方式・fail-safe）**に切り替える。本節は 4-2 の (3)(5)(6) を置き換え、(1)(2)(4) を補強する。

### 0-1. 判定の全体像（優先順）
1. **常に止める（exit 2・解除不可）**: ルートの `rm -rf`・mkfs・dd・shred・別 worktree への書き込み（既存どおり）
2. **危険操作（exit 2・DANGER_OK=1 で ask）**: ホスト・コンテナの両方に当てる列挙（下の 0-3）
3. **外部送信・秘密情報（ask）**: ホスト・コンテナの両方に当てる列挙（0-4）
4. **コンテナ内で安全と確認できない操作（ask）**: `docker compose exec|run` / `docker-compose exec|run` の中のコマンドが、0-5 の許可リストに入らなければ ask（素の `docker exec|run` は 2.・3. の列挙だけ。0-9 で変更）。**流し込み（パイプで受ける・`<<<`）・読めない書き方も ask**
5. それ以外のホストの操作は素通し（auto mode の判断が第 2 層）

### 0-2. コマンドの読み取り（作り直し）
- `shlex.shlex(posix=True, punctuation_chars=";&|()<>\n")` でトークン化し、`;` `&&` `||` `|` `&` `(` `)` 改行を区切りとして扱う（語にくっついた `x;rm`・`(rm` も分割する。第 1 周 #2）。`|` の直後のコマンドには「パイプで受ける」印を付ける。
- `$(...)` と `` `...` `` の中身は、取り出して別のコマンドとして判定する（第 1 周 #2）。
- ヒアドキュメント（`<<WORD` 〜 `WORD` の行）は本文を取り出し、受け手のコマンドに付ける。受け手が `manage.py shell` / `python` なら本文を Python コード、`psql` / `dbshell` なら SQL、`sh` / `bash` ならシェルとして判定する。それ以外（`cat > f` など）の本文はデータとして判定しない（`rm -rf` 等の誤反応を防ぐ）。
- リダイレクト（`2>&1`・`>f`・`>>f`・`<f`）は引数から除く。`<f` は「標準入力のファイル」として受け手に付ける（中身の判定は 0-6）。
- 包むコマンドを外して中を判定する: `sh` / `bash` / `dash` / `zsh` の `-c`（`-lc`・`-ec`・`-xc` などのまとめ書きを含む。第 1 周 #4）・`eval`・`time`・`nice [-n N]`・`nohup`・`timeout [opts] N`・`env [VAR=..] cmd`・`xargs`。先頭の `VAR=val` も外す。
- 同じコマンド文字列の読み取り結果は 1 回の実行の中で使い回す（第 1 周 #16 の性能）。

### 0-3. 危険操作の列挙（追加分。既存の列挙もトークン単位に直す）
| 対象 | 危険とする条件 |
|---|---|
| `manage.py` / `django-admin` / `python -m django`（第 1 周 #3） | `flush` / `sqlflush` / `reset_db` / `loaddata`・`migrate` の位置引数 2 つ以上・`seed_e2e --flush`（第 1 周 #6）・`dbshell` に破壊的 SQL か流し込み |
| `git`（`-C <path>`・`-c k=v`・`--no-pager` などの前置オプションを読み飛ばす。第 1 周 #5） | `reset --hard`・`clean` に `-f` と（`-d` または `-x`）・`push` の既存判定 |
| `docker compose` / `docker-compose`（`-f`・`-p`・`--project-name` などを読み飛ばす） | `down` に `-v` / `--volumes`（まとめ書き含む）・`rm` に `-v` |
| `docker volume rm|prune`・`docker system prune --volumes`（第 1 周 #11） | 常に |
| `psql`（`-c"..."` の付着形・`--command=` を含む。第 1 周 #12） | 破壊的 SQL・`-f`・`<f`・ヒアドキュメント本文が破壊的 SQL |
| `pg_restore`（`-cd` のようなまとめ書き） | `-c` / `--clean` |
| `redis-cli` | `FLUSHALL` / `FLUSHDB`（引数・ヒアドキュメント本文） |
| `find` | `-delete` |
| Python コード（`manage.py shell -c`・`python -c`・ヒアドキュメント本文・実行ファイル） | 既存の `_CODE_DANGER`＋変数経由の一括更新 `\.update\(` を QuerySet 変数（`qs`・`*_qs`・`queryset`）にも当てる |
| 破壊的 SQL の判定 | SQL の文字列リテラル（`'...'`）の中身は判定から外す（第 1 周 #16 の `select 'drop'`）。Python コードでは、文字列リテラルが SQL の動詞で始まるときだけ SQL として判定する |

### 0-4. 外部送信・秘密情報（ask）
- 外部送信: 既存の `_CODE_EXTERNAL` に、`django.core.mail` の import（別名 import を含む）・`.email_user(`・`send_verification_email`・`PasswordResetForm`・celery タスク関数の直接実行（`\w+_task\(`）を加える。`manage.py sendtestemail` も対象（第 1 周 #12）。
- 秘密情報（第 1 周 #7）: `cat` / `less` / `more` / `head` / `tail` / `grep` / `sed` / `awk` / `strings` / `cp` / `base64` の引数に `.env`・`.env.*`（`*.example` を除く）・`*.pem`・`*.key`・`secrets/` があるとき、`printenv`・引数なしの `env`・`docker compose config`・`docker inspect` は ask。
- `.claude/settings.json` の deny の `Read(./.env)`・`Read(./.env.*)`・`Edit(./.env)`・`Edit(./.env.*)` を、`Read(**/.env)`・`Read(**/.env.*)`・`Edit(**/.env)`・`Edit(**/.env.*)` に置き換える（`backend/.env`・`e2e/.env.e2e` を守る）。`*.example` と `frontend/.env.development` / `.env.production`（追跡済み・秘密を含まない）も読めなくなるが、秘密情報を守るほうを優先する。

### 0-5. コンテナ内の許可リスト（ここに入るものだけ確認なしで通す）
（表は 0-9 の変更〔`diffsettings`・`dumpdata`・`collectstatic` を外す〕を反映済み。一覧の正本は `pretooluse_guard.py` の定数）
| 種類 | 通す形 |
|---|---|
| テスト・lint・監査 | `pytest`・`python -m pytest`（`python -W ... -m pytest` を含む）・`ruff check|format --check`・`flake8`・`python -m flake8`・`bandit`・`pip-audit`・`mypy`・`npm test|audit|ls|outdated`・`npm run lint|typecheck|build|test`・`npx tsc|eslint|jest` |
| 依存の確認 | `pip freeze|list|show|check`・`pip index versions`・`npm view` |
| manage.py（`django-admin`・`python -m django` も同じ） | `test`・`check`・`showmigrations`・`sqlmigrate`・`help`・`version`・`makemigrations --check` / `--dry-run`・`migrate`（位置引数 1 つまで）・`shell`（コードが全部見えて〔`-c`・`--command`・ヒアドキュメント・`<` の読めるファイル〕、危険操作・外部送信が無いとき） |
| `python -c` | コードに危険操作・外部送信が無いとき |
| `python <ファイル>.py` | ファイルを読めて、中身に危険操作・外部送信が無いとき |
| psql・dbshell | SQL の全文が `SELECT` / `SHOW` / `EXPLAIN`（`ANALYZE` なし）/ `CREATE DATABASE` / `\d*` / `\l` / `\dt` で始まるとき（`\!`・`\copy`・`\i` は除く） |
| redis-cli | `PING`・`INFO`・`KEYS`・`GET`・`TTL`・`PTTL`・`EXISTS`・`DBSIZE`・`SCAN`・`--scan`・`TYPE`・`HGETALL`・`LRANGE`・`SMEMBERS` |
| celery | `inspect`・`status`・`report` |
| 読み取り | `ls`・`pwd`・`cat`・`head`・`tail`・`grep`・`wc`・`sed -n`・`which`・`whoami`・`id`・`find`（`-delete`・`-exec` なし）・`python|node|pip|npm --version`（秘密情報の引数は 0-4 で ask） |
| 疎通確認 | `curl` の宛先が `localhost` / `127.0.0.1` / `backend` のとき |
| `sh` / `bash -c` | 中の全コマンドが許可リストに入るとき |
| `sh` / `bash <ファイル>` | ファイルを読めて、中の全コマンドが許可リストに入るとき（第 1 周 #10） |

上の表に無いもの（例: `seed_e2e`・`createsuperuser`・`pip install`・`npm install`・`dbshell` の対話・独自の管理コマンド・パイプで受けるコマンド）は ask。

### 0-6. テストの直し（第 1 周 #8〜#10・#14・#15）
- shell の判定と `python -c` の判定を別々に確かめる（`./manage.py shell -c ...`・`shell --command=...`・`python3 -c ...` を単独のケースにする）。
- `DANGER_OK=1 rm -rf /*` のケースを足す。
- コンテナ内 `sh <スクリプト>` のケースを足す。
- パターンごとのケースを足す（`apply_async`・`mail_admins`・`EmailMessage`・`openai.`・`call_command('migrate', ..., 'zero')`・`reset_db`・`ALTER TABLE`・`eval` 展開・`--command=`・`-R`・`2>&1` を位置引数に数えない・`FOO=1` 前置）。
- `.claude/settings.json` の ask・allow・deny の中身を JSON として確かめるテスト `scripts/claude/tests/test_settings_permissions.sh` を新規に作る（「残す 7 行」が ask にあり allow に無いこと。第 1 周 #14）。

### 0-7. 受け入れ条件の追加・変更
- AC-4 を補強: 第 1 周の再現コマンド（ヒアドキュメント・パイプ・付着記号・`$(...)`・`django-admin`・`python -m django`・`bash -lc`・`git -C`・`compose -f`・`seed_e2e --flush`・`docker volume rm`・`git clean -fdx`）を exit 2 または ask にする
- AC-13（新規）: `docker compose exec|run` の中の操作は、0-5・0-9・0-10 の許可リストに入るものだけが素通しで、それ以外は ask（素の `docker exec|run` は列挙だけ）
- AC-14（新規）: 秘密情報の読み出し・表示は ask。settings.json の deny が `backend/.env` に効く
- AC-9 は維持（許可リストの操作は止めず、ask も出さない）

### 0-8. danger-ops.md の直し（第 1 周 #13）
「どれで実行しても止める」を、実際に見張りが判定する範囲（0-3〜0-5）に合わせて書き直し、判定しないもの（secrets の Edit 以外の操作のうち列挙外・`docker compose cp` 後の実行など）を明記する。

### 0-9. 第 2 周の後の方針（2026-10-16・ユーザー決定）
敵対的レビュー第 2 周（`docs/reviews/I174_adversarial_review_20261016_1930.md`）で、①素の `docker exec|run` まで許可リストの対象にしたため、もともと確認の無かった操作に確認が増え、docker 全体の承認待ちは 17% しか減っていない ②許可リストを「コマンド名」で通していて書き込み・実行・外部送信のオプションを見ていない、と分かった。ユーザーの決定で次のとおりにする。
- **許可リストを当てるのは `docker compose exec|run` と `docker-compose exec|run` だけ**。素の `docker exec|run`・`docker container exec|run` は、I174 の前と同じく列挙（危険操作・外部送信・秘密情報）だけで判定する（中のコマンドは展開して列挙を当てる）。
- **脅威モデルは「事故」**（Claude が普段書くコマンドでの事故を防ぐ。意図的な回避は対象外。既存の I083 の方針と同じ）。ただし、直すのが簡単な回避は塞ぐ。
- 許可リストは「名前」でなく「書き込み・実行・外部送信につながるオプションが無いこと」まで確かめて通す。判断できないオプションは確認に回す（compose の中だけ）。
  - 外す: `diffsettings`（秘密を表示）・`dumpdata`（セッション・トークン）・`collectstatic`（書き込み）
  - 絞る: `curl`（宛先がすべて localhost の URL で、データ送信・アップロード・プロキシ・宛先の付け替え・ファイル出力・未知のオプションが無いとき）・`sed -n`（行番号か `/正規表現/p` の表示だけ）・`sort`（`-o` なし）・`uniq`（出力ファイルなし）・`find`（`-exec` 系・`-delete`・`-fprint` 系なし）・`ruff`（`--fix` なし）・`npm audit`（`fix` なし）・`celery`（サブコマンドの位置で `inspect|status|report`）・psql の読み取り（行の途中を含むすべてのメタコマンドが安全な一覧に入る・`EXPLAIN (ANALYZE)` / `ANALYSE` なし・`lo_export` 等の関数なし・`-o` / `-L` なし・`WITH` は書き込みの語が無いときだけ）・`echo` / `printf`（`$` を含まないとき）
  - 出力リダイレクト（`>` / `>>`、行き先が `/dev/null` 以外）があるものは素通しにしない
  - パイプで受けてよいのは読み取りのフィルタ（`grep`・`head`・`tail`・`wc`・`sort`・`cut`・`tr`・`jq`・`uniq`）だけ
  - 追加: `cd`（`sh -c "cd /app && ..."`）・`psql -tAc` のまとめ書き・`WITH ... SELECT`・既定コマンドで動かす `docker compose run e2e`（`/test` の E2E）
  - compose の exec / run の未知のオプション・`--entrypoint` は確認に回す
- 直す不具合: `sudo` / `nice` の展開（スライスの誤り）・`xargs rm -rf`（対象なし）と `find -exec rm -rf`・`docker container exec|run`・`-c` の複数指定・`$(...)` の中のヒアドキュメントの IndexError・包むコマンドの追加（`setsid`・`stdbuf`・`ionice`・`busybox`・`flock`・`su -c`・`script -c`・`watch`・`time -p`・`nohup --`・`command -p`・`exec -a`）・`python -W ... -m django`・`docker run --entrypoint` の中身・`-w` と `..` を考えたパスの読み替え
- 秘密情報の追加: Python コードの `os.environ` / `getenv` / `/proc/` / `.env` の文字列 / `settings.SECRET_KEY` 等・`/proc/*/environ`・`echo $...KEY` 等・`cat < .env`・`grep -r`（`--include` なしで `.env` を含むディレクトリ）・`docker cp` / `docker compose cp`・`docker container inspect`・`gh auth token`
- Python コードの列挙の追加: `.delete ()`（空白入り）・`_raw_delete`・`shutil.rmtree`・`os.remove|unlink|rmdir`・`subprocess` / `os.system` / `os.popen`（外部コマンド）・`smtplib` / `socket` / `requests` / `urllib` / `httpx`（外部送信）・書き込みモードの `open(`・SQL 文字列の先頭のコメントと `WITH`
- 誤判定の修正: `cache.delete(` は削除扱いにしない・`objects ... .update(` は `;` をまたがない（`qs.update(` は別の判定）・ホストの Python は Django を使うコードのときだけ中身を判定する（文書の書き換えスクリプトに危険語の文字列が入っているだけでは止めない）・`docker inspect -f` で環境変数を出さない指定は素通し・grep のパターン引数を秘密情報のパスとして扱わない
- 残余リスクとして明記: `migrate`（前進）で未適用の破壊的マイグレーションが走ること（マイグレーションは PR でレビューされ、コンテナ起動時にも自動で走る）・素の `docker exec|run` の中の列挙外の操作・意図的な回避
- テスト: 第 2 周 #17・#18 の生き残り（包むコマンド・区切り・秘密情報・compose の許可リストの各枝・流し込み・`$(...)`・docker のオプション・ヒアストリング・細かい枝）を確かめるケースを足す。`test_settings_permissions.sh` に、PreToolUse の Bash フックの登録・`defaultMode` が `bypassPermissions` でないこと・allow に `Bash(*)` / `Bash(docker *)` が無いことを加える

### 0-10. fix-loop（敵対的レビュー第 3 周・上限到達への対応・2026-10-17・ユーザー決定＝案 C）
診断メモ `docs/reviews/I174_fix_diagnosis_20261017_0030.md`（診断レビュー PASS）。根本原因は「Python のコードを正規表現で判定していること」と「`-c "$(...)"` の中身をコードとして扱っていないこと」。
- **Python コードの判定を構文木（標準ライブラリ `ast`）に置き換える**（`_code_ast` / `_CodeVisitor` / `_code_findings`）。呼び出し・import・属性の参照・ループを、改行・空白・変数名の揺れに関係なく取り出す。構文として読めないコードは、compose では確認、ホスト・素の docker では従来の正規表現（予備）で判定する。
  - 危険操作（共通）: `.delete()` / `_raw_delete()`（`cache.delete` は除く）・QuerySet の `.update()`（呼び出しのチェーン・`objects` を含む連鎖・関連マネージャ〔2 段以上の属性〕・`*_set`・QuerySet を代入した変数・`qs` 等）・`.bulk_update()`・`cache.clear()` / `.flushall()` / `.flushdb()`・ループや内包表記の中の `save` / `delete` / `update` / `set_password` / `create`・`call_command`（`flush` / `sqlflush` / `reset_db` / `loaddata`・`seed_e2e` の `flush=True` / `--flush`・`migrate` の位置引数 2 つ以上）・`shutil.rmtree` / `os.remove` 等 / `Path().unlink()`・`execute()` の破壊的 SQL のリテラル
  - 外部送信・秘密情報（共通）: 通信・外部コマンドのモジュールの import・`django.core.mail`・メール送信の関数とクラス・`.delay()` / `.apply_async()`・`*_task()`・`os.system` 等・OpenAI・`reverse('register')` 等・API パスの文字列・`os.environ` の読み出し（`setdefault` は除く）・`getenv`・`.env` の `open`・`settings.SECRET_KEY` 等・`/proc/*/environ`
  - compose の許可リスト: 上に当たらず、すべての呼び出しが `_SAFE_CALLS`（表示・変換・ORM の読み取り・1 件の書き込み・テスト用クライアント・日時・JSON など）に入り、import が `_SAFE_IMPORT_ROOTS` に入るときだけ素通し。大文字で始まる名前の呼び出し（クラスの生成）は通す（メール・AI のクラスは先に外部送信として判定する）。
  - ホストの Python: `manage.py shell` のコードは常に判定する。素の `python` は、アプリ（`django` 等）を import するときだけ危険操作を判定し、秘密情報と API パスはいつも判定する。書き込みモードの `open(` は危険操作から外す（ホストのファイル編集は通常の作業）。
- **`-c "$(cat <<'EOF' ... EOF)"` / `-c "$(cat <ファイル>)"` の中身をコードとして戻す**（`_SUBST_STORE` と `_resolve_marks`）。中身が分からない `$(...)` のコードや SQL は「見えない」扱い（compose では確認）。
- そのほか: ホスト側のリダイレクトをコンテナ内の書き込みとして引き継がない・パイプで受ける psql / dbshell は流し込みとして危険操作・パイプで受ける見えないコード（ホスト・素の docker）は確認・`migrate --fake` / `--prune` / `--run-syncdb` は compose の許可リストから外す・引用符の中の `<<` をヒアドキュメントとして扱わない・push の判定はヒアドキュメントの本文を除き改行を区切りにしたテキストで行う・frontend サービスの `/app` は `frontend/` に読み替える・作業ディレクトリ（`-w`）とサービス名を入れ子の判定に引き継ぐ・ホストの `echo $...KEY`・`gh auth status -t`・`git diff` 等の `.env`・`docker compose config --services` 等と環境変数を出さない `docker inspect --format` は素通し・deny の `**/.env.*` を、実際に秘密を含む名前（`**/.env.e2e`・`**/.env.local`・`**/.env.*.local`）に絞る（`.env.example` 等の編集を妨げない）
- テスト: 第 3 周の再現と生き残り（A118〜A144・X33〜X38・S28〜S47・C42〜C54・P58〜P70・G9〜G10）を足す。settings テストに `disableAllHooks` と guard を呼ばないフックの検出を足す
- 残余リスク（受け入れ）: ホストの `git checkout -f` / `git switch -f` での未コミット変更の消失（I174 の前から・範囲外）・`_SAFE_CALLS` の中の呼び出しを意図的に悪用する形（脅威モデル外）・settings.json の deny は実在する秘密ファイルの名前（`.env`・`.env.e2e`・`.env.local`・`.env.*.local`）に絞ったため、将来 `.env.prod` のような別の名前の秘密ファイルを置くと Read / Edit の deny が効かない（Bash での読み出しは guard の `_SECRET_PATH_RE` が引き続き確認に回す。新しい秘密ファイルを置くときは deny に名前を足す）・ホストの素の python で API パスの文字列や `os.environ` の読み出しを含むもの（文書の書き換えスクリプトを含む）は確認になる（0-10 の方針どおり）
- 実装レビュー（手順5.5）の指摘で追加した修正: `_quote_state` が引用符の外の `#` コメントを飛ばす（`# don't` の ' でヒアドキュメントを読み落とさない）・`_read_exec_file` は普通のファイルだけを読む（`$(cat /dev/zero)` で固まらない）
- 実装再レビュー（手順5.5・2 回目）の指摘で追加した修正（連続 NG 2 回のエスカレーションの後、ユーザーの了承で 3 回目へ）: コメントの中の `<<`（`# 例: cat <<EOF`）をヒアドキュメントとして扱わない（`_scan_quotes` がコメントの中かどうかも返す）・引用符の外のコメントは `_strip_comments` で先に取り除いて改行を残し、shlex のコメント処理は使わない（shlex は改行ごと消すため、次の行のコマンドが前の行の引数としてつながっていた）・自動テスト文書のケース表と件数を 552 に同期
- 実装再レビュー（手順5.5・3 回目）の指摘で追加した修正（連続 NG 3 回のエスカレーションの後、ユーザーの了承で 4 回目へ）: コメントの始まりの判定を `_is_comment_start` の 1 か所にまとめ、直前の文字に `)` `<` `>` を足す（bash と同じく語の始まりの `#` をコメントとする。`(true)#<<EOF` の次の行を飲み込まない）。`echo $(true)#<<EOF` は bash では本物のヒアドキュメントだが、guard はコメントとして扱い本文をコマンドとして判定する（止めすぎる側・普段書かない形のため受け入れ）。ケース表と件数を 559 に同期
- 計画レビュー（2026-10-17・`docs/reviews/I174_plan_review_20261017_1220.md`・OK）の指摘への対応: 旧 C3（パイプでの compose psql）は危険操作なので (A) の A159 に移した・新しい秘密ファイルを置くときに deny へ名前を足す運用を danger-ops.md に明記・テストの最終件数は 574（テストレビューで足したケースを含む。ケース表は `docs/tests/open/I174_auto_test.md`）・`_SAFE_CALLS` / `_SAFE_IMPORT_ROOTS` の具体的な中身は `scripts/claude/hooks/pretooluse_guard.py` の定数が正本（計画書には写さず二重管理を避ける）
- 残余リスク（受け入れ・追記）: ホストの素の python3 で、アプリを import しないコードのファイル削除（`shutil.rmtree('backend')` 等）は判定しない（0-10 の方針どおり。ホストのファイル操作は通常の作業で、取り消せない削除は settings の `rm` の ask と git で守る）

### 0-11. 敵対的レビューのやり直し（fix-loop 後・2026-10-17）
記録: `docs/reviews/I174_adversarial_review_20261017_1443.md`（第 1 周）・`docs/reviews/I174_adversarial_review_20261017_1911.md`（第 2 周）。設計の変更は無く、0-10 の方針の中での判定の追加と直しだけ。
- 第 1 周: 別名の import・`reverse` の名前空間とキーワード・設定の秘密の参照の形（getattr・vars・別名・import・`settings_dict`）・`caches[...]` の変数・`migration_name=`・多対多の `.set()`・`ps e`・語にくっついた `;` `&` の区切り
- 第 2 周:
  - 同じコマンドの中で書き込むファイルを実行するときは、ディスクの中身と書き込む中身を合わせて判定し、中身が見えない書き込み（`sed -i`・`echo >` 等）なら確認にする（`_WRITTEN`・`_record_writes`）
  - celery タスクを起点にした呼び出し（`.apply()`・`.run()`・`.s().apply()`・別名）を外部送信にする
  - `git clean -f` は `-d` / `-x` が無くても危険操作にする（`-n` は除く）。danger-ops.md も同じに直す
  - **mkfs・dd・shred の解除不可の停止を、コマンド名で判定する**（R8 を範囲に入れる。引数・コミットメッセージ・grep の検索語の中の語では止めない）
  - 読み取りだけの標準ライブラリ（`time`・`inspect`・`importlib.metadata`・`secrets`・`logging`・`glob`・`hashlib` 等）を compose の許可リストに足す
  - `.env` の判定を、glob・ブレース展開・`/proc/*/environ`・Python の文字列（`Path().read_text()`・`dotenv_values()`）にも当てる（`_secret_path`）
  - `python -`（引数あり）と `python /dev/stdin` はパイプの中身をコードとして実行するので、中身が見えない確認を外さない
  - `>|`・`2>&1` を区切りとして分けない（第 1 周の `;` `&` の区切りでの後退の修正）
- 第 3 周（`docs/reviews/I174_adversarial_review_20261017_1926.md`）:
  - シェルの予約語（`if`・`then`・`elif`・`else`・`while`・`until`・`do`）の後ろもコマンドとして判定する（`if X; then rm -rf x; fi` の本体を見逃していた）。`strace`・`ltrace`・`parallel` も包むコマンドとして外す
  - `.env` の glob は、シェルの `*` が `.` で始まるファイルに当たらないことに合わせ、`.` で始まる glob だけを `.env` 系と見る（`.env.e2*` 等も当てる）。鍵は拡張子付きの glob・`secrets/` の下はすべて。Python の文字列は glob の記号を含むものを対象外にする（`docs/reviews/*`・`'*'` を秘密扱いしていた第 2 周の誤判定の修正）
  - `python3 - < f.py`・`python3 /dev/stdin < f.py` は、流し込むファイルの中身を判定する
- 残余リスク（追記）: `ssh` / `kubectl exec` の先のコマンドは判定しない（このプロジェクトの作業で使わない）

### 0-16. fix-loop（/security-review の Blocker への対応・2026-10-21）
診断メモ `docs/reviews/I174_fix_diagnosis_20261021_1422.md`（§5 で改訂・診断レビュー PASS）。見張りが判定のために実行する git に、判定対象のコマンドの `-c` や、cd の先のリポジトリの設定が効き、人の承認より前にコマンドが実行されていた（0-14 で入った）。
1. 見張りが git を実行してよい場所を、見張りの作業ディレクトリの `git worktree list` から得た「このリポジトリとその worktree」に**一致**で限る（`_git_resolve`）。配下でも入れ子のリポジトリは除外。`--git-dir`・`--work-tree`・`GIT_DIR`・`GIT_WORK_TREE` は信頼する値と完全一致のときだけ（worktree の `.git` ファイルは読んで解決）。
2. 実行する git には信頼する git-dir と最上位を明示し（探索を使わない）、`-c core.fsmonitor=false -c core.hooksPath=/dev/null` を付け、判定対象の `-c`・環境変数は渡さず、見張りの環境からも `GIT_` で始まる変数を除く。`status` は `--no-renames --untracked-files=no`。
3. 信頼しない場所での、場所に依存する判定（未コミット変更の取り消し・今のブランチで宛先が決まる push）は確認（0-15 と同じ）。
4. テスト: checkout G81〜G87（PWNED が作られないこと。仕込みは core.fsmonitor と clean フィルタの 2 種類。clean フィルタは `core.fsmonitor=false` では防げず、信頼する場所に限ることで防ぐことを実測）・FG-TRUST（信頼する場所の判定を外すと判定中に実行される）。G43〜G45 は別のリポジトリを指すので 2 から ASK に。FG-M の複製は `_git_loc_trusted` も外す形に。
- /code-review 20261021_1509 第 1 周の対応: 信頼の起点をプロジェクト（`CLAUDE_PROJECT_DIR`）に固定（Bash の作業ディレクトリが入れ子のリポジトリでも信頼しない）・`--git-dir` だけの形は作業ディレクトリが最上位と一致するときだけファイルの変更を調べる（今のブランチは git-dir で決まるので問わない）・条件付きの cd（`A && cd X; …`・`A || cd X; …`・`cd X || true; …`）は場所が 1 つに決まらない扱い。
- /code-review 20261021_1509 第 2・3 周の対応: サブモジュールの中へ status を入れない（`--ignore-submodules=all`）・cd の先は論理パス（`..` を文字の上で畳む）・**「場所が 1 つに決まる」を許可リストに切り替え**（cd が無い、または `&&`／`;` だけでつながり cd がすべて `cd <文字どおりの実在する場所>` で無条件に実行される形だけ。それ以外は確認。決まらない書き方の列挙〔`( … )`・パイプ・条件付き・制御構文・`cd -P`・CDPATH…〕は終わらないため・ユーザー了承）。
- 残余リスク: 信頼するこのリポジトリの `.git/config` を、それより前のコマンド（`git config core.fsmonitor …`）で書き換えた場合は、見張りの git でも効く（I174 以前から同じ・本物の git も同じ設定で動く）。

### 0-15. fix-loop（/code-review 20261021_0905 の敵対的レビュー 3 周・再び上限到達への対応・2026-10-21・ユーザー決定＝「読み切れないときは確認に回す」）
診断メモ `docs/reviews/I174_fix_diagnosis_20261021_1226.md`（診断レビュー PASS）。0-14 の後の 3 周で、実行場所（`( … )`・`cd -`・失敗する cd・読めない cd の先）と対象（`$(…)`・xargs・find・中かっこ）の推測が「止める側に倒す → 止めすぎを緩める → 緩めすぎ」と往復した。根本原因は、bash がどこで何を実行するかを静的に推測して、通す・止めるを決めていたこと。
1. **場所が一意か（`_loc_ambiguous`）**: cd / pushd / popd が無ければ一意。あれば、`( … )`・popd・パイプ・`&`・入れ子のシェル（`sh -c`・`bash <<`・eval・xargs・parallel・`find -exec`）の中にありうる・元へ戻る（`cd -`・`~-`・`$OLDPWD`）・先が読めない（変数・`$(…)`）・先が存在しない、のどれかで一意でない。
2. **一意でなければ確認**: 場所に依存する判定（未コミット変更の取り消し・宛先を書かない／HEAD／@ の push）は、場所を推測せず確認（`git_unsure`・`push_dynamic`）。場所に依存しない危険操作（保護ブランチ名の push・force・reset --hard 等）は停止のまま。
3. **対象が読めなければ、その場所に変更があるとき確認**（以前は停止、または一覧のコマンド以外は通す）。`--pathspec-from-file` も同じ扱い。`git checkout "$BR"` は変更があれば確認（ブランチの切り替えかファイルの取り消しかを読めないため）。
4. 推測の部品（通った場所すべてを候補にする `cds`・`_CD_HERE_RE`・`_FILE_LIST_RE`）を廃止。一意なら cd の先で精密に判定（停止は停止）。
5. その他: `read-tree` は `-u --reset` だけ（`-m` は変更を残す）・`git mv -f` の移動先がディレクトリならその中の同名ファイル・checkout-index の `-a` のテスト・danger-ops.md の更新。
6. テスト: checkout G63〜G75・FG-AMB（`_loc_ambiguous` を外すと `cd -` の後の checkout が素通し）、push XP72〜XP75。場所・対象が 1 つに決まらない既存ケース（G21・G27・G32〜G36・G50・G52・G57・G58・G60・XP13・XP60）は 2 から ASK に変更（AC-10 の例外。人の確認に寄る変化）。

### 0-14. fix-loop（/code-review 20261019_0037 の敵対的レビュー 3 周・上限到達への対応・2026-10-21・ユーザー決定＝案 B）
診断メモ `docs/reviews/I174_fix_diagnosis_20261021_0148.md`（診断レビュー PASS）。第 1〜2 周の修正（73fbd19・dd941c5）の後、第 3 周で High 3 が残った。根本原因は「git の判定が最上位の文字列と単純コマンドの 2 経路に分かれている」だが、ユーザーは一本化（案 A）ではなく**指摘ごとの修正（案 B）**を選んだ。経路は 2 つのまま、共通の部品を両方から使う形で直す。
1. **git の実行場所の共通部品**: `_git_find`（git.exe・絶対パス・前置きの `GIT_DIR=` を含めて git とサブコマンドの位置を返す）・`_git_loc`／`_git_run`（`cd`／`pushd` の先〔`cd --`・`cd -P`・引数なし・`~`〕・`-C`・`--git-dir`・`--work-tree`・`-c`・`GIT_DIR`／`GIT_WORK_TREE` を再現して git を実行）・`_cd_target`。今のブランチ（push）と未コミット変更（checkout/restore）の両方がこれを使う。
2. **未コミット変更の取り消し**: `_git_revert_target_on_dirty` を、git の前のオプション・cd の先・入れ子の中（`_cmd_danger` から単純コマンドごとに呼ぶ）でも判定する。コミットから戻す形（`git checkout <コミット> -- f`・`git restore -s`・`-S -W`）はステージ済みの変更も数える。`--pathspec-from-file` は対象を読めないので止める。`git rm -f`（`--cached` なし）で変更のあるファイルも止める。
3. **宛先の読めない push**: `_analyze` が単純コマンドごとに `push_dynamic`（宛先に `$`・`` ` ``・`{`・`(`・置換〔`__SUBST_`〕、xargs／parallel が語を足す形、実行場所が変数）を返し、main が確認にする（`bash -lc`・`sh -ec`・ヒアドキュメント・`timeout … bash -lc` の中も同じ）。第 2 周で入れた文字列一致の (ii) `sh -c`・(iii) xargs/parallel は廃止（`xargs grep "git push"` 等の余計な確認を消す）。
4. **判定の追加**: `-c remote.*.push=`／`-c push.default=` 付きの push・`git config remote.*.push <値>`／`git config push.default <値>`・`git -c clean.requireForce=false clean`・`rm -r`／`-R`（`-f` なし）・`find -exec rm`・`xargs rm`／`parallel rm` を危険操作（停止）に。
5. **xargs／parallel の値を取るオプション**: `--arg-file` ほかの長い形、parallel の `-a`・`--halt`・`--colsep`・`-I` など（`_XARGS_VALUE`・`_PARALLEL_VALUE`）。parallel の区切りは `:::` で始まる語（`::::`・`:::+`）。
6. **テスト**: push（XP28〜XP44）・checkout（G16〜G29）・container（H24〜H39）・差分テスト（git.exe・`rm -r`。3,984 件）。S28・S29 は一時ディレクトリで（作業ツリーの `.env` に依存しない）。偽合格の防止の複製（FG-I・checkout の FALSEGREEN）は新しい経路も外す形に。

### 0-13. fix-loop（0-12 後のコードレビューの敵対的レビュー・上限到達への対応・2026-10-18・ユーザー決定＝案 B）
診断メモ `docs/reviews/I174_fix_diagnosis_20261018_1321.md`（診断レビュー PASS）。根本原因は「bash の文法（引用符・コメント・ヒアドキュメント・行の継続）を読む処理が 6 か所に分かれ規則がばらばら」「bash と同じに読めているかを確かめる仕組みがない」「読みきれない形を素通しにする」。
1. **bash との差分テスト**（新規 `scripts/claude/tests/test_guard_bash_oracle.sh`＋`guard_bash_oracle.py`）: 危険なコマンド（`git reset --hard`・`git push --force`・`rm -rf`）を、前置きの文脈（引用符の中の `#`・`$'…'`・`#` で終わるコメントの `\`・各種ヒアドキュメント・`<<<`・`$(( << ))` 等）× つなぎ方（改行・`&&`・`;`）× 書き方（1 行・継続で折る 2 通り）× 包み方（そのまま・`bash -c '…'`・`bash <<'X'`）で生成する。mktemp -d の中で本物の bash に実行させ（`git` と `rm` は危険な引数で呼ばれたら印を出すだけの関数に置き換えて `export -f`。ほかは echo・cat・wc 等の無害なものだけ）、**bash が危険なコマンドを実行した形で見張りが素通し（0）なら不合格**。bash が実行しない形で見張りが止めた件数は表示する（余計な停止）。
2. **読みきれない形は確認**: 精密判定と安全網が何も返さなくても、引用符が閉じないなど読み取りが代替経路に落ちた形は確認にする。閉じないヒアドキュメントは、bash も残りを本文として扱い実行しないので対象外（実装レビューの指摘で記述を実装に合わせた）。
3. **差分テストで見つかった食い違いを直し、読み方の規則をそろえる**（引用符・`$'…'`・コメントの判定を 1 つにまとめ、各処理が同じものを使う）。
- 結果（実装時）: 差分テスト 786 件で、修正前の guard は見逃し 130 件（入れ子のシェルの中の `git push --force`・`$'it\'s'` の後ろ）と余計な停止 2 件（コメントの中の push）→ 0 件。直したもの: (a) `_cmd_danger` にも push の判定（保護ブランチ・force）を入れ、入れ子のシェルの中の push を単純コマンドごとに判定 (b) `$'…'` は読み取りの最初（`_join_continuations`）で同じ文字列の `"…"` に書き換える（ほかの処理が `$'…'` を知らなくても読み違えない。規則を 1 か所に寄せる） (c) push の最上位の判定はコメントを除いてから行う (d) 引用符が閉じない形は確認（`unsure`）。作業記録の再判定は新しく確認・停止 0 件
- 実装レビュー（1 回目・BLOCKER＝実行の不備）への対応: `$'…'` の書き換えがエスケープ（`\x6d`・`\055`）を展開せず、`git push origin $'\x6dain'`（= main）が素通りしていた → `_ansi_c_decode` で bash と同じ規則で展開。差分テストに `$'…'` で書いた引数・宛先と、保護ブランチへの push（`git push origin main`）を追加（計 1,844 件・見逃し 0・余計な停止 0。修正前の guard では見逃し 692）。コメント・本文の中の `$'…'` で「宛先の分からない push」の確認が出ていたので、その判定もコメントと本文を除いてから行う
- 既存テストの期待値の変更（AC-10 の例外）: `eval "git push …"`・`sh -c "git push …"` は、中身を読んで単純コマンドごとに判定するようになったので、直接書いたときと同じく停止（以前は「宛先を確定できない」として確認）。`test_pretooluse_push_guard.sh` の D5・D6・F7・FG-J2・FG-L2 を 2 に、偽合格の防止の複製（FG-A・FG-J・FG-L）は追加した判定も外す形に直した。入れ子の中に書いた `DANGER_OK=1`（`bash -c 'DANGER_OK=1 git push origin main'`）は解除にならず停止（最上位の `DANGER_OK=1` だけが人の承認に切り替える。止める側に寄った変化）
- 規則の統一は、各処理を書き換えるのではなく「読み取りの入口で bash と同じ形に正規化する」（継続をつなぐ・`$'…'` を `"…"` にする）方式にした。各処理の規則の差は、差分テストが bash との食い違いとして検出する（第 3 周 T1〜T6 の分岐を 1 つずつ外した複製で、どれも見逃しとして検出〔`$'…'` の分岐だけは確認止まり 43 件＝読みきれない形の確認が働く〕）

### 0-12. fix-loop（敵対的レビューやり直し第 3 周・上限到達への対応・2026-10-17・ユーザー決定＝案 B）
診断メモ `docs/reviews/I174_fix_diagnosis_20261017_1927.md`（診断レビュー PASS・`_20261017_1933.md`）。根本原因は「読めないシェルの書き方を素通しにする（fail-open）」と「修正の影響を網羅的に確かめる仕組みがない（後退が毎周出る）」。0-10・0-11 の精密判定は残し、その上に重ねる。
1. **安全網（`_safety_net` / `_sn_judge`）**: 精密判定（危険操作・外部送信・秘密情報・コンテナの許可リスト・push）がすべて何も返さなかったコマンドだけを対象にする。文法に依存しない区切り（先頭・`; & | && || ( ) { } $`・改行・予約語・`function 名前`・`coproc`・包むコマンド・`VAR=値`・プロセス置換 `<(` `>(`・`find -exec` の後）で「コマンドの位置」を見つけ、そこから始まる各コマンドを**精密判定（`_analyze`）にかけ直し**、何か出れば**確認（ask）**にする（止めない）。
   - 独自の危険語の一覧は持たない（実装の途中で、独自の一覧は精密判定が意図して通しているもの〔一時フォルダの削除など〕と食い違い、余計な確認が作業記録で +16 件出たため。かけ直しなら精密判定と食い違わない）。読めない文法を一律に確認にすることもしない（`diff <(sed …)` 等の読み取りで余計な確認が出たため）
   - ヒアドキュメントの本文・引用符の中・コメントは見ない（`grep "rm -rf"`・`YYYY-MM-DD` に反応しない）。引用符の中の `$( )` やヒアドキュメントを含むコマンドはかけ直さない（組み直すと意味が変わるうえ、精密判定が中身を判定済み）
2. **組み合わせのテスト**（新規 `scripts/claude/tests/test_pretooluse_guard_matrix.sh`）: 危険な操作の代表 × 書き方（そのまま・`&&`・`;`・`( )`・`{ }`・if/else・for/while/until・case・関数 2 形・`$( )`・`<( )`・`bash -c`・`sh -c`・`sudo`・`timeout`・`nohup`・`time`・`env`・`nice`・`coproc`・`xargs`・`find -exec`）を総当たりで生成し、すべて 2 か ASK（素通しでない）を確かめる。
3. **作業記録の再判定**（新規 `scripts/claude/tests/guard_corpus_diff.py`）: 作業記録（`~/.claude/projects/<このリポジトリ>/**/*.jsonl`）の Bash コマンドを手元のキャッシュ（`~/.cache/claude-guard-corpus/`）に抜き出し、**コミット済み（HEAD）の guard と作業ツリーの guard を同じ時点・同じ環境で並べて判定**して差分を出す。確認＋停止の増加が記録の 1% を超えたら不合格。素通し→停止になったものは一覧を出す（意図どおりかを人が見る）。作業記録が無い環境（CI 等）と、guard に未コミットの変更が無いとき（コミットの後）は SKIP（コミットの前に流すゲート）。決定論ゲートでは、code-review.sh の許可された形に合わせて `bash scripts/claude/tests/test_guard_corpus_diff.sh` で呼ぶ。
   - 結果（実装時）: 作業記録 3,701 件で、確認＋停止は 182 件（4.92%）→ 182 件（増減 0）。総当たりの表は安全網の前の guard で 23 件が素通し → 0 件
   - 診断メモからの変更: 作業記録はリポジトリに**入れない**（このリポジトリは公開のため、作業のコマンド約 3,400 件を公開しない）。基準の判定結果も保存せず、HEAD の guard との並列比較にした（変更の有無などの環境の差が結果に混ざらないため）。
- 先送り（Medium・Low。この周の通過条件外。/close の時に、まとめて別イシューとして起票するかを判断する）: 多対多の `.clear()`・変数に入れた SQL / `executemany` / `raw` / `WHERE 1=1`・素の docker exec の `dumpdata` / `remove_stale_contenttypes` / `get_connection_params()` / `ps auxeww`・`git worktree remove --force` / `git stash clear|drop`・`settings.DATABASES['default']['HOST']` と `getenv('DEBUG')` の余計な確認・`wget` / httpie / `node fetch` での登録 API・キャッシュの別名と `delete_pattern('*')`・`import os as o`・`vars(connection)`・`call_command('generate_ai_problems' | 'sendtestemail')`・`/proc/1/task/1/environ`・`env -u X`・`ps -o user` の余計な確認・frontend の `npm audit | node -e`・`psql -lqt`・（第 3 周）`export -p` / `declare -x` / `set`・パス無しの `dotenv_values()`・`column` / `paste` / `iconv` / `node readFileSync` での `.env`・`'->' &` の直後の結合・F17 / `2>&1` の結合のテストの覆い隠し
  - 注（2026-10-21 計画レビュー Warning）: これらが安全網で確認になる保証は無い（安全網は精密判定のかけ直しなので、精密判定が見ない書き方は安全網でも素通しになりうる）。受け入れる残余リスクとして扱い、/close の時に別イシューとして起票するかを判断する。

## 1. 背景/目的

**背景**: I151 の作業中に、`docker compose exec` の承認待ちが約 28 回出て作業が滞った。過去 51 セッションの集計では、確認対象の操作 125 回のうち 120 回（約 96%）が `docker compose exec` で、中身は pytest・ruff・pip-audit・npm audit・読み取りの `manage.py shell` が大半だった。`.claude/settings.json` の `permissions.ask` が「コマンドの種類」で一律に確認をかけていて、「危険かどうか」を見ていないのが原因である。

**目的**: 本当に危険な操作（`docs/runbooks/danger-ops.md` の定義）と外部への送信だけを、見張り（PreToolUse フック `scripts/claude/hooks/pretooluse_guard.py`）が止めるか、人に確認を求める。それ以外の操作は auto mode の判断で止まらずに進める。安全性は落とさない。むしろ、調査で見つかった見張りの既存の穴（破壊的 SQL の見逃し・DANGER_OK=1 の自己承認）も塞ぐ。

## 調査結果

### 原因の概要
「確認が必要な操作」の設定が、コンテナの中で何をするかを見ずに `docker compose exec` を一律で止めている。一方で見張りは、コンテナ内の危険操作をほとんど捕まえられていない。人の承認も、その一律の設定に頼っていた。そのため、設定を外したくても外せなかった。

### 詳細な原因分析（2026-10-16 にフックへ直接入力して実測）
1. **一律の ask**: `.claude/settings.json:84-89` の `Bash(docker compose exec *)` などが ask になっていて、auto mode が安全と判断できる操作でも必ずプロンプトが出る（画面表示 `Ask rule Bash(docker compose exec *) overrides auto mode for this command.`）。
2. **効いていない allow**: `.claude/settings.json:68-77` の `docker compose exec backend pytest *` などの 10 行は、ask が allow より優先されることと、実際のコマンドに `-T` が付いていて一致しないことから、一度も効いていない。`Write(...)` ルールの 10 行（allow 9・11・13・15・17 行目、deny 122・123・124・126・128 行目）も、Claude Code が「`Write(docs/**) is not matched by file permission checks — only Edit(path) rules are`」と警告していて効いていない（同じ範囲は `Edit(...)` が受け持っている）。
3. **破壊的 SQL の見逃し（既存の不具合）**: `pretooluse_guard.py:503-512` は判定語の前に空白を要求するので（`" drop "` など）、SQL 文が判定語で始まると一致しない。二重引用符の `-c "..."` しか見ていない。実測では `docker compose exec -T db psql -U postgres -c "DROP DATABASE migrate_check;"`・`... -c "TRUNCATE problems_problem;"`・`... -c "DELETE FROM problems_problem;"`・`... -c 'DROP DATABASE x;'` がすべて exit 0（素通り）だった。
4. **コンテナ内の危険操作は素通り**: `manage.py flush`・`migrate problems zero`・`sqlflush`・`dropdb`・`psql ... < dump.sql`・shell 内の `.delete()` は、すべて exit 0 だった。
5. **DANGER_OK=1 の自己承認**: `pretooluse_guard.py:454` の `if not danger_ok:` は、DANGER_OK=1 が付くと危険操作の判定をすべて飛ばす。現状で人の承認がかかるのは、ask ルール（`git reset *`・`docker compose down *`・`rm *` など）が当たっているからにすぎない。ask を外すと、Claude が `DANGER_OK=1` を付けるだけで通ってしまい、CLAUDE.md 絶対ルール 4（危険操作は承認制）に反する。
6. **`rm -rf` の止めすぎ（既存の不具合）**: hard-block の `\brm\s+-rf\s+/\b`（433 行目）は、ルート `/` だけでなく絶対パスの `rm -rf` すべてに一致し、DANGER_OK=1 でも解除できない（実測: `rm -rf /tmp/claude-1000/xyz` → exit 2）。さらに、通常ルールの `\brm\s+-rf\b`（491 行目）はコマンド行の文字列全体を見るので、grep の検索文字列やヒアドキュメントの中身にも反応する。本セッションでも、`grep -n -E "...rm -rf..."` と検証用スクリプトを書くヒアドキュメントの 2 回、誤って止められた。
7. **実メール・有料 API への送信**: 開発環境は `EMAIL_BACKEND` が SMTP 固定（`backend/core/settings.py:266`）である。送信経路は 3 つ: 登録（`accounts/views.py:197`）・パスワード再設定の依頼（同 320 行目）・`send_study_reminders_task`（`studylogs/tasks.py:70`）。OpenAI による AI 問題生成は、`problems/views.py:365`（`generate_ai`）・500 行目（`generate_adaptive`）・`manage.py generate_ai_problems` の 3 経路。いまは `openai.ChatCompletion.create` が廃止 API のため必ず失敗するが、I153 で直ると送信が始まる。ほかの外部 SDK は使われていない。

### 既存テストのベースライン（2026-10-16・本ブランチ）
| テスト | 結果 |
|---|---|
| `scripts/claude/tests/test_pretooluse_push_guard.sh` | pass=87 fail=0 |
| `scripts/claude/tests/test_pretooluse_checkout_guard.sh` | pass=14 fail=0 |
| `scripts/claude/tests/test_pretooluse_worktree_guard.sh` | pass=27 fail=0 |
| `scripts/claude/tests/test_adversarial_trigger.sh` | pass=40 fail=0 |

既存テストは exit code と `runj`（exit 0 ＋ `permissionDecision=ask` の JSON）だけで判定していて、stderr の文言は検査していない（`grep` で確認）。

### 環境前提
- `python3`（フック実行）・`bash`・`git`・`gh` はホストで使用中（本セッションで実行済み）。追加のツールは不要。
- フックの変更は、そのセッションで次に実行するツールから効く（フックは毎回 `python3` で起動されるため）。`.claude/settings.json` の権限変更は、**新しいセッションから**効く。

### ハーネス挙動の未実証事項（スパイク区分 (2)）
- **auto mode でフックの `permissionDecision=ask` が人へのプロンプトになるか**は、本計画の前提（解決方針 1(d)・(b2)）である。既存の `_ask`（`HIGH_RISK_EDIT_PATTERNS`・動的 push）は I079・I083 で使われているが、auto mode で観測した記録は見当たらない。稼働中のセッションでは、プロンプトがどこから出たか（フックの ask／通常の権限／モード）を区別できない。そのため「未実証」とし、**実装ステップ 1 で新しいセッションで実証する**。成り立たなければ、計画をやり直す（1(d) を「DANGER_OK=1 でも exit 2 にし、承認後に人が手で実行する」形に変えるなど）。

### 文書の消費箇所（grep・2026-10-16）
`DANGER_OK` と ask に触れている文書は次のとおり。変更が要るのは danger-ops.md だけである。
| ファイル | 記述 | 対応 |
|---|---|---|
| `docs/runbooks/danger-ops.md:3,17,23` | DANGER_OK=1 の運用・checkout のブロック | **更新**（ステップ 5） |
| `docs/runbooks/worktree.md:41,43,93` | `DANGER_OK=1 bash scripts/claude/wt-remove.sh` | 変更なし（スクリプト内の `down -v` は guard から見えない。既存の挙動のまま。リスク R7） |
| `docs/runbooks/worktree.md:173` | worktree 横断の書き込みは DANGER_OK でも解除しない | 変更なし（本計画でも exit 2 のまま） |
| `docs/runbooks/workflow.md:42`・`.claude/skills/implement/SKILL.md:19` | Danger Ops は danger-approved＋DANGER_OK=1 が必須 | 変更なし（記述は本計画後も正しい）。「DANGER_OK=1 を付けても guard が人の承認を求める」挙動の変化は、両ファイルが参照する danger-ops.md に書く（計画レビュー Info 1 を検討し、説明の重複を避けるため追記しないと判断） |

## 2. 受け入れ条件
イシュー I174 の受け入れ条件をそのまま採用する（ステップと TC の対応は「6. テスト計画」）。
- [ ] AC-1 `.claude/settings.json` の ask に `docker compose exec/run/down`・`docker-compose exec/run/down`・`git reset`・`git merge`・`git cherry-pick` が無い
- [ ] AC-2 効いていない exec の allow 10 行が無い
- [ ] AC-3 `Write(...)` ルールが無い
- [ ] AC-4 危険操作（破壊的 SQL・DB 全消去・マイグレーション巻き戻し・ダンプ流し込み・loaddata・Redis 全消去・shell 内の削除と一括更新・`rm -rf`）を exit 2 で止める。書き出し（ホスト／`docker exec`／`docker compose exec/run`／`docker-compose`／`sh -c`）に関係なく止める
- [ ] AC-5 上記に `DANGER_OK=1` を付けると ask を返す。既存の解除経路（reset --hard・down -v・checkout・push 系）も ask を返す
- [ ] AC-6 外部送信（メール・celery の起動・登録とパスワード再設定依頼の API・OpenAI）に ask を返す。ログインとパスワード再設定の確定には返さない
- [ ] AC-7 実行されるファイルの中身にも AC-4・AC-6 の判定をかける。読めなければ stderr に出して素通しする
- [ ] AC-8 `rm -rf /` と `rm -rf /*` は DANGER_OK=1 でも exit 2。ルート以外は通常の危険操作として扱う。grep の検索文字列やヒアドキュメントの中の `rm -rf` には反応しない
- [ ] AC-9 読み取り・テスト系（pytest・ruff・pip-audit・npm audit・makemigrations --check・migrate・`psql -c "\dt"`・CREATE DATABASE・読み取りの shell・1 件だけの更新・`redis-cli ping` / `KEYS`・dumpdata）は止めず、ask も返さない
- [ ] AC-10 既存の guard のテストが全件合格（DOK1〜3・P6・P7・P23・P24・P26・P31・G7 は ASK・A19 は exit 2）
- [ ] AC-11 danger-ops.md に、guard が止める操作・DANGER_OK=1 でも人の承認が要ること・回避の書き方を使わないことが書かれている
- [ ] AC-12 新しいセッションで `docker compose exec -T backend python -m pytest -q` にプロンプトが出ない

## 3. 影響範囲
- Backend: なし（アプリのコードは変更しない）
- Frontend: なし
- DB: なし
- Config/Infra:
  - `scripts/claude/hooks/pretooluse_guard.py`（判定の追加・是正）
  - `scripts/claude/tests/test_pretooluse_container_guard.sh`（新規）
  - `scripts/claude/tests/test_pretooluse_push_guard.sh`・`scripts/claude/tests/test_pretooluse_checkout_guard.sh`（DANGER_OK=1 の期待値を ASK に）
  - `.claude/settings.json`（ask・allow・deny の整理）
  - `docs/runbooks/danger-ops.md`（追記）
  - fix-loop で追加したテスト（0-12〜0-15）: `scripts/claude/tests/test_pretooluse_guard_matrix.sh`（総当たり）・`guard_corpus_diff.py`＋`test_guard_corpus_diff.sh`（作業記録の再判定）・`guard_bash_oracle.py`＋`test_guard_bash_oracle.sh`（本物の bash との差分テスト）・`test_settings_permissions.sh`（settings.json の中身）
  - 先送り（0-12 の一覧）は、安全網で確認になる保証が無い。個別の評価（どれが素通しになりうるか）は /close の時の起票で行う（2026-10-21 計画レビュー Warning）
  - 波及: Claude Code の全セッション（primary と wt-harness の両方。settings.json と guard は commit で共有される）。新しいセッションから効く

## 4. 変更点一覧（具体）

### 4-1. 修正アプローチ（全体像）
見張りの判定を「コマンドの書き出し」ではなく「実際に何をするか」で行う形に作り替える。そのうえで、一律の確認設定を外す。判定は 3 種類に分ける。
- **常に止める（解除不可・exit 2）**: ルート `/` の削除・mkfs・dd・shred・別 worktree への書き込み（既存どおり）
- **危険操作（exit 2・DANGER_OK=1 を付けると人の確認）**: 既存の危険操作（保護ブランチへの push・force push・`reset --hard`・`down -v`・変更ありのファイルの checkout）＋本計画で足す危険操作
- **外部送信（人の確認）**: メール・celery の起動・OpenAI

文字列全体への部分一致はやめ、`_segments()`（shlex でのトークン分割）で得たトークン列に対して判定する。これで grep の検索文字列などへの誤反応を防ぐ。`sh -c` / `bash -c` の中身と `manage.py shell -c` / `python -c` のコードは、取り出して同じ判定にかける。

### 4-2. `pretooluse_guard.py` の変更

**(1) 判定の入口の作り替え（解決方針 1(d)）**
- 修正方針: `main()` の Bash 分岐で、危険操作の理由を `_danger_reasons(cmd)` に集めてから、DANGER_OK=1 の有無で分ける。DANGER_OK=1 が付いていても、該当すれば素通しせずに ask を返す。既存の判定（保護 push・`--all/--mirror`・`--repo`・force・`reset --hard`・`down -v`・checkout・破壊的 SQL）も、この入口に移す。
- 置き場所: 既存の hard-block（mkfs・dd・shred）と worktree 横断のブロックは、今の位置のまま（DANGER_OK でも解除しない）。
```python
def _danger_reasons(cmd: str) -> list:
    """DANGER_OK=1 で人の承認に切り替わる危険操作の理由を集める（該当なしは []）。"""
    reasons = []
    dest = _push_protected_target(cmd)
    if dest:
        reasons.append(f"push to protected branch '{dest}' is forbidden "
                       f"(release/hotfix は計画書明記＋danger-approved＋DANGER_OK=1 のみ)")
    # ... 既存の --all/--mirror・--repo・force・reset --hard・down -v・checkout をここへ移す（文言は既存のまま）
    if _rm_rf_targets(cmd):                        # (4) ルート以外の rm -rf
        reasons.append("rm -rf requires DANGER_OK=1")
    for toks, ctr in _expand_segments(cmd):        # sh -c / eval の中身も展開
        reasons += _segment_danger(toks, ctr)      # (2)(3) 破壊的 SQL・DB 全消去・巻き戻し・流し込み・Redis・shell
        for path, fctr in _exec_files(toks, ctr):  # (6) 実行ファイルの中身
            reasons += [f"{why} requires DANGER_OK=1" for why in _file_reasons(path, fctr)[0]]
    return reasons

# main() の Bash 分岐（hard-block・worktree の後）
reasons = _danger_reasons(cmd)
if reasons:
    if danger_ok:
        _ask("DANGER_OK=1 付きの危険操作です。内容を確認して承認してください: " + " / ".join(reasons))
    _block(reasons[0], raw)
external = _external_reasons(cmd)                  # (5) 外部送信
if external:
    _ask("外部への送信を伴う操作です。確認してください: " + " / ".join(external))
if _push_is_dynamic(cmd):                          # 既存。DANGER_OK=1 でも ask にする（DOK1〜3）
    _ask("動的・不透明な宛先の push です。protected ブランチに解決し得るため確認してください。")
```
- 既存のメッセージ文言は変えない（`requires DANGER_OK=1` など）。ただし、旧 psql 判定の 3 文言（`UPDATE without WHERE ...`・`DELETE without WHERE ...`・`destructive SQL ...`）は `destructive SQL requires DANGER_OK=1` に 1 本化する（既存テストは文言を検査していない）。
- **判定は先頭の `DANGER_OK=1` を外したコマンドで行う**（実装時に追加・2026-10-16）。`DANGER_OK=1 eval "git push --force origin x"`（既存テスト DOK3）は、先頭トークンが `DANGER_OK=1` になるため、`eval` の検出（先頭トークンで判定）をすり抜けていた。これまでは DANGER_OK=1 で判定ごと飛ばしていたので表に出なかったが、本計画で DANGER_OK=1 を ask にすると、確認なしで通ってしまう。あわせて、`_expand_segments` と `_is_container_seg` は先頭の環境変数の代入（`FOO=1 cmd`）を読み飛ばす（`_strip_env`）。

**(2) 破壊的 SQL の判定（解決方針 1(a)）**
- 修正方針: 引用符の種類と書き出しに関係なく、`psql` のトークン列から SQL を取り出し、文（`;` 区切り）ごとに単語境界で判定する。
```python
def _sql_is_destructive(sql: str) -> bool:
    for stmt in sql.split(";"):
        s = stmt.lower()
        if re.search(r"\b(drop|truncate)\b", s) or re.search(r"\balter\s+table\b", s):
            return True
        has_where = re.search(r"\bwhere\b", s)
        if re.search(r"\bupdate\b", s) and re.search(r"\bset\b", s) and not has_where:
            return True
        if re.search(r"\bdelete\s+from\b", s) and not has_where:
            return True
    return False
```
- SQL を取り出す場所: `psql` を含むセグメントの `-c` / `--command` の次のトークンと `--command=...`。shlex が引用符を外すので、`"..."` と `'...'` の両方を扱える。
- shell・`python -c`・実行ファイルの中身では、引用符で囲まれた文字列リテラルだけにこの判定をかける（`(['"])(.*?)\1`）。コード全体にかけると、`.drop(` などに誤反応するため。

**(3) コンテナ内の危険操作（解決方針 1(b)）**
- 修正方針: セグメントの中で `manage.py`（`basename` が `manage.py` のトークン）・`psql`・`dropdb`・`pg_restore`・`redis-cli` を探し、その後ろのトークンで判定する。トークンをセグメントのどこからでも探すので、ホストで直接実行・`docker exec <名前>`・`docker compose exec/run`・`docker-compose` のどの書き出しでも同じ結果になる。`sh` / `bash` / `dash` / `zsh` の `-c` の次のトークンは、再帰的に `_segments()` に通す（深さ 3 まで）。
- 判定表:

| 対象 | 危険とする条件 |
|---|---|
| `manage.py` の次が `flush` / `sqlflush` / `reset_db` | 常に |
| `manage.py loaddata` | 常に |
| `manage.py migrate` | 位置引数が 2 つ以上（値を取るオプション `--database` / `--settings` / `--pythonpath` / `-v` / `--verbosity` の値は数えない） |
| `manage.py shell` | `-c` / `--command` のコードが (3-a) に該当、または `<` で流し込むファイルの中身が (3-a) に該当（(6) を参照） |
| `python` / `python3` の `-c` | コードが (3-a) に該当 |
| `psql` | `-f` / `--file` / `--file=`、`<` によるファイルの流し込み（`<` 単独のトークンと `<ファイル` の付着形の両方） |
| `dropdb` | 常に |
| `pg_restore` | `--clean` / `-c` |
| `redis-cli` | 引数のどれかが（大文字小文字を区別せず）`FLUSHALL` / `FLUSHDB` |

- (3-a) コードの危険パターン（Python のコード文字列に対して）:
```python
_CODE_DANGER = [
    (r"\.delete\(", "データ削除（.delete()）"),
    (r"\bobjects\b[^;\n]*\.update\(", "QuerySet の一括更新（.update()）"),
    (r"\.bulk_update\(", "一括更新（bulk_update）"),
    (r"call_command\(\s*['\"](flush|sqlflush|reset_db)['\"]", "管理コマンドによる DB 全消去"),
    (r"call_command\(\s*['\"]migrate['\"][^)]*['\"]zero['\"]", "管理コマンドによるマイグレーション巻き戻し"),
]
# ＋ 文字列リテラルへの _sql_is_destructive（(2)）
```

**(4) `rm -rf` の判定（解決方針 1(c)）**
- 修正方針: 433 行目と 491 行目の文字列への正規表現をやめ、セグメントのトークン列で判定する。`rm`（`basename` が `rm`）のトークンを探し、その後ろのフラグに再帰（`r` / `R` / `--recursive`）と強制（`f` / `--force`）の両方があるときだけ対象にする。対象（フラグ以外のトークン）に `/` または `/*` があれば **hard-block（解除不可）**、それ以外は**危険操作**（DANGER_OK=1 で ask）にする。`grep -n "rm -rf"` は `rm -rf` が 1 つのトークンになるので反応しない。ヒアドキュメントの中身は、shlex 上は別トークンになりうるが、`rm` の直前が `<<` の区切り語の後ろ……と厳密に追うのは難しい。そこで、ヒアドキュメント（`<<`）を含むコマンドは `<<` 以降を判定対象から外す。
```python
def _rm_rf_targets(cmd: str):
    """rm の再帰＋強制削除の対象を返す（[] は該当なし）。<< 以降（ヒアドキュメント本文）は見ない。"""
    head = cmd.split("<<", 1)[0]
    for toks in _expand_segments(head):            # sh -c の中身も展開する
        for i, t in enumerate(toks):
            if os.path.basename(t) != "rm":
                continue
            flags = [a for a in toks[i + 1:] if a.startswith("-")]
            short = "".join(a[1:] for a in flags if not a.startswith("--"))
            rec = any(c in short for c in "rR") or "--recursive" in flags
            force = "f" in short or "--force" in flags
            if rec and force:
                return [a for a in toks[i + 1:] if not a.startswith("-")]
    return []
```
- hard-block の判定（`/` または `/*`）は、既存の mkfs などと同じく DANGER_OK の前に行う。

**(5) 外部送信（解決方針 1(b2)）**
- 修正方針: 「実行されるコード」にだけ判定をかける。対象は `manage.py shell -c` のコード・`python -c` のコード・実行ファイルの中身（(6)）・構造で分かるもの（`celery ... call`・`manage.py generate_ai_problems`）である。コマンド行の文字列全体には判定をかけない（`grep -rn send_mail backend` のような検索で ask が出ないようにするため）。
```python
_CODE_EXTERNAL = [
    (r"\b(send_mail|send_mass_mail|mail_admins|mail_managers)\(", "メール送信"),
    (r"\bEmail(Message|MultiAlternatives)\b", "メール送信"),
    (r"\.(delay|apply_async)\(", "celery タスクの起動"),
    (r"\bsend_study_reminders_task\b", "学習リマインダー送信タスク"),
    (r"auth/register/", "登録 API（確認メールを送信）"),
    (r"auth/password-reset/", "パスワード再設定依頼 API（メールを送信）"),
    (r"\bAIQuestionGenerator\b|problems/generate_(ai|adaptive)/|\bopenai\.", "OpenAI への送信"),
]
```
- `auth/password-reset/` は、`auth/password-reset-confirm/` には一致しない（`password-reset-confirm/` には、末尾が `/` の `password-reset/` という並びが含まれないため）。
- 構造での判定: セグメントに `celery` と `call` の両方のトークンがある／`manage.py` の次が `generate_ai_problems`。

**(6) 実行ファイルの中身（解決方針 1(b3)）**
- 修正方針: 実行されるファイルを特定できるときは、中身に (3-a)・(2) の文字列リテラル判定・(5) をかける。
- 対象の形と、パスの読み方:

| 形 | パスの読み方 |
|---|---|
| `manage.py shell < <パス>`（`<` は単独トークンと付着形の両方） | ホストのパス（`<` はホストのシェルが処理するため） |
| `python` / `python3` の最初の位置引数が `.py` で終わる（`-m` / `-c` があるときは対象外） | コンテナ内の実行（セグメントに `exec` / `run` があり、その前に `docker` / `compose` / `docker-compose` がある）なら、コンテナのパスとして読み替える。それ以外はホストのパス |
| `sh` / `bash` の最初の位置引数（コンテナ内の実行のときだけ） | コンテナのパスとして読み替える |

- コンテナのパスの読み替え（`docker-compose.yml:48-49` のマウントに合わせ、guard に固定で持つ）: `/app/docs/<x>` → `<リポジトリ>/docs/<x>`、`/app/<x>` → `<リポジトリ>/backend/<x>`、相対パス `<x>` → `<リポジトリ>/backend/<x>`（作業ディレクトリが `/app` のため）。`<リポジトリ>` は `git rev-parse --show-toplevel`（`_current_worktree_root()`）。
- 対象外: ホストの `bash` / `sh` で実行するスクリプト（`bash scripts/claude/tests/*.sh` などのテストは、危険な命令を**入力データとして**含むため）。`scripts/claude/` 配下のファイル（ハーネス自身のコード。guard 自身も判定パターンを文字列として含むため）。
- 読めないとき（パスを解決できない・存在しない・1 MB を超える・UTF-8 で読めない）: 判定を飛ばし、stderr に `[guard] 実行ファイルの中身を確認できませんでした（判定を省略）: <パス>` と出す。exit 0。

**(7) 定数**
- コンテナのパスの対応表・判定パターンの表・ファイルの大きさの上限（`_MAX_SCRIPT_BYTES = 1_000_000`）は、モジュールの先頭付近の定数にまとめる（ハードコードを散らさない）。

### 4-3. テスト
- `scripts/claude/tests/test_pretooluse_container_guard.sh`（新規）: 既存の `test_pretooluse_push_guard.sh` と同じ形（`json()`・`run()`・`runj()`・`ck()`・最後に `pass=` / `fail=` を出して `[ "$fail" -eq 0 ]`）で書く。ケースは自動テスト文書の TC-01 の表を全件入れる。偽合格を防ぐため、判定関数の呼び出しを無効化した複製（`sed` で `reasons += _segment_danger(toks, ctr)` を `pass` に、`external = _external_reasons(cmd)` を `external = []` に置き換える）では素通しになり、実体では止まることも確かめる（既存の FALSEGREEN と同じ方式）。
- `scripts/claude/tests/test_pretooluse_push_guard.sh`: `DOK1`〜`DOK3`（114・140・141 行目）の期待値を `ASK` にする。`P6`・`P7`・`P23`・`P24`・`P26`・`P31`（51・52・71・72・74・79 行目）を `run` から `runj` に変え、期待値を `ASK` にする。
- `scripts/claude/tests/test_pretooluse_checkout_guard.sh`: `runj()` を `test_pretooluse_push_guard.sh:33-35` と同じ定義で追加し、`G7`（38 行目）を `runj` の `ASK` にする。

### 4-4. `.claude/settings.json`
- `permissions.ask` から削除（9 行）: `Bash(git merge *)`・`Bash(git reset *)`・`Bash(git cherry-pick *)`・`Bash(docker compose exec *)`・`Bash(docker compose run *)`・`Bash(docker compose down *)`・`Bash(docker-compose exec *)`・`Bash(docker-compose run *)`・`Bash(docker-compose down *)`
- `permissions.ask` に残す（7 行）: `Bash(git rebase *)`・`Bash(psql *)`・`Bash(rm *)`・`Bash(mv *)`・`Bash(cp *)`・`Bash(chmod *)`・`Bash(chown *)`
- `permissions.allow` から削除（15 行）: 68〜77 行目の `docker compose exec ...` / `docker-compose exec ...` 10 行、`Write(docs/**)`・`Write(docs/issues/**)`・`Write(backend/**)`・`Write(frontend/**)`・`Write(scripts/claude/**)` の 5 行
- `permissions.deny` から削除（5 行）: `Write(./.env)`・`Write(./.env.*)`・`Write(./secrets/**)`・`Write(**/*.pem)`・`Write(**/*.key)`（同じ範囲は `Edit(...)` の deny が残る）

### 4-5. `docs/runbooks/danger-ops.md`
- 「例」の DB に `manage.py flush` / `sqlflush` / `reset_db`・`migrate <app> <移動先>`（巻き戻し）・`loaddata`・ダンプと SQL ファイルの流し込み（`psql -f` / `< ファイル`・`pg_restore --clean`・`dropdb`）・shell 内の `.delete()` と一括更新を、Docker に `redis-cli FLUSHALL` / `FLUSHDB` を追記する。
- 新しい節「見張り（pretooluse_guard.py）の扱い」を追加する。中身は 4 点: ①上の操作は、ホスト・`docker exec`・`docker compose exec/run` のどれで実行しても止まる ②`DANGER_OK=1` を付けても、見張りは人の承認を求める（自分で付けて通すことはできない） ③外部送信（メール・celery の起動・OpenAI）は人の確認になる ④変数・`eval`・base64 での組み立て・`docker compose cp` 後の実行・コンテナ内で作ったファイルの実行などの、見張りを避ける書き方を使わない。

## 5. 実装手順（ステップ）
1. **スパイク: auto mode でフックの ask がプロンプトになるかを実証**（未知リスク先行）。→ 手動テスト No.1。**ゲート**: 成り立たなければステップ 2 以降に進まず、計画をやり直す。
2. **判定の入口の作り替え・破壊的 SQL・`rm -rf` の是正**（4-2 の (1)(2)(4)）と、既存テストの期待値の更新（4-3 の push・checkout）。新規テストには (1)(2)(4) のケースを先に入れる。ステップ 1 の完了が前提。→ TC-01（(1)(2)(4) の部分）・TC-02・TC-03・TC-04・TC-05・TC-10・TC-11 参照
3. **コンテナ内の危険操作・外部送信・実行ファイルの中身**（4-2 の (3)(5)(6)(7)）と、そのテストケース。ステップ 2 の完了が前提。→ TC-01（全件）・TC-10 参照
4. **`.claude/settings.json` の整理**（4-4）。ステップ 3 の完了が前提（見張りの強化を先に入れる順序の制約。コミットもこの順にする）。→ TC-06・TC-07・TC-08 参照
5. **danger-ops.md の追記**（4-5）。ステップ 4 と並行してよい。→ TC-09 参照
6. **I146 マージ後の取り込み**（マージ前に必須）。I146（#260）が develop にマージされたら、develop を本ブランチへ取り込み、`pretooluse_guard.py`・`.claude/settings.json` の競合を解消する。I146 が足した解除経路にも (1) の入口（DANGER_OK=1 で ask）を当てる。I146 マージ前に `/test` まで進んだ場合は、ここで止めて待つ。→ TC-12 参照
7. **新しいセッションでの確認**（設定はセッション開始時に読まれるため）。ステップ 4・6 の完了が前提。→ 手動テスト No.2〜No.4 参照

サービスの再起動は不要（アプリのコードを変えないため）。設定の反映には Claude Code のセッションを開き直す。

## 6. テスト計画
### 自動（`docs/tests/open/I174_auto_test.md`）
- テストレベル: すべて決定論の単体テスト（フックへ JSON を入れて exit code と ask の JSON を確かめる bash スクリプト）と、ファイルの静的検査（`grep` / `json.tool` / `py_compile` / `bash -n`）。アプリの pytest・E2E は、アプリのコードを変えないため対象外。
- TC と受け入れ条件の対応:

| TC | 内容 | AC |
|---|---|---|
| TC-01 | 新規 `test_pretooluse_container_guard.sh` | AC-4〜AC-9 |
| TC-02 | `test_pretooluse_push_guard.sh` | AC-5・AC-10 |
| TC-03 | `test_pretooluse_checkout_guard.sh` | AC-5・AC-10 |
| TC-04 | `test_pretooluse_worktree_guard.sh`（変更なし・回帰） | AC-10 |
| TC-05 | `test_adversarial_trigger.sh`（変更なし・回帰） | AC-10 |
| TC-06 | settings.json の JSON 構文 | AC-1〜AC-3 |
| TC-07 | 外した ask が無く、残す ask がある | AC-1・AC-2 |
| TC-08 | `Write(` が無い | AC-3 |
| TC-09 | danger-ops.md の追記 | AC-11 |
| TC-10 | guard の構文 | — |
| TC-11 | 新規テストの構文 | — |
| TC-12 | I146 マージ後の `test_pretooluse_gh_pr_guard.sh` | AC-10 |

- 再発防止: 破壊的 SQL の見逃しと `rm -rf` の止めすぎは既存の不具合なので、TC-01 に再現ケース（`-c "DROP ..."`・`-c '...'`・`rm -rf /tmp/xxx` が解除できること・grep の検索文字列に反応しないこと）を入れる。
- 偽合格の防止: TC-01 は判定の呼び出しを無効化した複製で素通しになることも確かめる。TC-07・TC-08・TC-09 は、実装前（違反がある状態）に実行して不合格になることを計画時点で確かめた（auto_test の実施記録）。

### 手動（`docs/tests/open/I174_manual_test.md`）
- No.1: フックの ask が auto mode でプロンプトになる（ステップ 1・新しいセッション・Human 目視）
- No.2: pytest にプロンプトが出ない（AC-12・新しいセッション）
- No.3: DANGER_OK=1 付きの危険操作にプロンプトが出る（新しいセッション）
- No.4: 外部送信にプロンプトが出る（新しいセッション）

## 7. ロールバック
- PR を revert する（`.claude/settings.json`・guard・テスト・danger-ops.md が一緒に戻る）。データの変更は無い。
- 一時的に戻すだけなら、`.claude/settings.json` の ask に `Bash(docker compose exec *)` などを戻して、セッションを開き直せばよい（guard の強化は残っても害はない）。

## 8. Risk & 回避策
| # | リスク | 回避策 |
|---|---|---|
| R1 | auto mode でフックの ask がプロンプトにならない | ステップ 1 のスパイクをゲートにする。不成立なら計画をやり直す |
| R2 | 誤検知で確認や停止が増える（例: `grep` の検索、テストスクリプト） | 判定を「実行されるコード」と「トークン」に限る。ホストの bash スクリプトと `scripts/claude/` を中身の判定から外す。TC-01 に誤検知しないケースを入れる |
| R3 | 見逃し（変数・eval・base64・`docker compose cp` 後の実行・コンテナ内で作ったファイル） | 受け入れる残余リスクとしてイシューと danger-ops.md に明記する。auto mode の判断を第 2 層にする。Claude は回避の書き方を使わない |
| R4 | I146 との競合（guard +256 行・settings.json +9 行） | マージを I146 の後にし、ステップ 6 で取り込む。I146 の解除経路にも (1) を当て、I146 のテスト（TC-12）を合格させる |
| R5 | 権限の変更が今のセッションに効かず、「直った」と誤認する | 手動テスト No.2〜No.4 は新しいセッションで行う |
| R6 | compose のマウントを変えると、(6) の読み替え表が古くなる | 表を guard の定数にまとめ、`docker-compose.yml:48-49` を参照するコメントを付ける |
| R7 | `DANGER_OK=1 bash scripts/claude/wt-remove.sh` の中の `down -v` は、guard から見えない（既存の挙動のまま） | 本計画では変えない（スクリプト自身が DANGER_OK=1 を要求する）。気づいた点としてレビュー文書に記録する |
| R9 | celery の起動（`.delay(` / `.apply_async(`・`celery ... call`）は、メールや OpenAI と関係のないタスクにも反応する。今後タスクが増えると確認が増えうる（2026-10-16 計画レビュー Warning 2） | 現状、shell から celery タスクを起動する作業はまれで、送信の有無はタスクの中を見ないと分からないため、広めに確認を出すほうを選ぶ。確認が頻繁に出るようになったら、送信するタスクの名前の一覧で判定する形に絞る（その時点で別イシュー）。発動の目安: 送信しないタスクへの確認が 1 セッションで 5 回以上出たら、または作業記録の再判定（TC-15）で celery の確認が記録の 0.5% を超えたら起票する（2026-10-21 計画レビュー Warning） |
| R10 | ステップ 1 で、対話セッションの一部（wt-harness・版 2.1.300・permissionMode default）では、guard が ask を返しても承認画面が出ずに実行されると分かった（auto mode の対話セッションと、非対話の 3 モードでは承認が求められた。手動テスト No.1 の実結果） | 本計画の前提（auto mode）は成り立つので進める。ただし、DANGER_OK=1 の ask 化と外部送信の ask は、この条件のセッションでは効かない。手動テスト No.3・No.4 は auto mode で行う。原因（版・モード・セッション固有のどれか）の切り分けと Claude Code への報告は、本イシューの範囲外としてユーザーに引き継ぐ（I146 の手動テストの「gh pr 系が止まらない」も同じ現象の可能性が高い）。手動テスト No.3・No.4 で承認画面が出ずに実行された場合は、見張りの判定そのものを非対話で確かめる（`claude -p` の非対話モード、または JSON を `python3 scripts/claude/hooks/pretooluse_guard.py` に渡して出力の `permissionDecision: ask` を確認）。この場合は「見張り側 OK・画面側の現象」として記録する（2026-10-21 計画レビュー Warning） |
| R8 | `\bdd\b`（437 行目）が `dd` という単語にも反応する止めすぎ | 2026-10-17 に範囲へ入れて解消（0-11）。当初は範囲外としたが、敵対的レビューで High とされ、`YYYY-MM-DD`・grep の検索語で DANGER_OK=1 でも解除できない停止が作業中に実際に起きたため |

## 9. 承認ポイント
- [ ] 計画内容（4 章の変更点・3 章の影響範囲）
- [ ] 判定を 3 種類（常に止める／危険操作＝DANGER_OK=1 で人の確認／外部送信＝人の確認）に分ける設計
- [ ] イシューからの範囲の変更 2 点: ①`rm -rf` の判定をトークン単位にし、grep やヒアドキュメントへの誤反応も直す（イシューでは「含まない」だった。本セッションで 2 回起きたため含める）②実行ファイルの中身の判定から、ホストの bash スクリプトと `scripts/claude/` を外す（テストスクリプトと guard 自身が判定パターンを入力データとして含むため）
- [ ] Danger Ops: 無（権限設定とフックの変更のみ）
- [ ] テスト計画（自動 TC-01〜TC-12・手動 No.1〜No.4）
- [ ] マージ順（I146 の後）と作業場所（primary・例外）

## レビュー結果
- [20261021_1336 判定: ✅ 完了（Blocker 0 件）](../../reviews/I174_plan_review_20261021_1336.md)
- [20261021_0900 判定: ✅ 完了](../../reviews/I174_plan_review_20261021_0900.md)
- [20261019_0005 判定: ✅ 完了](../../reviews/I174_plan_review_20261019_0005.md)
- [20261017_1220 判定: ✅ 完了](../../reviews/I174_plan_review_20261017_1220.md)
- [20261016_1621 判定: ✅ 完了](../../reviews/I174_plan_review_20261016_1621.md)

## セキュリティレビュー結果

**実施日**: 2026-10-21（/plan-issue-review 20261021_1336 の高リスク判定 Yes を受けて。fix-loop 0-15 の後・831c7bf／b942c6c 時点）

対象: アプリのコード（backend / frontend）の変更なし。対象は PreToolUse の見張り `scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`・テスト類。

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Blocker | 入力検証 / OWASP（コマンドインジェクション・セキュリティ設定ミス） | **見張りが判定のために実行する git（`_git_run`：`rev-parse`・`status --porcelain`）に、判定対象のコマンドに書かれた `-c key=val`・`--git-dir`・`--work-tree`・`GIT_DIR=` と、`cd`／`-C` の先のリポジトリの設定がそのまま効く。** git は `core.fsmonitor`・clean/smudge フィルタ（`filter.*.clean`・`filter.*.process`）などの設定で任意のコマンドを実行するため、**人の承認より前に、見張り自身がコマンドを実行する**。実測（mktemp -d）: `git -c core.fsmonitor='touch PWNED' checkout -- f` を判定させるだけで PWNED が作られた（判定結果は 2 でも実行は済んでいる）。`cd <core.fsmonitor を設定したリポジトリ> && git checkout -- g` も同じ。計画 0-14（実行場所の共通部品）で入った。I174 以前は見張りの作業ディレクトリ（信頼できるこのリポジトリ）でだけ git を実行していた | **禁止**: 判定対象のコマンドから取った `-c`・`--config-env`・`GIT_*` 環境変数・設定ファイルの指定を、見張りが実行する git に渡さない。**必須**: 見張りが git を実行してよい場所は、このリポジトリとその worktree（見張りの作業ディレクトリで `git worktree list --porcelain` から得た一覧の配下・realpath で比較）だけにする。それ以外（一時ディレクトリ・別のリポジトリ・`--git-dir`／`GIT_DIR` の指す先が一覧の外）では git を実行せず「場所が読めない」として確認にする。実行する git には `-c core.fsmonitor=false`・`-c core.hooksPath=/dev/null` 等の無害化を付け、`status` には `--no-renames`・`-c status.showUntrackedFiles=no` を付ける（フィルタの実行を避けられない場合は、信頼できる場所だけで実行する上の条件で守る）。テスト: 上の 2 つの実測を自動テストにし、PWNED が作られないことと判定（確認または停止）を確かめる |
| High | 認証・認可（承認の強制） | settings.json の ask から `docker compose exec` 等を外し、危険操作の人の承認（DANGER_OK=1 の ask 化）と外部送信の確認を、フックの `permissionDecision: ask` に頼る。R10（wt-harness の対話セッション 2.1.300・default／2.1.301 の新規 auto mode でも、フックの ask で承認画面が出ずに実行された）の条件では、**確認が実質無効**になる。停止（exit 2）は効く | 既知・受け入れ済み（R10）。必須: 手動テスト No.3・No.4 を auto mode で行い、画面が出ない場合は「見張り側 OK・画面側の現象」として記録する（計画 R10）。Claude Code への報告はユーザーに引き継ぎ済み。停止にすべきもの（危険操作）は確認に格下げしない（DANGER_OK=1 が無ければ停止のまま） |
| Medium | 認証・認可（最小権限） | コンテナ内の操作の人の確認（settings.json の ask）を外し、見張りの許可リストだけで素通しを決める。見張りの読み違いがそのまま素通しになる | 許可リスト方式（fail-safe）・安全網・本物の bash との差分テスト・作業記録の再判定・総当たりのテストで守る（0-9〜0-15）。意図的な回避（変数・eval・base64）は脅威モデルの外（danger-ops.md に「使わない」と明記） |
| Medium | 入力検証（読み違い） | 場所・対象が 1 つに決まらない git の書き換えは確認（0-15）。確認は R10 の条件で効かない可能性があり、その場合は素通しと同じになる | 停止（場所も対象も決まる形・場所に依存しない危険操作）は効く。R10 の切り分けを優先して進める（上の High と同じ） |
| Low | 機密情報 | 見張りの理由表示（stderr）に判定したコマンドの一部が出る。コマンドに秘密情報を書いた場合に記録に残る | 既存の挙動（I174 前から）。秘密情報をコマンドに直接書かない運用（danger-ops.md の secrets）で扱う |
| Low | 機密情報 | 作業記録の再判定（`guard_corpus_diff.py`）は手元の作業記録の Bash コマンドを `~/.cache/claude-guard-corpus/` に抜き出す | 0700/0600 で作成・リポジトリに入れない（公開リポジトリのため）。対処済み |
| Low | ファイル操作 / 可用性 | 見張りが `git status -- :/` を場所ごとに実行するため、大きなディレクトリで判定が遅くなる | git の書き換え操作を含むコマンドのときだけ実行する。タイムアウトの導入は Blocker の修正と合わせて検討 |
| — | マルチテナント | なし（アプリのコード変更なし） | — |
| — | 外部通信 | 見張りは外部と通信しない（外部送信の確認は判定するだけ） | — |
| — | 依存ライブラリ | 新規追加なし（Python 標準ライブラリのみ） | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | PreToolUse の見張り（Bash の判定） | Claude（モデル）が書くコマンド・または取り込んだ外部リポジトリの設定 | `git -c core.fsmonitor=<任意のコマンド> checkout -- f` を書く／`.git/config` に fsmonitor やフィルタを仕込んだリポジトリへ `cd` して git の書き換えを書く | 見張りが判定のために実行する git で、コマンドや外部リポジトリの設定によるコマンド実行が起きない | Yes: 上の 2 形で PWNED が作られないこと（Blocker の修正と同時に追加） | No | 信頼する場所（このリポジトリと worktree）の `.git/config` は信頼する前提 | Blocker |
| 2 | 見張り（危険操作の承認） | Claude | `DANGER_OK=1` を自分で付けて危険操作を通す | 人の承認画面が出る（確認）か、出ない環境では止まる | Yes: 既存（DOK1〜3・G7 など） | Yes: 手動 No.3・No.4（R10） | R10 の条件では確認の画面が出ない | High |
| 3 | 見張り（コンテナの許可リスト） | Claude | 許可リストにある名前で書き込み・外部送信を行う（`sed -i`・`curl -d` 等のオプション） | オプションまで見て許可リストから外す | Yes: 既存（container テスト） | No | 意図的な回避（変数・eval）は範囲外 | Medium |
| 4 | 見張り（場所・対象の読み違い） | Claude | `cd -`・`( … )`・`$(…)`・xargs で、未コミット変更の取り消しや保護ブランチへの push の判定をずらす | 場所・対象が 1 つに決まらなければ確認 | Yes: 既存（G63〜G80・XP72〜XP75・FG-AMB） | No | R10 の条件では確認が効かない | Medium |
| 5 | 本物の bash との差分テスト | 開発者 | 生成したスクリプトを本物の bash で実行する | 無害なコマンドと、印を出すだけの関数に置き換えた git・rm だけを使い、一時ディレクトリで動かす | Yes: 既存（STUBS・DANGERS の固定一覧） | No | DANGERS に本物の危険コマンドを書き足す変更はレビューで防ぐ | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 1件 | 1件 |
| High    | 1件 | 1件 |
| Medium  | 2件 | 2件 |
| Low     | 3件 | 1件 |

### 残余リスク処遇
（/retro で決定する）

## セキュリティレビュー結果（再実施）

**実施日**: 2026-10-21（fix-loop 0-16・9504316 の後）

前回（上の「セキュリティレビュー結果」）の Blocker への対応を確かめ、見張りが外部コマンドを実行する箇所をすべて洗い直した。アプリのコード（backend / frontend）の変更なし。

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| （解消） | 入力検証 / OWASP（コマンドインジェクション） | 前回の Blocker（見張りが判定のために実行する git に、コマンドの設定や cd の先のリポジトリの設定が効く） | 0-16 で対処済み。見張りが git を実行する場所を「このリポジトリと worktree」に一致で限り（入れ子のリポジトリ・偽の git-dir・シンボリックリンクで外へ出る形は realpath と `.git` の有無で除外）、git-dir と最上位を明示、コマンドの `-c`・環境変数を渡さない。再現スクリプト（core.fsmonitor と clean フィルタ）で、判定中の実行は修正前 6 件 → 修正後 0 件。自動テスト G81〜G87・FG-TRUST |
| High | 認証・認可（承認の強制） | R10（一部のセッションでフックの ask の承認画面が出ない）。前回と同じ | 前回と同じ（既知・受け入れ済み。手動テスト No.3・No.4 で確認・記録） |
| Medium | 認証・認可（最小権限） | コンテナ内の操作の人の確認を、見張りの許可リストに置き換える。前回と同じ | 前回と同じ |
| Medium | 入力検証（読み違い） | 場所・対象が 1 つに決まらない形の確認が、R10 の条件で効かない。前回と同じ | 前回と同じ |
| Low | 入力検証（残余） | 信頼するこのリポジトリの `.git/config` を、それより前のコマンド（`git config filter.x.clean …`・`core.fsmonitor`）で書き換えた場合は、見張りの git でもその設定が効く | I174 以前から同じで、本物の git も同じ設定で動く。設定を書き換えるコマンド自体が先に判定・実行される。0-16 の残余リスクとして記録済み |
| Low | 入力検証 | 見張りのほかの git 呼び出し（`_repo_relative`・`_worktree_roots`・`_current_worktree_root`）は、見張りの作業ディレクトリで固定の引数（`rev-parse --show-toplevel`・`worktree list`）だけを実行する。判定対象のコマンドの値は使わず、設定でコマンドが実行される操作でもない | 対処不要（確認済み） |
| Low | 機密情報 | 前回と同じ（理由表示にコマンドの一部が出る・作業記録の抜き出しは 0700/0600） | 前回と同じ |
| — | マルチテナント・外部通信・依存ライブラリ | なし | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | 見張り（Bash の判定） | Claude・または取り込んだ外部リポジトリの設定 | `git -c core.fsmonitor=…`／外のリポジトリ・入れ子のリポジトリ・偽の git-dir（core.fsmonitor・clean フィルタを仕込む）で git の書き換えを書く | 判定中にコマンドが実行されない。場所に依存する判定は確認 | Yes: G81〜G87・FG-TRUST（実装済み） | No | 信頼するリポジトリ自身の .git/config の書き換え（Low） | 解消（前回 Blocker） |
| 2 | 見張り（シンボリックリンク） | Claude | リポジトリ内のシンボリックリンクから外のリポジトリへ `cd` して git の書き換え | realpath で比較し、外なら確認 | No（realpath の比較で設計上保証。必要なら次の周で追加） | No | なし | Low |
| 3 | 見張り（危険操作の承認） | Claude | `DANGER_OK=1` を自分で付ける | 前回と同じ | Yes: 既存 | Yes: 手動 No.3・No.4 | R10 | High |
| 4 | 見張り（コンテナの許可リスト・場所と対象の読み違い） | Claude | 前回のシナリオ 3・4 と同じ | 前回と同じ | Yes: 既存 | No | 前回と同じ | Medium |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 1件 | 1件 |
| Medium  | 2件 | 1件 |
| Low     | 3件 | 1件 |

### 残余リスク処遇
（/retro で決定する）
