# I597 計画書: DB の控えの入口を Claude から流せる形で直す

## 基本情報
- **計画書ID**: plan_I597
- **関連イシュー**: #597
- **Draft PR**: #598
- **作成根拠資料**: docs/issues/open/I597.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I597_review.md
- **作成日**: 2026-11-20

## 1. 背景/目的
- 破壊的な DB の操作（列の削除など）の前に、開発の DB の控えを取る決まりがある。I587（2026-11-19）と I590（2026-11-20）で、計画どおり `bash scripts/db_backup.sh` を流すと 2 回とも止まり、空の控えのファイルが残った。どちらも手順書に無い `docker compose exec … pg_dump -f /tmp/…` → `docker compose cp` の回り道でしのいだ
- 目的: Claude が危険操作の前に、手順書どおりの 1 つのコマンドで、確かな控え（空でない・途中で切れていない）を取れるようにする。失敗したら控えのファイルを残さず、はっきり止まる

### 調査結果
**原因の概要**: Claude のコマンドは「サンドボックス」という囲いの中で動き、その中では秘密の設定ファイル（`.env`）が読めない。`scripts/db_backup.sh` は囲いの外に出られる名前の場所（`scripts/claude/`）に無いので、中の `docker compose` が `.env` を読めずに止まる。しかも止まる前に空の控えのファイルを作ってしまう。

**詳細**:
1. 外に出るのは `.claude/settings.json` の `sandbox.excludedCommands`（`docker *`・`docker-compose *`・`gh *`・`git *`・`bash scripts/claude/*`）に、1 回の呼び出しの全体が当たるときだけ（`docs/runbooks/danger-ops.md:29`・`:33-45`）。`bash scripts/db_backup.sh` は当たらないので、子の `docker compose` も中で動き、`.env`（`Read(**/.env)` の deny・`docs/runbooks/danger-ops.md:26`）が読めず `open <ワークツリー>/.env: permission denied` で止まる。このセッションでも、サンドボックスの中から見える `.env` は中身の無い装置ファイル（`crw-rw-rw- … 1, 3`）だった
2. `scripts/db_backup.sh:10` が `> "$OUTPUT"` で `docker compose` より先にファイルを作るので、失敗しても 0 バイトの `backup_<日時>.sql` が残る（`set -e` で止まるが、作ったファイルは消さない）
3. 外で動く確かめ（スパイク・2026-11-20）: `bash scripts/claude/issue-source.sh body I597` は単体で流すと `gh` が鍵を読めて成功し、`; echo` をつないだ呼び出しでは鍵が読めず失敗した。外に出る判定は呼び出し全体に効き、`bash scripts/claude/…` の子のプロセス（`gh`・`docker compose`）も外で動く。単体の `docker compose config --services` はこのワークツリーで `.env` を読んでサービスの一覧を出した
4. **pg_dump の出力の最後の行（スパイク・2026-11-20）**: このワークツリーで `docker compose up -d --wait db` を起動して確かめた。DB は `postgres (PostgreSQL) 15.19`。出力は先頭近くに `\restrict <鍵>`、終わりが `-- PostgreSQL database dump complete` → `--` → 空行 → `\unrestrict <鍵>` → 空行（CVE-2025-8714 の対策で 15.14 から入った形）。**最後の行は `-- PostgreSQL database dump complete` ではない**。イシューの受け入れ条件の「最後の行が `-- PostgreSQL database dump complete`」は、そのままでは正しい控えでも満たせない。目的（途中で切れていない）に合わせて、「完了の行がある」かつ「`\restrict <鍵>` があるときは、最後の空でない行が同じ鍵の `\unrestrict <鍵>`」で確かめる（9 に記録）。存在しない DB を指すと `pg_dump` は終了コード 1 で止まった
5. `.gitignore:88` が `.github_tokenbackup_migration.sql` と 2 つの行がつながって壊れている（I004 の `8b6a3399` から）。`backup_*.sql`（`:90`）があるので控えのファイルは git から外れているが、`.github_token`（GitHub の鍵を置く名前）が外れていない（`git check-ignore .github_token` が当たらない）。控えの置き場の `.gitignore` の確かめと同じ所なので、このイシューで 2 行に分けて直す
6. 参照の洗い出し: `grep -rn db_backup` で当たるのは `scripts/db_backup.sh` 自身・`docs/runbooks/worktree.md:94`・`scripts/claude/wt-remove.sh:146,149`（どちらも「撤去するワークツリーには使えない」という説明で、今回の変更の後も正しい・直さない）・`scripts/claude/tests/test_i205_stop_criteria.sh:128`（ファイル名の一覧の 1 行・中身は読まない）。`docs/plans/open/` に `bash scripts/db_backup.sh` を Claude の手順として書いた計画は無い（I590 の計画は app のワークツリーにあり、I590 の側で直す）
7. 高リスクのパスの判定（`scripts/claude/code-review.sh:309-318` の `path_risk_trigger`）: 変更するファイルはどれも当たらない
8. ハーネスのテストは `scripts/claude/tests/test_*.sh` を `run-all.sh` が全部流し、CI の Harness Tests ジョブ（`.github/workflows/ci.yml:203`）が PR ごとに流す。`scripts/` は pre-commit の shellcheck の対象（`.pre-commit-config.yaml:39-43`）

