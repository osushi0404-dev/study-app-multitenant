# 危険操作（Danger Ops）ルール

以下は原則「計画書に明記」＋「ユーザー明示承認」＋「PRに danger-approved」＋「実行時 DANGER_OK=1」でのみ実行する。

## 例
- DB: DROP / TRUNCATE / WHEREなし UPDATE・DELETE / 大量更新・削除 / 破壊的マイグレーション
  - `manage.py flush` / `sqlflush` / `reset_db`（DB 全消去・`django-admin` / `python -m django` も同じ）・`migrate <app> <移動先>`（巻き戻し。`zero` を含む）・`loaddata`（既存の行の上書き）・`seed_e2e --flush`
  - ダンプ・SQL ファイルの流し込み（`psql -f <ファイル>` / `psql ... < <ファイル>`・`dbshell < <ファイル>`・`pg_restore --clean`）・`dropdb`
  - `manage.py shell` / `python -c` / ヒアドキュメントで渡す Python の `.delete()`・QuerySet の一括 `update()`・`bulk_update()`・`call_command('flush')` など
- Git: force push / reset --hard / 大規模rebase / `git clean -f`（`-d`・`-x` の有無を問わない。追跡されていないファイルの削除）/ **未コミット変更があるファイルへの `git checkout/restore <file>`**（下記注記。コミットから戻す形〔`git checkout HEAD <file>`・`git restore -s`〕はステージ済みの変更も対象・`git rm -f`・`git checkout-index -f`・`git read-tree -u --reset`・`git mv -f` の上書きを含む）/ push の宛先・強制を変える設定（`remote.*.push` を保護ブランチ・`+`・`:` に・`push.default` を `matching`／`upstream`／`tracking` に・`remote.*.mirror true`）/ `clean.requireForce` を偽にする設定
- Docker: down -v / --volumes（データ消失）・`docker compose rm -v`・`docker volume rm|prune`・`docker system prune --volumes`・`redis-cli FLUSHALL` / `FLUSHDB`（ログイン状態・celery の待ち行列・レート制限カウンタの全消去）
- Files: rm -rf（`-f` の無い `rm -r` も同じ。端末につながっていない実行では確認が出ずに全部消える）/ `find -delete`・`find -exec rm`・`xargs rm` / secrets 操作

## 見張り（pretooluse_guard.py）の扱い（I174）

