# 計画書: I200 見張りの確認を「本当に危ない操作」だけに絞る

## 基本情報
- **計画書ID**: plan_I200
- **関連イシュー**: #335
- **Draft PR**: #397
- **作成根拠資料**: docs/issues/open/I200.md
- **実装後評価**: docs/reviews/open/I200_review.md
- **作成日**: 2026-10-29

## 1. 背景/目的
普通の開発・検証の操作（コンテナの中で Python のファイルを動かす・Dockerfile や依存のファイルを直す・ワークフローの action の版を上げる など）で承認画面が出て、作業と裏で動くレビュー役が止まっている（I166・I211・I213）。ユーザーの方針（2026-10-25・10-29）に沿い、確認を次の 3 種類（＋残すと決めたもの）に絞る。
- (A) GitHub の破壊（force push・保護ブランチへの push・リモートのブランチの削除・fork の PR の取り込み など）
- (B) 復旧できない状態（未コミットの変更を消す git の操作・ファイルの削除・dev DB のデータを消す操作）
- (C) 秘密・個人情報の流出（秘密ファイルの表示・外部への送信・秘密情報を使うワークフローの書き換え）

あわせて、許可の判定の一部が primary（元のフォルダ）の設定で行われるのに primary が古いまま残る穴を、セッションの開始時の自動の早送りで塞ぐ（設計確認メモ 2026-10-29）。

## 2. 受け入れ条件
イシューの受け入れ条件のとおり（`docs/issues/open/I200.md`）。この計画での確かめ方の対応は「6. テスト計画」の表。

## 3. 影響範囲
- Backend・Frontend・DB: なし
- Config/Infra（ハーネス）: `scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`・`scripts/claude/hooks/sessionstart_context.py`・ハーネステスト・`docs/runbooks/danger-ops.md`・`docs/runbooks/worktree.md`
- `pretooluse_guard.py`・`.claude/settings.json` は「GitHub から復旧できない例外」に関わるファイル（`scripts/claude/code-review.sh` の `path_risk_trigger()`）。安全装置そのものの変更なので高リスク（設計のセキュリティレビュー・敵対的レビューの対象）

## 調査結果（2026-10-29・計画の前に実測）

### どの層が確認を出しているか（イシューの「未特定・計画の最初に確定」）
`scripts/claude/check-permission-prompt.sh`（通常モード・ブランチの設定）で 6 つとも「承認画面が出る」（exit 10）。見張りに直接かけた結果（JSON を `pretooluse_guard.py` に渡す）で層を切り分けた。

| 操作 | 見張り単体 | 承認画面を出している層 |
|---|---|---|
| `docker compose cp <scratchpad のファイル> backend:/tmp/x.py` | ASK「コンテナからのファイルの取り出し（docker cp）」 | 見張りの 2（外部送信）。**向きを見ていない誤判定**（ホスト→コンテナでも「取り出し」になる・`pretooluse_guard.py:2267-2268`）。加えて許可の設定に `docker compose cp` が無い |
| `docker compose exec -T backend python /tmp/x.py` | ASK「コンテナ内の操作を安全と確認できませんでした」 | 見張りの 3（コンテナ内）＋許可の設定（`docker compose exec` が allow に無い） |
| `docker compose exec -T backend python manage.py shell -c "exec(open('/tmp/x.py').read())"` | ASK（同上） | 見張りの 3＋許可の設定 |
| `docker compose exec -T -e PYTHONPATH=/tmp backend python -m pytest --co -q -p i200x accounts/tests.py` | 0（通す） | 許可の設定だけ |
| `docker compose exec -T db psql ... -tAc 'select 1'` | 0 | 許可の設定だけ |
| `git rebase --help` | 0 | 許可の設定の `ask`（`Bash(git rebase *)`） |
| `docker compose exec -T backend python manage.py seed_e2e`（参考） | ASK（見張りの 3） | 見張りの 3＋許可の設定 |
| `docker compose exec -T backend python manage.py test accounts`（参考） | 0 | 許可の設定だけ |

→ 見張りを直すだけでは足りない。許可の設定に `docker compose exec|run|cp` を足し、判定を見張りに一本化する（`git push *` が allow で見張りが判定するのと同じ形。`.claude/settings.json:42-43`）。

