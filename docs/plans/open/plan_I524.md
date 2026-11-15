# I524 計画書: ダッシュボードの確かめ用データを各科目・各曜日 10 問以上にし、開発の起動のたびに作り直す

## 基本情報
- **計画書ID**: plan_I524
- **関連イシュー**: #524
- **Draft PR**: #526
- **作成根拠資料**: docs/issues/open/I524.md（GitHub #524 の本文の写し）
- **実装後評価**: docs/reviews/open/I524_review.md
- **作成日**: 2026-11-16

## 1. 背景/目的
- I513 で作った確かめ用データ（`seed_dashboard_verify`）は、1 科目・1 日 1〜5 問で、解く日・科目も乱数のため、直近 7 日のすべての曜日に全科目の解答があるとは限らない（解答の無い日も 1〜2 日）。曜日ごと・科目ごとの見え方を確かめる例として量が少ない
- データはコマンドを流した日を基準に作るので、流し直さずに日がたつと直近 7 日が空になる
- 目的: 直近 7 日のうち解答の無い 1 日を除くすべての日に、すべての科目で 10 問以上（同じ日・同じ科目はすべて違う問題・科目ごとに日ごとの数がすべて違う）にする。開発の環境の起動のたびに自動で作り直す。#508 から移した同じファイルの軽い指摘 F5・F6・F9・F10 を直す

### 調査結果
- **原因の概要**: I513 の確かめ用データは「境目が毎回入ること」「値が毎回変わること」を目的に作り、1 日の量を要件にしていなかった。1 日 1 科目の上限は科目ごとの問題の数（5）で決まっていた。作り直しは手で流すしかなかった
- **詳細**:
  - `backend/dashboard/verify_data.py:36` `PROBLEMS_PER_SUBJECT = 5`。`plan_answers`（85〜121 行）は、直近 7 日の中から `rng.randint(1, 2)` 日を解答の無い日にし（97 行）、解く日ごとに科目を 70% で選び（107 行）、1 科目 `rng.randint(1, PROBLEMS_PER_SUBJECT)` 問を作る（109 行）
  - `_write_answers`（272〜298 行）は (日・科目) ごとにセッションを 1 つ作り、`problems[i]`（i は 0 からの連番）を割り当てる。同じセッションで同じ問題は 1 回まで（`QuizAnswer` の `(session, problem)` の一意制約）なので、1 日 1 科目の数は問題の数まで
  - F6: `_random_time`（69〜82 行）は `int(rng.random() * span)` で 0〜span-1 秒を足す。過去の日は `span = DAYTIME_HOURS * 3600 - 1` なので 7:00:00〜22:59:58 になり、docstring の「7:00〜22:59」の終わり（22:59:59）と 1 秒ずれる。今日は 0:00〜「今の 1 分前」の 1 秒前まで
  - F5: `test_I513_seed_dashboard_verify.py:155-164`（TC-49）は `plan_answers` の結果（時刻で並べた後）を位置ごとに比べる。今日の解答の時刻は `int(r * span)` で、0:30 に流すと span が短く、2 件が同じ秒に丸まりやすい。丸まった 2 件は作った順のまま残り、23:00 の側（丸まらない）は r の順に並ぶので、並びが入れ替わって落ちうる。今日の解答が 10 問以上になると起きやすくなる。比べたいのは「同じ解答の集まりか」なので、並び順に依らない比べ方にする
  - F9: `verify_data.py:53-54` の `VerifyDataError` の docstring が「呼び出し元の管理コマンドが CommandError に変える」と呼び出し元を書いている
  - F10: `test_I513_seed_dashboard_verify.py:283-295`（TC-47）は `seed_verify_data` を直接呼ぶだけで、管理コマンドが `CommandError` に変える経路を見ていない
