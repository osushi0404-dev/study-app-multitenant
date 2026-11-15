# I468 計画書: ワークツリーで ESLint のフックをコンテナで流す・Playwright MCP が切れたときの手順

## 基本情報
- **計画書ID**: plan_I468
- **関連イシュー**: #468
- **Draft PR**: #522
- **作成根拠資料**: docs/issues/open/I468.md（GitHub #468 の本文の写し・正は GitHub）
- **実装後評価**: docs/reviews/open/I468_review.md
- **作成日**: 2026-11-15

## 1. 背景/目的
- I452 で、ワークツリーで frontend を変えてコミットすると、pre-commit の ESLint のフック（ホストで `npm run lint`）が `eslint: not found`（exit 127）で止まり、`SKIP=eslint` を使った。ワークツリーの手順書は「依存はコンテナの中だけ」と決めており、決まり同士が食い違っている
- 同じく I452 で、`/clear` の後に Playwright MCP が「古い接続」として止められ、implement では画面確認ができず、test-gate でユーザーに `/mcp` の再接続を頼むまで止まった
- 目的: frontend を変えるイシューで、コミットの検査と画面確認が、ワークツリーでも人の手を借りずに進むようにする

## 調査結果
### 原因の概要
- ESLint: フックが「ホストに node_modules がある」前提のまま、ワークツリーでは node_modules がコンテナの中にしか無い
- MCP: Claude Code 本体が `/clear` の後に MCP のサーバーを古い接続として止める。手順書に「使えないとき」の手順が無く、気づくのが test-gate まで遅れた

### 詳細な原因分析
- `.pre-commit-config.yaml:50` の `entry: bash -c 'cd frontend && npm run lint'`（`language: system`）はホストの `npm` と `frontend/node_modules/.bin/eslint` を使う。`docker-compose.yml:126-127` は `./frontend:/app` と匿名ボリューム `/app/node_modules` を取り付けるので、ホストの `frontend/node_modules` は空のフォルダのまま（`docs/runbooks/worktree.md:147`「ホストで npm install を使わない」）
- MCP の記録 `~/.cache/claude-cli-nodejs/-mnt-c-app-study-app-multitenant--claude-worktrees-app-1/mcp-logs-playwright/*.jsonl` に `"excludeStalePluginClients: marking stale (declared under a previous workspace root)"` が 2026-11-05〜11-08 の間に複数回ある（2026-11-15 に確かめた）。これが「古い接続として止めた」目印

### 確かめたこと（2026-11-15・スパイク）
- 環境: `docker` あり・このワークツリー（harness-1）のコンテナは起動していない（`docker compose ps` が空）。harness-1 の frontend のイメージは無かった（`docker image ls`）
- **不成立 → 設計に反映**: `docker compose run --rm --no-deps -T frontend npm run lint` は lint を流さず、開発サーバーを起動したまま終わらなかった。原因: `frontend/Dockerfile.dev:23` が node の公式イメージの ENTRYPOINT（`/usr/local/bin/docker-entrypoint.sh`）を、引数を無視して `npm start` する自前のスクリプト（`frontend/docker-entrypoint.sh`）で上書きしている。残ったコンテナは `docker rm -f` で消した（その匿名ボリューム 1 つは使われないまま残った。`docker volume ls -f dangling=true` の中のどれかは特定できないので、消していない）
- **成立**: `docker compose run --rm --no-deps -T --entrypoint npm frontend run lint` は lint を流して exit 0（違反 0 件・24 秒。イメージは harness-2 のビルドの層の再利用で数十秒で作れた）
- **成立**: `--build` を足した形（`docker compose run --rm --no-deps -T --build --entrypoint npm frontend run lint`）は 13 秒（`npm install` の層は package*.json が変わらなければ再利用される）
- **成立**: 使い捨てのコンテナの中の終了コードがそのまま返る（`--entrypoint npx frontend eslint --no-eslintrc --rule "no-debugger: error" --stdin` に `debugger;` を渡して exit=1）
- **成立**: Claude の Bash（サンドボックスの中）から Docker のデーモンに届き、ビルドもできる（上の実行がすべてサンドボックスの中）
- **成立**: Playwright MCP が使えるかは、`ToolSearch` の `select:mcp__playwright__browser_tabs` で読み込み、`browser_tabs`（`action: list`）を呼ぶと分かる。害がなく（タブの一覧だけ）、`.claude/settings.json:97` で許可済みなので承認画面も出ない（このセッションで `0: (current) [](about:blank)` が返った）
- lint のベースライン: 違反 0 件（上の実行）