### 見張りが確認を出す場所（`pretooluse_guard.py` の `main()`・3453〜3575 行と 3590〜3597 行）
| # | 確認の理由 | 方針（設計確認メモ） | この計画での扱い |
|---|---|---|---|
| 1 | `DANGER_OK=1` 付きの危険操作（3440・3523・3565） | (B) | 残す |
| 2 | 外部への送信・秘密情報の表示（3534） | (C) | 残す。ただし `docker compose cp` のホスト→コンテナは外す（誤判定の是正・下の 5-3） |
| 3 | コンテナ内の操作を安全と確認できない（3538・安全網 3567 の container） | 一律の確認をやめる | 危ない語を含むときだけ確認（5-2） |
| 4 | 未コミットの変更を消すかもしれない git（3547） | (B) | 残す |
| 5 | GitHub から戻せないことがある操作（3550） | (A) | 残す |
| 6 | 動的・不透明な宛先の push（3553） | (A) | 残す |
| 7 | 読みきれない（読み解きの例外 3499・安全網の例外 3560・引用符が閉じていない 3573） | 危ない語を含むときだけ確認 | 5-2 の同じ判定に寄せる |
| 8 | fork の PR の取り込み・対象を特定できない `gh pr`（3424・3450） | (A)・(C)（外部のコードを手元で動かしうる） | 残す（grill-me の 2 回目で確認・技術判断） |
| 9 | 見張り自身の失敗（`_fail_safe`・3597） | 読みきれない側 | 5-2 の同じ判定に寄せる（判定自体が失敗したら確認のまま） |

### 許可の設定の `ask`（16 件・`.claude/settings.json:96-113` 付近）
設計確認メモのとおり 15 件を外し、`Edit(.secrets.baseline)` だけを残す（5-5）。

### 既存のテスト（この計画で期待値が変わるもの）
- `scripts/claude/tests/test_settings_permissions.sh`（ask の一覧・exec 系の行の禁止）
- `scripts/claude/tests/test_pretooluse_container_guard.sh`（コンテナ内の ASK 208 件のうち、見張りの 3 による ASK。外部送信〔X1〜〕の ASK は変わらない）
- `scripts/claude/tests/test_i182_guard_failsafe.sh`（見張りの失敗の確認）
- `scripts/claude/tests/test_pretooluse_guard_matrix.sh`・`test_guard_corpus_diff.sh`・`test_guard_bash_oracle.sh`（danger-ops.md「見張りを直したら流す 3 つ」）

### セッションの開始のフック
- `scripts/claude/hooks/sessionstart_context.py`（`.claude/settings.json` の `SessionStart`・timeout 30 秒）。各コマンドは 5 秒で打ち切り、失敗しても exit 0。出力は 10 行以内（`test_sessionstart_context.sh` の TC-11b）
- フックはツールの呼び出しではないので、Claude Code 本体のワークツリー隔離（`git -C <primary>` を拒否する判定）の対象外の見込み。**未実証**（実際のセッションの開始で動くかはステップ 4 の最後とマージ後の手動テストで確かめる。フックは素の子プロセスとして動くので、`python3` で直接実行した結果と同じになる見込み）

### 軽い指摘の一覧
- 一覧の該当なし（`docs/reviews/backlog/` に実装対象のファイルと `FILE=-` の行が無い）

## 4. 変更点一覧
| ファイル | 変更 |
|---|---|
| `scripts/claude/hooks/pretooluse_guard.py` | 5-1〜5-4（危ない語の判定の追加・コンテナ内と読みきれないときの一律の確認をやめる・`docker compose cp` の向き・ワークフローと pre-commit の設定の編集の中身の確認） |
| `.claude/settings.json` | 5-5（ask を 1 件に・allow に `docker compose exec|run|cp`・`docker-compose` の同じもの・`git rebase *`・`psql *`、Edit の `.github/workflows/**`・`.github/dependabot.yml`・`.pre-commit-config.yaml`・`docker-compose.yml` を足す） |
| `scripts/claude/check-permission-prompt.sh`・`scripts/claude/tests/test_check_permission_prompt.sh` | 5-5b（Write に承認画面が出るかを確かめる種類 `write` を足す） |
| `scripts/claude/hooks/sessionstart_context.py` | 5-6（primary の早送り） |
| `scripts/claude/tests/test_i200_guard_narrowing.sh`（新規） | TC-01〜TC-05 |
| `scripts/claude/tests/test_sessionstart_context.sh` | TC-07 を足す |
| `scripts/claude/tests/test_settings_permissions.sh`・`test_pretooluse_container_guard.sh`・`test_i182_guard_failsafe.sh` | 期待値を新しい基準に合わせる（変えたケースを auto_test に列挙） |
| `docs/runbooks/danger-ops.md` | 「見張りの扱い」の 3〜5・失敗時・編集の確認・「避ける書き方」、「GitHub から復旧できる範囲」の表のワークフローの行を新しい基準に書き直す。確認を出す基準（(A)〜(C)＋残すもの）を 1 か所にまとめる |
| `docs/runbooks/worktree.md` | §9 に「primary の早送りだけの例外」、§2 に開始時の早送りの説明 |

