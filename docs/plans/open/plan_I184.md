# plan_I184: I179 のワークツリー運用を既存の環境に適用する（wt-harness の移行・harness-1/2 の作成・ラベル説明文の更新）

## 基本情報
- **計画書ID**: plan_I184
- **関連イシュー**: #312
- **Draft PR**: #313
- **作成根拠資料**: docs/issues/open/I184.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I184_review.md
- **テスト文書**: docs/tests/open/I184_auto_test.md・docs/tests/open/I184_manual_test.md
- **作成日**: 2026-10-24

## 1. 背景/目的
I179 でワークツリーの運用を見直した（人が使うワークツリーは primary から公式の `claude --worktree <track>-<連番>` で作る・トラックはラベルで分ける）。I179 では手順書とスクリプトだけを変え、今ある環境の移行は残作業にした（作業場所が `wt-harness` 自身だったため）。本イシューで次の 4 点を行い、環境を I179 の形に揃える。
1. 旧方式の `wt-harness` を、未コミットのイシューファイルを失わずに撤去する
2. primary から公式方式で harness-1・harness-2 を作る
3. GitHub ラベルの説明文からワークツリー名を消す
4. 手順書 §11 どおりに進め、詰まった点と §7 の誤読しやすい点を直す

## 2. 受け入れ条件
イシューの AC をそのまま使う（→ 自動テストの TC 対応は §6）。
- [ ] `git worktree list` に `/mnt/c/app/wt-harness` が無く、`<primary>/.claude/worktrees/harness-1`・`harness-2` がある（TC-2）
- [ ] 撤去前の `wt-harness` にあった未コミットのイシューファイル・イシューレビューのうち closed 済みでないものがすべて primary にあり、`cmp` で一致を確かめた記録がある（対象の一覧と、コピーしなかったものとその理由を含む）（TC-4a・TC-4b・I184_review.md の一覧）
- [ ] `git symbolic-ref refs/remotes/origin/HEAD` が `refs/remotes/origin/develop`（TC-1）
- [ ] 新しいワークツリー 2 つに CLAUDE.md・`.claude/settings.json`・`backend/.env` があり、基点が develop（TC-3）
- [ ] `gh label list --search track` の説明文に `wt-harness`・`study-app-multitenant` が無い（TC-5）
- [ ] `docker compose ls -a` に `wt-harness` の取り残しが無い（TC-6。volume も見る）
- [ ] `worktree.md` §7 に反映のタイミングの補足がある（TC-7）
- [ ] 手順どおりに進まなかった箇所があれば `worktree.md` が直されている（無ければ「無し」と記録）（手動 No.4）

## 調査結果（2026-10-24・primary で確認）

### 環境前提
| 確認 | 結果 |
|------|------|
| `claude --version` | 2.1.310（`--worktree` は 2.1.304/2.1.306 で確認済みの挙動。worktree.md §2） |
| `docker compose ls -a` | `study-app-multitenant`（primary）のみ稼働 |
| `gh` | 利用可（ラベル一覧の取得は成功） |
| primary の Claude Code 信頼 | 済み（このセッションが primary で動いている） |
| §2 確認 2（`.worktreeinclude`・`.gitignore`・`_owning_root`） | 本ブランチ（develop 3ca7375 から作成）で `ok` |
| `origin/HEAD` | `refs/remotes/origin/main`（§2 確認 1 に通らない → ステップ 1 で直す） |
| `origin/main` と `origin/develop` | main は develop の祖先（`merge-base --is-ancestor` が exit 0）。main 基点の空ワークツリーでも「HEAD が develop の履歴にある」は成り立つため、基点の確認には `.worktreeinclude` の有無を併用する（TC-3） |

### wt-harness の状態
- ブランチ `feature/I181-slim-review-process`・HEAD 26d06ec（PR #311 で develop にマージ済み・`git branch --merged origin/develop` に出る）。未 push コミット無し。ロック無し・入れ子無し（`git worktree list --porcelain`）。**I181 は完了済みなので、イシューの「着手の時期」の前提は満たしている。**
- `??`（`--untracked-files=all`）は 39 件。分類（develop の `docs/issues/closed/` と primary の同名ファイルとの突き合わせ。両方にあるものは 0 件）:

| 区分 | 件数 | ファイル | 扱い |
|------|-----:|---------|------|
| イシューファイル（open のまま） | 17 | `docs/issues/open/` の I093・I094・I099・I101・I110・I112・I118・I125・I128・I130・I135・I136・I139・I152・I175・I176・I177 | primary にコピー |
| イシューファイル（closed 済み） | 2 | `docs/issues/open/I121.md`・`I151.md`（develop に `docs/issues/closed/I121.md`・`I151.md` がある） | **コピーしない**（§11「コピーしないもの」＝古い版） |
| イシューレビュー | 20 | `docs/reviews/I{093,094,099,100,101,110,112,118,121,125,128,130,135,136,139,151,152,175,176,177}_issue_review_*.md` | primary にコピー（§11 の「コピーしないもの」はイシューファイルだけが対象。I100・I121・I151 は closed 済みイシューのレビューだが、develop の `docs/reviews/closed/` に無く、ここで捨てると記録が消えるためコピーする） |

- `!!`（gitignore 済み）: `.claude/settings.local.json`・`.env`・`backend/.env`・キャッシュ類（`.ruff_cache/`・`__pycache__/`・`.pytest_cache/`）・`backend/celerybeat-schedule`・`backend/logs/`。
  - `.claude/settings.local.json`: wt-harness 側は `enabledMcpjsonServers: ["github"]` だけで、primary 側に同じ行がある（primary が上位集合）→ **反映不要**。
  - `.env`: wt-harness のポート割当（offset 10）。撤去で不要になる → 反映不要。
  - `backend/.env`: wt-harness 作成時に primary からコピーしたもの。秘密情報のため中身を読まない（比較の `cmp` も権限で拒否された）→ 反映しない（primary が元）。
  - キャッシュ・ログ・celerybeat-schedule: 作業の記録ではない → 反映不要。
- **Docker（イシューの想定と違う）**: `docker compose ls -a` には出ないが、**named volume が 4 つ残っている**（`wt-harness_postgres_data`・`wt-harness_redis_data`・`wt-harness_backend_logs`・`wt-harness_backend_static`、作成 2026-10-21T00:42:28Z＝I179/I181 を wt-harness で進めていた時期。コンテナは無い）。`wt-remove.sh` はこの場合「コンテナが無く volume だけが残っている」で止まり、バックアップの手順を示して `DANGER_OK=1` での再実行を求める（`scripts/claude/wt-remove.sh` 165〜181 行）。同名の別ワークツリー・別クローンは無い（`git worktree list` に `wt-harness` は 1 つ・このPCのクローンはこの 1 つ）。→ イシューの影響範囲「あれば `wt-remove.sh` の判定と danger-ops に従う」の分岐に入る（ステップ 4）。
- AC の「`docker compose ls -a` に取り残しが無い」は volume だけの取り残しを見逃すため、TC-6 では `docker volume ls` のラベル検索も見る。

### ラベル
- `track:app`「学習アプリ開発トラック（worktree: study-app-multitenant）」・`track:harness`「ハーネス改善トラック（worktree: wt-harness）」。
- `danger-ops.md` 3 行目の「PR に danger-approved」のラベルは GitHub に無い（`gh label list --search danger` が空）。→ ユーザーの選択で、作成して PR #313 に付ける（設計判断 D8・4-11）。

### `claude --worktree` の注意（worktree.md §2 の既知事項）
- 対話セッションとして起動する（Bash ツールからは実行できない）→ 作成はユーザーが別のターミナルで行う。
- 変更が無いまま対話セッションを終えると「Worktree removed (no changes)」で自動的に消える（2.1.306 で確認済み）。作った直後のワークツリーは変更が無いので、確認（TC-2・TC-3）が終わるまでセッションを開いたままにする。§11 手順 4 にこの注意が無いので、ステップ 6 で補う（手動 No.4 で実際の挙動も確かめる）。

### 参照先の実在
本計画で触る `worktree.md` の参照（`scripts/claude/wt-remove.sh`・`scripts/claude/wt-ports.sh`・`.worktreeinclude`・`scripts/claude/hooks/pretooluse_guard.py`・`docs/runbooks/danger-ops.md`）は全件存在（`test -f`）。

