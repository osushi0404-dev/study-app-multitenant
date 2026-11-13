# I486 計画書: 敵対的レビューの実験の環境（コンテナ）と空振りの見分けを決定論にする

## 基本情報
- **計画書ID**: plan_I486
- **関連イシュー**: #486
- **Draft PR**: #490
- **作成根拠資料**: docs/issues/open/I486.md
- **実装後評価**: docs/reviews/closed/I486_review.md
- **作成日**: 2026-11-13

## 1. 背景/目的
- I228 で、敵対的レビューの実験がアプリのテストを流せず空振りする問題（I431・I446・I452・I455 の 4 回連続）に、(1) 実験の案内（`docker compose exec -T backend …`）、(2) 出力の形で「実行できなかった」を見分ける判定（`exp_not_executable`）、(3) review-gate §3-1 の「アプリを変えたイシューは起動の前に `docker compose up -d backend`」の手順を入れた。
- (3) は「変えたか」の判断が Claude・失敗時の分岐なし・`--build` なし（台帳 F6・F7・F8）。(2) は全行が決まった形のときだけ当たる列挙（台帳 F2）。言い直しの案内に新しい id が無い（台帳 F1）。
- 目的: 実験の前提（このワークツリーの backend のコンテナが動いている）を、スクリプトの起動時の決定論にする。整わなければレビュー役を呼ばずに止める。そのうえで空振りの見分けを粗く確実な形にし、言い直しの id を具体的に案内する。

### 調査結果
- **原因の概要**: 実験の前提（コンテナ）を、手順書を読んだ Claude の判断に置いていた。前提が崩れたときの空振りを、後から出力の文字の形で見分けている。
- **詳細**:
  1. `scripts/claude/adversarial-review.sh` は起動時にコンテナを見ない。review-gate §3-1（`.claude/skills/review-gate/SKILL.md:68-72`）の `docker compose up -d backend` は、Claude が「backend を変えたか」を決めて流す手続きで、失敗しても敵対的レビューはそのまま起動する
  2. `exp_not_executable()`（`adversarial-review.sh:397-407`）は `all(pat.fullmatch(l) for l in lines)`。`…; echo "exit=$?"` のように別の行が 1 行でも混ざると「実行した」になる。`sh: 1: python: not found`・`Cannot connect to the Docker daemon` は形に無い
  3. noexec の案内（`adversarial-review.sh:313`）は「言い直す」だけ。`run_perspective()` の 268 行目（`exp_status` にある id を飛ばす）と `extract_experiments()` の「既に .cmd がある id は出さない」のため、同じ id で出し直した案は黙って捨てられる
- **環境の確認（全イシュー必須）**:
  - `docker compose version` → `Docker Compose version v5.6.0`。`docker compose up --help` に `--build`・`--wait`（running|healthy まで待つ・detached を含む）・`--wait-timeout` がある（スパイクで確認）
  - Compose のプロジェクト名はワークツリーのフォルダ名（`docker ps` で `app-1-backend-1` の `com.docker.compose.project.working_dir` ラベルが `/mnt/c/app/study-app-multitenant/.claude/worktrees/app-1`＝そのワークツリーの `git rev-parse --show-toplevel` と同じ表記。スパイクで確認）。`docker compose` をリポジトリのルートで流せば、そのワークツリーのスタックに当たる。ただし環境変数・`.env` の `COMPOSE_PROJECT_NAME` で別のプロジェクトを指すと、別のワークツリーのコンテナ（＝別のコード）に当たりうる
  - `docker compose ps -q --status running backend` は v5.6.0 で使え、このワークツリー（コンテナなし）では空の出力・exit 0。`docker inspect --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}' app-1-backend-1` はパス 1 行を出す（計画レビュー W1 を受けてスパイクで確認）
  - `docker-compose.yml` の backend には healthcheck（`curl -f http://localhost:8000/health/`・start_period 60s・retries 18）があり、`--wait` は healthy まで待つ。起動のたびに collectstatic・migrate が走る
  - ワークツリーは直下 `.env`（`scripts/claude/wt-ports.sh` が作る）でポートをずらす。harness-1 には `.env` が無く、このまま `up` すると app-1 のスタック（8000 番など）とぶつかって失敗する（`docs/runbooks/worktree.md` §6「静かには壊れない」）
  - `.claude/settings.json` に `sandbox` の設定は無い。スクリプトの中の `docker` は Bash ツールの許可の判定を受けない（Bash ツールに渡るのは `bash scripts/claude/adversarial-review.sh I###` だけ）。settings.json は変えない