## 2. 受け入れ条件
- [ ] Claude（Bash ツール・サンドボックスあり）から、手順書に書いた 1 つのコマンド `bash scripts/claude/db-backup.sh <名前>` で開発の DB の控えが取れる。控えは空でなく、完了の行 `-- PostgreSQL database dump complete` があり、`\restrict <鍵>` があるときは最後の空でない行が同じ鍵の `\unrestrict <鍵>`（途中で切れていない）。控えは本人だけが読める（ファイルの権限 600）
- [ ] 控えが取れないとき、非 0 で止まり、作業フォルダに控えのファイル（空・途中まで・一時のファイル）を残さない。「`pg_dump` が非 0 で終わる」「出力が空」「完了の行が無い（途中で切れた）」「完了の行の後ろの `\unrestrict` が欠けた」の 4 通りをテストで固定する
- [ ] 名前に使えない文字（`/`・`..`・空白など）を渡したとき、DB に触らずに非 0 で止まり、ファイルを作らない
- [ ] `scripts/db_backup.sh`（人が使う）も、失敗したときに控えのファイルを残さない。Claude がサンドボックスの中から流したときは、非 0 で止まり、入口のコマンドを案内する
- [ ] `docs/runbooks/danger-ops.md` に、破壊的な DB の操作の前の控えの取り方（入口のコマンド・出力の場所・`.gitignore` 済みであること・マージ後に消すこと・確かめの中身）がある
- [ ] I590 の Danger Ops の控え（I590 の計画 5 のステップ 1・手動 M2）を、この入口で取り直せる。I590 はこのイシューのマージの後、I590 のワークツリーで入口を流す（このイシューでは、同じコマンドがワークツリーの開発の DB で動くことを手動 M1 で確かめる）
- [ ] `.github_token` が git から外れる（`.gitignore` のつながった行を直す）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし（読むだけの `pg_dump`）
- Config/Infra: `scripts/claude/db-backup.sh`（新規）・`scripts/db_backup.sh`・`docs/runbooks/danger-ops.md`・`.gitignore`・`scripts/claude/tests/test_i597_db_backup.sh`（新規）。`.claude/settings.json`・`scripts/db_restore.sh` は変えない

## 4. 変更点一覧（具体）

### 修正アプローチ
- 控えを取る処理を `scripts/claude/db-backup.sh` の 1 か所に置く。`bash scripts/claude/*` は外で動くので `docker compose` が `.env` を読める（サンドボックスの設定は変えない）
- 書く先は一時のファイルにし、確かめがすべて通ったときだけ正式の名前に移す。どこで止まっても一時のファイルは消える（`trap`）
- 人が使う `scripts/db_backup.sh` は入口を呼ぶだけの薄い包みにして、確かめを 1 か所にまとめる（同じ確かめを 2 か所に写さない）
- 外で動くスクリプトなので、中身を「`docker compose exec -T db pg_dump` と、作業フォルダの直下への書き込み」だけに絞る。名前は文字の種類を限って受け、パスにならないようにする。テストのために外から命令を差し替える口（環境変数など）は作らない