`docs/runbooks/workflow.md` は変えない（「権限と二重ガード」の詳しい基準は danger-ops.md にあり、workflow.md には確認の基準を書いた所が無い。イシューの実装対象からの読み替え）。

## 5. 実装手順

### 5-1. 危ない語の判定（新設・見張りの中に 1 つ）
**修正方針**: 「安全と確認できない」操作を、一律に確認するのをやめ、(A)〜(C) につながる語が文字列のどこかにあるときだけ確認にする。粗い文字の一致にとどめ、シェルの動きを読む精密な判定は作らない（I179 の教訓）。見張りの脅威モデルは「事故」（意図的な回避は対象外。danger-ops.md）。

- 関数 `_risky_words(text) -> list[str]`: 大文字・小文字を区別せず、次の語を探して、当たった語を返す。英数字で始まる語は、直前が英数字・`_` でないときだけ当たる（`(?<![A-Za-z0-9_])` を前に付けた正規表現。`dd` が `add`・`odd` に当たらないように。計画レビュー 1 の Warning）。英数字で終わる短い語（`rm`・`dd`・`git`・`gh`・`nc`・`ssh`・`scp`）は直後も英数字・`_` でないときだけ当たる。引用符の中・ヒアドキュメントの本文・コメントも含めて見る（読みきれない書き方では区切りが当てにならないため、文字列全体を見る）
  - (B) 消す・壊す: `rm`・`rmdir`・`unlink`・`rmtree`・`remove(`・`truncate`・`drop`・`delete`・`flush`・`destroy`・`wipe`・`shred`・`mkfs`・`dd`・`.update(`・`bulk_update`
  - (A) GitHub: `git`・`gh`・`push`
  - (C) 外部・秘密: `curl`・`wget`・`nc`・`ncat`・`ssh`・`scp`・`rsync`・`requests`・`urllib`・`http.client`・`httpx`・`socket`・`smtplib`・`send_mail`・`mail_admins`・`email_user`・`EmailMessage`・`.delay(`・`apply_async`・`openai`・`.env`・`environ`・`printenv`・`secret`・`password`・`token`・`api_key`
  - 広すぎて普通の書き方を確認にしやすい `reset`・`clean`・`email` は入れない（`git reset`・`git clean` は `git` で、メールの送信は `send_mail` などで拾う）
  - 誤って確認になる量は、既存の `test_guard_corpus_diff.sh`（過去の作業コマンドで、新しく確認・停止になったものが記録の 1% を超えないか）で測る（TC-08）
- 一覧は定数 `_RISKY_WORDS` に置き、理由ごとに分けたコメントを付ける。語を足すのは事故の例が出たときだけ（作り込まない）
- 書き込みのリダイレクト（`>`・`>>`）は、行き先が `/tmp/` か `/dev/null` 以外なら確認（コンテナの `/app/` はリポジトリの `backend/` で、未コミットの変更を上書きしうる・(B)）。既存の `c["writes"]` を使う

### 5-2. コンテナ内と読みきれないときの扱い（見張りの 3・7・9）
- 見張りの 3（`main()` の `an["container"]`・安全網の `net["container"]`）: 許可リスト（`_container_safe`）に入らないコンテナ内の操作は、その単純コマンドの文字列に `_risky_words` が当たるか、5-1 の書き込みがあるときだけ確認。当たらなければ通す。コンテナの中で実行するスクリプト・`-c` のコードの中身が読める（`/app/` → `backend/` などの読み替え〔`_CONTAINER_MOUNTS`〕で手元のファイルになる）ときは、その中身にも語の判定をかける（既存の読み替えを使う）
- 見張りの 7: 引用符が閉じていない（`an["unsure"]`）・読み解きの例外（3499）・安全網の例外（3560）は、コマンド全体の文字列に `_risky_words` が当たるときだけ確認
  - 読み解きが例外で止まったときは、危険操作（停止）の判定も走っていない。このため、語が当たれば確認にする（停止にはしない。確認＝人が見る）。語が当たらなければ通す