- **消費箇所の全件（`up -d backend`・`exp_not_executable`・`noexec` の grep。closed と記録は除く）**: `scripts/claude/adversarial-review.sh`（310・313・397・566 行）・`scripts/claude/tests/test_i197_adversarial_process.sh`（A36・FG-A36）・`.claude/skills/review-gate/SKILL.md:71`・`.claude/agents/adversarial-reviewer.md:70`（noexec の説明「形の行だけ」）・`docs/reviews/backlog/I228.md`。`docs/runbooks/common-commands.md:137`・`docs/runbooks/frontend-verify.md:65` の `up -d backend` は E2E のレート制限の話で別物（変えない）

## 2. 受け入れ条件
- [ ] ブランチ（`ADV_BASE...HEAD`。2 周目以降の見る範囲の縮みに左右されない）に `backend/` の変更があるとき、`adversarial-review.sh` はレビュー役を呼ぶ前に `docker compose up -d --build --wait backend` を流し、そのうえで動いている backend のコンテナがこのワークツリーのもの（ラベル `com.docker.compose.project.working_dir` ＝ リポジトリのルート）かを確かめる。起こせない・時間切れ・別のワークツリーのコンテナのときは `ADVERSARIAL_ERROR: CONTAINER`・exit 2 で止まり、レビュー役を呼ばない（TC-01 の A39〜A41・FG）
- [ ] ブランチに `backend/` の変更が無いときは、docker を一度も呼ばない（TC-01 の A42・FG）
- [ ] 2 周目に、直した差分（見る範囲）に `backend/` が無くても、ブランチに `backend/` の変更があればコンテナを起こす（TC-01 の A46・FG）
- [ ] コンテナを起こす待ち時間は 1 周の締め切り（`ADV_DEADLINE`）の外（TC-01 の A43・FG）
- [ ] 出力に「見つからない」形の行が混ざる実験も `noexec` になる（TC-01 の A44・FG）。正しい「無い」の実験（`ls: cannot access …`）は今までどおり「実行した」（A37 のまま）
- [ ] `noexec` の結果に、新しい id（`P<観点>-E<まだ使っていない番号>`）での言い直しの案内が付く（TC-01 の A45・FG）
- [ ] `docs/reviews/backlog/I228.md` から F1・F2・F6・F7・F8 の行が消えている（TC-02）
- [ ] review-gate §3-1 からコンテナの手順が消え、exit 2 の `CONTAINER` の扱いが判断なしで書かれている（TC-03・手動 No.2）
- [ ] 既存のハーネステスト・CI がすべて pass する

## 3. 影響範囲
- Backend: なし（コードは変えない。敵対的レビューのときにコンテナを起こすだけ）
- Frontend: なし
- DB: なし（起こすときに既存の `command` の migrate が走るのは今の §3-1 の手順と同じ）
- Config/Infra: `scripts/claude/adversarial-review.sh`・`scripts/claude/tests/test_i197_adversarial_process.sh`・`.claude/skills/review-gate/SKILL.md`・`.claude/agents/adversarial-reviewer.md`・`docs/reviews/backlog/I228.md`。`.claude/settings.json`・見張り・`docker-compose.yml` は変えない

## 4. 変更点一覧（具体）

### 修正アプローチ
コンテナの前提を、スクリプトの起動時の 1 つの関数（`ensure_backend_container`）にまとめる。backend を変えたイシューでは「動いているか」を見て分岐せず、常に `up -d --build --wait backend` を流す（動いていて何も変わっていなければ作り直さない＝冪等。依存を変えていれば作り直す。F6・F7 を 1 つの形で覆う）。そのあと「このワークツリーのコンテナか」を確かめ、どれか 1 つでも崩れたら止める（F8）。前提が保証されるので、空振りの見分けは「どこかの行に見つからない形があれば noexec」と粗くし（取りすぎは未検証＝止める側）、noexec の案内には次の id を具体的に出す。