### 4-1. `scripts/claude/db-backup.sh`（新規）
達成すること: 1 つのコマンドで確かな控えを取り、失敗したら何も残さず止まる。
- 使い方: `bash scripts/claude/db-backup.sh [名前]`。名前は省略できる（人の包みが使う）
- 終了コード: 0 = 控えを取った／1 = 控えが取れない（`pg_dump` の失敗・確かめの不合格・同じ名前のファイルがある）／2 = 使い方の誤り（引数が 2 つ以上・名前に使えない文字）
- 処理の順:
  1. `set -uo pipefail`・`umask 077`（DB の中身の控えを本人だけが読める権限で作る）
  2. 引数の確かめ: 2 つ以上なら 2。名前があれば `^[A-Za-z0-9_-]{1,64}$` に当たらなければ 2（`/`・`..`・空白・空の名前は止まる）。ここまで `docker` を呼ばない
  3. `ROOT=$(git rev-parse --show-toplevel)` に `cd`（`docker compose` が `docker-compose.yml` と `.env` を見つける場所・今いるワークツリーのプロジェクトが相手）
  4. 正式の名前: `backup_<名前>_<YYYYmmdd_HHMMSS>.sql`（名前なしは `backup_<YYYYmmdd_HHMMSS>.sql`・今までと同じ形）。既にあれば 1（上書きしない）
  5. 一時のファイル: `mktemp --suffix=.sql "$ROOT/backup_partial_XXXXXX"`（`backup_*.sql` に当たるので `.gitignore` 済み・同じフォルダなので移すのが 1 回の名前の付け替えで済む）。`trap 'rm -f "$TMP"' EXIT`
  6. `docker compose exec -T db pg_dump -U postgres learning_app > "$TMP"`（振り向けはスクリプトの中。DB の中身はコンテナの中に写しを残さず、標準出力で受ける）
  7. 確かめ（どれかが駄目なら理由を出して 1。一時のファイルは trap が消す）:
     - `pg_dump` の終了コードが 0
     - 一時のファイルが空でない（`-s`）
     - 行ちょうどの `-- PostgreSQL database dump complete` がある（`grep -qxF`）
     - `\restrict <鍵>` の行があるときは、最後の空でない行が `\unrestrict <同じ鍵>`。`\restrict` の行が無い古い形（15.13 以前）は、完了の行だけで確かめる
  8. `mv -n "$TMP" "$DEST"` の後、`$DEST` があり `$TMP` が無いことを確かめる（`mv -n` は先にファイルがあると黙って移さないため）。出力: `✅ 控えを取りました: <ワークツリーからの相対パス>（<バイト数> バイト）`
- 失敗のときの案内（標準エラー）: 理由の 1 行と、「Claude からは `bash scripts/claude/db-backup.sh <名前>` を前置き・振り向け・つなぎなしで単体で流す（サンドボックスの中では `.env` が読めず止まる・`docs/runbooks/danger-ops.md`「破壊的な DB の操作の前の控え」）」。DB のコンテナが動いていないときの `docker compose up -d --wait db` も案内する
- 冒頭のコメントに、外で動く中身はこれだけであること（`docs/runbooks/danger-ops.md:31` の確かめの対象）を書く

### 4-2. `scripts/db_backup.sh`
達成すること: 人が使う道具も失敗で空のファイルを残さない。確かめは入口と共有する。
- 中身を `cd "$(git rev-parse --show-toplevel)"` → `bash scripts/claude/db-backup.sh "$@"` → 成功したら今までの案内（「このファイルを Google Drive 等に保存して…」）にする（`set -e` のまま。入口の終了コードをそのまま返す）
- 使い方のコメントを `bash scripts/db_backup.sh [名前]` に直す