- **起動の形の調べ**（2026-11-16）:
  - `docker-compose.yml` の `e2e-init` は backend のイメージで一度きりの処理を動かす前例（`depends_on: backend: condition: service_healthy`・`profiles: [e2e]`）。今回は既定の起動で動かすので profile は付けない
  - 標準の起動コマンドは `docker compose up -d --build --renew-anon-volumes`（`docs/runbooks/common-commands.md:14`・`worktree.md:152`）で、サービスを名前で指定しない＝新しいサービスも動く
  - CI（`.github/workflows/e2e.yml:29`）は `docker compose up -d --wait db backend frontend` と名前で指定し、続けて `exec backend` で `seed_e2e` を流す。名前で指定した起動は、依存先でないサービスを起こさない。敵対的レビューのコンテナ（`scripts/claude/adversarial-review.sh:425`）も `up -d --build --wait backend` で同じ
  - backend のコンテナは `e2e/.env.e2e` を読まない（`E2E_TEST_PASSWORD` が無い）。`e2e-init` と同じく `env_file` に `e2e/.env.e2e`（`required: false`）を足せば、値は会話・出力に出ない
- **スパイク（2026-11-16・スクラッチパッドの使い捨ての compose・プロジェクト名 `i524spike`・片付け済み）**: redis のイメージで、健康確認つきの `base` と、`base` が healthy の後に 1 行出して終わる `once` を作った
  - `up -d` を 2 回 → `once` のログに 2 行（`ran-at-1794759740`・`ran-at-1794759744`）。**成立**: 終わった一度きりのサービスは、`up -d` のたびにもう一度動く（`base` が動いたままでも、健康確認を待ってから）
  - `up -d --wait`（名前の指定なし）→ **exit 1**（`container i524spike-once-1 exited (0)`）。正常に終わった一度きりのサービスでも、名前を指定しない `--wait` は失敗扱いにする。→ 手元で名前を指定しない `--wait` の起動はしていない（上の grep）。手順書に注意を書く（R3）
- **環境の前提**（2026-11-16）: `docker compose version` → v5.6.0。`docker compose ps` で backend・db・frontend・redis が稼働（app-1）。`.claude/settings.json` の許可に `docker compose up *`・`docker compose logs *` がある（承認画面なし）
- **compose を読む決定論テスト**: `scripts/claude/tests/test_compose_ports.sh`（公開ポート）・`test_i213_dependabot.sh`（I1: `image:` の指紋・V1: 名前の無い保存領域は frontend の `/app/node_modules` だけ）。新しいサービスはポートを出さず、`image:` を使わず（`build`）、保存領域は `./backend:/app` の bind だけなので、どちらにも当たらない（6 の決定論ゲートで確かめる）
- 既存テストの事前実行・lint の事前計測: CI・lint の変更ではないので省く（pytest は CI が PR ごとに流す）

## 2. 受け入れ条件
- [ ] AC1: どの種でも、直近 7 日のうち今日より前の 1 日だけが全科目とも解答なしで、それ以外の 6 日（今日を含む）はすべての科目で 10〜20 問ある（TC-01・種 0〜99）
- [ ] AC2: どの種でも、同じ日・同じ科目の解答はすべて違う問題である（TC-03・DB に書いた解答で確かめる）
- [ ] AC3: どの種でも、科目ごとに、解答のある 6 日の問題数がすべて違う（科目どうしで同じ数は許す・TC-02）
- [ ] AC4: 範囲の外の解答（1 科目 1〜5 問のまま）・300 秒超えの解答・今日の解答は毎回入る。`--seed` が同じなら同じデータ・違えば違うデータ。期待値は overview の応答と一致する（TC-01・I513 の TC-40〜TC-43・TC-49 が通る）
- [ ] AC5: 画面確認で、作り直した後のダッシュボードの「すべて」と科目ごとに、曜日ごとの棒の読み上げの文が、解答の無い 1 日を除いてすべて 10 問以上で、出力の期待値と一致した記録がある（手動 No.2）
- [ ] AC6: `docs/runbooks/frontend-verify.md` §11 の説明が新しい作り（量・起動のたびの作り直し・ログの読み方）と合っている
- [ ] AC7: F5（TC-49 が並び順に依らない）・F6（時刻の範囲と docstring が一致・TC-06）・F9（docstring）・F10（`call_command` で `CommandError`・TC-07）が直っている。#508 に「I524 に移した」とコメントする
- [ ] AC8: `docker compose up -d` で起動し直すと、確かめ用データがその日を基準に作り直され、種と期待値が `docker compose logs dashboard-verify-seed` で読める。起動し直す前と後で種と値が変わり、どちらも直近 7 日にデータがある（手動 No.1・No.3）
- [ ] AC9: パスワードの設定が無い・`DEBUG` が偽のとき、起動の処理（`--soft-stop`）はデータを作らず、案内を出して正常に終わる（TC-04・TC-05）
- [ ] AC10: CI の E2E は、確かめ用データの処理を動かさない（名前で指定した起動のまま）。PR の E2E が合格する（手動 No.4）
- [ ] AC11: 既存の機能に退行が無い（CI の全テスト）