- 見張りの 9（`_fail_safe`）: 標準入力の JSON からコマンド・編集の中身を取り出せれば、同じ語の判定で決める。取り出せない・語の判定自体が失敗したときは、今までどおり確認
- `_container_safe` は残す（許可リストに入る操作は、語があっても通す。例: `pytest -k delete`）

### 5-3. `docker compose cp` の向き（見張りの 2 の誤判定の是正）
- `docker cp`・`docker compose cp` の「取り出し」は、コピー元がコンテナ側（`<サービスかコンテナ>:<パス>` の形）のときだけにする（コンテナの中の秘密ファイル・データを手元に出しうるため確認のまま）
- ホスト→コンテナ（コピー先がコンテナ側）は外部送信ではない。コピー元の手元のファイルが読めるときは、その中身に `_risky_words` をかけ、当たれば確認（コピーしてからコンテナで実行する形〔danger-ops.md「見張りを避ける書き方」〕の中身を、コピーの時点で見る）。読めない（存在しない・ディレクトリ・1MB を超える）ときは確認

### 5-4. ワークフローと pre-commit の設定の編集（見張りの Edit／Write の分岐・`main()` 3456〜3464 行）
**修正方針**: 設定の `ask` の一律の確認をやめ、書き換えの前と後の中身を比べて、秘密が外に出うる語・検査を弱める語が**増えた**ときだけ確認にする。action の版の書き換えなど、語が増えない編集は通す。

- 前後の中身の作り方: Edit は今のファイルの中身に `old_string` → `new_string` の置き換え（`replace_all` を含む）をかけたもの、MultiEdit は順にかけたもの、Write は `content`。今のファイルが無ければ前は空。今のファイルが読めない・置き換えの前の文字が見つからないときは、`new_string`（Write は `content`）だけを「後」、空を「前」として比べる（語が新しく出れば確認＝安全側）
- `.github/workflows/` 配下（`*.yml`・`*.yaml`）: 次の語の出現数が前より後で増えたら確認
  - `secrets.`・`secrets: inherit`（秘密情報を使う・広げる）
  - `write`・`id-token`（権限を広げる。`permissions:` の `contents: write`・`write-all` を粗く拾う）
  - `pull_request_target`・`workflow_run`（外の人の PR の中身を秘密情報つきで動かせるきっかけ）
  - `curl`・`wget`・`nc `（外部への送信）
  - `github.event.`・`github.head_ref`（外から入る値の埋め込み。`run:` の中かどうかは見ない＝粗い判定）
- `.pre-commit-config.yaml`: 次のどれかで確認
  - `detect-secrets` の出現数が減った（秘密の検査のフックを消す・外す）
  - `exclude`・`skip`・`stages` の出現数が増えた（検査の対象を減らしうる）
  - `.secrets.baseline` の出現数が変わった（検査の基準のファイルの差し替え）
  - それ以外（フックの追加・`rev` の版の書き換え）は通す
- `.secrets.baseline`: 設定の `ask` に残す（5-5。編集はほぼ「許す秘密を足す」＝検査を弱める方向で、めったに編集しないため、中身の比較は作らない）
- 対象かどうかは、`file_path` を `os.path.realpath` で正規化し、リポジトリの root（見張りの既存の worktree の判定と同じ求め方）からの相対パスにしてから照合する（相対パス・`..`・シンボリックリンク・別の書き方の絶対パスで取りこぼさない。計画レビュー 1 の Warning）。root が求められない・root の外のときは、名前（`.github/workflows/` を含むか・`.pre-commit-config.yaml` で終わるか）で照合する（安全側）
- 別 worktree への書き込みの停止（I095）はこの判定より前のまま
- 確認の理由の文に、当たった語と「設計確認メモ 2026-10-29 の基準」を書く

