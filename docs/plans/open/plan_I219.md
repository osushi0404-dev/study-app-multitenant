# 計画書: I219 セッションの開始時の primary の早送りを裏で動かし、打ち切りで index.lock を残さない

## 基本情報
- **計画書ID**: plan_I219
- **関連イシュー**: #399
- **Draft PR**: #403
- **作成根拠資料**: docs/issues/open/I219.md
- **実装後評価**: docs/reviews/open/I219_review.md
- **作成日**: 2026-10-30

## 1. 背景/目的
I200 で入れた「セッションの開始時に primary を develop へ早送りする」処理（`scripts/claude/hooks/sessionstart_context.py` の `sync_primary`）が、実際の primary で動かず、さらに primary に `.git/index.lock` を残した（I200 の手動テスト M-04b の NG）。設計確認メモ（2026-10-30）のとおり、早送りを裏の処理に分けてセッションの開始を待たせず、読み取りの git はロックを取らない指定で動かす。

## 2. 受け入れ条件
イシューの受け入れ条件のとおり（`docs/issues/open/I219.md`）。確かめ方の対応は「6. テスト計画」。

## 3. 影響範囲
- Backend・Frontend・DB: なし
- ハーネス: `scripts/claude/hooks/sessionstart_context.py`・`scripts/claude/tests/test_sessionstart_context.sh`・`docs/runbooks/worktree.md`。`.claude/settings.json` は変えない（開始時のフックはすぐ戻るので `timeout: 30` で足りる）
- 記録: 最初のコミットで `docs/tests/closed/I200_manual_test.md` の M-04b に NG の結果を書く

## 調査結果（2026-10-30）
### 原因の分解
- M-04b の実際の出力は「primary: 状態を読めませんでした」。`sync_primary` の `git -C <primary> status --porcelain --untracked-files=no` が `_run`（`subprocess.run` の timeout 5 秒・`sessionstart_context.py:21,28-30`）で打ち切られ、None になった
- 打ち切りは SIGKILL。`git status` は、ついでに索引を書き直すためのロック（optional lock）を取るので、`.git/index.lock` が残った（作成時刻が M-04b のセッションの起動と一致・残った時点で動いている git は 0）
- 今のワークツリー自身の `git status --porcelain`（`sessionstart_context.py:160`・I185 から）も同じ形で、遅いと今のワークツリーにロックを残しうる

### 実際の primary での所要時間（読み取りだけの診断・2026-10-30）
| 操作 | 所要 |
|---|---|
| `status --porcelain --untracked-files=no`（今の形） | 4.8 秒 |
| 同じ・`GIT_OPTIONAL_LOCKS=0` | 1.1 秒・5.2 秒（ばらつく） |
| `diff-index --quiet HEAD`（`GIT_OPTIONAL_LOCKS=0`） | 0.7 秒。ただし索引の stat の情報が古いと「変更あり」と誤る（rc=1）ので使わない |
| `rev-parse HEAD` | 0.0 秒 |
- `GIT_OPTIONAL_LOCKS=0` は、索引の書き直しをせず、ロックを取らない（git の公式の文書の「裏で状態を見るとき」の指定）。速さは変わらないが、打ち切られてもロックは残らない
- 早送り（`merge --ff-only`）と取得（`fetch`）は必須のロックを取る（optional ではない）。打ち切りは SIGTERM（git が自分でロックを片付ける）で行う
- どれも 1 回 1〜5 秒で、裏の処理の打ち切りを 60 秒に取れば足りる

### 既存のテスト
- `bash scripts/claude/tests/test_sessionstart_context.sh` → `pass=16 fail=0`（変更前）。TC-07 は `sync_primary` を同期で呼ぶ前提なので、裏の処理の形に合わせて書き直す

### 軽い指摘の一覧
- `docs/reviews/backlog/I200.md` の F8（`sessionstart_context.py` の時間の見積もりのコメントが rev-parse の 5 秒を数えていない）が当たる