## 3. 影響範囲
- Backend: 確かめ用データの中身（`backend/dashboard/verify_data.py`）と管理コマンド（`backend/dashboard/management/commands/seed_dashboard_verify.py`・引数 `--soft-stop` を足す）とそのテストだけ。API・集計（`backend/dashboard/selectors.py`）は変えない
- Frontend: なし
- DB: なし（マイグレーションなし。開発の DB で、確かめ用の科目ごとに問題を 15 問足して計 20 問にし、確かめ用の利用者のセッションと解答を作り直す）
- Config/Infra: `docker-compose.yml` に一度きりのサービス `dashboard-verify-seed` を足す（ポート・保存領域・profile なし）
- Docs: `docs/runbooks/frontend-verify.md` §11（と §12 の 1 語・一覧の同梱）・`docs/reviews/backlog/I468.md`（同梱した F5 の行を消す）
- 変えないもの: CI のワークフロー・`e2e-init`・`seed_e2e`・依存（requirements・package）・Dockerfile

## 4. 変更点一覧（具体）

### 修正アプローチ
計画（乱数）を「境目と量を先に決め、その後で正誤・時間・時刻を乱数で足す」形に組み直す。直近 7 日は、解答の無い日を 1 日だけ選び、残り 6 日は全科目で、科目ごとに 10〜20 から重ならない 6 つの数を割り当てる。問題は科目ごとに 20 問にして、(日・科目) ごとのセッションに違う問題を割り当てる。起動のたびの作り直しは、compose の一度きりのサービスで、backend が healthy になった後に管理コマンドを `--soft-stop` 付きで流す（止まる理由があれば案内を出して正常に終わる）。

### 4-1. 確かめ用データの量と形（`backend/dashboard/verify_data.py`）
修正方針: 境目（解答の無い日・範囲の外の日）と、直近 7 日の量（科目ごとの日ごとの数）を、乱数の正誤・時間・時刻より先に確定する。乱数の消費量は `now` に依らない（I513 の TC-49 を保つ）。

- 定数:
  - `PROBLEMS_PER_SUBJECT = 20`（コメント: 同じセッションで同じ問題は 1 回までなので、1 日 1 科目の解答数の上限）
  - `RECENT_COUNT_RANGE = (10, PROBLEMS_PER_SUBJECT)`（直近 7 日の解答のある日の、1 科目の問題数。科目ごとに日どうしで重ならない）
  - `OUTSIDE_COUNT_RANGE = (1, 5)`（範囲の外の日の 1 科目の問題数・I513 のまま）
  - `SUBJECT_RATE` のコメントを「範囲の外の日に、その科目を解く割合」に直す（直近 7 日は全科目で解くため）
