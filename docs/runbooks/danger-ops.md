# 危険操作（Danger Ops）ルール

下の「例」の操作は、次の 3 つがそろったときだけ実行する。
- **計画書の Danger Ops 欄に書く**（影響範囲・代替案・ロールバック・実行コマンド。形は `docs/plans/templates/plan_template.md`）
- **ユーザーが明示して承認する**（承認の言葉と日付を計画書か `docs/reviews/open/I###_review.md` に残す）
- **実行するコマンドの先頭に `DANGER_OK=1` を付ける**（見張りが承認画面を出す。下の「`DANGER_OK=1` を付けても人の承認」）

前の 2 つは人の約束で、仕組みが確かめるのは 3 つ目だけ。

## 例
- DB: DROP / TRUNCATE / WHEREなし UPDATE・DELETE / 大量更新・削除 / 破壊的マイグレーション
  - `manage.py flush` / `sqlflush` / `reset_db`（DB 全消去・`django-admin` / `python -m django` も同じ）・`migrate <app> <移動先>`（巻き戻し。`zero` を含む）・`loaddata`（既存の行の上書き）・`seed_e2e --flush`
  - ダンプ・SQL ファイルの流し込み（`psql -f <ファイル>` / `psql ... < <ファイル>`・`dbshell < <ファイル>`・`pg_restore --clean`）・`dropdb`
  - `manage.py shell` / `python -c` / ヒアドキュメントで渡す Python の `.delete()`・QuerySet の一括 `update()`・`bulk_update()`・`call_command('flush')` など
- Git: force push / reset --hard / `git clean -f`（`-d`・`-x` の有無を問わない。追跡されていないファイルの削除）/ **未コミット変更があるファイルへの `git checkout/restore <file>`**（コミットから戻す形〔`git checkout HEAD <file>`・`git restore -s`〕はステージ済みの変更も対象・`git rm -f`・`git checkout-index -f`・`git read-tree -u --reset`・`git mv -f` の上書きを含む。そのファイルの未コミットの変更ごと消えるので、一時の変更は Edit ツールで戻す。変更の無いファイルの revert・ブランチの切り替えは普通に行ってよい）/ push の宛先・強制を変える設定（`remote.*.push` を保護ブランチ・`+`・`:` に・`push.default` を `matching`／`upstream`／`tracking` に・`remote.*.mirror true`）/ `clean.requireForce` を偽にする設定 / **秘密情報の検査（pre-commit）を飛ばす `git commit --no-verify`／`-n`・`git push --no-verify`**（I182）
  - rebase は危険操作にしない。rebase の前に commit しておけば `git reflog` から戻せる（push 済みなら GitHub からも）
- Docker: down -v / --volumes（データ消失）・`docker compose rm -v`・volume rm / prune（`docker volume rm|prune`）・`docker system prune --volumes`・`redis-cli FLUSHALL` / `FLUSHDB`（ログイン状態・celery の待ち行列・レート制限カウンタの全消去）。ワークツリーの撤去は `scripts/claude/wt-remove.sh` を使い、消す相手を確定できない場合は許可があっても止まる → `docs/runbooks/worktree.md` §4。docker が使えないときにデータを消さずに撤去する合図は `KEEP_DATA=1` で、`DANGER_OK` とは別＝消す操作の許可ではない
- Files: rm -rf（`-f` の無い `rm -r` も同じ。端末につながっていない実行では確認が出ずに全部消える）/ `find -delete`・`find -exec rm`・`xargs rm` / 秘密ファイルの表示・外への送信（下の見張りの 3.）
- ワークツリー（I179）: 別のワークツリーを消す・変更を捨てる操作はしない（決まりの正は `docs/runbooks/worktree.md` §9。撤去は `wt-remove.sh`）

## 破壊的な DB の操作の前の控え（I597）