### 4-3. `docs/runbooks/danger-ops.md`
達成すること: Claude が危険操作の前の控えの取り方を手順書から 1 つに決められる。
- 「## 例」の後に「## 破壊的な DB の操作の前の控え（I597）」を足す。中身:
  - コマンド: `bash scripts/claude/db-backup.sh <イシュー番号>_before`（単体で流す。前置き・振り向け・`&&` を付けない。理由は「外に出すコマンドの書き方」）。`bash scripts/db_backup.sh` は人の道具で、Claude から流すとサンドボックスの中で止まる
  - DB のコンテナが動いていないときは先に `docker compose up -d --wait db`
  - 出力: 今いるワークツリーの直下の `backup_<名前>_<日時>.sql`（`.gitignore` の `backup_*.sql` で git から外れる・権限 600）。確かめの中身（終了コード・空でない・完了の行・`\restrict` と `\unrestrict` の対）と、失敗したらファイルを残さず非 0 で止まること
  - 計画書の Danger Ops 欄の「ロールバック」には、この控えのファイル名を書く（戻すのは `psql` の流し込みで、それ自体が危険操作）
  - 控えは DB の中身の写しなので、イシューのマージの後に消す（close の片付け。消すのは自分が作った `backup_<名前>_*.sql` だけ）。コンテナの中に写しを作る回り道（`pg_dump -f /tmp/…` → `docker compose cp`）はしない

### 4-4. `.gitignore`
達成すること: つながった行を 2 行に戻し、`.github_token` を git から外す。
- `.github_tokenbackup_migration.sql` → `.github_token` と `backup_migration.sql` の 2 行

### 4-5. `scripts/claude/tests/test_i597_db_backup.sh`（新規）
達成すること: 本物の docker を使わずに、入口と人の包みの成功・失敗を固定する。
- 一時のフォルダに `git init` した写しのリポジトリを作り、`scripts/claude/db-backup.sh`・`scripts/db_backup.sh` を同じ相対パスに写す。`PATH` の先頭に偽の `docker`（呼ばれたことを記録し、決めた出力と終了コードを返す小さなスクリプト）を置く。本物のリポジトリには何も書かない
- 偽の `docker` を外の命令（境界）の差し替えにとどめ、入口の中には差し替えの口を作らない（9 に理由）
- 項目は auto_test の TC-01〜TC-03（成功・失敗の 4 通り・古い形・名前の誤り・人の包み）と FG（失敗の注入）

## 5. 実装手順（ステップ）
1. `scripts/claude/tests/test_i597_db_backup.sh` を書き、入口が無い今の状態で落ちることを見る（→ TC-01）
2. `scripts/claude/db-backup.sh` を書く（4-1）。ステップ 1 の後（→ TC-01・TC-02）
3. `scripts/db_backup.sh` を包みにする（4-2）。ステップ 2 の後（→ TC-01 の人の包みの項目・TC-02）
4. `.gitignore` を直す（4-4）。ほかのステップと独立（→ TC-04）
5. `docs/runbooks/danger-ops.md` に節を足す（4-3）。ステップ 2 の後（コマンドの形を確定してから。→ TC-05）
6. 失敗の注入（FG）を流して記録する（→ TC-03）