- `plan_answers(rng, now)` を次の順にする（docstring も合わせる）:
  1. `today`・`outside_days`（13〜7 日前）・`recent_past_days`（6〜1 日前）・`slugs` を作る
  2. 境目と量を先に確定する:
     - `empty_day = rng.choice(recent_past_days)`（解答の無い日はちょうど 1 日）
     - `forced_outside_day = rng.choice(outside_days)`
     - `recent_days = [d for d in recent_past_days if d != empty_day] + [today]`（6 日）
     - `recent_counts = {slug: rng.sample(range(RECENT_COUNT_RANGE[0], RECENT_COUNT_RANGE[1] + 1), len(recent_days)) for slug in slugs}`（10〜20 の 11 個から重ならない 6 個。`recent_days` の並びに対応）
  3. 範囲の外の日: `forced_outside_day` か `rng.random() < OUTSIDE_DAY_RATE` の日に、科目を 70% で選び（最低 1 科目）、1 科目 `rng.randint(*OUTSIDE_COUNT_RANGE)` 問（I513 のまま）
  4. 直近の 6 日: すべての科目で `recent_counts[slug][i]` 問
  5. 各解答の正誤・時間・時刻は I513 のまま（`CORRECT_RATE`・`SECONDS_RANGE`・`_random_time`）
  6. 直近 7 日の解答のどれか 1 つを 300 秒超えにする（I513 のまま）。時刻で並べて返す
  - 実装の形: (日, 科目, 数) の組を先に並べ（`_day_groups` のような小さな関数に分けてもよい）、その組ごとに解答を作る。1 つの関数が長くなりすぎないようにする
- `_random_time`（F6）: 範囲を「開始以上・終わり未満」にそろえる。過去の日は `span = DAYTIME_HOURS * 3600`（7:00:00〜22:59:59）。今日は今のまま（0:00:00〜今の 1 分前の 1 秒前。今の 1 分前が 0:00 より前なら 0:00:00）。docstring を「今日は 0:00 から今の 1 分前まで（今の 1 分前は含まない。0:01 より前に流したときは 0:00）、過去の日は 7:00 から 23:00 まで（23:00 は含まない）」にする
- `VerifyDataError` の docstring（F9）: 「確かめ用のデータを作らずに止まるとき（DEBUG が偽・パスワードが空・同じメールの利用者がほかの組織にいる）」
- `_ensure_subjects`: 中身はそのまま（`range(1, PROBLEMS_PER_SUBJECT + 1)` の `get_or_create` で、今ある 1〜5 を使い、6〜20 を作る）
- `_write_answers`: そのまま（`problems[i]` の連番で、1 セッション 20 問まで違う問題になる。`total_problems=len(problems)` は 20 になる）
- モジュールの docstring に「直近 7 日は解答の無い 1 日を除いて全科目 10〜20 問（I524）」を 1 行足す

### 4-2. 起動の処理から呼ぶ引数（`backend/dashboard/management/commands/seed_dashboard_verify.py`）
修正方針: 起動の処理から呼ぶとき、止まる理由（`VerifyDataError`）があっても起動を失敗に見せないため、案内を出して終了コード 0 で終わる引数を足す。手で流すとき（引数なし）は今どおり `CommandError` で止まる。

- `parser.add_argument('--soft-stop', action='store_true', help='止まる理由があれば、作らずに案内を出して正常に終わる（開発の起動の処理から呼ぶため）')`
- `handle` の `except VerifyDataError as error:` で、`options['soft_stop']` が真なら `self.stdout.write(f'確かめ用のデータは作りませんでした: {error}')` を出して `return`。偽なら今どおり `raise CommandError(str(error)) from error`
- モジュールの docstring に「開発の起動のたびに compose の `dashboard-verify-seed` が `--soft-stop` 付きで流す」を足す
- DB の接続エラーなど `VerifyDataError` 以外は今どおり例外で終わる（起動のほかのサービスには影響しない。ログに出る）

### 4-3. 起動のたびの作り直し（`docker-compose.yml`）
修正方針: `e2e-init` と同じ形（backend のイメージ・`backend/.env` と `e2e/.env.e2e` を読む・backend が healthy の後）で、profile の無い一度きりのサービスを足す。