## 4. 変更点一覧
| ファイル | 変更 |
|---|---|
| `scripts/claude/hooks/sessionstart_context.py` | 5-1〜5-3 |
| `scripts/claude/tests/test_sessionstart_context.sh` | TC-07 を裏の処理の形に書き直し、TC-08〜TC-10 を足す |
| `docs/runbooks/worktree.md` | §2・§9 の早送りの説明 |
| `docs/tests/closed/I200_manual_test.md` | M-04b の NG の結果（最初のコミット） |
| `docs/reviews/backlog/I200.md` | F8 の行を消す（5-1 で時間の見積もり自体が無くなる） |

## 5. 実装手順

### 5-1. 開始時のフックは裏の処理を起動するだけ
**修正方針**: 開始時のフックは、前回の早送りの結果を 1 行読んで出し、裏の早送りを起動してすぐ戻る。待たない・打ち切らない。
- `collect()` の最後の `sync_primary(start)` を、`primary_line_and_spawn()` に置き換える:
  0. primary のパスを `git worktree list --porcelain` の最初の `worktree` 行から取り（5-2 と同じ関数）、結果のファイルの場所（5-3）を決める。取れなければ「primary: 確かめられませんでした」の 1 行にして、裏の処理だけ起動する
  1. 結果のファイル（5-3）があれば、その 1 行を「primary: 前回（<時刻>）: <結果>」として返す。無ければ「primary: まだ結果がありません（裏でそろえています）」
  2. 裏の処理を起動する: `subprocess.Popen([sys.executable, <このファイル>, "--sync-primary"], start_new_session=True, stdin/stdout/stderr=DEVNULL)`。起動に失敗したら、同じ 1 行の文末に「（裏の処理を起動できませんでした）」を足すだけ（開始を止めない・行は増やさない）
  - 開始時のフックに残る git は、今のワークツリーの `branch`・`status` と `worktree list` の 3 回（各 5 秒で打ち切り・読み取りはロックを取らないのですぐ SIGKILL）。gh 2 回（各 5 秒）と合わせ最悪 25 秒で、フックの `timeout: 30` の内に収まる（計画レビュー 1 の Warning・計画変更記録 2 で直した形）
- 時間の上限の定数（`PRIMARY_SKIP_AFTER_SEC`・`PRIMARY_STOP_AFTER_SEC`）と、開始時の経過を見る仕組みは消す（裏の処理には要らない）
- 出力は 10 行以内のまま（1 行）

### 5-2. 裏の早送りの処理（`--sync-primary`）
**修正方針**: I200 の条件（develop にいる・追跡済みファイルがきれい・早送りだけ）はそのまま。時間に余裕を持たせ、どの打ち切りでもロックを残さない。
- `main()` で引数が `--sync-primary` なら `sync_primary_bg()` を呼ぶ
- 排他: 結果のファイルと同じ場所の `<名前>.lock` を `fcntl.flock(LOCK_EX | LOCK_NB)` で取る。取れなければ（ほかの裏の処理が動いている）何もせず終わる
- 手順（I200 の `sync_primary` と同じ判定。primary のパスは `git worktree list --porcelain` の最初の行だけから取る）:
  1. `symbolic-ref --short HEAD` が develop でなければ「develop にいないのでそろえません（今: …）」
  2. `status --porcelain --untracked-files=no`（`GIT_OPTIONAL_LOCKS=0`）が空でなければ「未コミットの変更があるのでそろえません」
  3. `fetch --quiet origin develop`（失敗しても手元の origin/develop で続ける）
  4. `merge --ff-only --quiet origin/develop`。HEAD が動けば「develop を origin/develop へ早送りしました（前..後）」、動かなければ「最新です」、失敗は「そろえられませんでした（…）。手で: cd <primary> && git switch develop && git pull --ff-only」
- 各 git の打ち切りは 60 秒（定数 `BG_GIT_TIMEOUT_SEC`）。必須のロックを取る fetch・merge の打ち切りは SIGTERM → 2 秒待って SIGKILL（`_run` の `grace=2`）。読み取りはロックを取らないのですぐ打ち切る（計画変更記録 2）
- 結果（時刻と 1 行）を 5-3 のファイルに書いて終わる。例外は結果「確かめられませんでした（例外の型名）」にして書く