### 4-1. `scripts/claude/adversarial-review.sh`
1. **既定値**: `ADV_CONTAINER_TIMEOUT`（既定 600 秒。起こして healthy まで待つ上限）・`ADV_DOCKER_BIN`（既定 `docker`。テスト用。`CLAUDE_BIN` と同じ形）を 29-30 行目の既定値の並びに足し、冒頭の「環境変数」の説明にも足す。
2. **新しい関数 `ensure_backend_container`**（関数の並び。`REVIEW_LIB_SOURCE_ONLY` の前）:
   - 修正方針: ブランチに backend の変更があるときだけ（docker を流す作業フォルダは、スクリプトが先頭で cd したリポジトリのルート）、このワークツリーの backend を起こして確かめる。崩れたら理由を出して 1 を返す（呼び出し側が exit 2）
   - 中身:
     ```bash
     # 実験の前提（I486）: ブランチに backend/ の変更があれば、このワークツリーの backend のコンテナを起こして確かめる。
     # 動いているかで分けずに常に up する（変わっていなければ作り直さない・依存を変えていれば --build で作り直す）。
     # 起動のたびに migrate が走る（docker-compose.yml の command）。起こせない・時間切れ・別のワークツリーのコンテナなら止める
     ensure_backend_container() {
       local id wd
       CONTAINER_NOTE="確かめていない（ブランチに backend/ の変更なし）"
       grep -q '^backend/' "$RUN/branch_files.txt" || return 0
       local t0; t0=$(date +%s)
       if ! timeout "${ADV_CONTAINER_TIMEOUT}" "${ADV_DOCKER_BIN}" compose up -d --build --wait backend > "$RUN/container.log" 2>&1; then
         echo "⛔ backend のコンテナを起こせません（上限 ${ADV_CONTAINER_TIMEOUT} 秒）。出力の最後:"; tail -20 "$RUN/container.log"
         echo "（ワークツリーで初めて起こすときは、先に bash scripts/claude/wt-ports.sh でポートを割り当てる・docs/runbooks/worktree.md §6）"
         echo "ADVERSARIAL_ERROR: CONTAINER"; return 1
       fi
       id=$("${ADV_DOCKER_BIN}" compose ps -q --status running backend 2>/dev/null)
       wd=""; [ -n "$id" ] && [ "$(printf '%s\n' "$id" | grep -c .)" -eq 1 ] && wd=$("${ADV_DOCKER_BIN}" inspect --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}' "$id" 2>/dev/null)
       if [ "$wd" != "$REPO_ROOT" ]; then
         echo "⛔ 動いている backend のコンテナが、このワークツリー（${REPO_ROOT}）のものではありません（元の場所: ${wd:-不明}・COMPOSE_PROJECT_NAME などで別のプロジェクトを指していないか）。"
         echo "ADVERSARIAL_ERROR: CONTAINER"; return 1
       fi
       CONTAINER_NOTE="backend を起こして確かめた（$(( $(date +%s) - t0 )) 秒・締め切りの外）"
     }
     ```
   - `files.txt` は `git diff --name-status --no-renames` の `<状態>\t<パス>`。`backend/` で始まるパスだけに当たる（`docs/…/backend/x` や `frontend/` は当たらない）
   - **計画変更（close の後・F1）**: 起こすかの判定は、その周の見る範囲（`files.txt`・2 周目以降は前の周の後の差分だけ）でなく、ブランチ全体（`git diff --name-only --no-renames "${ADV_BASE}...HEAD"` を `$RUN/branch_files.txt` に書く。取れなければ既存の `ADVERSARIAL_ERROR: DIFF` で止める）に `^backend/` があるかで決める。`CONTAINER_NOTE` の文言も「ブランチに backend/ の変更なし」にする
3. **本体の並び替え**（447-503 行あたり）:
   - 449 行目の `ADV_START=$(adv_now) || { … CLOCK … }` を、差分を取った後（503 行の後）に移し、その直前に `ensure_backend_container || exit 2` を置く。コンテナの待ちを締め切りの外にする:
     ```bash
     ensure_backend_container || exit 2
     ADV_START=$(adv_now) || { echo "⛔ 今の時刻を読めません（ADV_CLOCK_FILE=${ADV_CLOCK_FILE}）"; echo "ADVERSARIAL_ERROR: CLOCK"; exit 2; }
     ```
   - `worktree_state > "$RUN/state0"`（491 行）も `ADV_START` の後へ移す（起こしたときにできたファイルを実験のせいにしない）。`DIRTY0` の確かめ（476-482 行）は今の位置のまま（docker の前に止める）
   - `ADV_START` を読むのは `remaining`・`elapsed_since`・`run_perspective` だけで、どれも移した後にしか呼ばれない
