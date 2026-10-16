# I174 敵対的レビュー記録（第 3 周・上限到達・未収束）

- 対象: ブランチ `feature/I174-guard-based-permission-review`（head d079b26・計画書 0-9 の方針で修正した後）
- 前周: `docs/reviews/I174_adversarial_review_20261016_1745.md`（第 1 周）・`docs/reviews/I174_adversarial_review_20261016_1930.md`（第 2 周）
- 周回: 第 3 周（上限）・エージェント 4（固定 3 観点＋動的 1 観点「余計な確認・誤ブロック」）。総エージェント数 12（上限 15 以内）
- 今回から重大度の基準に脅威モデル「事故」を明示した（Claude が普段書くコマンドで起こるものだけを Critical/High とする）

## 第 3 周の集計
- NEW_CRITICAL: 1 ／ NEW_HIGH: 7

## findings（重複をまとめたもの）
| # | 重大度 | 内容 | 出した観点 |
|---|---|---|---|
| 1 | Critical | `-c "$(cat <<'EOF' … EOF)"` / `-c "$(cat file.py)"` で渡したコード・SQL を判定しない（`$(...)` が `__SUBST__` に置き換わり、`-c` の値が「見えて危険なし」扱い）。compose の shell の `.delete()`・`.delay()`・`os.environ`、素の docker exec・ホストの psql の `DROP` / `TRUNCATE` が素通り | ロジック回避 |
| 2 | High | ホストの `manage.py shell` のコードにも「Django らしい語があるときだけ判定」を当てていた。Django 5.2 はモデルを自動で読み込むので、import なしの `Problem.objects.all().delete()` 等が素通り | ロジック回避 |
| 3 | High | 改行をはさんだメソッドチェーンの `.update(`（`.filter(⏎...⏎).update(`）と関連マネージャ経由の `s.problems.update(` を見逃す（第 2 周の誤検知対策 `[^;\n]*?` の副作用） | ロジック回避 |
| 4 | High | `cache.clear()`・`get_redis_connection().flushall()` が素通り（cache は sessions・celery・レート制限と同じ Redis db 0 のため、`FLUSHDB` と同じ結果） | 要件 |
| 5 | High | ループでの全件の `.save()`（`for u in User.objects.all(): ...; u.save()`・内包表記）が素通り | 要件・ロジック回避 |
| 6 | High | ホストで記録を書き換える Python ヒアドキュメント（`open(p,'w')`）が exit 2 で停止。本文の「connection」「settings.」「manage.py」等の語で Django のコードと判定され、書き込みモードの `open(` が危険操作になる。作業記録で約 50 件中 12 件 | 余計な確認 |
| 7 | High | テスト: `grep -rn SECRET_KEY .`（サブディレクトリの探索・既定の `.`）を確かめるケースが無い | テスト偽合格 |
| 8 | High | テスト: ホストの `curl` で登録 API・パスワード再設定 API を叩くケースが無い（X27 はコンテナの許可リストの確認に覆い隠されている） | テスト偽合格 |
| 9 | Medium | `call_command('seed_e2e', flush=True)`・`call_command('migrate','problems','0003')`・`migrate --fake` / `--prune` が compose の許可リストを通る | 要件・ロジック回避 |
| 10 | Medium | パイプで受ける psql・manage.py shell（素の docker exec とホスト）が素通り（`cat dump.sql \| docker exec -i db psql`） | ロジック回避 |
| 11 | Medium | 誤判定: ホスト側の出力リダイレクト（`docker compose exec ... pytest > /tmp/log`）がコンテナ内の書き込み扱いで確認・`os.environ.setdefault('DJANGO_SETTINGS_MODULE', ...)` が秘密情報の参照扱い・scratchpad の検証スクリプトの停止・`sed -n '/a/,/b/p'`・`docker inspect --format '{{range .Mounts}}'` | 余計な確認・ロジック回避 |
| 12 | Medium | AC-13 の文面（イシュー・計画 0-1）がまだ素の `docker exec` を許可リストの対象に含めている | 要件 |
| 13 | Medium | deny の `Edit(**/.env.*)` が、追跡済みで秘密を含まない `.env.example` 等の編集まで拒否する（I170 の作業と衝突） | 要件 |
| 14 | Medium | ホストの秘密情報の漏れ: `echo $OPENAI_API_KEY`・`gh auth status -t`・`git diff --no-index ... backend/.env`・ホストの `python3 -c "open('backend/.env')"`・ホストの `python3 -c "requests.post('.../auth/register/')"` | 要件・ロジック回避 |
| 15 | Medium | テスト: diffsettings（ホスト）・`docker inspect -f '{{json .Config.Env}}'`・`_SECRET_VAR_RE`（素の docker exec）・書き込みモードの `open(`・`_UNSAFE_SQL_RE`（`WITH ... DELETE`・`pg_terminate_backend`）・DANGER_OK=1 が途中にある否定ケース・`ruff format` / `npx --fix` / `curl -o` の各条件が未検証。第 2 周の生き残りのうち、秘密情報の読み取りコマンド 25 個・`{ }` `!` `watch` `flock`・読めないシェル（パイプで sh）・素の docker exec の `-e` / `-u` / `--user=`・try/except の ask 化・settings の `disableAllHooks` が未修正 | テスト偽合格 |
| 16 | Low | `git checkout -f` / `git switch -f` で未コミットの変更が消える（I174 の前から）・`docker compose config \| grep published`（runbook の手順）が確認・push 判定がヒアドキュメント本文に反応・二重引用符の中の `<<` でヒアドキュメントの切り出しがずれる・frontend の `/app` を backend に読み替える | 要件・余計な確認・テスト偽合格 |

## 承認待ちの実測（作業記録 2,627 件・第 3 周の余計な確認の観点）
| 区分 | I174 の前 確認+停止 | d079b26 確認+停止 |
|---|---|---|
| docker compose exec/run（先頭で厳密に判定） | 133 | 67（50% 減） |
| 素の docker exec/run | 12 | 28（増えた 17 件のうち 9 件は使い捨て DB の DROP の停止＝設計どおり） |
| ホスト | 62 | 80（増加分の多くは #6・#11 の誤判定） |

## 判断（オーケストレーター）
- 上限 3 周に達し、新規 Critical 1・High 7 が残った。SKILL 3-2 に従い自動 OK にせず「上限到達・未収束」として打ち切り、最終判定を HIGH に固定してユーザーにエスカレーションする。
- 第 3 周の指摘は、どれも具体的な修正方針が立つもの（設計の変更は不要）。次の作業は `/fix-loop I174`（標準の手順）。

VERDICT: HIGH