### 5-3. 結果のファイルの置き場所と、読み取りの git の指定
- 置き場所: `${XDG_CACHE_HOME:-~/.cache}/claude-primary-sync/<primary のパスの sha1 の先頭 16 桁>.json`（リポジトリの外。primary にもワークツリーにも書かない）。テストのために、環境変数 `CLAUDE_PRIMARY_SYNC_DIR` があればその場所を使う（置き場所を変えるだけで、判定には効かない）
- 書き込みは一時のファイルに書いてから `os.replace`（読む側が書きかけを読まない）。置き場所のディレクトリは `mode=0o700` で作る（計画レビュー 1 の Info）
- フックの中の読み取りの git（今のワークツリーの `branch`・`status`、primary の `worktree list`・`symbolic-ref`・`status`・`rev-parse`）は、すべて `GIT_OPTIONAL_LOCKS=0` を付けて呼ぶ（`_run` で付ける）
- テストのために、環境変数 `CLAUDE_PRIMARY_SYNC_TIMEOUT` があれば `BG_GIT_TIMEOUT_SEC` の代わりに使う（打ち切りのテスト用。短くするだけ）

### 5-4. 手順書
- `docs/runbooks/worktree.md` §2・§9: 早送りは裏で動き、開始は待たない・結果は次の開始時に「primary: 前回 …」で出る・読み取りはロックを取らない・裏の処理は 1 本ずつ・結果のファイルの場所

### ステップの順と依存
1. 最初のコミット: I200 の M-04b の NG の記録
2. 5-3（読み取りの git の指定・結果のファイル）→ 5-2（裏の処理）→ 5-1（開始時のフック）。TC は各ステップに対応（auto_test）
3. 5-4（手順書）・一覧の F8 を消す

## 6. テスト計画
- 自動: `docs/tests/open/I219_auto_test.md`。一時のディレクトリに bare の origin・primary（develop）・ワークツリーを作る（I200 の TC-07 と同じ作り）。裏の処理は `--sync-primary` を直接呼んで決定論で確かめ、開始時のフックの起動はフックを動かして結果のファイルが出るのを待つ（上限つき）
- 手動（Claude）: `docs/tests/open/I219_manual_test.md`。マージ前に、このブランチの設定の新しいセッションで開始が待たされないこと・2 回目の開始で結果の行が出ること。マージ後に、実際の primary が早送りされること

| 受け入れ条件 | 確かめ |
|---|---|
| 開始が待たされず、裏で早送りされ、次の開始で結果が出る | TC-07・TC-08・M-01・M-02 |
| 同時に複数でも 1 本だけ | TC-09 |
| 打ち切られてもロックを残さない（primary・今のワークツリー） | TC-10 |
| 既存の行を失わず timeout の内 | TC-07i・TC-08 |
| M-04b の記録 | 最初のコミット（M-03 で読む） |
| 既存のテスト・CI | TC-11 |

## 7. ロールバック
PR を revert する（フック・テスト・手順書だけ）。結果のファイル（`~/.cache/claude-primary-sync/`）は残っても害が無い（消してよい）。

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| 裏の処理が残り続ける・増え続ける | 排他（flock）で 1 本だけ。各 git は 60 秒で打ち切る。全体でも数分で終わる |
| 裏の処理の失敗が誰にも見えない | 結果を必ず書き、次の開始時に 1 行出す（失敗の理由と手で行うコマンドを含む） |
| primary で人が作業中に早送りされる | 条件（develop・追跡済みファイルがきれい・早送りだけ）は I200 のまま。git 自身が上書きを拒む |
| 開始時のフックの子が、Claude Code の終了で殺される | `start_new_session=True` で別のセッションにする。殺されても、次の開始で起動し直すだけ（結果が古いままになる） |
| 打ち切りのテストのための環境変数が悪用される | 変えられるのは結果の置き場所と打ち切りの長さだけで、早送りの条件・primary のパスは変えられない |