破壊的なマイグレーション（列の削除など）・DB の流し込みの前に、開発の DB の控えを取る。Claude は次の入口だけを使う。
- コマンド: `bash scripts/claude/db-backup.sh <イシュー番号>_before`（例: `bash scripts/claude/db-backup.sh I590_before`）。**単体で流す**（前置きの代入・振り向け・`&&` を付けない。理由は下の「外に出すコマンドの書き方」）。名前は英数字・`_`・`-` の 1〜64 文字
- DB のコンテナが動いていないときは、先に `docker compose up -d --wait db`
- `bash scripts/db_backup.sh` は人の道具（中で同じ入口を呼ぶ）。Claude から流すとサンドボックスの中で `.env` が読めず止まる
- 出力: 今いるワークツリーの直下の `backup_<名前>_<日時>.sql`。`.gitignore` の `backup_*.sql` で git から外れる。`umask 077` で作る（`/mnt/c` の drvfs では権限が付かない）
- 入口の確かめ: `pg_dump` の終了コードが 0・空でない・完了の行 `-- PostgreSQL database dump complete` がある・先頭近くに `\restrict <鍵>` があれば最後の空でない行が同じ鍵の `\unrestrict <鍵>`。どれかが駄目なら、控えのファイル（一時の `backup_partial_*.sql` を含む）を残さず非 0 で止まる
- 計画書の Danger Ops 欄の「ロールバック」に、この控えのファイル名を書く（戻すのは `psql` の流し込みで、それ自体が危険操作）
- 控えは DB の中身の写しなので、そのイシューのマージの後に消す（close の片付け。消すのは自分が作った `backup_<名前>_*.sql` と、強制終了などで残りうる `backup_partial_*.sql` だけ）
- コンテナの中に写しを作る回り道（`pg_dump -f /tmp/…` → `docker compose cp`）はしない

## サンドボックス（第 1 層・I430）

Bash のコマンドは、Claude Code の公式のサンドボックス（`.claude/settings.json` の `sandbox`・https://code.claude.com/docs/en/sandboxing.md ）の中で動く。サンドボックスの中のコマンドは承認なしで通るが、次の範囲に閉じ込められる。見張りは、公式と GitHub で止まらない漏れだけを見る（下の「見張りの扱い」）。