### 5-5. 許可の設定（`.claude/settings.json`）
- `permissions.ask` から 15 件を外す: `Bash(git rebase *)`・`Bash(psql *)`・`Edit(.github/workflows/**)`・`Edit(.pre-commit-config.yaml)`・`Edit(backend/Dockerfile)`・`Edit(backend/Dockerfile.dev)`・`Edit(frontend/Dockerfile)`・`Edit(frontend/Dockerfile.dev)`・`Edit(frontend/nginx.conf)`・`Edit(backend/requirements*.txt)`・`Edit(backend/pyproject.toml)`・`Edit(frontend/package.json)`・`Edit(frontend/package-lock.json)`・`Edit(**/migrations/*.py)`・`Edit(backend/init-db.sql)`。残るのは `Edit(.secrets.baseline)` だけ
- `permissions.allow` に足す（Bash）: `Bash(git rebase *)`・`Bash(psql *)`・`Bash(docker compose exec *)`・`Bash(docker compose run *)`・`Bash(docker compose cp *)`・`Bash(docker-compose exec *)`・`Bash(docker-compose run *)`・`Bash(docker-compose cp *)`。どれも見張りが判定する（危険操作は停止・(A)〜(C) は確認）
  - 既存の I187 の 4 行（型チェック・lint）と e2e の 2 行は、上の行に含まれるので消す（重複を残さない）
  - `Bash(docker compose *)` のような広すぎる行は足さない（`down`・`rm` などは見張りが止めるが、許可の設定でも default の確認を残す）
- `permissions.allow` に足す（Edit）: `Edit(.github/workflows/**)`・`Edit(.github/dependabot.yml)`・`Edit(.pre-commit-config.yaml)`・`Edit(docker-compose.yml)`。今の allow の `Edit(...)` は `docs/**`・`backend/**`・`frontend/**`・`scripts/claude/**` だけで、リポジトリ直下と `.github/` の yml は、ask から外しても通常モードでは既定の確認が出るため（計画レビュー 1 の Blocker）。ワークフローと pre-commit の設定は、見張り（5-4）が中身を比べて危ない書き換えだけ確認にする。`.github/dependabot.yml`・`docker-compose.yml` はユーザーの「yml の修正の確認は必須か」（設計確認メモ 2026-10-29）に当たり、git と CI（`check-dependabot`・E2E）で戻せる・捕まる
  - `Edit(...)` のルールは Edit・Write・MultiEdit・NotebookEdit のすべてに効く（公式。`.claude/settings.json` の読み込み時の警告「only Edit(path) rules are」でも確認）。`deny`（`Edit(**/.env)` など）は `allow` より優先される（公式の評価順 deny → ask → allow）ので、足した allow が秘密ファイルの deny に勝つことは無い
- Edit の外した 13 件は `ask` から行を消すだけで、ファイル自体は編集しない（イシューのとおり）。Dockerfile・依存のファイル・マイグレーション・nginx.conf・init-db.sql は既存の `Edit(backend/**)`・`Edit(frontend/**)` の allow に入るので、ask を外せば通る
- `Edit(.secrets.baseline)` の ask は Write・MultiEdit にも効く（上の公式の扱い。計画レビュー 1 の Info への回答）

### 5-5b. 承認の仕組み全体で Edit を確かめる道具（`check-permission-prompt.sh`）
- 今の `scripts/claude/check-permission-prompt.sh` は `bash`・`mcp` だけで、Edit・Write に承認画面が出るかを確かめられない（計画レビュー 1 の Blocker）。種類 `write <パス> <中身のファイル>` を足す: claude -p に「Write ツールで <パス> に <中身> を書く」を 1 回だけ呼ばせ、承認画面が出れば自動で拒否されて permission_denials に入る（既存の bash・mcp と同じ判定）。承認なしで通ると実際に書かれるので、確かめは新しいファイル（`.github/workflows/i200-probe.yml` など）で行い、終わったら消す（M-03）
- `scripts/claude/tests/test_check_permission_prompt.sh` に、保存した stream-json（`CHECK_PERMISSION_PROMPT_LOG`）で `write` の判定を確かめるケースを足す（既存の bash・mcp のケースと同じ形）

### 5-6. primary の自動の早送り（`sessionstart_context.py`）
**修正方針**: セッションの開始のたびに、primary が develop にいて追跡済みファイルがきれいなら、`origin/develop` へ早送りする。何も消さない。合わないときは理由と手で行うコマンドを出すだけ。