4. **`exp_not_executable` を粗くする**（397-407 行）:
   - 修正方針: 「全行が決まった形」をやめ、「どこかの行に見つからない形を含む」で当てる。形の列挙を増やすのでなく、当て方を部分一致・どの行でもに広げる（取りすぎは未検証になるだけ）
     ```python
     pat = re.compile(r"command not found|: not found\s*$|failed to run command|is not running|Cannot connect to the Docker daemon|no such service"
                      r"|^(?:\S*/)?(?:bash|sh|env|timeout|nice|xargs)(?:: line \d+)?: .*No such file or directory\s*$"
                      r"|^[^\s:]+: No such file or directory\s*$")
     lines = [l.strip() for l in open(sys.argv[1], encoding="utf-8", errors="replace").read().split("\n")]
     sys.exit(0 if any(pat.search(l) for l in lines) else 1)
     ```
   - `ls: cannot access 'x': No such file or directory`（コマンドの中身の結果）は、行頭がシェル・`timeout` などでないので当たらない（A37 のまま「実行した」）。今の形の `<1 語>: No such file or directory`（接頭辞なし・1 行まるごと）は残す（最後の選択肢。落とすと取り逃しの側に緩むため・計画レビュー W2）。`cat: x: No such file or directory` は 1 語の後に `x:` が続くので当たらない
   - 関数の上のコメントを「どこかの行が見つからない形を含むか」に直す
5. **noexec の案内に新しい id**（`run_perspective()` 301-314 行）:
   - 結果を書く前に、その観点で使った `P<p>-E<n>` の最大の番号を `$d/exp/*.cmd` から数え、`next_eid="P${p}-E$(( max + 1 ))"` を決める
   - 313 行を次にする:
     ```bash
     [ "$st" = noexec ] && printf 'コマンドが見つからない（実行できなかった）。言い直すときは、まだ使っていない新しい id（%s から）で出す（同じ id で出した案は扱い済みとして実行されない）。%s\n' "$next_eid" "$APP_TEST_HINT" >> "$next_in"
     ```
6. **記録**: 記録の冒頭の箇条に `- コンテナ: ${CONTAINER_NOTE}` を足す（1 行）。

### 4-2. `scripts/claude/tests/test_i197_adversarial_process.sh`
- docker のスタブ `$TMP/stub_docker`（bash）を足す。呼び出しの引数を `$STUB_DIR/docker_calls` に 1 行ずつ残す。`compose up` は `$STUB_DIR/docker_up_rc`（既定 0）で終わり、`$STUB_DIR/docker_up_advance` があれば `ADV_CLOCK_FILE` の秒をその数だけ進める。`compose ps` は `$STUB_DIR/docker_ps`（既定 `cid1`）、`inspect` は `$STUB_DIR/docker_wd`（既定 `git rev-parse --show-toplevel`）を出す
- `run()` に `ADV_DOCKER_BIN="$DSTUB"` を足す。`backend_commit <名前>`（`backend/x.py` を足してコミット）を足す
- 足すテスト:
  - A39 backend の変更あり・起こせた → exit 0・OK・`docker_calls` に `compose up -d --build --wait backend`・記録に「コンテナ: backend を起こして確かめた」
  - A40 `docker_up_rc=1` → exit 2・`ADVERSARIAL_ERROR: CONTAINER`・claude の呼び出し 0・記録 0
  - A41 `docker_wd` が別の場所 → exit 2・`ADVERSARIAL_ERROR: CONTAINER`・claude の呼び出し 0。`docker_ps` が空（動いていない）でも同じ
  - A42 backend の変更なし（A1 のまま）→ `docker_calls` が無い（docker を呼ばない）。`frontend/backend/x`・`docs/backend.md` だけの変更でも呼ばない
  - A43 `ADV_CLOCK_FILE` を使い、`docker_up_advance=100000` で docker が時計を締め切りより先へ進めても、exit 0・OK（締め切りは起こした後から数える）
  - A44 出力が `is_error=false` / `collecting ...` / `sh: 1: python: not found` / `exit=127` の 4 行（別の行が混ざる）→ V1 未検証・記録に「実行できなかった」。`Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?` を含む出力も未検証。`python: No such file or directory` の 1 行（今の形）も未検証のまま
  - A45 noexec の後の 2 回目の入力に「新しい id（P1-E2 から）」。続けて P1-E2 で出し直した案は実行され、V1 が「確認済み（実験）」になる（言い直しが通る筋）
  - A46（計画変更）1 周目に backend の変更あり → 記録だけを直して 2 周目 → 2 周目も `compose up -d --build --wait backend` を呼ぶ（`docker_calls` の up が 2 行）。FG-A46: 判定を見る範囲（`files.txt`）に戻すと up が 1 行になる