```yaml
  # 開発の起動のたびに、ダッシュボードの確かめ用データを今日を基準に作り直して終わる（I524）
  # 出力（種と期待値）: docker compose logs dashboard-verify-seed。手順: docs/runbooks/frontend-verify.md §11
  # パスワードが無い・DEBUG が偽なら、作らずに案内を出して正常に終わる（--soft-stop）。CI は名前で指定して起動するので動かない
  dashboard-verify-seed:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: dev
    env_file:
      - path: ./backend/.env
        required: false
      - path: ./e2e/.env.e2e   # E2E_TEST_PASSWORD（確かめ用の利用者のパスワード）
        required: false
    environment:
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./backend:/app
    depends_on:
      backend:
        condition: service_healthy   # migrate の後
    networks:
      - app-network
    command: python manage.py seed_dashboard_verify --password-env E2E_TEST_PASSWORD --soft-stop
```
- 置き場所: `frontend` の後・`e2e-init` の前（開発の既定の起動で動くサービスの並びの最後）
- `restart` は書かない（既定の `no`。終わったら止まったまま）

### 4-4. テスト
| ファイル | 変更 |
|---|---|
| `backend/dashboard/tests/test_I524_dashboard_verify_volume.py`（新規） | TC-01〜TC-07（auto_test） |
| `backend/dashboard/tests/test_I513_seed_dashboard_verify.py` | F5: TC-49 の比べ方を `collections.Counter` にする（並び順に依らない）。TC-42 はそのまま（新しい作りでも成り立つ。新しい決まりは TC-01〜TC-03 で見る） |

### 4-5. 手順書（`docs/runbooks/frontend-verify.md` §11）
- 冒頭: 「開発の環境を起動するたびに、`dashboard-verify-seed` がその日を基準に作り直す（I524）。画面から解いて足した分も、次の起動で消える」
- 1. 作り直す: 「起動のたび（自動）」と「手で流す（今のコマンド）」の 2 つ。起動の出力は `docker compose logs dashboard-verify-seed` で読む（種・期待値。作らなかったときは `確かめ用のデータは作りませんでした: <理由>`）。`docker compose up -d backend` のように名前を指定した起動では動かない。名前を指定しない `docker compose up -d --wait` は、このサービスが終わることで失敗扱いになるので使わない（R3）
- 「毎回入るもの」: 直近 7 日は、今日より前の 1 日だけが解答なしで、ほかの 6 日（今日を含む）は全科目で 10〜20 問（同じ日・同じ科目は違う問題・科目ごとに日ごとの数がすべて違う）。範囲の外（8〜14 日前）の解答（1 科目 1〜5 問）・300 秒を超える解答・今日の解答
- 「消さずに使い続ける」の文を「確かめ用の利用者・組織・科目・問題は残し、セッションと解答だけを作り直す」に直す
- 2. の「流した直後に確かめる。日付をまたいだら流し直す」に「起動し直してもよい」を足す
- §12（一覧 I468.md F5 の同梱）: 「作業場所のパスの / を - にしたもの」を「作業場所のパスの `/` と `.` を `-` にしたもの」にする。直したら `docs/reviews/backlog/I468.md` から F5 の行を消す

## 5. 実装手順（ステップ）
1. **起動のたびの作り直し（未知リスク先行）**: 4-2 の `--soft-stop` と 4-3 のサービスを足し、TC-04・TC-05 を書く。開発の環境を `docker compose up -d --build --renew-anon-volumes` で起動し直し、ログに種と期待値が出ることを見る（→ TC-04・TC-05・手動 No.1 の下見）。この時点のデータは I513 の作り（量は 4-1 の前）
2. **量と形**（ステップ 1 と並行可）: 4-1 を直し、TC-01〜TC-03・TC-06 を書く（→ TC-01〜TC-03・TC-06）
3. **F5・F10**（ステップ 2 と並行可）: 4-4 の TC-49 の直しと TC-07（→ TC-07・TC-49）
4. **手順書**（ステップ 1〜3 の後）: 4-5
5. implement 段階の下見: `docker compose up -d` でもう一度起動し、ダッシュボードの棒の読み上げで各日 10 問以上を見る（手動 No.2 の下見。正式な記録は test-gate）
- 関係するテスト（手元で流すもの）: `dashboard/tests/test_I524_dashboard_verify_volume.py`・`dashboard/tests/test_I513_seed_dashboard_verify.py`・`studylogs/tests/test_I455_org_scoped_querysets.py`（`dashboard` のコードの組織の絞り込みのコメントを見る・I513 の fix-loop の教訓）
- サービスの再起動: ステップ 1 と 5 で `docker compose up -d` を行う（新しいサービスを作るため）。backend のコードは bind なので、ほかの再起動は要らない