- **書き込み**: 作業ディレクトリの下と一時ディレクトリだけ（リンクされたワークツリーでは共有の `.git` も。`hooks/`・`config` は不可）。`.claude/worktrees/` は `denyWrite` で書けない（primary のセッションから他のワークツリーを守る）。設定ファイル（`.claude/` の settings・`.mcp.json`）は Claude Code が書き込みを拒む
- **読み取り**: ほぼ全体。ただし `.claude/settings.json` の Read の deny の場所（`.env` など）と、`sandbox.filesystem.denyRead` の場所（GitHub App の鍵 `~/.config/github-app`・鍵の控え `~/.cache/github-app`）は読めない
- **通信**: どこにもつながらない（`allowedDomains: []`・`strictAllowlist: true`）
- **外での再実行はしない**（`allowUnsandboxedCommands: false`）。道具（bubblewrap・socat）が無いと Claude Code が起動しない（`failIfUnavailable: true`。入れ方は `docs/runbooks/onboarding.md`）
- **外に出すコマンド**（`excludedCommands`）: `docker`・`docker-compose`・`gh`・`git`・`python3 .claude/hooks/unreviewed.py run *`（スクリプトの起動役・I599）。中では動かないものだけ（docker は両立しない・gh と git は鍵の控えを読み書きする・git は設定ファイルの違うブランチへの切り替えで `.claude/settings.json` を書き換える・起動役が動かすスクリプトはレビュー役の `claude -p` と gh を使う）。外に出したコマンドも、許可の設定・見張り・auto モードの判定役が今までどおり見る
  - **外に出す一覧に一般のインタプリタ・シェル（`bash *`・`sh *`・`python3 *` など）を足さない**（書いたファイルを外で動かせる。`scripts/claude/tests/test_settings_permissions.sh` が止める）
  - **`scripts/claude/` のスクリプトは既定でサンドボックスの中で動く**（I599）。`bash scripts/claude/…` はそのままでは外に出す型に当たらない（新しく書いた・書き換えたスクリプトも、どんな書き方でも中）
    - 外で動く必要のあるスクリプト（gh・`claude -p`・docker を使う入口）だけを、**起動役** `python3 .claude/hooks/unreviewed.py run <名前> <引数…>` が外で動かす。一覧は `.claude/hooks/unreviewed.py` の `OUTSIDE_SCRIPTS`（`code-review.sh`・`issue-source.sh`・`adversarial-review.sh` など 16 本）。起動役は、`scripts/claude/` に**レビュー前の中身**（このブランチが develop から分かれた時点〔`git merge-base HEAD origin/develop`〕との差・追跡していない新規・git が無視するファイル）が 1 つでもあれば、外で動かさずに理由と案内を出して終了コード 3 で終わる。基準を求められないときも同じ。サンドボックスの中で動いたら終了コード 4
    - 見張りは、単体の形の `bash scripts/claude/<一覧の名前> <引数…>`（`$`・バッククォート・かっこ・`;`・`&`・`|`・`<`・`>`・改行・前置きの代入なし、プロジェクトの最上位で）を起動役の形に付け替える（承認の画面は出ない）。だから**スクリプトは今までどおり `bash scripts/claude/<名前> …` を単体で流す**。読み切れない形は何もしない（中で動く＝gh などは失敗する）
    - 起動役を、つなぎ・置き換え・振り向け・前置きつき、またはプロジェクトの最上位でない場所（`cd` の後）で流すと、見張りが止める
    - 起動役・判定は `.claude/hooks/` に置く（サンドボックスから書けず、Edit は承認が要る）。**外で動く必要のある入口を足すときは `OUTSIDE_SCRIPTS` に足す**（足し忘れは中で動いて失敗するので気づける）。一覧を見直すときは `grep -lE '(^|[^a-z_-])(gh|claude|docker|curl)( |$)' scripts/claude/*.sh`
    - **ハーネスのイシューで `scripts/claude/` を変えたブランチでは、マージまで起動役も外で動かない**。レビュー役・gh を使うスクリプトを流す必要があるときは、ユーザーに `! bash scripts/claude/<名前> …` で流してもらう（レビュー役の写しで動かす改善は I593）
    - `scripts/claude/test-session.sh` に許可の表に無い引数（自分で書いた設定ファイルの `--settings`・`--mcp-config`・確認を外す `--permission-mode`・プロジェクトの設定を読まない `--setting-sources` など）を渡すときは承認を求める（子のセッションのフックは外で動く）
    - `scripts/claude/code-review.sh` は、レビュー前の中身があるとき、自動テスト文書の決定論ゲートの `bash scripts/claude/tests/test_*.sh` を手元で流さない（CI の Harness Tests が流す）
  - **フックは起動役を通す**: `.claude/settings.json` の `hooks` の `command` はすべて `bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/reviewed-hook.sh scripts/claude/hooks/<名前>.py`。`scripts/claude/` に分かれた時点との違いがあるあいだは、分かれた時点の写し（`~/.cache/claude-reviewed-hooks/<コミット>/`）でフックを動かす。**見張りを直すイシューでは、直した見張りが効くのはマージの後**（確かめは CI の決定論のテスト。`scripts/claude/tests/test_settings_permissions.sh` が起動役を通らないフックを止める）
  - 受け入れた残り（plan_I599.md 8）: Claude Code の版が変わり、見張りの付け替え（`updatedInput`）の後のコマンドで外に出すかが決まらなくなる（中で動く側に崩れるので安全。`docs/runbooks/harness-audit.md` で点検）／git が無視するフォルダ（`.venv`・`__pycache__`）の中の書き換えと `origin/develop` の参照の書き換え（わざと避ける形・参照は I600）／基準を求められないときはフックの起動役が作業ツリーのフックを動かす（フック全体を止めると見張りを直せなくなるため）／一覧のスクリプトが `scripts/claude/` の外の git の設定・docker・frontend の設定を動かす（I600）

### 外に出すコマンドの書き方（Bash を 1 つずつ流す理由）

