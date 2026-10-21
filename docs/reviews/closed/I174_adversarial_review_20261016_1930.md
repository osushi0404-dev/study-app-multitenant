# I174 敵対的レビュー記録（第 2 周・方針判断のためユーザー確認で停止）

- 対象: ブランチ `feature/I174-guard-based-permission-review`（head cf8607c・コンテナ内の許可リスト方式に切り替えた後）
- 前周: `docs/reviews/I174_adversarial_review_20261016_1745.md`（第 1 周）
- 周回: 第 2 周・エージェント 4（固定 3 観点＋動的 1 観点「余計な確認・誤ブロック」）

## 第 2 周の集計
- NEW_CRITICAL: 12 ／ NEW_HIGH: 22（観点ごとの合計。重複を含む）

## findings（重複をまとめたもの）
| # | 重大度 | 内容 | 出した観点 |
|---|---|---|---|
| 1 | Critical | `_expand` の `sudo` / `nice` が `rest[idx]`（1 要素）で、`sudo rm -rf /`・`nice docker compose down -v` 等がすべて素通り（旧 guard は止めていた＝後退。テストも 0 件） | ロジック回避・テスト偽合格 |
| 2 | Critical | `xargs rm -rf`（対象をパイプで受ける）・`find -exec rm -rf` が素通り | ロジック回避・テスト偽合格・要件 |
| 3 | Critical | `docker container exec|run` をコンテナ内の操作として扱わず素通り | ロジック回避 |
| 4 | Critical | `-c` の値が複数回のとき最初しか見ない（psql は全部実行・shell は最後が有効） | ロジック回避 |
| 5 | Critical | `curl` の許可が `://` を含む引数だけを宛先として見る。`-d @/app/.env`・`--resolve`・`-x`・POST/DELETE・`-o` 上書きが通る。登録 API・AI API への curl が外部送信と判定されない | ロジック回避・要件 |
| 6 | Critical | 許可リストの `manage.py diffsettings` が秘密（SECRET_KEY・SendGrid・OpenAI のキー）をそのまま表示。`dumpdata` もセッション・トークンを出す | 要件 |
| 7 | Critical | 秘密情報の表示の別経路（`echo $VAR`・`/proc/1/environ`・コード内の `os.environ` / `open('.env')` / `settings.SECRET_KEY`・`sort`/`diff` 等・`cat < .env`・`grep -r`） | ロジック回避・要件 |
| 8 | Critical | 許可リストを「コマンド名」で通し、書き込み・実行のオプションを見ない（`sed -n` の `e`/`w`・`sort -o`・`uniq IN OUT`・`find -fprint/-ok`・`dumpdata -o`・`collectstatic --clear`・`ruff --fix`・`npm audit fix`）。出力先（`>`）も許可の判定に使っていない | ロジック回避・要件 |
| 9 | Critical | psql の読み取り判定の穴（行の途中のメタコマンド `\gexec` / `\!`・`EXPLAIN (ANALYZE)` / `ANALYSE`・`-o` 上書き・`lo_export`・`pg_terminate_backend`） | ロジック回避・要件 |
| 10 | Critical | `docker run` の値付きオプション（`--mount`・`--platform` 等）を知らず、サービス名とコマンドの位置を取り違えて許可リストを通る。`--entrypoint` の中身を見ない | ロジック回避・要件 |
| 11 | High | 包むコマンドの漏れ（`setsid`・`stdbuf`・`ionice`・`su -c`・`script -c`・`busybox`・`time -p`・`nohup --`・`command -p`・`exec -a`） | ロジック回避・要件 |
| 12 | High | Python コードの危険・外部送信の揺れ（`.delete ()`・`_raw_delete`・コメントや `WITH` で始まる SQL・`shutil.rmtree`・`os.system`・`subprocess`・`smtplib`・`requests`・`urllib`・`reverse('register')`） | ロジック回避・要件 |
| 13 | High | ホストの秘密情報の表示の漏れ（`grep -rn <キー> backend/`・`docker container inspect`・`docker cp` / `docker compose cp`・`gh auth token`） | 要件 |
| 14 | High | `$(...)` の中のヒアドキュメント（`gh pr create --body "$(cat <<'EOF' ...)"`・`git commit -m "$(cat <<'EOF' ...)"`）で IndexError → 毎回確認（PR・コミット作成の正規手順） | 余計な確認 |
| 15 | High | 「承認待ち 9 割減」の主張は誤り。作業記録 2,806 件の実測で、`docker compose exec/run` は 204→69（66% 減）だが、もともと確認の無かった素の `docker exec/run` が 3→103 に増え、docker 全体では 207→172（17% 減） | 余計な確認 |
| 16 | High | `/test` の E2E 手順 `docker compose --profile e2e run --rm e2e`（コンテナ内のコマンド名なし）が毎回確認 | 余計な確認 |
| 17 | High | テスト: 包むコマンド・区切り（`&&` `||` `&` 改行 `|&`）・外部送信（コンテナの確認に覆い隠し）・秘密情報・コンテナ許可リストの各枝・流し込み・`$(...)`（`(` の区切りに覆い隠し）を壊しても全件合格 | テスト偽合格 |
| 18 | High | `test_settings_permissions.sh` が PreToolUse フックの登録削除・`bypassPermissions`・`Bash(*)` の allow 追加を見逃す | テスト偽合格 |
| 19 | Medium | 誤ブロック・余計な確認: `cache.delete('k')`（exit 2）・1 行の shell での dict の `.update(`・ホストで文書を書き換える Python の文字列に危険語・外部送信の語が入っているだけで止まる／確認・`docker inspect -f '{{.State.Status}}'`・`psql -tAc`・CTE（`WITH ... SELECT`）・`sh -c "cd /app && ..."`・grep のパターン引数の `.key` | 余計な確認 |
| 20 | Medium | `migrate`（前進）で未適用の破壊的マイグレーションが走る（danger-ops の「破壊的マイグレーション」と不整合・文書に無い） | 要件 |
| 21 | Medium | `celery` の許可が `inspect` の語の位置を見ない（`purge -f -X inspect`）・`python3 -W ignore -m django flush` がホストで素通り・`-w` での作業ディレクトリ変更と `..` を含むパスの読み替えのずれ | ロジック回避・要件 |
| 22 | Medium/Low | テスト: try/except の ask 化・docker のオプション読み飛ばし・ヒアドキュメント／ヒアストリング系・細かい危険操作の枝・許可リストの縮小（承認待ちが増える後退）が未検証。ケース表の G0 の転記が途中で切れている | テスト偽合格 |

## 判断（オーケストレーター）
- #15 で、I174 の目的（承認待ちの削減）に対して、現方式の効果が想定より大きく小さいことが分かった。さらに #1〜#10 の穴を塞いで許可リストを厳しくすると、確認はさらに増える。安全と速さのどちらを優先するかは価値判断に当たるため、SKILL 3-3 に従いユーザーに確認して停止する。
- 選択肢: ①許可リスト方式は `docker compose exec/run` だけに当て、素の `docker exec/run` は I174 の前と同じ列挙方式に戻す（推奨）②全体を列挙方式に戻す ③ `docker compose exec` の ask を戻す。いずれでも #1・#2・#14・#16・#19 の不具合は直す。
- 敵対的レビューは上限 3 周のうち 2 周を使った。

VERDICT: HIGH
