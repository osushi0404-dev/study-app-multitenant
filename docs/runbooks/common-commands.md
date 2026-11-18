# よく使うコマンド

Django・node はコンテナの中にだけある（ホストには無い）。アプリのコマンドは `docker compose exec -T <サービス> …` で流す。Bash の書き方（1 つずつ流す・前置きやパイプを付けない理由）は `docs/runbooks/danger-ops.md`「外に出すコマンドの書き方」。

## エラー調査手順
```bash
# 直近のエラーを操作履歴付きで確かめる
docker compose exec -T backend python manage.py analyze_logs --last-errors=1
```

## よく使用するコマンド

### 開発環境起動
```bash
docker compose up -d --build --renew-anon-volumes
```
- 毎回この形で起動する（I213）。依存の一覧（`requirements*.txt`・`package-lock.json`）や土台イメージの指紋が変わっていれば作り直し、変わっていなければキャッシュで数秒で終わる。Dependabot の PR を取り込んだあとも、これだけで手元が新しい版になる
- `--renew-anon-volumes` が作り直すのは名前の無い保存領域（frontend の `/app/node_modules`）だけ。DB（`postgres_data`）・redis の中身は名前付きなので消えない（`scripts/claude/tests/test_i213_dependabot.sh` の V1 が固定）

### worktree ごとのポート分離（同時起動・I097）
複数の worktree のスタックを同時に起動するときは、起動の前に今いるワークツリーで `bash scripts/claude/wt-ports.sh` を 1 回流す（直下の `.env` に `BACKEND_PORT` などの空きのポートを割り当てる）。決まりと仕組みは `docs/runbooks/worktree.md` §6。割り当てたポートは `docker compose port backend 8000` で確かめる。

### ログ確認
```bash
# コンテナの標準出力（直近 200 行）
docker compose logs --tail=200 backend
# ファイルのログ（名前付きの保存領域 backend_logs の中。ホストの backend/logs/ には無い）
docker compose exec -T backend tail -n 200 /app/logs/django.log
```
`-f`（追い続ける）は終わらないので使わない。

### フロントエンド・バックエンド再起動
```bash
docker compose restart frontend backend
```

### テスト実行
手元では、変えた所に関係するテストのファイルだけを流す。全体は CI（PR ごと）が流すので、手元で流し直さない。
```bash
# バックエンド（CI と同じ pytest。対象のファイルを指定する）
docker compose exec -T backend python -m pytest <テストのファイル> --tb=short
# フロントエンド（CI=true が無いと監視モードで終わらない）
docker compose exec -T -e CI=true frontend npm test -- <テストのファイル>
```

## シェルスクリプトのロジック検証

シェルスクリプトのロジック（`grep`/`sed`/`awk` の正規表現の動きに頼る関数など）を確かめるときは、対象を**スクリプトファイルとして `bash` で実行**する（例: `bash scripts/claude/tests/test_review_verdict.sh`）。

- Claude Code の対話シェルでは `grep` が同梱のラッパー（`ugrep`）に置き換わっていて、`-E`・`-o` などの動きが GNU grep と違うことがある。`bash <スクリプト>` の子のプロセスと CI では GNU grep が使われる（どうしても対話シェルで使うなら `/usr/bin/grep` と書く）
- Bash ツールは、`test`・`[`・`grep` の終了コード 1 をエラーとして目立たせないことがある。手で流す決定論の確かめ・失敗の注入は、スクリプトか `bash -c '…'` で包んで終了コードを出させて読む（表示が無いことを合格と読まない）

## モデル変更時の必須手順（migration drift 防止）

`backend/*/models.py` を変えたら、マイグレーションを作ってコミットする。
```bash
docker compose exec -T backend python manage.py makemigrations
# 食い違いが無ければ "No changes detected"（exit 0）
docker compose exec -T backend python manage.py makemigrations --check --dry-run
```
書き忘れると、新しい DB（CI・新しい環境）でだけ NOT NULL 違反などで壊れる（I049）。CI の backend-lint も `makemigrations --check` で止める。

## API の形を変えたとき（型の作り直し・I493）

契約に入れた API（`backend/core/openapi.py` の `CONTRACT_PATHS`）のシリアライザ・ビューを変えたら、スキーマと画面の型を作り直してコミットする。

```bash
# 1. シリアライザから OpenAPI のスキーマ（backend/openapi.yaml）を作る（警告が 1 つでもあれば失敗する）
docker compose exec -T backend python manage.py spectacular --file openapi.yaml --validate --fail-on-warn

# 2. スキーマから画面の型（frontend/src/types/api/schema.d.ts）を作る（道具を入れるのは初回だけ）
npm --prefix tools/api-types ci --ignore-scripts
npm --prefix tools/api-types run generate
```

- 作った 2 つのファイル（`backend/openapi.yaml`・`frontend/src/types/api/schema.d.ts`）は手で直さない
- 作り直し忘れは CI が止める（スキーマは backend-test の `core/tests/test_I493_openapi_contract.py`、型は `API Types Up To Date` ジョブ）
- 契約に API を足すときは `CONTRACT_PATHS` にパスを足し、警告 0 で作れるようにビュー（`extend_schema`）とシリアライザ（`extend_schema_serializer` など）に注釈を付ける。画面は `frontend/src/types/api/index.ts` に短い名前を足して使う
- 道具（`tools/api-types`）は画面の本体とは別の置き場で TypeScript 5 で動く（画面は `react-scripts` 5 の制約で TypeScript 4.9 のまま）

## ローカルで E2E を流す

手順・落とし穴（ホストで動かさない・レート制限の外し方・初回の `e2e/.env.e2e`）は `docs/runbooks/frontend-verify.md` §8 を正にする。

## webpack キャッシュトラブル対処

新しい `.ts`/`.tsx` を足した後に `TS2307: Cannot find module '...'` が出たら、`docker compose restart frontend` で直る（起動のたびにキャッシュを消す・I024）。