外に出るのは、1 回の呼び出しの中のコマンドが**すべて**一覧に当たるときだけ。次のどれかが入ると呼び出し全体がサンドボックスの中で動く（公式 sandboxing）。
- 一覧に無いコマンドとのつなぎ（`&&`・`;`・`|`。例: `git checkout X && npm …`・`gh … | head`）
- 振り向け（`>`・`>>`）・`$(…)`・`cd`
- 前置きの代入（`X=1 bash scripts/claude/…`）

中で動くと、`gh` は App の鍵が読めず失敗する（「鍵を受け取れません」）。`git` の切り替えは `.claude/settings.json` だけが古く残り（`error: unable to unlink old '.claude/settings.json'`）、作業ツリーの確かめが DIRTY になる。

決まり:
- `gh`・`git`・`docker`・`bash scripts/claude/<名前>`（見張りが起動役に付け替える形）は 1 回の呼び出しで単体で流す。`; echo "exit=$?"` も付けない
- 値は前置きの代入ではなく引数で渡す
- 出力を絞りたいときは、ファイルに書く道具の引数（`--body-file` など）か、後から Read ツールで読む
- git どうしのつなぎ（`git fetch … && git checkout …`）は外で動くのでよい

`.claude/settings.json` だけが古く残ったときの戻し方:
1. `git diff .claude/settings.json` の差分が、切り替える前のブランチの中身だけ（自分の未コミットの変更が無い）ことを確かめる
2. git を単体で `git checkout -- .claude/settings.json` と流す
3. 自分の変更が混ざっていれば、Edit で切り替え先の中身に合わせる

公式・GitHub に任せて、見張りから消した判定（I430）:

| 消した判定 | 代わりに止めるもの |
|---|---|
| Bash での別のワークツリー・primary への書き込み（と「絶対パス宛先のみ検査」の警告） | サンドボックスの書き込みの制限・`denyWrite: [".claude/worktrees"]` |
| develop／main への push・宛先の決まらない push の確認・`git push --repo` | GitHub のブランチ保護（PR 必須・bypass 不可・Restrict who can push。bot は push・マージできない）と `.claude/settings.json` の deny |
| fork（外部）の PR の取り込み（`gh pr checkout`・`gh co`）・マージ・ready・edit・update-branch・承認 | 取り込みは `.claude/settings.json` の deny（前方一致なので `gh -R x pr checkout` のようにオプションを挟んだ形には当たらない。意図的な回避は対象外）。マージ・承認は GitHub（Code Owners の承認だけが数えられ、bot はマージできない）。手順は下の「外部（fork）からの PR の扱い」 |

## 見張り（pretooluse_guard.py）の扱い（I174）

**確認を出す基準（I200・ユーザーの方針 2026-10-25・10-29）**: 承認画面（確認）を出すのは、次の 3 種類につながる操作だけ。それ以外の普通の開発・検証の操作は確認なしで通す。
- **(A) GitHub の破壊**: force push・`--all`／`--mirror`・push の宛先や強制を変える設定・リモートのブランチの削除（保護ブランチへの push と fork の PR は I430 から GitHub と deny に任せた＝上の「サンドボックス（第 1 層）」）
- **(B) 復旧できない状態**: 未コミットの変更を消す git の操作・ファイルの削除・dev DB のデータを消す操作（`down -v`・volume の削除・破壊的な SQL）。危険操作は停止し、`DANGER_OK=1` を付けたときだけ確認
- **(C) 秘密・個人情報の流出**: 秘密情報の表示・外部への送信（メール・celery・OpenAI・`curl` など）・秘密情報を使うワークフローの書き換え・秘密の検査を弱める書き換え・DB の中身をまとめて出す操作
- **残すと決めたもの**: `.secrets.baseline` の編集（`.claude/settings.json` の `ask`）・見張り自身が失敗して中身を読めないとき（Edit 系・MCP）
- 「安全と確認できない」（コンテナ内の一覧外の操作・読みきれない書き方・見張りの例外）だけを理由には確認しない。その場合は、(A)〜(C) につながる**危ない語**が文字列のどこかにあるときだけ確認する（粗い文字の一致。語の一覧の正は `pretooluse_guard.py` の `_RISKY_WORDS`。ここには写さない）