## 6. テスト計画
### 自動（`docs/tests/open/I524_auto_test.md`）
- テストのレベル: 計画（`plan_answers`）は DB を使わないユニット（種 0〜99）。違う問題・`--soft-stop`・`call_command` は DB を使う結合（pytest）。compose の起動は手動（Claude）で見る（compose の中身をテストにもう一度書く照合は作らない・plan-writing-rules の「写しのテストを作らない」）
- 再発防止: 量の決まり（TC-01〜TC-03）・起動の処理が止まらないこと（TC-04・TC-05）・時刻の範囲（TC-06）・コマンドの止まり方（TC-07）
- 認可・テナント: API は変えない。作り直しが確かめ用の利用者以外に触らないことは I513 の TC-44・TC-47 が見ている（作り直しの範囲は変えない）
- pytest は CI が PR ごとに流す（手元では関係するテストだけ）。決定論ゲートは compose を読む 2 本（`test_compose_ports.sh`・`test_i213_dependabot.sh`）
### 手動（`docs/tests/open/I524_manual_test.md`・実施者はすべて Claude）
- 起動し直してログに種と期待値が出る・画面の棒の読み上げが各日 10 問以上で出力と一致・もう一度起動し直すと種と値が変わる・PR の E2E が合格する

## 7. ロールバック
- PR を revert する（マイグレーション・依存の変更なし）。revert の後、開発の環境では `docker compose up -d --remove-orphans` で `dashboard-verify-seed` のコンテナが消える（消さなくても止まったまま）。開発の DB の確かめ用の問題 6〜20 は残るが、I513 の作りは 1〜5 しか使わないので害はない

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 起動のたびの作り直しが、本番やほかの利用者のデータを消す | 作り直しの範囲は I513 のまま（`DEBUG` が偽なら最初に止まる・消すのは確かめ用の組織にいる確かめ用の利用者のセッションだけ。I513 の TC-44・TC-45・TC-47）。`docker-compose.yml` は開発の起動の定義で、本番（`nginx` の production の profile）とは別。`DEBUG` が偽のときは `--soft-stop` で何も作らずに終わる（TC-04） | 回避 |
| R2: 起動の処理が失敗して開発の起動を止める | どのサービスも `dashboard-verify-seed` に依存しない。`VerifyDataError` は `--soft-stop` で終了コード 0（TC-04・TC-05）。それ以外の例外もこのコンテナが止まるだけ | 回避 |
| R3: 名前を指定しない `docker compose up -d --wait` は、このサービスが終わることで失敗扱いになる（スパイクで確かめた） | 手元・CI・スクリプトに、名前を指定しない `--wait` の起動は無い（1 の調査結果）。手順書 §11 に「使わない」と書く | 受け入れ |
| R4: 画面から解いて足した分・手で流した種のデータが、次の起動で消える | ユーザーが選ぶ前に了承（設計確認メモ）。手順書 §11 に書く | 受け入れ |
| R5: 今日の解答も 10 問以上になるので、日付が変わった直後に起動すると今日の解答の時刻が 0:00 付近に詰まる | 期待値・画面の数には影響しない（時刻の並びだけ）。イシューの制約・引き継ぎに記載済み | 受け入れ |
| R6: 量が増えて起動の時間が延びる | 解答は 2 科目 × 6 日 × 最大 20 問＋範囲の外（最大 2 × 7 × 5）で 310 件以下を `bulk_create`・`bulk_update`。数秒で終わり、ほかのサービスを待たせない | 受け入れ |
| R7: 量の決まり（重ならない数・解答の無い日 1 日）が、乱数の作りの変更で気づかずに崩れる | 種 0〜99 で TC-01・TC-02 が毎回見る。FG で落ちることを確かめる | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ・本文）:
- 同じ日・同じ科目はすべて違う問題、かつ科目ごとに日ごとの問題数がばらばら（両方）。科目どうしで同じ数は許す
- 解答の無い日は直近 7 日のうち今日より前の 1 日だけ。ほかの 6 日（今日を含む）は全科目 10 問以上
- 科目ごとの問題は計 20 問（今ある 1〜5 はそのまま・6〜20 を足す）。数は 10〜20 から重ならないように選ぶ
- 範囲の外の日の量は今のまま（1 科目 1〜5 問）。正誤・時間・時刻は乱数（種で再現）。期待値の出し方と表記は変えない
- 開発の環境の起動（`docker compose up`・再起動を含む）のたびに自動で作り直す。種は毎回乱数・出力は起動のログ。パスワードが無い・`DEBUG` が偽なら作らずに正常に終わる。画面から足した分も消える（了承済み）
- #508 の F5・F6・F9・F10 をこのイシューで直す