### 原因の概要
I179 は wt-harness の中で進めたので、自分の作業場所を移せなかった。ラベル説明文と `origin/HEAD` は PR に入らない環境側の状態なので、手順書を直しただけでは変わらない。

## 3. 影響範囲
| 区分 | 内容 |
|------|------|
| Backend / Frontend / DB（アプリ） | なし |
| Config/Infra | primary の `refs/remotes/origin/HEAD`・ワークツリー構成（wt-harness 撤去・harness-1/2 作成）・wt-harness の Docker volume 4 つの削除（危険操作）・GitHub ラベル説明文 2 件・GitHub ラベル `danger-approved` の新規作成と PR #313 への付与 |
| ドキュメント | `docs/runbooks/worktree.md`（§7 の補足・§11 手順 4 の注意・実行中に見つかった不足） |
| primary の未コミットファイル | `docs/issues/open/`（17 件）・`docs/reviews/`（20 件）を追加（未コミットのまま） |
| primary の gitignore 済みファイル | `backup_wt-harness_<日時>.sql`（`.gitignore` の `backup_*.sql` に当たる） |
| ローカルブランチ | `feature/I181-slim-review-process`（マージ済み）を `git branch -d` で消す |
| 依存関係ファイル | 変更なし |

## 4. 変更点一覧
| # | 対象 | 変更 |
|---|------|------|
| 4-1 | primary `refs/remotes/origin/HEAD` | `git remote set-head origin --auto` → `refs/remotes/origin/develop` |
| 4-2 | `<primary>/.claude/worktrees/harness-1`・`harness-2` | ユーザーが primary で `claude --worktree harness-1`・`claude --worktree harness-2` |
| 4-3 | primary `docs/issues/open/`・`docs/reviews/` | wt-harness から 37 件を `cp`（§2 調査結果の表） |
| 4-4 | primary 直下 `backup_wt-harness_<YYYYmmdd_HHMM>.sql` | wt-harness の Postgres のバックアップ（`wt-remove.sh` が示す 3 手順） |
| 4-5 | wt-harness の untracked 39 件 | wt-harness 側で削除（ユーザーのターミナル） |
| 4-6 | `/mnt/c/app/wt-harness`・Docker volume 4 つ | `DANGER_OK=1 bash scripts/claude/wt-remove.sh /mnt/c/app/wt-harness`（`docker compose -p wt-harness down -v` → `git worktree remove`） |
| 4-7 | ローカルブランチ `feature/I181-slim-review-process` | `git branch -d`（マージ済み。未マージなら -d が拒否するので消えない） |
| 4-8 | ラベル `track:harness`・`track:app` | 説明文を「ハーネス改善トラック」「学習アプリ開発トラック」に |
| 4-9 | `docs/runbooks/worktree.md` §7 | 冒頭の 1 文の後に「ワークツリー間の反映のタイミング」を追記（下の文案） |
| 4-11 | GitHub ラベル `danger-approved`（新規）・PR #313 | 危険操作の承認後に `gh label create danger-approved --description "危険操作（danger-ops.md）をユーザーが承認済み" --color b60205` → `gh pr edit 313 --add-label danger-approved`。404（権限不足）ならユーザーが Labels 画面で同じ名前・説明で作り、PR に付ける |
| 4-10 | `docs/runbooks/worktree.md` §11 手順 4 | 作った直後は変更が無く、セッションを終えると自動で消える注意を追記（下の文案）。ほかに実行中に手順どおりに進まなかった箇所があれば同じく直す |

**4-9 の文案（§7 の冒頭の段落の直後に入れる）**:

```markdown
**ワークツリー間の反映のタイミング**: 「共有される」のはコミットの履歴であって、作業中のファイルではない。各ワークツリーのファイル（スキル・手順書・`.claude/settings.json` を含む）は、そのワークツリーが今チェックアウトしているブランチの内容で動く。
- 別のワークツリーで直したスキル・手順書は、PR で develop にマージされ、さらに自分のワークツリーがそれを取り込むまで反映されない（どこかで直せば即全体に効く、ではない）。新しいイシューは `/plan-issue` が最新の `origin/develop` からブランチを作るので自然に入る。
- 作業途中のワークツリーに取り込むときは、そのワークツリーのセッションで `git fetch origin` → `git merge origin/develop` を行う（未コミットの変更は先にコミットしておく）。
- 例外（ブランチによらない）: `~/.claude` の個人設定・メモリ、git config、git stash は 1 つで全ワークツリーに即効く（下の「共有される」）。サブエージェントのフック（ガード）と `.worktreeinclude` は、作業しているワークツリーではなく primary が今チェックアウトしているブランチの内容で決まる（§2「primary のブランチ」）。
```

**4-10 の文案（§11 手順 4 の末尾に足す）**:

```markdown
     作った直後のワークツリーは変更が無いので、そのセッションを終えると確認なしで自動的に消える（§2「終了時の確認」）。使うときに作ればよく、残しておきたいときはセッションを開いたままにする（消えても同じコマンドで作り直せる）。
```

## 5. 実装手順
**順序の考え方**: 未知リスク（`claude --worktree` が develop 基点で作れるか）を先に確かめる（ステップ 1・2）。作成は撤去と独立なので、撤去（危険操作）より前に行う。撤去はコピーの確認（ステップ 3）の後でなければ行わない。

| ステップ | 内容 | 実施 | 前提 |
|---------|------|------|------|
| 1 | primary で `git fetch origin` → `git remote set-head origin --auto`。→ TC-1・TC-0 参照 | Claude | なし |
| 2 | ユーザーが primary（`/mnt/c/app/study-app-multitenant`）の別のターミナルで `claude --worktree harness-1`、さらに別のターミナルで `claude --worktree harness-2` を起動し、どちらも**セッションを開いたまま**にする（ステップ 7 の確認が終わるまで）。Docker は使わないので `wt-ports.sh` は実行しない（使うときに §5・§6 で行う）。→ TC-2b・TC-3 参照 | Human | 1 |
| 3 | primary のセッションで、§2 の表の「コピー」37 件を `cp /mnt/c/app/wt-harness/<パス> <パス>` でコピーする（primary に同じパスのファイルが無いことは調査で確認済み。コピー直前にもう一度 `test ! -e <パス>` を見て、あれば止まって `cmp`）。コピーした一覧・コピーしなかった 2 件と理由を `I184_review.md` の一覧に書く。→ TC-4a・TC-4b 参照 | Claude | なし（1・2 と並行可） |
| 4 | **危険操作の承認を得る**（下の「Danger Ops」の内容を提示）。承認後、4-11 で `danger-approved` ラベルを作って PR #313 に付け（→ TC-9 参照）、primary で `wt-remove.sh` が示すバックアップの 3 手順を行う: `( cd '/mnt/c/app/wt-harness' && docker compose -p 'wt-harness' up -d db )` → `( cd '/mnt/c/app/wt-harness' && docker compose -p 'wt-harness' exec -T db pg_dump -U postgres learning_app ) > backup_wt-harness_<YYYYmmdd_HHMM>.sql`。→ TC-8 参照 | Claude（承認は Human） | 3 |
| 5 | ユーザーが wt-harness のターミナル（wt-harness で開いている Claude セッションがあれば終了してから）で、untracked の 39 件を削除する: `cd /mnt/c/app/wt-harness && git status --porcelain --untracked-files=all \| sed -n 's/^?? //p' \| xargs -d '\n' rm --`。続けて primary のセッションで `DANGER_OK=1 bash scripts/claude/wt-remove.sh /mnt/c/app/wt-harness`（見張りが承認画面を出す）。完了メッセージに出たブランチを `git branch -d feature/I181-slim-review-process` で消す。→ TC-2a・TC-6 参照 | Human（削除）・Claude（撤去） | 3・4 |
| 6 | ラベル: `gh label edit track:harness --description "ハーネス改善トラック"`・`gh label edit track:app --description "学習アプリ開発トラック"`。404（権限不足）ならユーザーが GitHub の Labels 画面で同じ文言に変える。`worktree.md` に 4-9・4-10 を入れ、ステップ 1〜5 で手順どおりに進まなかった箇所があれば直す（無ければ `I184_review.md` に「無し」）。→ TC-5・TC-7 参照 | Claude（ラベルの UI 操作は Human） | 5（4-10 以外の手順の修正はステップ 5 までの結果で決まる） |
| 7 | 自動テスト全件を実行して記録し、計画書・テスト・レビュー文書をコミットして push。→ auto_test 全件 | Claude | 1〜6 |