PreToolUse フック（`scripts/claude/hooks/pretooluse_guard.py`）は、コマンドを読み解いてから（行の継続・`;` `&&` `|`・`$(...)`・ヒアドキュメント・`sh -c`・`eval`・`env` などを展開してから）、次の順に判定する。判定の細かい仕様（場所の決め方・コンテナの中で通す形・書き込み先の見方）の正は `pretooluse_guard.py` の docstring とテスト（`scripts/claude/tests/guard_must_stop_cases.txt`）で、ここには写さない。

1. **常に止める（解除不可）**: `rm -rf /` と `rm -rf /*`・mkfs・dd・shred・Edit／Write／MultiEdit／NotebookEdit での別 worktree への書き込み（Bash の書き込みはサンドボックスが止める・I430）。入れ子では、パスを含む最も内側のワークツリーを所有者として判定し、境界を確定できないときは止める（`DANGER_OK=1` でも解除しない・I179）
2. **危険操作として止める**（exit 2。`DANGER_OK=1` を付けたときだけ確認）: 上の「例」のうち、見張りが判定できるもの（DB・git・Docker・Redis・削除の各操作と `git commit --no-verify`／`-n`・`git push --no-verify`〔I182〕）。git は `-C`・`cd` の先・`--git-dir`・`GIT_DIR=` の場所で判定する。場所が 1 つに決まらない・戻す対象が読めない、うえにその場所に変更があるときは、推測で通さず確認にする（いちばんありそうな場所で危険に当たれば停止のまま）。判定のために git を実行するのはこのリポジトリとその worktree の中だけで、判定するコマンドの `-c` 等の設定は使わない。ホスト・`docker exec`・`docker compose exec|run`・`docker-compose` のどれで実行しても同じ
3. **人の確認**: 外部への送信（メール送信・celery タスクの起動・登録 API とパスワード再設定依頼 API・OpenAI）と、秘密情報の表示（`.env` 等の読み出し・環境変数をまとめて表示する形〔代表: `printenv`・コマンドを包まない `env`・引数なしの `export`。形の正は `_cmd_external`・I444〕・`docker compose config`・`docker inspect`）、**リモートブランチの削除**（`git push --delete`・`-d`・`<remote> :<ブランチ>`・`--prune`。I182）
4. **`docker compose exec|run` の中の操作**: 引数に語が出やすいが (A)〜(C) を起こさない形（テスト・lint・読み取りの `manage.py`・読み取りの SQL・ローカル宛ての `curl` など。形の正は `_container_safe`・I444）は通す。それ以外は、**危ない語があるか、コンテナの `/tmp/` 以外へ書き込む**（形の正は `_write_targets`・`_container_risky`・I454）ときだけ確認する。`docker compose cp` は、取り出しは 3. の確認、送り込みはコピー先が `/tmp/` 以外・中身に危ない語・中身を読めないときだけ確認（I200）。素の `docker exec|run` は 2. と 3. の列挙だけで判定する
5. **安全網（最後の層）**: 上の判定が読み落とした書き方（`function f { … }` の本体・`coproc`・`<( )` の中 など）でも、コマンドの位置ごとに上の判定をかけ直す（1. は止める・2. は止める・3.／4. は確認）。読み取りが代替経路に落ちた形は、危ない語があるときだけ確認（I200）