## 2. 受け入れ条件
- [ ] AC1: ワークツリー（ホストに node_modules が無い）で frontend の変更をコミットすると、ESLint のフックが `SKIP` なしで流れ、lint の違反があれば止まる（失敗の注入で確かめる）。frontend のコンテナが起動しているとき・起動していないときの両方で確かめる
- [ ] AC2: Docker が使えず、ホストにも eslint が無いときは、フックが通らずに止まり、理由と対処が表示される
- [ ] AC3: `docs/runbooks/frontend-verify.md` に、MCP が使えないときの見分け方と再接続の頼み方がある
- [ ] AC4: implement の段階で MCP が使えないとき、test-gate まで持ち越さずにその時点で再接続を頼む流れになっている

## 3. 影響範囲
| 区分 | 内容 |
|---|---|
| Backend | なし |
| Frontend | なし（`frontend/` のファイルは変えない。検査の流し方だけ） |
| DB | なし |
| Config/Infra | `.pre-commit-config.yaml`（ESLint のフックの `entry`） |
| ハーネス | 新しいスクリプト `scripts/claude/lint-frontend.sh`・テスト `scripts/claude/tests/test_i468_lint_frontend.sh`・`.claude/skills/implement/SKILL.md`・`.claude/skills/test-gate/SKILL.md` |
| 文書 | `docs/runbooks/pre-commit.md`・`docs/runbooks/frontend-verify.md` |
| 意図的に変えない | `.github/workflows/ci.yml`（CI の ESLint の段と、pre-commit の段の `SKIP: eslint`）・`docs/runbooks/worktree.md`（§5 の「依存はコンテナの中だけ」は正しく、フックをそれに合わせる）・`frontend/Dockerfile.dev`・`frontend/docker-entrypoint.sh`（引数を無視する入口はアプリの起動の話で、このイシューでは `--entrypoint` で避ける。直すかは下の 9 に記録） |
| 依存 | 追加なし（`package*.json`・`requirements*.txt` は変えない） |

## 4. 変更点一覧（具体）
### 修正アプローチ
pre-commit の ESLint のフックを、新しいラッパーのスクリプト経由にする。ラッパーは「Docker が使えて frontend のコンテナが起動していればその中で」「起動していなければ使い捨てのコンテナで」「Docker が使えなければホストの eslint で」「どれも無ければ止める」の順で lint を流す。Playwright MCP は、手順書に見分け方と依頼の文例の節を足し、implement の最初と test-gate の画面確認の前に使えるかを確かめる手順を足す。

### 4-1. `scripts/claude/lint-frontend.sh`（新規）
修正方針: どこで流しても同じ `npm run lint`（`frontend/package.json` の `eslint src/ --ext .ts,.tsx --max-warnings 0`）を流し、終了コードをそのまま返す。黙って通す分岐を作らない（fail-closed）。
```bash
#!/usr/bin/env bash
# pre-commit の ESLint のフック（I468）。ワークツリーではホストに node_modules が無い（docs/runbooks/worktree.md §5）ので、
# Docker が使えればコンテナの中で、使えなければホストの eslint で流す。どれもできなければ止める（黙って通さない）。
# 呼び出し元: .pre-commit-config.yaml の eslint のフック。終了コード: lint の終了コード・流せないとき 1
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  running=$(docker compose ps --status running --services 2>/dev/null || true)
  if grep -qx frontend <<<"$running"; then
    echo "ESLint: 起動中の frontend コンテナで流します" >&2
    exec docker compose exec -T frontend npm run lint
  fi
  echo "ESLint: 使い捨ての frontend コンテナで流します（初回はイメージの準備に数分かかることがあります）" >&2
  # --entrypoint npm: frontend/Dockerfile.dev が入口を「引数を無視して npm start する」スクリプトにしているため
  # --build: package*.json が変わったら依存を作り直す（変わっていなければ層の再利用で数秒）
  exec docker compose run --rm --no-deps -T --build --entrypoint npm frontend run lint
fi

if [ -x frontend/node_modules/.bin/eslint ]; then
  echo "ESLint: Docker が使えないので、ホストの frontend/node_modules で流します" >&2
  cd frontend && exec npm run lint
fi

echo "⛔ ESLint を流せません: Docker が使えず（docker が無い・Docker が起動していない）、ホストにも frontend/node_modules/.bin/eslint がありません" >&2
echo "   対処: Docker（Docker Desktop）を起動してから、もう一度コミットしてください（docs/runbooks/pre-commit.md「ESLint のフックの流し方」）" >&2
exit 1
```
- `docker compose ps` の出力は変数に受けてから `grep -qx` で 1 行ちょうどの一致を見る（パイプにすると `pipefail` の下で `grep -q` の早い終了が前のコマンドを SIGPIPE で落としうる・I210。部分一致だと `frontend` を含む別のサービス名に当たる）
- 文言・コマンドの細部（表示の文）は実装で整えてよいが、分岐の順・終了コードの返し方・止める形はこのとおり