- 関数 `sync_primary() -> str`（1 行を返す）:
  1. `git worktree list --porcelain` の最初の `worktree` 行を primary とする。取れなければ「primary: 確かめられませんでした」
  2. `git -C <primary> symbolic-ref --short HEAD` が `develop` でなければ「primary: develop にいないのでそろえません（今: <ブランチ>）」
  3. `git -C <primary> status --porcelain --untracked-files=no` が空でなければ「primary: 未コミットの変更があるのでそろえません」
  4. `git -C <primary> fetch origin develop`（5 秒で打ち切り。失敗しても手元の `origin/develop` で続ける）
  5. `git -C <primary> merge --ff-only origin/develop`。成功し HEAD が動いたら「primary: develop を origin/develop へ早送りしました（<前>..<後>）」、動かなければ「primary: 最新です」、失敗（早送りできない・未追跡のファイルとぶつかる・ロック）は「primary: そろえられませんでした（<理由の短い言葉>）。手で: cd <primary> && git switch develop && git pull --ff-only」
- コマンドの引数はリスト（シェルを通さない）。primary のパスは `git worktree list` の出力だけから取る（外から渡された値を使わない）
- 出力は今の 10 行以内に 1 行足す。どの段階で失敗しても exit 0（セッションの開始を止めない）
- 時間: 各コマンド 5 秒の打ち切り（既存の `_run`）。全体はフックの 30 秒の内

### 5-7. runbook
- `docs/runbooks/danger-ops.md`: 「見張りの扱い」に「確認を出す基準」を (A)〜(C)＋残すもの（fork の PR・`.secrets.baseline`・見張りの失敗で中身を読めないとき）で書き、3〜5 と「見張りが失敗したとき」「編集の確認」「見張りを避ける書き方」を 5-1〜5-5 に合わせて直す。危ない語の一覧は見張りの定数が正（runbook には分類と代表だけを書き、一覧を写さない）。「GitHub から復旧できる範囲」の表のワークフロー・検査設定の行の対策を「見張りが書き換えの中身を比べて、秘密が外に出うる語・検査を弱める語が増えたときだけ確認（I200）」に直す
- `docs/runbooks/worktree.md`: §9 に「例外: セッションの開始のフックが primary を develop へ早送りする（develop にいる・追跡済みファイルがきれい・早送りだけのとき。何も消さない）」、§2 か §7 に「primary は開始時に自動でそろう。そろわないときはフックの出力の手順で」

### ステップの順と依存
1. 5-6（primary の早送り）と TC-07。続けて、このブランチの設定で新しいセッションを始め（`claude -p --settings .claude/settings.json`）、開始時の文脈に「primary:」の行が出て、Claude Code 本体の隔離に止められないことを確かめる（M-04a。**未実証の前提を最初に確かめる**。止められたら「知らせるだけ」に落として計画変更記録に書く）
2. 5-1 → 5-2 → 5-3（見張りの Bash の分岐。5-1 が前提）と TC-01〜TC-03・既存テストの期待値の更新
3. 5-4 と TC-04・TC-05
4. 5-5b（確かめの道具の `write`）とそのテスト
5. 5-5（許可の設定）と `test_settings_permissions.sh` の更新。**見張りの後に置く**（見張りの判定が先に整っていないと、allow を広げた分だけ素通しになるため）
6. 5-7（runbook）
→ 各ステップの確かめは auto_test の TC 参照

## 6. テスト計画
- 自動（決定論・ハーネステスト）: `docs/tests/open/I200_auto_test.md`。見張りに JSON を渡して判定（停止 2・確認 ASK・通す 0）を見る形（既存の `test_pretooluse_container_guard.sh` と同じ）。セッションの開始のフックは一時のリポジトリ（bare の origin＋primary＋ワークツリー）で確かめる
- 手動（Claude）: `docs/tests/open/I200_manual_test.md`。`check-permission-prompt.sh`（通常モード・ブランチの設定）で、外した確認が出ないこと・残した確認が出ることを実際の承認の仕組みで確かめる（AC の「通常モードで」の正の確かめ。claude -p を使い重いので run-all には入れない）

| 受け入れ条件 | 確かめ |
|---|---|
| 基準が runbook に書かれている | M-05（読んで確かめる） |
| (A)〜(C)＋残すものは確認・停止 | TC-02・TC-04・TC-05・M-02 |
| I166 の普通の操作が確認なしで通る | TC-01（見張り）・M-01（承認の仕組み全体） |
| ワークフローの編集は危ない書き換えだけ確認 | TC-04（見張り）・M-03（承認の仕組み全体） |
| ask が `.secrets.baseline` だけ・`psql` の危ない使い方は止まる | `test_settings_permissions.sh`・TC-02 |
| 読みきれないコマンドは危ない語のときだけ確認 | TC-03 |
| primary の自動の早送り | TC-07・M-04a（マージ前・実際のセッションの開始でフックが動く）・M-04b（マージ後・実際に早送りされる） |
| 既存のハーネステスト・CI | TC-08 |