- **見張りが失敗したとき（I182・I200）**: 判定中の例外とメモリの上限（512MB）超えは、Bash のコマンドなら**危ない語があるときだけ確認**、無ければ通す（停止の操作の代表語〔`rm`・`git`・`down`・`volume`・`drop` など〕も語に入れてある）。Edit 系・MCP・コマンドを取り出せないときは**確認**。**20 秒**を超えた・起動できない・異常終了した（exit 0/2 以外）ときは、`.claude/settings.json` のフック設定（`"timeout": 20`・`"onFailure": "block"`。Claude Code の公式の仕組み）で**停止**する。見張りが起動できない（構文の誤り等）と Edit まで止まり、Claude が見張りを直せない。そのときはユーザーが端末で `! git restore scripts/claude/hooks/pretooluse_guard.py` を実行して戻す（`!` はツールを通らないのでフックが動かない）
- **編集の確認（I200）**: ワークフロー（`.github/workflows/**`）と pre-commit の設定（`.pre-commit-config.yaml`）の Edit／Write／MultiEdit は、見張りが書き換えの前と後の中身を比べ、秘密情報・権限・外部送信に関わる語や、検査を弱める語が**増えた**ときだけ確認にする（語の正は見張り。action の版の書き換え・フックの追加は通る）。`.secrets.baseline` は `.claude/settings.json` の `ask`。Dockerfile・`frontend/nginx.conf`・依存のファイル・マイグレーション・`backend/init-db.sql`・`.github/dependabot.yml`・`docker-compose.yml` は確認なし（git で戻せ、CI の監査・レビューで捕まる）
- **見張りを直したら、コミットの前に 4 つのテストを流す**: `bash scripts/claude/tests/test_guard_bash_oracle.sh`（本物の bash との突き合わせ）・`bash scripts/claude/tests/test_pretooluse_guard_matrix.sh`（危険な操作 × 書き方の総当たり）・`bash scripts/claude/tests/test_guard_corpus_diff.sh`（過去の作業コマンドで、新しく確認・停止になったものが記録の 1% を超えないか。手元の作業記録を `~/.cache/claude-guard-corpus/` に抜き出して使い、リポジトリには入れない）・`bash scripts/claude/tests/test_guard_must_stop_cases.sh`（止めるべき形の一覧 `scripts/claude/tests/guard_must_stop_cases.txt` で、変更前より弱い判定が無いか。CI でも流れる・I463）。止める形を足したとき・取りこぼしを直したときは、その形を一覧に足す
- **新しい秘密を置くとき**: `.claude/settings.json` の deny に名前を足す（`Read(**/<名前>)`・`Edit(**/<名前>)`。Read・Edit の deny は Bash の `cat` などの読み出し・振り向けにも効く〔公式 permissions〕）。リポジトリの外に置くときは `sandbox.filesystem.denyRead` にも場所を足す（I430 で GitHub App の鍵が読めたのを確かめた）。deny は実在する秘密ファイルの名前（`.env`・`.env.e2e`・`.env.local`・`.env.*.local`）に絞ってある（`.env.example` 等の編集を妨げないため）。`scripts/claude/tests/test_settings_permissions.sh` の期待値と、見張りの `_SECRET_PATH_RE`（`pretooluse_guard.py`）に当たるかも合わせる
- **`DANGER_OK=1` を付けても人の承認**: 見張りは承認画面を出す。Claude が自分で `DANGER_OK=1` を付けて通すことはできない（ユーザーの明示の承認を技術的に強制する）。`DANGER_OK=1` が効くのはコマンドの先頭に書いたときだけで、`bash -c 'DANGER_OK=1 …'` のように入れ子の中に書いても解除にならず止まる
- **見張りが判定しないもの**: ホストで実行するシェルスクリプトの中身・コードを経由しない大量更新・secrets のうち上の 3. に当たらない操作（ファイルの編集は settings.json の deny で拒否）・ふだんの `migrate`（前進）で未適用の破壊的マイグレーションが走ること（マイグレーションは PR でレビューし、コンテナ起動時にも自動で走る）・素の `docker exec|run` の中の列挙外の操作。これらは計画書と人の承認で管理する。見張りの脅威モデルは「事故」で、意図的な回避は対象外
- **見張りに判定を足すときの決まり（I430）**: 判定を足す計画では、次の 3 つを計画に書く（決まりの正はここ）。
  1. 足す前に、公式の仕組み（`.claude/settings.json` の deny／ask・サンドボックスの設定）や GitHub の守りで表せないかを書く。表せるなら公式・GitHub を使い、見張りに足さない
  2. 足すなら、実際に起きた事故の例（いつ・どの作業で・何が起きたか）を書く。レビューの「この書き方でもすり抜けられる」だけでは足さない
  3. レビューで見張りへの意図的な回避（普通の書き方の事故では起きない形）の指摘が出たら、Low として一覧（`docs/reviews/backlog/`）に回すだけにし、後続のイシューにしない