### 4-2. `.pre-commit-config.yaml`
修正方針: ESLint のフックの `entry` をラッパーにする。`files: ^frontend/src/`・`pass_filenames: false`・`language: system` は変えない。
```yaml
      - id: eslint
        name: ESLint
        language: system
        entry: bash scripts/claude/lint-frontend.sh
        pass_filenames: false
        files: ^frontend/src/
```
上に 1 行のコメントで、ワークツリーでも動くようにコンテナで流すこと（I468・`scripts/claude/lint-frontend.sh`）を書く。

### 4-3. `docs/runbooks/pre-commit.md`
- フック一覧の `eslint` の行に「`scripts/claude/lint-frontend.sh` 経由。コンテナで流す（下の節）」を足す
- 新しい節「## ESLint のフックの流し方（I468）」: 流す場所の順（4-1 の 4 つ）・かかる時間（起動中のコンテナはすぐ・使い捨ては 15〜30 秒ほど・初回はイメージ作りで数分）・止まったときの対処（Docker を起動する）・`SKIP=eslint` は使わない（流せないなら Docker を起動する）・起動中のコンテナの依存が古いとき（package*.json を変えた後）は `docker compose up -d --build --renew-anon-volumes`・使い捨てのコンテナの `--build` で使われなくなったイメージ（`<none>`）が溜まったら `docker image prune` で消せる（任意。データは消えない）・CI は別の段で ESLint を流す（pre-commit の段は `SKIP: eslint`）

### 4-4. `docs/runbooks/frontend-verify.md`
- 新しい節「## 11. MCP が使えないとき」:
  - 確かめ方: `ToolSearch` で `select:mcp__playwright__browser_tabs` を読み込み、`browser_tabs`（`action: list`）を呼ぶ。タブの一覧が返れば使える。読み込めない・呼ぶとエラー・`ToolSearch` が「接続中」と返し続ける、のどれかなら使えない
  - 原因の見分け方: 接続の記録 `~/.cache/claude-cli-nodejs/<作業場所のパスの / を - にしたもの>/mcp-logs-playwright/` の最新の `*.jsonl` に `excludeStalePluginClients: marking stale` があれば、`/clear` などの後に Claude Code 本体が古い接続として止めた（Claude からはつなぎ直せない）。それ以外のエラー（起動の失敗など）は「2. 初回だけの準備」を見直す
  - ユーザーへの依頼の文例: 「画面の確認に使う Playwright MCP の接続が切れています。`/mcp` を打って playwright を選び、Reconnect（再接続）を選んでください。終わったら『つないだ』と返信してください」
  - いつ確かめるか: implement の最初（画面の動きを変える計画のとき）と、test-gate の画面確認の前。使えなければその時点で依頼して止まる（`docs/runbooks/workflow.md`「止めて聞く条件」3）。test-gate まで持ち越さない
- 「1. 目的と範囲」の後ろか「6. 確かめること」の前に「MCP が使えないときは 11」の 1 行を足す