- サービスの再起動は不要（primary の Docker には触れない。wt-harness の db は手順 4 で起動し、手順 5 の `down -v` で止まる）。
- 未コミットのイシューファイル・イシューレビュー（コピーした 37 件）はコミットしない（運用上わざと未コミット）。

### Danger Ops（ステップ 4・5）
- **対象**: Compose プロジェクト `wt-harness` の named volume 4 つ（Postgres・Redis の開発データ・ログ・static）の削除（`docker compose -p wt-harness down -v`）と、wt-harness フォルダの撤去（gitignore 済みの `.env`・`backend/.env`・キャッシュも消える）。primary（`study-app-multitenant`）のデータには触れない（`-p wt-harness` で固定・`wt-remove.sh` が作業フォルダのラベルと同名の検査を行う）。
- **代替案**: volume を消さずに撤去する（`KEEP_DATA=1` は docker が使えるときは効かず止まる）→ 使わないデータが残り続けるため採らない。
- **ロールバック**: Postgres はステップ 4 のバックアップから戻せる（`docker compose -p <名前> exec -T db psql -U postgres learning_app < backup_…sql`）。Redis・ログ・static は開発用の一時データで戻さない。ワークツリーはブランチが残る（I181 のブランチは develop にマージ済み）ので `git worktree add` で作り直せる。untracked のファイルは primary 側のコピーから戻す。
- **実行コマンド**: `DANGER_OK=1 bash scripts/claude/wt-remove.sh /mnt/c/app/wt-harness`
- **承認の記録**: ユーザーの明示承認を `I184_review.md` に記録し、PR #313 に `danger-approved` ラベルを付ける（D8・4-11）。

## 6. テスト計画
- アプリのコード変更が無いため pytest・Jest・E2E は対象外。
- 自動（`docs/tests/open/I184_auto_test.md`）: 環境の状態を見る決定論 TC（TC-0〜TC-8）。合否は exit code。否定・不在の TC（TC-2a・TC-4a・TC-5・TC-6・TC-7）は、計画時点で実際に不合格になることを確かめた（いまの環境そのものが失敗条件＝移行前の状態）。存在を見る TC（TC-2b・TC-3・TC-4b・TC-8）は欠けた対象を与えて不合格になることを確かめた（FG）。
- 手動（`docs/tests/open/I184_manual_test.md`）: `claude --worktree` の作成・終了時の挙動（Human）、コピーしなかったものの妥当性、手順の不足の記録、ラベルの見た目。
- テストレベル: すべて環境・文書の確認（結合相当）。認可・テナント境界の変更は無い。

## 7. ロールバック
| 変更 | 戻し方 |
|------|-------|
| `origin/HEAD` | `git remote set-head origin main`（戻す理由は無い想定） |
| harness-1/2 | `bash scripts/claude/wt-remove.sh <パス>`、または変更が無ければセッション終了で自動的に消える |
| コピーした 37 件 | primary で `rm <パス>`（wt-harness 撤去後は primary が唯一の写しなので戻さない） |
| wt-harness・volume | 「Danger Ops」のロールバック |
| ラベル説明文 | `gh label edit` で元の文言に戻す |
| `danger-approved` ラベル | 残す（以後の危険操作でも使う）。不要なら `gh pr edit 313 --remove-label danger-approved` → `gh label delete danger-approved` |
| `worktree.md` | PR を戻す（revert） |