Claude が決めた（技術的な選択と理由）:
- 起動の形は compose の一度きりのサービス `dashboard-verify-seed`（backend の起動の手順に入れない）。理由: backend のコンテナは `e2e/.env.e2e` を読まず、読ませると backend の全プロセスにパスワードが入る。CI も backend を起動するので、backend の起動に入れると CI でも動く。別のサービスなら、CI の名前で指定した起動では動かず、失敗しても backend に影響しない。`e2e-init` と同じ形で読み手が迷わない
- サービスに profile を付けない（既定の起動で動かすため）。ポート・名前の無い保存領域を持たない（`test_compose_ports.sh`・`test_i213_dependabot.sh` の決まりのまま）
- 起動から呼ぶときの止まり方は、管理コマンドの引数 `--soft-stop`（シェルで `|| true` などを書かない）。理由: 止まる理由（`VerifyDataError`）だけを正常終了にして、DB の接続エラーなど想定外の失敗は失敗のまま見えるようにする。手で流すときは今どおり `CommandError`
- `--soft-stop` の案内は標準出力に `確かめ用のデータは作りませんでした: <理由>`（理由は `VerifyDataError` の文。パスワードの値は含まない）
- 量の割り当ては `rng.sample(range(10, 21), 6)`（科目ごと）。理由: 重ならないことを作りで保てる（後で確かめて引き直す作りにしない）。乱数の消費量は `now` に依らない
- 問題の割り当ては今の `problems[i]`（連番）のまま。理由: 同じセッションの中で違う問題になることは連番で保てる（一意制約もある）。ダッシュボードの値は問題の中身に依らないので、どの問題を選ぶかを乱数にする価値が無い
- TC-42 はそのまま残す（新しい作りでも成り立つ。解答の無い日が「1 日以上」の確かめは、TC-01 の「ちょうど 1 日」に含まれる）。新しい決まりは新しいファイルの TC-01〜TC-03 で見る（I524 の分を I513 のファイルと分けて、どのイシューの決まりかを追えるようにする）
- F6 は式を直す（過去の日 `span = DAYTIME_HOURS * 3600`）。範囲は「開始以上・終わり未満」で docstring にそろえる。今日の範囲は式を変えず docstring を直す（今より後の解答を作らない決まりを保つ）
- F5 は `Counter` で比べる（同じ解答の集まりかを見る。並べ替えの安定性に依らない）
- F10 は TC-47 の隣に `call_command` の版（TC-07）を足す
- #508 への「I524 に移した」のコメントは close 段階の push の後に書く（GitHub への書き込みの時点）
- 一覧（`docs/reviews/backlog/`）: 実装対象のファイル（`verify_data.py`・`seed_dashboard_verify.py`・`test_I513_seed_dashboard_verify.py`・`docker-compose.yml`・`docs/runbooks/frontend-verify.md`）と `FILE=-` で grep し、当たったのは次の 6 行
  - 一覧 docs/reviews/backlog/I223.md B1〜B4: 残す — ハーネスの行（`FILE=-`）で、本イシューの変更点と関係が無い
  - 一覧 docs/reviews/backlog/I224.md F9: 残す — 同上
  - 一覧 docs/reviews/backlog/I468.md F5: 同梱 — 同じファイル（`frontend-verify.md` §12）の説明の 1 語の直しで、手順書を触るついでに直せる。「作業場所のパスの `/` を `-` にしたもの」を「作業場所のパスの `/` と `.` を `-` にしたもの」にする（4-5）。直したら一覧から F5 の行を消す