- **見張りを避ける書き方を使わない**: 変数・`eval "$VAR"`・base64 などで命令を組み立てる形、コンテナの中で作ったファイルを実行する形は、見張りが中身を判定できない（`docker compose cp` でファイルを送ってから実行する形は、I200 からコピーの時点でコピー元の中身に語の判定をかける）。危険操作や外部送信をこうした書き方で行わない（判定できない部分は auto mode の判断が第 2 層になる）

## GitHub から復旧できる範囲（I182）

**前提**: develop/main は GitHub 側で保護され（ブランチ保護・CODEOWNERS・承認必須）、bot は PR を出すだけでマージできない。このため Claude がローカルで壊しても GitHub から復旧でき、失いうるのは push していない手元の変更だけである。手元の見張りやレビューの重さは、この前提で決める（`docs/issues/closed/I181.md` の「前提」）。

**例外（GitHub から復旧できない操作）**: 次の操作は、マージしなくても GitHub 側に取り返しのつかない影響が出る。この範囲の変更は「GitHub が最後の守り」の対象外として扱う。

| 操作 | なぜ復旧できないか | 対策 |
|------|-------------------|------|
| 秘密情報を含むコミットの push | リポジトリは公開なので、push した時点で全世界に公開される。消しても複製・キャッシュが残る | GitHub の push protection（push を拒否）・見張りが `git commit --no-verify`／`-n`・`git push --no-verify` を停止・CI の `Backend Lint & Security`（必須チェック）の detect-secrets（push 後の検出）・下の「秘密情報を push してしまったとき」 |
| ワークフロー（`.github/workflows/`）・秘密情報の検査設定（`.pre-commit-config.yaml`・`.secrets.baseline`）の書き換え | PR を出した時点で、PR 側のワークフローが secrets 付きで動く。検査設定を外すと CI の検出も効かない | 上の「編集の確認」・レビュー観点（`docs/runbooks/review-rules.md`）・CI の検査が外されないことの決定論テスト（`scripts/claude/tests/test_i182_secret_gates.sh`） |
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
4. **push protection に拒否されたとき**（`push protection`・`Push cannot contain secrets` などの文言が出る）は、拒否を回避しない（GitHub の「bypass」を使わない）。まだ公開されていないので、該当のコミットから秘密情報を消してから push し直す。

## 外部（fork）からの PR の扱い

public リポジトリのため、第三者（自律 AI エージェントを含む）から fork 経由の PR が届くことがある。外部からのコード寄稿は受け付けない（`CONTRIBUTING.md`）。届いた場合は次の手順で処理する。

1. head リポジトリを確かめる: `gh pr view <PR番号> --json isCrossRepository -q .isCrossRepository` → `true` なら外部 PR（close 段階の最初の `scripts/claude/pr-base-sync.sh` も自動で見分ける）
2. **Actions の実行を承認しない**（fork PR には repository secrets が渡らない）
3. **base 追従・CI 対応・レビューをしない**。**手元に checkout しない**（`.claude/` と hook 本体が相手の版に置き換わり、次の操作でそのコードが実行されるため）。中身は `gh pr diff <PR番号>`・`gh pr view <PR番号>` で読む。`gh pr checkout`・`gh co` は deny で止まるが、`git fetch origin pull/<N>/head` → `git checkout`・`gh pr diff <N> | git apply`・オプションを挟んだ `gh -R … pr checkout` などの別経路は止まらないので行わない。`gh pr ready`・`edit`・`update-branch`・`review --approve` も使わない
4. 方針コメントを付けて close する: `gh pr comment <PR番号> --body-file <file>` → `gh pr close <PR番号>`
5. 対象のイシューは OPEN のまま残し、必要なら通常の流れ（/plan-issue 以降）で自前で実装する
