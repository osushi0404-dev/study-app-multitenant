# I174 敵対的レビュー記録（第 1 周・設計判断のためユーザー確認で停止）

- 対象: ブランチ `feature/I174-guard-based-permission-review`（head f3ce221）
- 基本レビュー: `docs/reviews/I174_code_review_20261016_1702.md`（FINAL_VERDICT: OK・RISK: YES）
- 周回: 第 1 周・エージェント 4（固定 3 観点＋動的 1 観点「文書・設定・権限の整合」）

## 第 1 周の集計
- NEW_CRITICAL: 1 ／ NEW_HIGH: 12（観点ごとの合計。重複を含む）

## findings（重複をまとめたもの）
| # | 重大度 | 内容 | 出した観点 |
|---|---|---|---|
| 1 | Critical | ヒアドキュメント・パイプでコンテナ内の `psql`・`manage.py shell`・`manage.py dbshell`・`sh`・`redis-cli` に流し込む破壊的 SQL・`.delete()`・`rm -rf`・`FLUSHALL` を判定しない（`_stdin_file` が `<<` を除外・パイプの左側を見ない）。以前は `docker compose exec *` の ask で止まっていた | ロジック回避・要件・文書整合 |
| 2 | High | shlex が語に付いた `;` `&&` `$(` `` ` `` `(` を分割しないため、`echo hi;rm -rf backend`・`(rm -rf x)`・`$(rm -rf x)`・`true;redis-cli FLUSHALL`・`true;dropdb app` が素通り（旧 guard の正規表現は rm -rf を止めていた＝後退） | ロジック回避 |
| 3 | High | `django-admin flush`・`python -m django flush`・`manage.py dbshell -- -c 'DROP ...'`・`dbshell < dump.sql` が素通り | ロジック回避・要件 |
| 4 | High | `bash -lc` / `sh -ec` / `bash -xc`（短いオプションのまとめ書き）の中身を展開しない | ロジック回避 |
| 5 | High | `git -C <path> reset --hard`・`git --no-pager reset --hard`・`docker compose -f x down -v`・`-p name down -v`・`git -C . push --all` が素通り（正規表現の弱さは既存だが、ask 撤廃で guard が唯一の決定論ゲートになった） | ロジック回避・要件 |
| 6 | High | 独自の管理コマンド `seed_e2e --flush`（内部で `call_command('flush')`）が素通り | 要件 |
| 7 | High | 秘密情報: 実在する秘密ファイルは `backend/.env` のみだが、deny は `./.env` 固定で一致しない（allow の `Edit(backend/**)` に一致・既存）。exec の ask 撤廃で `docker compose exec backend cat .env`・`printenv` も確認なしで通る。イシュー本文の「deny の .env も Edit 側で拒否済み」は事実と違う | 文書整合 |
| 8 | High | テスト: `$M` に `python` と `-c` が含まれ、`python -c` の枝が shell の枝を覆い隠す。shell の判定を消しても A17〜A21・X1〜X4・X8〜X10 が合格 | テスト偽合格 |
| 9 | High | テスト: `DANGER_OK=1 rm -rf /*` のケースが無く、hard-block から `/*` を外しても合格 | テスト偽合格 |
| 10 | High | コンテナ内 `sh <スクリプト>` の中身を Python 用パターンでしか見ず、`python manage.py flush` を見落とす（テストも 0 件） | テスト偽合格 |
| 11 | Medium | `docker volume rm`・`docker volume prune`・`docker system prune --volumes`・`docker compose rm -v`・`git clean -fdx`・`find -delete` が対象外 | ロジック回避・要件 |
| 12 | Medium | `psql -c"..."`（値の付着）・`pg_restore -cd`・`qs.update(...)`（変数経由）・`sendtestemail`・`send_mail` の別名・`email_user()`・`send_verification_email()`・`PasswordResetForm().save()` が対象外 | ロジック回避・要件 |
| 13 | Medium | danger-ops.md の「どれで実行しても止める」が、secrets 操作・`-f` 付き down -v などに当てはまらない | 要件・文書整合 |
| 14 | Medium | TC-07 の「残す 7 行」は settings.json 全体での存在確認で、ask から allow に移しても合格する | テスト偽合格 |
| 15 | Medium | パターンごとに確かめるテストの不足（apply_async・mail_admins・EmailMessage・openai.・call_command migrate zero・reset_db・ALTER TABLE・eval 展開・`--command=`・`-R`・`_REDIRECT_RE`・`_strip_env`） | テスト偽合格 |
| 16 | Low | 誤検知: `psql -c "select 'drop' as x"`・SQL 語を含む文字列リテラル・`migrate app 0005`（前進も巻き戻し扱い）。巨大な 1 トークンで処理時間が 2 乗に増える | ロジック回避 |

## 判断（オーケストレーター）
- 個々の穴の修正では収束しない構造的な問題（「危険なものを列挙して止める」方式＋ask の撤廃で、見落としが確認なしで通る）と判断した。修正方針は設計判断に当たるため、SKILL 3-3 に従いユーザーに確認して停止する。
- 選択肢: ①コンテナ内は「安全と確かめられたものだけ通し、それ以外は確認」に切り替える（推奨）②現方式のまま全件修正 ③ exec の ask を戻し、範囲を guard の不具合修正と設定整理に縮小。いずれでも #7（秘密情報）は修正する。

VERDICT: HIGH