- セキュリティ: API・認可は変えない。作り直しの範囲・`DEBUG` の止まり方は I513 のまま（最小権限）。パスワードは `e2e/.env.e2e` を `env_file` で読み、コマンドは環境変数の名前だけを受ける（引数・出力・ログに値を出さない。`--soft-stop` の案内にも出ない）。入力は `--seed`（int）と環境変数の名前だけで、SQL は ORM だけ。XSS・CSRF は画面を変えないので該当なし。依存の追加なし。bandit は MEDIUM 以上を直す・LOW は `# nosec` で抑える（`random` は確かめ用のデータで暗号の用途ではない＝B311 は I513 の `# nosec B311` のまま）。npm audit は依存を変えないので対象外
- P3/P5/P8 影響なし（DB のスキーマの変更・外部 API・非同期・新しいインフラの費用・依存の変更なし。compose のサービスは開発の手元だけで、一度きり・数秒）
- P6 影響なし（画面・API を変えない。解答は最大 310 件で `bulk_create`）
- P9 影響なし（個人情報を新しく集めない。確かめ用の架空の利用者だけを開発の DB に作る）
- 要件・UI/UX の仮定で決めたものは無い（引数の名前・サービスの名前・ログの文は技術的な選択）

Danger Ops（有無/手順/ロールバック）:
- 無。起動のたびに消すのは、開発の DB の確かめ用の利用者のクイズのセッションと解答だけ（I513 の範囲のまま・本番では `DEBUG` が偽で止まる）。戻すときは PR の revert（7）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | `--soft-stop` で正常に終わるのは `VerifyDataError` のときだけで、そのとき何も作らず・消さない（TC-04・TC-05。`ensure_debug()` とパスワードの確かめが書き込みより前にあることを読む）。`--soft-stop` が無いときは今どおり `CommandError`（I513 の TC-45・TC-46） |
| V2 | 2 | 読んで可 | 量の TC（TC-01〜TC-03）が、種を変えても毎回「ちょうど 1 日の空き」「全科目 10〜20 問」「科目ごとに重ならない」「同じ日・科目で違う問題」を見ていて、作りを崩すと落ちる（FG-1〜FG-3） |
| V3 | 3 | 読んで可 | 新しいサービスが CI の起動（`.github/workflows/e2e.yml` の名前で指定した `up`）で動かず、どのサービスもこれに依存しない。パスワードは `env_file` から読み、command・ログに値が出ない |

## 計画変更記録
- 計画レビュー（`docs/reviews/I524_plan_review_20261116_0127.md`）の Warning 2 件への対応: 手動 No.2 の備考に「No.1 と No.2 の間に起動し直さない」を足した／TC-05 の「環境変数が無い」経路が同じ分岐を通ることは、実装で TC-05 を流して確かめる。計画レビューのやり直し: 不要（findings への対応の追記だけ。方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261116_0127 判定: ✅ 完了](../../reviews/I524_plan_review_20261116_0127.md)