- FG（失敗の注入）: FG-A40（up の失敗で止める `|| exit 2` を外す → claude が呼ばれる）・FG-A41（作業フォルダの比較を外す → 止まらない）・FG-A42（backend の絞り込みを外す → docker が呼ばれる）・FG-A43（`ensure_backend_container` と `ADV_START` の順を入れ替える → 締め切りで未報告・exit 3）・FG-A44（当て方を `all(fullmatch)` に戻す → V1 確認済み）・FG-A45（案内の id を消す → 2 回目の入力に「P1-E2 から」が無い）
- 既存の A36・A37・FG-A36 は変えずに通す

### 4-3. `.claude/skills/review-gate/SKILL.md`
- §3-1 の 68-72 行（「アプリ（`backend/`）を変えたイシューでは…」の段落と `docker compose up -d backend` のコードブロック）を消し、「ブランチに `backend/` の変更があれば、スクリプトが起動時に backend のコンテナを起こして確かめる（I486。手で起こさない）」の 1 文にする（計画変更で「見る範囲に」から直した）
- §3-2 の exit 2 の箇条に足す: 「`ADVERSARIAL_ERROR: CONTAINER`（backend のコンテナを起こせない・別のワークツリーのコンテナ）は記録の場所で直せないので、実行し直さずに止める（止める条件 3）。出力の理由（docker の出力の最後・案内）をそのままユーザーに伝える」

### 4-4. `.claude/agents/adversarial-reviewer.md`
- 70 行を「出力のどこかに『コマンドが見つからない』形の行（`command not found`・`not found`・`failed to run command`・コンテナが動いていない など）がある実験は『実行できなかった』（`noexec`）として返り、実行したに数えない。言い直すときは、案内された新しい id で出す（同じ id は扱い済みとして実行されない）」に直す

### 4-5. `docs/reviews/backlog/I228.md`
- F1・F2・F6・F7・F8 の行を消す（F3・F5 は残す。ファイルは消さない）

## 5. 実装手順（ステップ）
1. テストを先に足す（4-2。docker のスタブと A39〜A45・FG。計画変更の後は A46・FG-A46 も）。この時点では A39〜A45（計画変更の後は A46）が落ちることを確かめる → TC-01 参照
2. `adversarial-review.sh` を直す（4-1）→ TC-01 参照（ステップ 1 の後）
3. review-gate・adversarial-reviewer.md・台帳を直す（4-3〜4-5）→ TC-02・TC-03 参照（ステップ 2 と並行可）
4. 実際の docker でこのワークツリーの backend を起こせるかを確かめる → 手動 No.1 参照（ステップ 2 の後）

## 6. テスト計画
### 自動
- TC-01 `bash scripts/claude/tests/test_i197_adversarial_process.sh`（ユニット＋結合: スクリプトを一時のリポジトリで丸ごと走らせる。claude と docker はスタブ。FG つき）
- TC-02 台帳から直した行が消えた（`! grep -q`）
- TC-03 review-gate から `docker compose up -d backend` が消えた（`! grep -q`）
- 既存のハーネステストは CI（`harness-tests`）が流す。手元で全部は流さない
### 手動
- No.1（Claude）: 実際の docker で `ensure_backend_container` を流し、このワークツリーの backend が healthy で起き、ラベルの比較が通る（compose v5 の `--wait`・ラベルの表記を実機で確かめる）
- No.2（Claude）: review-gate §3-1・§3-2 を読み、コンテナについて Claude が判断する文が残っていない

## 7. ロールバック
- PR を revert する（ハーネスのスクリプトと文書だけ。データの変更なし）。手動 No.1 で起こしたこのワークツリーのスタックは `docker compose stop` で止める（`down -v` はしない）