## 7. ロールバック
この PR を revert する（見張り・設定・フック・テスト・runbook だけ。データの変更なし）。revert の後、primary を develop にそろえ直す（開始時のフックが消えるので、手で `git pull --ff-only`）。

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| 確認を外した分、危ない操作が素通りする | 停止（危険操作・解除不可）の判定は変えない。外すのは「安全と確認できない」ことだけを理由にした確認だけ。TC-02 で (A)〜(C) の代表が止まることを固定 |
| 危ない語の一覧の漏れ | 脅威モデルは「事故」。語は理由ごとに広めに取り、誤って確認になる分は許す。漏れは GitHub が最後の守り（I179・I182）。漏れが出たら一覧に足す |
| `docker compose exec *` を allow にすると、見張りが唯一の判定になる | `git push *` と同じ形（既存）。見張りのフックは `onFailure: block`（失敗で止まる）。auto mode の判断は第 2 層として残る |
| primary の早送りが、別のセッションの作業とぶつかる | 追跡済みファイルがきれい・develop・早送りだけ、のときしか動かない。git が早送りできない・未追跡のファイルを上書きしうるときは git 自身が止める。失敗はメッセージだけ |
| フックが Claude Code 本体の隔離で動かない | 実際のセッションで M-04 を確かめる。動かなければ「知らせるだけ」に落とし、計画変更記録に書く |
| 既存のテストの期待値の書き換えで、守りを弱めた変更が紛れる | 期待値を変えたケースを auto_test に全件列挙し、変えた理由（見張りの 3・7・9 のどれか）を 1 行ずつ書く。停止（2）の期待値は 1 件も変えない（TC-08 の差分で確かめる） |

## 9. 確定事項と自律判断
### イシューに明記されていること
- 確認の基準は (A)〜(C)。見張りの 3・7 の一律の確認をやめ、危ない語のときだけ確認（設計確認メモ 2026-10-26）
- 設定の `ask` は秘密検査の 2 件だけを残し（絞るかは計画で判断）、13 件と `.github/workflows/**` を外す。ワークフローは秘密が外に出うる書き換えだけ確認（10-29）
- primary の早送りはセッションの開始のフックで、早送りだけ（10-29）

### Claude が技術的に決めたこと
- 危ない語の一覧（5-1）— イシューで「計画で確定」。理由ごとに広めに取る（誤って確認になる分は許す・漏れを減らす）
- `.pre-commit-config.yaml` は `ask` から外し、中身の比較で確認（5-4）。`.secrets.baseline` は `ask` に残す — 前者はフックの追加・版の書き換えが多く一律の確認の負担が大きい（I213 で実例）。後者はめったに編集せず、編集はほぼ検査を弱める方向
- 許可の設定に `docker compose exec|run|cp` を足す（5-5）— 調査で、見張りを直しても許可の設定で承認画面が出ることを実測したため。見張りに判定を一本化する形は `git push *` の前例に合わせた
- `docker compose cp` のホスト→コンテナを外部送信から外し、コピー元の中身に語の判定をかける（5-3）— 調査で見つけた誤判定の是正
- fork の PR・対象を特定できない `gh pr`・見張りの失敗で中身が読めないときの確認は残す — (A)・(C) の側（外部のコードを手元で動かしうる）／判定できない
- 読み解きが例外で止まったときは、語が当たれば「確認」（停止にはしない）— 停止の判定が走っていないので推測で止めない。人が見る
- 許可の設定の変更を最後のステップにする — 見張りの判定が先に整っていないと素通しが生まれるため
- `docs/runbooks/workflow.md` は変えない — 確認の基準を書いた所が無い（イシューの実装対象からの読み替え）
- 決定論テストは「壊れても気づきにくく被害が大きい」判定だけ（plan-writing-rules.md）。許可の設定の写しのテストは新しく作らない（既存の `test_settings_permissions.sh` は期待値を合わせるだけ）。承認の仕組み全体の確かめは M-01・M-02（claude -p）