### 4-5. `.claude/skills/implement/SKILL.md`
- 手順の 1) の前に「0) 画面の確かめの準備（計画が `frontend/src` の画面の動きを変えるとき）: `docs/runbooks/frontend-verify.md`「11. MCP が使えないとき」の確かめ方で Playwright MCP が使えるかを、コードを書く前に確かめる。使えなければ、その節の文例でユーザーに再接続を頼んで止まる（止める条件 3・test-gate に持ち越さない）。返信があれば確かめ直して続ける」を足す
- 1) の「画面の確かめ」の行に「使えなくなっていたら 11 の手順（その場で依頼して止まる）」を足す

### 4-6. `.claude/skills/test-gate/SKILL.md`
- 「画面の表示・遷移・入力の結果・コンソールは、`docs/runbooks/frontend-verify.md` の手順（§9 の安全上の注意を含む）で Playwright MCP を使って確かめ」で始まる行に「先に `docs/runbooks/frontend-verify.md`「11. MCP が使えないとき」の確かめ方で使えるかを確かめ、使えなければその節の文例で再接続を頼んで止まる」を足す（implement と同じ粒度にそろえる・plan-writing-rules「条件分岐を足すときのコマンド粒度のパリティ」）

### 4-7. `scripts/claude/tests/test_i468_lint_frontend.sh`（新規）
- 一時の git リポジトリを作り、その中からラッパー（本物のパス）を呼ぶ。`docker`・`npm` は、受け取った引数と作業フォルダを記録して決めた終了コードで終わる偽物を `PATH` の先頭に置く（本物の Docker は使わない）。中身は auto_test の TC-01〜TC-04 と FG

## 5. 実装手順（ステップ）
1. ラッパー（4-1）とテスト（4-7）→ TC-01〜TC-04・FG 参照。最初に置く（分岐と終了コードの返し方が土台）
2. `.pre-commit-config.yaml`（4-2）→ manual_test No.1・No.2 参照。ステップ 1 が前提
3. 手順書とスキル（4-3〜4-6）→ manual_test No.3〜No.5 参照。ステップ 1・2 と並行してよい
4. `/simplify` で整理し、push する（implement 段階）

## 6. テスト計画
### 自動（`docs/tests/open/I468_auto_test.md`）
- テストレベル: シェルの決定論テスト（`scripts/claude/tests/`・CI の `run-all.sh` が流す）。pytest・Jest・E2E は対象のコードが無いので対象外
- TC-01（AC1）: コンテナ起動中は `docker compose exec -T frontend npm run lint` を流し、終了コードを返す
- TC-02（AC1）: 起動していなければ使い捨てのコンテナ（`run --rm --no-deps -T --build --entrypoint npm frontend run lint`）を流し、終了コードを返す。`frontend` を含む別の名前のサービスでは起動中と見なさない
- TC-03（AC2）: Docker が使えずホストに eslint があればホストで流し、終了コードを返す
- TC-04（AC2）: どれもできなければ exit 1・理由と対処を表示・lint を呼ばない
- 決定論テストの対象の選び方（plan-writing-rules）: 黙って通す（終了コードを捨てる・流せないのに 0 で終わる）は、壊れてもコミットが通るだけで気づきにくく、安全装置が無いのと同じになるのでテストにする。手順書・スキルの文言はテストにしない（意図的な変更でしか消えない・manual_test で読む）。`.pre-commit-config.yaml` の `entry` の写しのテストも作らない（manual_test No.1・No.2 の本物のコミットで確かめる）
- 既存の `test_pipefail_negated_grep.sh`（scripts/claude の全スクリプトの走査）が新しいスクリプトにも当たる。shellcheck は commit 時のフックと CI が流す
### 手動（`docs/tests/open/I468_manual_test.md`・実施者はすべて Claude）
- No.1（AC1・コンテナ停止中）・No.2（AC1・起動中）: 本物のワークツリーで違反を入れたファイルをコミットして止まる／違反なしで通る
- No.3（AC3）: 手順書の 11 の目印の文言が本物の記録と一致する
- No.4（AC4）: implement・test-gate の手順の読み合わせ
- No.5（AC3）: `/mcp` の画面に playwright と再接続の項目がある（文例どおりに操作できる）