## 8. Risk & 回避策
- **起こすのに時間がかかる**（初回の build・healthcheck の start_period 60s）: 締め切りの外で待ち、上限 `ADV_CONTAINER_TIMEOUT`（600 秒）。超えたら止める。1 周 10 分・2 周の上限は変えない
- **ポートの衝突**（`.env` の無いワークツリー）: `up` が失敗 → 止める。案内に `wt-ports.sh` を出す。スクリプトは `.env` を書かない（ワークツリーの設定を勝手に作らない）
- **起こすと作り直し・migrate が走る**（台帳 F6）: 今の §3-1 の手順と同じ。依存・設定を変えたブランチのコードでコンテナを揃えるのが目的なので受け入れる（関数のコメントに書く）
- **`backend/` 以外の変更でアプリのテストを流す実験**: コンテナを起こさないので `is not running` などで noexec → 未検証 → HIGH（止める側）。起こす条件を広げない（ハーネスだけのイシューで docker を動かさない AC を優先）
- **noexec の取りすぎ**（テストの出力に `: not found` で終わる行がある など）: 未検証＝HIGH の側に倒れるだけ。案内に従い言い直せる
- **将来サンドボックスを有効にしたとき**、スクリプトの中の docker が止められる: `up` が失敗 → 止める（静かには通らない）

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 設計確認メモは無し（/grill-me で聞く点なし）。本文の解決方針・AC・制約（上限を変えない・起動の形を変えない・列挙を増やさない・docker はテストで差し替える）に従う
Claude が決めた（技術的な選択と理由）:
- **起こす（止めるのではなく）**: 止めると Claude が手で起こして再実行する手続きが残り、AC「手順書に Claude の判断が残らない」に反する。起こすのは冪等で、起こせないときだけ止める（イシューの「起こすなら失敗時は止める側」）
- **常に `up -d --build --wait`**（動いているかで分けない）: 分けると「動いているが古いイメージ」（F7）・「動いているが別の設定」（F6）を見逃す。`--build` はキャッシュが効けば短い。`--wait` で healthy まで待つ（起きただけで exec が失敗する間を残さない）
- **このワークツリーのコンテナかをラベルで確かめる**: `COMPOSE_PROJECT_NAME` などで別のワークツリーのスタックに当たると、実験が別のコードに対して走り、合格が偽になる（/grill-me で挙げた点）
- **待ちは締め切りの外**（`ADV_START` を起こした後に取る）: イシューの指定
- **`wt-ports.sh` はスクリプトから呼ばない**: ワークツリーの設定ファイルを作る操作で、敵対的レビューの責務の外。衝突は `up` の失敗で静かにならずに止まる
- **noexec の当て方**: 部分一致・どの行でも（イシューの例のとおり）。形は今の 3 つにイシューの例（`not found` で終わる・docker の不通・`no such service`）を足すが、当て方を広げたのが本体で、今後は形を足さない（取りすぎは止める側）
- **次の id の数え方**: その観点の `$d/exp/*.cmd` のうち `P<p>-E<n>` の最大＋1（扱い済みの id は必ず .cmd がある）
- **CONTAINER のときは実行し直さず止める**: 原因（ポート・デーモン・別のプロジェクト）は記録の場所で直せないので、既存の exit 2 の決まり「直せないときは止める」に当てる
- **高リスクの見立て**: `path_risk_trigger()` の対象（`.github/*`・見張り・settings.json など）を変えない。敵対的レビューの守り（未検証を合格にしない）を緩める変更ではない（noexec を広げるのは止める側）。見立ては No。判定は計画レビューに任せ、一覧は下に置く
- 一覧 docs/reviews/backlog/I228.md F1: 同梱 — 4-1 の 5（noexec の案内）
- 一覧 docs/reviews/backlog/I228.md F2: 同梱 — 4-1 の 4（粗い当て方）
- 一覧 docs/reviews/backlog/I228.md F3: 残す — イシューの「含まない」（わざとの回避は対象外）
- 一覧 docs/reviews/backlog/I228.md F5: 残す — イシューの「含まない」（案内の置き場が 2 か所は AC の結果）
- 一覧 docs/reviews/backlog/I228.md F6: 同梱 — 4-1 の 2・4-3（スクリプトが常に up・作り直しと migrate をコメントに書く）
- 一覧 docs/reviews/backlog/I228.md F7: 同梱 — 4-1 の 2（`--build`）
- 一覧 docs/reviews/backlog/I228.md F8: 同梱 — 4-1 の 2・4-3（失敗で止める）
- 一覧 docs/reviews/backlog/I210.md F1: 残す — `ADV_CLOCK_FILE` が本番にも効く件。`ADV_START` の位置は動かすが時計の読み方は変えない（このイシューの範囲の外）
- 一覧 docs/reviews/backlog/I206.md F3・F6: 残す — `flock` の戻り値・締め切りの周の比較。コンテナ・noexec と関係しない
- 一覧 docs/reviews/backlog/I224.md F9・I223.md B1〜B4（`FILE=-`）: 残す — 別のイシューの後始末で、このイシューと関係しない
- 要件適合性: AC の範囲を超える仕様の追加なし。マルチテナント・状態遷移は該当なし
- セキュリティ: アプリのコード・認証・機密データに触れない。スクリプトが docker を呼ぶのは backend の変更があるときだけ、引数は固定（入力から組み立てない）。依存の追加なし。セキュリティ影響なし（bandit・npm audit の対象の変更なし）
- P3/P5/P8 影響なし（DB・外部 API・インフラの追加なし）。P6 影響なし（UI なし）。P9 影響なし（個人情報を扱わない）
- 設計品質: 既定値は冒頭の 1 か所（`ADV_CONTAINER_TIMEOUT`・`ADV_DOCKER_BIN`）。エラーは `ADVERSARIAL_ERROR:` の既存の形
Danger Ops（有無/手順/ロールバック）:
- 無（コンテナを起こすだけ。`down -v`・データ削除なし）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | backend の変更があってコンテナを起こせない・別のワークツリーのコンテナのとき、レビュー役を呼ばずに exit 2 で止まる（TC-01 の A40・A41 と FG） |
| V2 | 2 | 読んで可 | A39〜A46 の FG が、それぞれの守りを外したときに本当に落ちる（実装の写しの tautology になっていない） |
| V3 | 3 | 読んで可 | backend の変更が無いイシューで docker を呼ばない／待ちが締め切りの外／noexec の取り逃しが「実行した」に数えられる道が残っていない（TC-01 の A42〜A44） |