## 9. 確定事項と自律判断
### イシューに明記されていること
- 裏で動かして待たない・結果は次の開始時・1 本ずつ・ロックを取らない（設計確認メモ）
- 今のワークツリーの `status` も直す（設計確認メモの範囲の追加）
- 早送りの条件は変えない

### Claude が技術的に決めたこと
- 裏の処理は同じファイルの `--sync-primary` で起動する（別のスクリプトを増やさない・判定を 1 か所に保つ）
- 結果のファイルはリポジトリの外（`~/.cache/`）に置く（primary にも git の管理にも書かない）
- 排他は `fcntl.flock`（OS の仕組み・プロセスが死ねば自動で外れる）
- 打ち切りは 60 秒・SIGTERM の後に SIGKILL（実測 1〜5 秒の 10 倍以上）
- `diff-index` に替えない（索引の stat が古いと誤るため・調査結果）
- 一覧 `docs/reviews/backlog/I200.md` F8: 同梱 — 時間の見積もりの仕組み自体を消すので、指摘が無くなる

### チェック
- 要件適合性: イシューの範囲内
- セキュリティ: 秘密情報・認証を扱わない。結果のファイルに書くのは時刻と 1 行（primary のパスとブランチ名を含む）だけ。外から渡された値で primary のパスや判定は変わらない
- P3/P5/P8 影響なし・P6 影響なし・P9 影響なし
- 高リスクの見込み: `path_risk_trigger` の集合（見張り・settings.json・`.github/*` など）には触らない。ワークツリーをまたいで primary を書き換える処理なので、計画レビューの判定に従う
- 要件・基本設計・UI/UX の価値判断で仮定したものは無い

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 裏の処理が I200 の条件（develop・追跡済みファイルがきれい・早送りだけ）を守り、未コミットの変更・未追跡のファイルを消さない（TC-07c〜07g・FG-07） |
| V2 | 1 | 読んで可 | どの打ち切りでも、primary と今のワークツリーに `.git/index.lock` を残さない（TC-10・FG-10） |
| V3 | 2 | 読んで可 | 同時に起動しても 1 本だけが早送りする（TC-09・FG-09） |
| V4 | 3 | 読んで可 | 開始時のフックが待たずに戻り、既存の行と結果の 1 行を出す（TC-08・M-01） |

## 計画変更記録
- 1（plan-review・2026-10-30・計画レビュー 1 は OK。Warning 5・Info 2）: 5-1 に primary のパスの取り方と、開始時のフックに残る git・gh の最悪の時間（25 秒）を書いた／`_run` の打ち切りも SIGTERM にそろえる／M-01 の基準を数値（フックの所要 5 秒以内）にした／TC-10b の偽の git は `exec sleep` で SIGTERM を受けて記録できる形にした／置き場所を `0o700` で作る／起動失敗は同じ 1 行の文末に足す。「フックから切り離した裏の処理が、フックの終了や `claude -p` の終了で殺されない」前提は、実装ステップの最後と M-01・M-02 で実環境で確かめる（殺されるなら計画を直す）。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）
- 2（implement・/simplify の指摘）: 計画変更記録 1 の「打ち切りはどれも SIGTERM の後に SIGKILL にそろえる」では、開始時の読み取り 5 回（git 3・gh 2）に 2 秒の待ちが付き、最悪 35 秒でフックの 30 秒を超える（25 秒の見積もりが誤り）。読み取りは `GIT_OPTIONAL_LOCKS=0` でロックを取らないのですぐ打ち切り、SIGTERM の後に待つのは裏の処理の fetch・merge だけにした（`_run` の `grace` 引数）。開始時の最悪は 5×5＝25 秒。テストの写し（TC-10b・wait_bg）も整理した。計画レビューのやり直し: 不要（方式は変えない）

## レビュー結果
- [20261030_0829 判定: ✅ 完了](../../reviews/I219_plan_review_20261030_0829.md)