## 7. ロールバック
- この PR を revert する（スクリプト・設定・文書だけ。データの変更なし）。revert 後はワークツリーでの frontend のコミットに `SKIP=eslint` が要る元の状態に戻る

## 8. Risk & 回避策
<!-- 処遇: 回避 か 受け入れ。受け入れの行は --route の照合で使う（I512） -->
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: ラッパーが黙って通る（終了コードを捨てる・流せないのに 0 で終わる）と、安全装置が無いのと同じになる | 各分岐は `exec` で終了コードをそのまま返し、最後は exit 1。TC-01〜TC-04 と FG で固定する | 回避 |
| R2: 使い捨てのコンテナのイメージが古く（package*.json を変えた後）、依存が合わない lint になる | `run --build` で package*.json が変われば `npm install` の層を作り直す | 回避 |
| R3: 起動中のコンテナの node_modules が古い（package*.json を変えたのに作り直していない）と、手元と CI の lint が食い違う | 手順書に `up -d --build --renew-anon-volumes` を書く。食い違っても CI の ESLint が止める | 受け入れ |
| R4: `--build` のたびに使われなくなったイメージ（`<none>`・数 MB）が溜まる | 手順書に `docker image prune` を書く（データは消えない）。層は共有されるので増えるのは frontend のファイルの写しの分だけ | 受け入れ |
| R5: frontend のコミットが 15〜30 秒ほど遅くなる（初回は数分） | 起動中のコンテナがあればそちらを使う（すぐ終わる）。`files: ^frontend/src/` の変更があるコミットだけで流れる | 受け入れ |
| R6: Claude のサンドボックスの中のコミットから Docker に届かない | スパイクでサンドボックスの中から run・build できることを確かめた。manual_test No.1・No.2 は本物のコミット | 回避 |
| R7: `COMPOSE_PROJECT_NAME` を全体に設定していると、別のワークツリーのコンテナで lint が流れる | worktree.md §5 (C) が設定を禁じ、`wt-ports.sh` が警告する。別のワークツリーのコンテナは別のフォルダを取り付けているので、lint の対象のファイルが違うだけで黙って通るわけではない | 受け入れ |
| R8: MCP が使えないときの依頼で止まる回数が増える | 止まるのは implement の最初の 1 回にまとめる（test-gate まで持ち越すより早く、同じ 1 回） | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 流す順: 起動中のコンテナ → 使い捨てのコンテナ → ホストの eslint → 止める（fail-closed）。警告だけ出して通す形は取らない
- CI の ESLint と、CI の pre-commit の `SKIP: eslint` は変えない
- MCP: 手順書に「MCP が使えないとき」の節を足し、implement の画面確認の前に確かめ、使えなければその時点で再接続を頼む

Claude が決めた（技術的な選択と理由）:
- 使い捨てのコンテナに `--entrypoint npm` を付ける — スパイクで、付けないと `frontend/docker-entrypoint.sh` が引数を無視して開発サーバーを起動し、lint が流れないと分かった（設計確認メモのコマンドの形の技術的な補い）。入口のスクリプトを `exec "$@"` に直す案は、アプリの起動（Dockerfile.dev・compose）を変えることになり、このイシューの範囲を超えるので取らない
- 使い捨てのコンテナに `--build` を付ける — package*.json が変わったときに古い依存で lint しないため。変わっていなければ 13 秒ほど（スパイク）
- ラッパーは `scripts/claude/` に置く — このリポジトリの自作スクリプトの置き場。pre-commit の `language: system` からそのまま呼べる。`language: docker_image` などの pre-commit の機能は、compose のプロジェクト（ワークツリーごとのコンテナ・匿名ボリューム）を知らないので使わない
- 「Docker が使えるか」は `docker` があることと `docker info` が通ることで見る — デーモンが止まっていても `docker` コマンド自体はあるため
- MCP が使えるかの確かめは、スクリプトにせず手順にする — 使えるかは Claude のそのセッションのツールの状態で、別のプロセス（スクリプト）からは見えない。`browser_tabs` の `list` は害がなく許可済み（スパイクで確かめた）
- MCP の確かめは implement の最初（コードを書く前）に置く — 依頼して止まるのが早いほど、ユーザーの再接続と Claude の作業の待ちが重ならない。画面確認の直前にも、使えなくなっていたら同じ手順で止まる
- test-gate のスキルにも同じ確かめを足す — implement の後の `/clear` で切れることもあり、手順の粒度をそろえる（イシューの実装対象の表に無いが、AC4 と同じ目的の対の分岐）
- 一覧 `docs/reviews/backlog/I209.md` F3（implement の最初に計画書のセキュリティレビュー結果の節を確かめる）: 残す — 高リスクの計画の確かめの話で、MCP とは関係しない
- 一覧 `docs/reviews/backlog/I213.md` F2（check-jsonschema の `rev` をタグでなく中身で固定する）: 残す — 同じファイルだが ESLint のフックとは別の話で、ほかの `rev` もタグのまま。固定するなら全部をそろえる別の作業になる
- 一覧 `FILE=-` の行（I224 F9・I223 B1〜B4）: 残す — 実測の約束・bot の停止中の作業で、このイシューと関係しない
- 一覧のほかの実装対象（`scripts/claude/lint-frontend.sh`・`docs/runbooks/pre-commit.md`・`docs/runbooks/frontend-verify.md`・`.claude/skills/test-gate/SKILL.md`・新しいテスト）: 一覧の該当なし