## 8. Risk & 回避策
| リスク | 回避策 |
|-------|-------|
| コピー漏れのまま wt-harness 側を削除し、イシューファイルが消える | ステップ 3 の TC-4a（全 `??` がコピー済みで一致、またはコピーしない理由に当たる）が exit 0 になるまでステップ 5 に進まない |
| `origin/HEAD` を直す前に `claude --worktree` を実行し、main 基点の空ワークツリーができる | ステップ 2 は TC-1 の合格後。TC-3 で `.worktreeinclude` の有無を見る（できていたら `wt-remove.sh` で消して作り直す） |
| 作った直後のワークツリーがセッション終了で消え、AC を確かめられない | 確認が終わるまでセッションを開いたままにする（ステップ 2）。消えても同じコマンドで作り直す |
| `down -v` が primary のデータを消す | `wt-remove.sh` が `-p wt-harness` で固定し、作業フォルダ・同名を検査する。手で `down -v` は打たない |
| バックアップが空のまま削除に進む | TC-8（`test -s`）が合格するまでステップ 5 に進まない |
| wt-harness で Claude セッションが開いたまま撤去し、そのセッションが壊れる | ステップ 5 の前にユーザーが wt-harness のセッションを終了する |
| ラベル編集が 404 | ユーザーの UI 操作に切り替える |

## 9. 承認ポイント
- [ ] コピーする 37 件・コピーしない 2 件（I121・I151 のイシューファイル）の仕分け（I100・I121・I151 のイシューレビューはコピーする）
- [ ] wt-harness の Docker volume 4 つを、バックアップのうえ `DANGER_OK=1` で削除する（危険操作。実行直前にもう一度承認をもらう）
- [ ] `danger-approved` ラベルを作って PR #313 に付ける（D8・計画時にユーザー選択済み）
- [ ] harness-1・harness-2 の作成はユーザーが別ターミナルで行い、確認が終わるまで開いたままにする
- [ ] `worktree.md` §7（4-9）と §11 手順 4（4-10）の文案
- [ ] マージ済みの `feature/I181-slim-review-process` をローカルから消す

## 設計判断の一覧
| # | 判断 | 根拠 |
|---|------|------|
| D1 | 着手は I181 完了後（今は完了済み） | イシューに明記（設計確認メモ） |
| D2 | closed 済みイシューのイシューファイルはコピーしない／イシューレビューはコピーする | イシュー・§11 に明記（「コピーしないもの」はイシューファイルだけ） |
| D3 | gitignore 済みのファイルは反映しない（`settings.local.json` は primary が上位集合） | §11 の手順で比べた結果 |
| D4 | wt-harness の volume はバックアップしてから `DANGER_OK=1` で消す | イシュー（Danger Ops「`wt-remove.sh` の停止メッセージにあるバックアップ手順と danger-ops.md の承認を経て」）に明記 |
| D5 | harness-1/2 の作成はユーザーが行い、`wt-ports.sh` は今は実行しない | イシュー（§5・§6 に従う＝Docker を使う前に実行）と `claude --worktree` が対話セッションであること |
| D6 | マージ済みの I181 ブランチを `git branch -d` で消す | §4「不要なら `git branch -d` で消す」 |
| D7 | §11 手順 4 に「作った直後は終了で消える」注意を足す | イシューのスコープ「実行中に見つかった手順の不足の修正」。§2 の既知事項を §11 から参照できていない |
| D8 | `danger-approved` ラベルが GitHub に無いので、作成して PR #313 に付ける（4-11） | 計画時にユーザーが選択（2026-10-24。選択肢は「ラベルを作って付ける」／「会話の承認を記録するだけ」） |

## セルフチェック
- 要件適合性: AC の範囲内。Docker volume の削除はイシューの「あれば」の分岐。§11 手順 4 の注意（4-10）はスコープ「手順の不足の修正」に入る。マルチテナント・ステータス遷移は該当なし。
- セキュリティ影響なし（アプリのコード変更なし）。`backend/.env` は中身を読まない。バックアップ（開発 DB のダンプ）は gitignore 済みの名前で primary 直下にのみ置き、コミット・共有しない。依存の追加なし。bandit・npm audit の対象変更なし。
- P3/P5/P8 影響なし（DB スキーマ変更・外部 API・新規インフラなし。Docker volume の削除は Danger Ops として扱う）。
- P6 影響なし（UI・性能に関わる変更なし）。
- P9 影響なし（個人情報・テナントデータを扱う変更なし。開発 DB のダンプは手元のみ）。
- 設計品質: 新しい仕組みを作らず、既存の手順（§2・§4・§11）とスクリプトを使う。設定値のハードコードなし。