## 計画変更記録
- 計画レビュー（20261113_0845）の Warning 3 件への対応: W1 `ps --status`・`inspect` のラベルを実機で確認して §1 に追記／W2 今の形の `<1 語>: No such file or directory` を当て方に残す（4-1 の 4・A44 に 1 件足す）／W3 手動 No.1 の `.env` は `.gitignore` の `*.env` で無視される（`git check-ignore -v .env` で確認済み）と手動テストに書いた。方式・範囲・受け入れ条件は変えないので計画レビューはやり直さない
- close の後（ユーザーとの評価で台帳 F1 を一覧から引き戻した）: 計画の記載「見る範囲（`files.txt`）に `backend/` の変更があれば起こす」→ 採った方法: ブランチ全体（`ADV_BASE...HEAD`）で判定する（4-1 の 2 の「計画変更」・AC 1〜3・A46 と FG-A46）。理由: 2 周目以降は見る範囲が直した差分だけに縮み、文書だけを直した周でコンテナを起こさず、このイシューの目的の空振りがそのまま起こるため。計画レビューのやり直し: 要（AC の文言を変える）。計画レビュー（20261113_1015）OK の Warning 4 件: 4-1 の 2 のコード例と方針を新しい判定に・イシュー（GitHub と写し）の AC 1・2 をブランチ全体に・手順 1 と V2 に A46・docker はスクリプトが先頭で cd したルートで流れる、を直した（方式は変えないので再レビューしない）
- 実装中（test_i202 の N18・N19 に当たった）: 計画の記載「既定値の並びに足す」「`t0=$(date +%s)` で所要秒」→ 採った方法: 新しい既定値は既存の 2 行を変えずに別の `:` 行に置く／所要秒は bash の `SECONDS` で数える。理由: 既定値の行を 1 字も変えない決まり（N18）と、実際の時計を読むのは `adv_now` の 1 か所だけの決まり（N19・I210）を守るため。所要秒は表示だけ。計画レビューのやり直し: 不要（書き方の違いだけ）

## レビュー結果
- [20261113_1015 判定: ✅ 完了](../../reviews/closed/I486_plan_review_20261113_1015.md)
- [20261113_0845 判定: ✅ 完了](../../reviews/closed/I486_plan_review_20261113_0845.md)

## 完了情報
- **完了日時**: Fri Nov 13 10:40:44 JST 2026
- **対応者**: Claude Code
- **レビュー結果**: OK（close の後に台帳 F1 を直して 1 巡し直した）