要件適合性・業務ロジック: 受け入れ条件の範囲を超える仕様の追加は無い。マルチテナント・ステータス遷移は該当なし

セキュリティ・ベストプラクティス:
- 入力: ラッパーは引数を受け取らない（`pass_filenames: false`）。流すコマンドは固定の文字列で、外からの値を組み立てない
- 機密: コンテナに渡すのは compose の既定の設定だけ（frontend は `env_file` を持たない）。秘密情報を表示しない
- 安全装置の変更（commit の検査）: 黙って通す分岐を作らない（R1・TC-04）。`SKIP=eslint` を勧める文言を書かない
- バックエンド・フロントエンドのコード変更なし。依存の追加なし。bandit・npm audit の対象なし（重大度の基準は変えない: bandit は MEDIUM 以上・npm audit は high/critical）
- P3/P5/P8 影響なし（DB・外部 API・非同期・新しいインフラなし。Docker のイメージは既存の Dockerfile.dev を使う）。P6 影響なし（UI・データ量の懸念なし）。P9 影響なし（個人情報・テナントデータを扱わない）

設計品質: 分岐ごとの終了コードの扱いを `exec` でそろえる。表示はすべて標準エラー（lint の出力と混ざらない）。設定値（サービス名 `frontend`）は compose の名前そのもの

Danger Ops（有無/手順/ロールバック）:
- 無（コミットの検査の流し方の変更。データの削除・GitHub の設定の変更なし。`docker image prune` は手順書に任意の片付けとして書くだけで、このイシューでは実行しない）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 流せないときに黙って通らない: TC-04 が、Docker が無い／止まっている・ホストに eslint が無いときに exit 1 で lint を呼ばないことを確かめ、最後を `exit 0` にした写しで不合格になる |
| V2 | 2 | 読んで可 | TC-01〜TC-03 が false-green でない: 偽の lint が 1 で終わるときにラッパーも 1 で終わることを確かめ、終了コードを捨てる写し（`|| true`）・部分一致の写しで不合格になる |
| V3 | 1 | 実験必須 | 本物のワークツリー（ホストに node_modules が無い）で、違反を入れたファイルのコミットが、コンテナの停止中・起動中のどちらでも止まる（manual_test No.1・No.2。本物の Docker・pre-commit・git の組み合わせでしか観測できない） |
| V4 | 3 | 読んで可 | CI の ESLint の段と pre-commit の段の `SKIP: eslint` が変わっていない（差分に `.github/` が無い） |

## 計画変更記録
- 計画レビュー（20261115_1038）の Warning: 4-6 の場所を行番号でなく文言で指すように直した。R3 の補足（`files: ^frontend/src/` は `package*.json`・ESLint の設定だけの変更では流れない）は既存の動きで、CI の ESLint が止めるので変えない。方式・範囲・受け入れ条件は変えていないので計画レビューはやり直さない

## レビュー結果
- [20261115_1038 判定: ✅ 完了](../../reviews/I468_plan_review_20261115_1038.md)