## 6. テスト計画
### 自動
- `scripts/claude/tests/test_i597_db_backup.sh`（決定論ゲート・CI の Harness Tests でも毎回流れる）: 入口の成功（中身がそのまま・権限 600・一時のファイルが残らない）／失敗の 4 通り（`pg_dump` の非 0・空・完了の行が無い・`\unrestrict` が欠けた）で非 0 かつ `backup_*.sql` が 1 つも無い／古い形（`\restrict` なし）は成功／名前の誤りは 2 で `docker` を呼ばない／人の包みの失敗でファイルが残らない。テストのレベルはスクリプトの単体（外の `docker` だけを偽にする）
- FG（テストの中）: 入口の写しから `trap` を消す・完了の行の確かめを消す、人の包みを今の形（`> "$OUTPUT"`）に戻す → 対応する項目が不合格になる
- `.gitignore`・手順書の節は TC-04・TC-05 の grep / `git check-ignore`
- 「Claude の手順として `bash scripts/db_backup.sh` を書いたら止める」決定論のテストは作らない（9 に理由）
### 手動
- M1（Claude）: このワークツリーで本物の DB に入口を流し、控えの中身・権限・一時のファイルが残らないこと・git に出ないことを確かめ、作った控えを消す
- M2（Claude）: Claude（サンドボックスの中）から `bash scripts/db_backup.sh` を流し、非 0・案内が出る・控えのファイルが増えないことを確かめる
- 終わったら、計画のスパイクで起動したこのワークツリーの DB を `docker compose stop db` で止める（データは消さない）