PreToolUse フック（`scripts/claude/hooks/pretooluse_guard.py`）は、コマンドを読み解いてから（行の継続 `\`＋改行を bash と同じ規則でつなぎ、付着した `;` `&&` `|` `( )`・`$(...)`・ヒアドキュメント・`sh -c` / `bash -lc`・`eval`・`env` などを展開してから）、次の順に判定する。

1. **常に止める（解除不可）**: `rm -rf /` と `rm -rf /*`・mkfs・dd・shred・別 worktree への書き込み
2. **危険操作として止める**（exit 2）: 上の「例」のうち、見張りが判定できるもの＝DB の各操作・`git reset --hard`・`git clean -f`・force push / 保護ブランチへの push・変更ありのファイルの checkout / restore / `git rm -f`・push と clean の設定の変更・Docker の各操作・Redis の全消去・`rm -r`・`find -delete` / `find -exec rm` / `xargs rm`。git は `-C`・`cd` の先・`--git-dir` / `--work-tree`・`GIT_DIR=` の場所で判定する。**場所が 1 つに決まらない**（`( … )`・パイプ・`&`・入れ子のシェルの中の cd、`cd -`・`$OLDPWD`・`~-`、先が読めない・存在しない cd）とき、または**戻す対象が読めない**（`$(…)`・変数・xargs・find・中かっこ・`--pathspec-from-file`）うえにその場所に変更があるときは、推測で止めたり通したりせず**確認**にする（場所に依存しない `git push origin main`・`--force`・`reset --hard` 等は停止のまま）。ホスト・`docker exec`・`docker compose exec|run`・`docker-compose` のどれで実行しても同じ
3. **人の確認**: 外部への送信（メール送信・celery タスクの起動・登録 API とパスワード再設定依頼 API・OpenAI）と、秘密情報の表示（`.env` 等の読み出し・`printenv`・引数なしの `env`・`docker compose config`・`docker inspect`）
4. **`docker compose exec|run`（`docker-compose` も同じ）の中の操作は「安全と確認済みの一覧」に入るものだけ素通し**: テスト・lint・監査・読み取りの `manage.py`（`test`・`check`・`showmigrations` など）・ふだんの `migrate`・中身が見えて危険のない `manage.py shell`・読み取りの SQL・`redis-cli` の読み取りなど。名前だけでなく、書き込み・実行・外部送信につながるオプション（`--fix`・`sed -i`・`curl -d` など）が無いことまで確かめる（一覧は `plan_I174.md` 0-5・0-9 章）。一覧にない操作（例 `seed_e2e`・`createsuperuser`・`pip install`・`dumpdata`・`diffsettings`）や、パイプで受ける流し込み・読めない書き方・未知の compose オプションは人の確認になる。素の `docker exec|run` は 2. と 3. の列挙だけで判定する（I174 の前と同じ）
5. **安全網（最後の層）**: 上の判定が読み落とした書き方（`function f { … }` の本体・`coproc`・`<( )` の中 など）でも、コマンドの位置ごとに上の判定をかけ直し、同じ扱いにする（1. は止める・2. は止める〔`DANGER_OK=1` なら確認〕・3.／4. は確認）。読み落としを素通しにしないため。

- **見張りを直したら、コミットの前に 3 つのテストを流す**: `bash scripts/claude/tests/test_guard_bash_oracle.sh`（本物の bash との突き合わせ。bash が実行する危険なコマンドを見張りが素通ししないか）と、`bash scripts/claude/tests/test_pretooluse_guard_matrix.sh`（危険な操作 × 書き方の総当たり。素通しの穴）と `bash scripts/claude/tests/test_guard_corpus_diff.sh`（過去の作業コマンドで、新しく確認・停止になったものが記録の 1% を超えないか・見張りが異常終了しないか）。後者は手元の作業記録を `~/.cache/claude-guard-corpus/`（本人だけが読める権限）に抜き出して使い、リポジトリには入れない
- **新しい秘密ファイルを置くときは、`.claude/settings.json` の deny に名前を足す**（`Read(**/<名前>)`・`Edit(**/<名前>)`）。deny は実在する秘密ファイルの名前（`.env`・`.env.e2e`・`.env.local`・`.env.*.local`）に絞ってある（`.env.example` 等の編集を妨げないため）。名前を足さないと、Read / Edit ツールでの読み書きが確認なしで通る（Bash での読み出しは見張りが確認に回す）。`scripts/claude/tests/test_settings_permissions.sh` の期待値も合わせて更新する。あわせて見張りの `_SECRET_PATH_RE`（`pretooluse_guard.py`）に当たる名前かも確かめる（当たらなければ Bash での読み出しも確認にならない）
- **`DANGER_OK=1 を付けても`、見張りは人の承認を求める**（承認画面が出る）。Claude が自分で `DANGER_OK=1` を付けて通すことはできない。上の「ユーザー明示承認」を技術的に強制するためである。`DANGER_OK=1` が効くのはコマンドの先頭に書いたときだけで、`bash -c 'DANGER_OK=1 …'` のように入れ子の中に書いても解除にならず止まる。
- **見張りが判定しないもの**: 「大規模 rebase」（settings.json の ask で人の確認。`git -C . rebase`・`git -c … rebase` のように git と rebase の間に何かを書くと ask に当たらないことがあるので、rebase はこの形で書かない）・ホストで実行するシェルスクリプトの中身・コードを経由しない大量更新・secrets のうち上の 3. に当たらない操作（ファイルの編集は settings.json の deny で拒否）・ふだんの `migrate`（前進）で未適用の破壊的マイグレーションが走ること（マイグレーションは PR でレビューし、コンテナ起動時にも自動で走る）・素の `docker exec|run` の中の列挙外の操作。これらは計画書と人の承認で管理する。見張りの脅威モデルは「事故」で、意図的な回避は対象外。
- **見張りを避ける書き方を使わない**: 変数・`eval "$VAR"`・base64 などで命令を組み立てる形、`docker compose cp` でファイルを送ってから実行する形、コンテナの中で作ったファイルを実行する形は、見張りが中身を判定できない。危険操作や外部送信をこうした書き方で行わない（判定できない部分は auto mode の判断が第 2 層になる）。

## 未コミット変更の取り消し（`git checkout/restore <file>`）

作業ツリーに**未コミット変更があるファイル**の一時変更を取り消す際、`git checkout/restore <file>` を使わない。同ファイルの未コミット分も HEAD に戻り**消失**する（一時的なテスト注入を戻すつもりが、未コミットの実装ごと失う事故になる）。

- 一時変更は **Edit ツールで元に戻す**（取り消したい行だけをピンポイントで復元する）。
- clean なファイルの revert やブランチ切替（`git checkout <branch>` / `-b` / `git switch`）は通常どおり可。
- PreToolUse フック（`scripts/claude/hooks/pretooluse_guard.py`）が、未コミット変更があるファイルへの `git checkout/restore <file>` を `DANGER_OK=1` 無しでブロックする。どうしても必要な場合のみ `DANGER_OK=1` を前置する。

## 実行テンプレ
- 影響範囲:
- 代替案:
- ロールバック:
- 実行コマンド（DANGER_OK=1 付き）:
