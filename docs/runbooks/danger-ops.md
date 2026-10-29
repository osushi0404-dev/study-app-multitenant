# 危険操作（Danger Ops）ルール

以下は原則「計画書に明記」＋「ユーザー明示承認」＋「PRに danger-approved」＋「実行時 DANGER_OK=1」でのみ実行する。

## 例
- DB: DROP / TRUNCATE / WHEREなし UPDATE・DELETE / 大量更新・削除 / 破壊的マイグレーション
  - `manage.py flush` / `sqlflush` / `reset_db`（DB 全消去・`django-admin` / `python -m django` も同じ）・`migrate <app> <移動先>`（巻き戻し。`zero` を含む）・`loaddata`（既存の行の上書き）・`seed_e2e --flush`
  - ダンプ・SQL ファイルの流し込み（`psql -f <ファイル>` / `psql ... < <ファイル>`・`dbshell < <ファイル>`・`pg_restore --clean`）・`dropdb`
  - `manage.py shell` / `python -c` / ヒアドキュメントで渡す Python の `.delete()`・QuerySet の一括 `update()`・`bulk_update()`・`call_command('flush')` など
- Git: force push / reset --hard / 大規模rebase / `git clean -f`（`-d`・`-x` の有無を問わない。追跡されていないファイルの削除）/ **未コミット変更があるファイルへの `git checkout/restore <file>`**（下記注記。コミットから戻す形〔`git checkout HEAD <file>`・`git restore -s`〕はステージ済みの変更も対象・`git rm -f`・`git checkout-index -f`・`git read-tree -u --reset`・`git mv -f` の上書きを含む）/ push の宛先・強制を変える設定（`remote.*.push` を保護ブランチ・`+`・`:` に・`push.default` を `matching`／`upstream`／`tracking` に・`remote.*.mirror true`）/ `clean.requireForce` を偽にする設定 / **秘密情報の検査（pre-commit）を飛ばす `git commit --no-verify`／`-n`・`git push --no-verify`**（I182）
- Docker: down -v / --volumes（データ消失）・`docker compose rm -v`・volume rm / prune（`docker volume rm|prune`）・`docker system prune --volumes`・`redis-cli FLUSHALL` / `FLUSHDB`（ログイン状態・celery の待ち行列・レート制限カウンタの全消去）。ワークツリーの撤去は `scripts/claude/wt-remove.sh` を使い、消す相手を確定できない場合は許可があっても止まる → `docs/runbooks/worktree.md` §4。docker が使えないときにデータを消さずに撤去する合図は `KEEP_DATA=1` で、`DANGER_OK` とは別＝消す操作の許可ではない
- Files: rm -rf（`-f` の無い `rm -r` も同じ。端末につながっていない実行では確認が出ずに全部消える）/ `find -delete`・`find -exec rm`・`xargs rm` / secrets 操作
- ワークツリー（I179）: 別のワークツリー（primary の中の `.claude/worktrees/` を含む）を消す・変更を捨てる操作（`rm`・`find -delete`・`git -C <別ワークツリー> reset/checkout/clean` 等・`git worktree remove`）はしない（撤去は `wt-remove.sh`。`docs/runbooks/worktree.md` §9）。中の入れ子ごと消える `git clean -ff` を含め、見張りは上の Git・Files の各操作として止める（別ワークツリー専用の判定は持たない）

## 見張り（pretooluse_guard.py）の扱い（I174）

**確認を出す基準（I200・ユーザーの方針 2026-10-25・10-29）**: 承認画面（確認）を出すのは、次の 3 種類につながる操作だけ。それ以外の普通の開発・検証の操作は確認なしで通す。
- **(A) GitHub の破壊**: force push・保護ブランチへの push・リモートのブランチの削除・fork（外部）の PR の取り込み・宛先の決まらない push
- **(B) 復旧できない状態**: 未コミットの変更を消す git の操作・ファイルの削除・dev DB のデータを消す操作（`down -v`・volume の削除・破壊的な SQL）。危険操作は停止し、`DANGER_OK=1` を付けたときだけ確認
- **(C) 秘密・個人情報の流出**: 秘密情報の表示・外部への送信（メール・celery・OpenAI・`curl` など）・秘密情報を使うワークフローの書き換え・秘密の検査を弱める書き換え・DB の中身をまとめて出す操作
- **残すと決めたもの**: `.secrets.baseline` の編集（`.claude/settings.json` の `ask`）・見張り自身が失敗して中身を読めないとき（Edit 系・MCP）
- 「安全と確認できない」（コンテナ内の一覧外の操作・読みきれない書き方・見張りの例外）だけを理由には確認しない。その場合は、(A)〜(C) につながる**危ない語**が文字列のどこかにあるときだけ確認する（粗い文字の一致。語の一覧の正は `pretooluse_guard.py` の `_RISKY_WORDS`。ここには写さない）

PreToolUse フック（`scripts/claude/hooks/pretooluse_guard.py`）は、コマンドを読み解いてから（行の継続 `\`＋改行を bash と同じ規則でつなぎ、付着した `;` `&&` `|` `( )`・`$(...)`・ヒアドキュメント・`sh -c` / `bash -lc`・`eval`・`env` などを展開してから）、次の順に判定する。

1. **常に止める（解除不可）**: `rm -rf /` と `rm -rf /*`・mkfs・dd・shred・別 worktree への書き込み
2. **危険操作として止める**（exit 2）: 上の「例」のうち、見張りが判定できるもの＝DB の各操作・`git reset --hard`・`git clean -f`・force push / 保護ブランチへの push・変更ありのファイルの checkout / restore / `git rm -f`・push と clean の設定の変更・Docker の各操作・Redis の全消去・`rm -r`・`find -delete` / `find -exec rm` / `xargs rm`・`git commit --no-verify`／`-n`（`-an` のようなまとめ書きも）・`git push --no-verify`（I182）。git は `-C`・`cd` の先・`--git-dir` / `--work-tree`・`GIT_DIR=` の場所で判定する。**場所が 1 つに決まらない**とき（1 つに決まるのは、cd が無いか、最後の cd までが `&&` でつながり〔`cd X && …` は cd が成功したときだけ後ろが動く。`cd X; …`・改行は cd が失敗しても後ろが動くので決まらない。最後の cd だけは `;` でもよい〕、cd がすべて `cd <文字どおりの実在する場所>` の形だけ。`( … )`・パイプ・`&`・`||`・制御構文・入れ子のシェルの中の cd、`cd -`・`cd -P`・`pushd`・`cd ~`・先が読めない／存在しない cd、CDPATH・`set -P`、飛ばされうる cd〔`A && cd X`〕の後ろの `;`・`||`・`&` の後の git、cd 以外で場所を変える書き方〔`env -C`・`sudo -D`・`GIT_DIR=`／`GIT_WORK_TREE=` の代入〕は 1 つに決まらない。行頭の `cd <repo> && git commit … | grep …; git push` は 1 つに決まる）、または**戻す対象が読めない**（`$(…)`・変数・xargs・find・中かっこ・`--pathspec-from-file`）うえにその場所に変更があるときは、推測で通さず**確認**にする。ただし、書かれたとおりに cd が成功した場所（いちばんありそうな場所）で危険に当たれば**停止**する（停止を確認に格下げしない。場所に依存しない `git push origin main`・`--force`・`reset --hard` 等も停止のまま）。また、見張りは判定のために git を実行するが、実行するのは**このリポジトリとその worktree の中だけ**で、判定するコマンドの `-c` 等の設定は使わない（外のリポジトリの設定〔core.fsmonitor・clean フィルタ等〕で、承認より前にコマンドが実行されるのを防ぐため）。外・入れ子のリポジトリ・一時リポジトリでの、場所に依存する git の書き換えは確認になる。ホスト・`docker exec`・`docker compose exec|run`・`docker-compose` のどれで実行しても同じ
3. **人の確認**: 外部への送信（メール送信・celery タスクの起動・登録 API とパスワード再設定依頼 API・OpenAI）と、秘密情報の表示（`.env` 等の読み出し・`printenv`・引数なしの `env`・`docker compose config`・`docker inspect`）、**リモートブランチの削除**（`git push --delete`・`-d`・`<remote> :<ブランチ>`・`--prune`。I182）
4. **`docker compose exec|run`（`docker-compose` も同じ）の中の操作**: 「安全と確認済みの一覧」（テスト・lint・監査・読み取りの `manage.py`・ふだんの `migrate`・中身が見えて危険のない `manage.py shell`・読み取りの SQL など。`plan_I174.md` 0-5・0-9 章）に入るものは通す。一覧にない操作（例 `seed_e2e`・`createsuperuser`・`pip install`・パイプで受ける流し込み・読めない書き方）は、**危ない語があるか、コンテナの `/tmp/` 以外へ書き込むか（リダイレクト・`tee`・`sed -i`・`cp`／`mv`／`install`／`ln`／`rsync` の書き先。/tmp/../app のような `..` はそろえてから見る）、環境変数をまとめて表示する（`ps e`・引数なしの `env`／`set`・`export -p`・`declare -p`／`-x`・`typeset -p`／`-x`）ときだけ確認**し、それ以外は通す（I200）。見える Python のコード・ヒアドキュメントの中身も語の判定にかける。`docker compose cp` は、コンテナ→ホスト（取り出し）は 3. の確認、ホスト→コンテナは、コピー先が `/tmp/` 以外（コンテナの /app/ は手元の `backend/`・`frontend/` に bind mount）・コピー元の中身に危ない語・中身を読めないときだけ確認（I200）。素の `docker exec|run` は 2. と 3. の列挙だけで判定する（I174 の前と同じ）
5. **安全網（最後の層）**: 上の判定が読み落とした書き方（`function f { … }` の本体・`coproc`・`<( )` の中 など）でも、コマンドの位置ごとに上の判定をかけ直し、同じ扱いにする（1. は止める・2. は止める〔`DANGER_OK=1` なら確認〕・3.／4. は確認）。読み落としを素通しにしないため。引用符が閉じていないなど読み取りが代替経路に落ちた形は、危ない語があるときだけ確認（I200）

- **見張りが失敗したとき（I182・I200）**: 判定中の例外とメモリの上限（512MB）超えは、Bash のコマンドなら**危ない語があるときだけ確認**、無ければ通す（読み解きが例外で止まると停止の判定も走らないので、停止の操作の代表語〔`rm`・`git`・`down`・`volume`・`drop` など〕も語に入れてある）。Edit 系・MCP・コマンドを取り出せないときは、今までどおり**確認**（理由には例外の型名だけを出す）。**20 秒**を超えた・起動できない・異常終了した（exit 0/2 以外）ときは、`.claude/settings.json` のフック設定（`"timeout": 20`・`"onFailure": "block"`。Claude Code の公式の仕組み）で**停止**する。見張りが起動できない（構文の誤り等）と Edit まで止まり、Claude が見張りを直せない。そのときはユーザーが端末で `! git restore scripts/claude/hooks/pretooluse_guard.py` を実行して戻す（`!` はツールを通らないのでフックが動かない）
- **編集の確認（I200）**: ワークフロー（`.github/workflows/**`）と pre-commit の設定（`.pre-commit-config.yaml`）の Edit／Write／MultiEdit は、見張りが書き換えの前と後の中身を比べ、ワークフローなら秘密情報・権限・外部送信・外から入る値に関わる語（`secrets`・`write`・`id-token`・`pull_request_target`・`workflow_run`・`curl`・`github.event.` など）が**増えた**とき、pre-commit なら detect-secrets が減った・検査の対象を狭める語（`exclude`・`files:`・`types`・`stages`・`skip`）が増えた・`.secrets.baseline` の指定が変わったときだけ確認にする（action の版の書き換え・フックの追加は通る）。パスは realpath で正規化して照合する。`.secrets.baseline` は `.claude/settings.json` の `ask`（公式の `Edit(...)` は Write・MultiEdit にも効く）。Dockerfile・`frontend/nginx.conf`・依存のファイル・マイグレーション・`backend/init-db.sql`・`.github/dependabot.yml`・`docker-compose.yml` は確認なし（git で戻せ、CI の監査・レビューで捕まる）。見張りの Edit 系の判定は、このほかに別 worktree への書き込みの停止
- **見張りを直したら、コミットの前に 3 つのテストを流す**: `bash scripts/claude/tests/test_guard_bash_oracle.sh`（本物の bash との突き合わせ。bash が実行する危険なコマンドを見張りが素通ししないか）と、`bash scripts/claude/tests/test_pretooluse_guard_matrix.sh`（危険な操作 × 書き方の総当たり。素通しの穴）と `bash scripts/claude/tests/test_guard_corpus_diff.sh`（過去の作業コマンドで、新しく確認・停止になったものが記録の 1% を超えないか・見張りが異常終了しないか）。後者は手元の作業記録を `~/.cache/claude-guard-corpus/`（本人だけが読める権限）に抜き出して使い、リポジトリには入れない
- **新しい秘密ファイルを置くときは、`.claude/settings.json` の deny に名前を足す**（`Read(**/<名前>)`・`Edit(**/<名前>)`）。deny は実在する秘密ファイルの名前（`.env`・`.env.e2e`・`.env.local`・`.env.*.local`）に絞ってある（`.env.example` 等の編集を妨げないため）。名前を足さないと、Read / Edit ツールでの読み書きが確認なしで通る（Bash での読み出しは見張りが確認に回す）。`scripts/claude/tests/test_settings_permissions.sh` の期待値も合わせて更新する。あわせて見張りの `_SECRET_PATH_RE`（`pretooluse_guard.py`）に当たる名前かも確かめる（当たらなければ Bash での読み出しも確認にならない）
- **`DANGER_OK=1 を付けても`、見張りは人の承認を求める**（承認画面が出る）。Claude が自分で `DANGER_OK=1` を付けて通すことはできない。上の「ユーザー明示承認」を技術的に強制するためである。`DANGER_OK=1` が効くのはコマンドの先頭に書いたときだけで、`bash -c 'DANGER_OK=1 …'` のように入れ子の中に書いても解除にならず止まる。
- **見張りが判定しないもの**: 「大規模 rebase」（I200 で確認をやめた。push していない手元の変更は rebase の前に commit・push しておけば `git reflog` と GitHub から戻せる）・ホストで実行するシェルスクリプトの中身・コードを経由しない大量更新・secrets のうち上の 3. に当たらない操作（ファイルの編集は settings.json の deny で拒否）・ふだんの `migrate`（前進）で未適用の破壊的マイグレーションが走ること（マイグレーションは PR でレビューし、コンテナ起動時にも自動で走る）・素の `docker exec|run` の中の列挙外の操作。これらは計画書と人の承認で管理する。見張りの脅威モデルは「事故」で、意図的な回避は対象外。
- **見張りを避ける書き方を使わない**: 変数・`eval "$VAR"`・base64 などで命令を組み立てる形、コンテナの中で作ったファイルを実行する形は、見張りが中身を判定できない（`docker compose cp` でファイルを送ってから実行する形は、I200 からコピーの時点でコピー元の中身に語の判定をかける）。危険操作や外部送信をこうした書き方で行わない（判定できない部分は auto mode の判断が第 2 層になる）。

## GitHub から復旧できる範囲（I182）

**前提**: develop/main は GitHub 側で保護され（ブランチ保護・CODEOWNERS・承認必須）、bot は PR を出すだけでマージできない。このため Claude がローカルで壊しても GitHub から復旧でき、失いうるのは push していない手元の変更だけである。手元の見張りやレビューの重さは、この前提で決める（`docs/issues/closed/I181.md` の「前提」）。

**例外（GitHub から復旧できない操作）**: 次の操作は、マージしなくても GitHub 側に取り返しのつかない影響が出る。この範囲の変更は「GitHub が最後の守り」の対象外として扱う。

| 操作 | なぜ復旧できないか | 対策 |
|------|-------------------|------|
| 秘密情報を含むコミットの push | リポジトリは公開なので、push した時点で全世界に公開される。消しても複製・キャッシュが残る | GitHub の push protection（push を拒否）・見張りが `git commit --no-verify`／`-n`・`git push --no-verify` を停止・CI の `Backend Lint & Security`（必須チェック）の detect-secrets（push 後の検出）・下の「秘密情報を push してしまったとき」 |
| ワークフロー（`.github/workflows/`）・秘密情報の検査設定（`.pre-commit-config.yaml`・`.secrets.baseline`）の書き換え | PR を出した時点で、PR 側のワークフローが secrets 付きで動く。検査設定を外すと CI の検出も効かない | 見張りが書き換えの中身を比べ、秘密が外に出うる語・検査を弱める語が増えたときだけ確認（I200。`.secrets.baseline` は settings.json の `ask`）・レビュー観点（`docs/runbooks/review-rules.md`）・CI の検査が外されないことの決定論テスト（`scripts/claude/tests/test_i182_secret_gates.sh`） |
| ワークフローが実行するコード（テスト・`package.json` の scripts・`manage.py` のコマンド 等）の変更 | ワークフローを書き換えなくても、PR 側のコードが CI の中で `GITHUB_TOKEN` に触れる | `ci.yml`・`e2e.yml` の最上位の `permissions: contents: read`（読み取りだけ）。CI の E2E のパスワード（`E2E_TEST_PASSWORD`）は e2e.yml がジョブごとに作る使い捨ての値で、secrets を使わずログは伏せ字（I213・対応不要） |
| リモートブランチの削除（`git push --delete`・`-d`・`<remote> :<ブランチ>`・`--prune`） | 手元に無い（別ワークツリー・別セッションの）ブランチの push 済みの作業は戻せない。PR も閉じる | 見張りが確認にする |
| イシュー・PR への書き込み（`gh issue edit --body-file` 等） | 公開されるが、bot 自身が編集・削除できる | 対策しない（書くのは Claude が書いた記録ファイルで、秘密情報を扱わない） |
| リポジトリ設定の変更・リリースの作成・ワークフローの手動実行 | — | 対策不要（bot に管理権限が無い、または allow に無くふだんの確認が出る） |
| マージ・cherry-pick・rebase で作るコミット | pre-commit（detect-secrets）は `git commit` でしか動かない | 対策しない（push protection と CI の detect-secrets で拾う） |

意図的な回避（`SKIP=detect-secrets`・`core.hooksPath` の書き換え・Bash でのワークフローの書き換え）は対象外（見張りの脅威モデルは「事故」）。

## 秘密情報を push してしまったとき（I182）

1. **すぐにユーザーへ報告し、作業を止める**。
2. **その鍵を発行元で無効化・再発行する**（履歴を書き換えても公開は取り消せないので、無効化が先）。
   - OpenAI・SendGrid の API キー: それぞれの管理画面で失効させ、新しいキーを発行する。
   - Django の `SECRET_KEY`・DB のパスワード: 値を変え、`backend/.env` と本番の設定を更新する。
   - そのほかの鍵も、発行元で失効させてから作り直す。
3. **その後でコミットから消す**。push 前のコミットなら `git commit --amend` や作り直しで消す。push 済みのコミットの書き換えは強制 push（危険操作）なので、計画書と承認で行う。
4. **push protection に拒否されたとき**（`GH013`・`push protection` の文言が出る）は、拒否を回避しない（GitHub の「bypass」を使わない）。まだ公開されていないので、該当のコミットから秘密情報を消してから push し直す。

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