### チェック
- 要件適合性: イシューの受け入れ条件の範囲内。仕様の追加なし（primary の早送りはイシューの受け入れ条件に含まれる）
- セキュリティ: 認証・認可・アプリの入力の変更なし。ハーネスの安全装置の変更で、(A)〜(C) の停止・確認を保つことを TC-02・TC-04・TC-05・M-02 で固定。秘密情報: 確認の理由の文に、コマンドの中身や秘密の値を出さない（当たった語だけ）。依存ライブラリの追加なし
- P3/P5/P8 影響なし（DB・外部 API・非同期・インフラの追加なし）
- P6 影響なし（画面なし）
- P9 影響なし（個人情報・未成年データを扱わない）
- 設計品質: 語の一覧・行き先の許可（`/tmp/`・`/dev/null`）は定数に置く。例外は「確認」か「通す」に倒す方向を明記（5-2）
- 要件・基本設計・UI/UX の価値判断で仮定したものは無い（基準はすべて設計確認メモにある）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | (A)〜(C) の代表（force push・保護ブランチへの push・`git push --delete`・`git reset --hard`・`docker compose down -v`・コンテナ内の `DROP TABLE`・`rm -rf`・`.env` の表示・コンテナ内の `requests.post`・`send_mail`）が、新しい見張りでも今までどおり停止か確認になる（TC-02。ホストの `curl`・`wget`・`ssh` は設定の deny が止め、I200 では変えない） |
| V2 | 1 | 実験必須 | コンテナ内・読みきれない書き方・`docker compose cp` で中身を送る形で、危ない語を含む普通の書き方（`os.remove`・`shutil.rmtree`・`.delete()`・`send_mail`）が素通りしない（TC-01 の FG・TC-03） |
| V3 | 1 | 実験必須 | ワークフローの編集で `secrets.`・`permissions` の `write`・`pull_request_target`・`github.event.` を新しく書き足すと確認になり、action の版の書き換えだけなら通る。Edit・MultiEdit・Write のどれでも同じ（TC-04） |
| V4 | 1 | 実験必須 | `.pre-commit-config.yaml` で detect-secrets のフックを消す・`exclude` を足すと確認になる（TC-05） |
| V5 | 2 | 読んで可 | 既存のテストで期待値を変えたケースが、見張りの 3・7・9 による確認だけで、停止（2）の期待値を 1 件も変えていない（auto_test の変更の一覧と差分） |
| V6 | 2 | 実験必須 | primary の早送りが、未コミットの変更がある・develop 以外・早送りできないときに動かず、未追跡のファイルを消さない（TC-07 の一時のリポジトリ） |
| V7 | 3 | 読んで可 | 許可の設定の allow に足した行が `docker compose exec|run|cp`・`docker-compose` の同じもの・`git rebase *`・`psql *`・`Edit(.github/workflows/**)`・`Edit(.github/dependabot.yml)`・`Edit(.pre-commit-config.yaml)`・`Edit(docker-compose.yml)` だけで、`Bash(docker compose *)` のような広い行が無い。`ask` が `Edit(.secrets.baseline)` だけ。秘密ファイルの deny が残っている（`test_settings_permissions.sh`） |
| V8 | 3 | 読んで可 | danger-ops.md の確認の基準が、見張りと設定の実物と食い違わない（M-05） |

## 計画変更記録
- 1（plan-review・2026-10-29・計画レビュー 1 の Blocker 2・Warning 4・Info 1）: (a) Edit の allow（`.github/workflows/**`・`.github/dependabot.yml`・`.pre-commit-config.yaml`・`docker-compose.yml`）を 5-5 に足した（ask から外すだけでは既定の確認が出る）。(b) Edit・Write に承認画面が出るかを確かめる道具が無いので、`check-permission-prompt.sh` に種類 `write` を足す 5-5b を範囲に入れ、M-03 をそれで行う形に書き直した（このセッションは primary の設定で判定されるため、承認画面の有無はこのセッションでは確かめない）。(c) フックが Claude Code 本体の隔離に止められないかを、実装ステップ 1 の M-04a（マージ前・このブランチの設定の新しいセッション）で先に確かめる。(d) 危ない語に語の境界を付け、`reset`・`clean`・`email` を外した。(e) TC-03d・03e の注入の方法を具体化した。(f) 5-4 のパスの正規化を足した。(g) `.secrets.baseline` の ask が Write にも効く根拠を書いた。計画レビューのやり直し: 要（範囲〔5-5b・Edit の allow〕を変える）

## レビュー結果
- [20261029_1918 判定: 差し戻し（Blocker 2件）](../../reviews/I200_plan_review_20261029_1918.md)