## 7. ロールバック
- PR を revert する。DB・設定に変更は無い。入口が無くなると、Claude が控えを取る手段は回り道に戻る

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 外で動くスクリプトが、名前の引数を通じて作業フォルダの外に書く | 名前を `^[A-Za-z0-9_-]{1,64}$` に限り、書く先を `$ROOT/backup_…sql` に固定。TC-01 の名前の誤りの項目で固定 | 回避 |
| R2: 途中で切れた控えを「控えがある」と思い、戻せない状態で破壊的な操作をする | 一時のファイル → 4 つの確かめ → 移す。失敗の 4 通りを TC-01 で固定し、FG で確かめが外れると落ちることを確かめる | 回避 |
| R3: DB の中身の控えがほかのユーザー・git・コンテナの中に漏れる | `umask 077`（権限 600 を TC-01 で確かめる）・`backup_*.sql` の `.gitignore`・標準出力で受けてコンテナに写しを作らない・手順書でマージ後に消す | 回避 |
| R4: 将来の pg_dump の版で最後の行の形が変わり、正しい控えでも止まる | 止まる側に倒れる（壊れた控えを通すより安全）。止まったら理由の行が出るので、すぐ気づいて直せる | 受け入れ |
| R5: 計画を書く人が、また `bash scripts/db_backup.sh` を Claude の手順に写す | 手順書に入口を書き、人の包みは中で止まったときに入口を案内する。決定論のテストは作らない（9） | 受け入れ |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 入口を `scripts/claude/` に置き、サンドボックスの設定は変えない／一時のファイル → 確かめ → 正式の名前／出力は作業フォルダの `backup_*.sql`／`scripts/db_backup.sh` も空のファイルを残さない／`danger-ops.md` に節を足す／戻す操作・`DANGER_OK=1` の前置き・ワークツリーの撤去の前の控えはスコープ外（/grill-me では聞くことは無かった）
Claude が決めた（技術的な選択と理由）:
- 入口の名前は `scripts/claude/db-backup.sh`（イシューの例のまま・`scripts/claude/` のほかのスクリプトと同じ kebab-case）— 仮定で決めた
- **受け入れ条件の「最後の行」の読み替え**: 調査結果 4 のとおり、今の pg_dump（15.19）は最後の行が `\unrestrict <鍵>` で、イシューの文言のままでは正しい控えも不合格になる。イシューの目的（途中で切れていない）は変えず、確かめを「完了の行がある」＋「`\restrict` があれば最後の空でない行が同じ鍵の `\unrestrict`」にした。仕様の価値判断ではなく、事実に合わせた技術的な直し — 仮定で決めた
- 人の包みは入口を呼ぶだけにする（同じ確かめを 2 か所に書かない。人が使っても同じ確かめが効く）— 仮定で決めた
- テストは外の命令（`docker`）だけを `PATH` の偽物で差し替える。入口に「流す命令を環境変数で替える口」を作ると、外で動くスクリプトに任意の命令を流せる口ができる（`docs/runbooks/plan-writing-rules.md:18` の「本番の設計を変えて差し替えを不要にする」より、外で動く中身を絞る安全を優先）— 仮定で決めた
- 一時のファイルは作業フォルダの直下（`backup_partial_XXXXXX.sql`）。`$TMPDIR` だと、移すのがファイルシステムをまたぐ写しになりうる・`.gitignore` の外の名前で途中まで残りうる — 仮定で決めた
- 名前を付けたときも日時を付ける（同じ名前で 2 回取ったときに前の控えを上書きしない）。既にあるときは上書きせず 1 — 仮定で決めた
- 「計画・手順書が Claude の手順として `bash scripts/db_backup.sh` を書いたら止める」決定論のテストは作らない。`docs/runbooks/plan-writing-rules.md`「決定論テストの対象の選び方」の 2 つの問いで、書いてしまっても、implement で流した時点で非 0 と入口の案内が出て、すぐ後の作業で気づける（被害は空の控えが残ることだったが、それはこのイシューで無くなる）— 仮定で決めた
- `.gitignore` のつながった行は、このイシューで直す（控えの置き場の `.gitignore` の確かめの途中で見つけた・`.github_token` が外れていない）— 仮定で決めた
- 一覧 docs/reviews/backlog/I224.md F9（FILE=-）: 残す — I224 の効果の測定で、DB の控えと関係しない
- 一覧 docs/reviews/backlog/I223.md B1（FILE=-）: 残す — bot の停止に関わる片付けで関係しない
- 一覧 docs/reviews/backlog/I223.md B2（FILE=-）: 残す — 同上
- 一覧 docs/reviews/backlog/I223.md B3（FILE=-）: 残す — 同上
- 一覧 docs/reviews/backlog/I223.md B4（FILE=-）: 残す — 同上
- 実装対象のファイル（`scripts/db_backup.sh`・`docs/runbooks/danger-ops.md`・`.gitignore`・`scripts/claude/db-backup.sh`）に当たる一覧の行は無い
- 要件適合: 受け入れ条件のうち「名前の誤り」「権限 600」「`.github_token`」はイシューに無い追加。前の 2 つは外で動くスクリプトの守り（イシューの「外で動いてよい中身かをレビューで見る」の具体化）、最後は調査で見つけた壊れの直しで、仕様の追加ではない。マルチテナント・ステータス遷移は該当なし
- セキュリティ: アプリのコードの変更は無い（Django・React・依存の変更なし。bandit・npm audit の対象なし）。入力の確かめは名前の正規表現（R1）。機密データは DB の中身の控え（R3）と `.env`（読み取りの禁止は変えない・入口は外で動くので `docker compose` が読むが、中身を出力しない）。`.github_token` を git から外す
- P3/P5/P8 影響なし（DB の変更・外部 API・非同期・新しいインフラは無い）
- P6 影響なし（画面・データ量の懸念なし）
- P9 影響なし（個人情報・テナントデータの新しい扱いは無い。開発の DB の控えは本人の手元だけで、マージ後に消す）
- 設計品質: 定数（DB 名 `learning_app`・ユーザー `postgres`）は `docker-compose.yml:6-7` と同じ値で、今の `scripts/db_backup.sh` と同じく入口の頭に変数として 1 回だけ書く。エラーの扱いは「理由の 1 行＋案内＋非 0」に統一
- UI の変更なし
Danger Ops（有無。有りのときは 影響範囲・代替案・ロールバック・実行コマンド を書く。条件と手順は docs/runbooks/danger-ops.md）:
- 無（読むだけの `pg_dump` と、作業フォルダの `.gitignore` 済みのファイルへの書き込み・自分が作った控えの削除だけ）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 2 | 読んで可 | 失敗の 4 通りで非 0 かつ控えのファイルが残らないことを TC-01 が本当に確かめているか（`backup_*.sql` の数を数える・偽の `docker` の出力が本物の pg_dump の形に沿う）。TC-03 の FG で確かめが外れると落ちるか |
| V2 | 3 | 読んで可 | 外で動く入口が、名前の引数・`cd`・振り向けを通じて作業フォルダの直下の `backup_*.sql` 以外に書かないか（TC-01 の名前の誤りの項目） |

## 計画変更記録
-
