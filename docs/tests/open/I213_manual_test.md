# I213 手動テスト: Dependabot を点検し、動いて役に立つ形に直す

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | app-1 のワークツリーで、起動前に `docker compose exec -T db psql -U postgres -d learning_app -tAc "select count(*) from users"`（DB 名・ユーザー名は `docker compose config` の `POSTGRES_DB=learning_app`・`POSTGRES_USER=postgres`、テーブル名は `backend/accounts/models.py:142` の `db_table = 'users'` で確認済み） の件数を控え、frontend のコンテナで `touch /app/node_modules/.i213_marker` を作る → 標準の起動コマンド `docker compose up -d --build --renew-anon-volumes` → 同じ件数を読み、`test -e /app/node_modules/.i213_marker` を見る | 全サービスが起動（`docker compose ps` で backend・frontend が healthy）。利用者の件数が起動前と同じ（DB は残る）。目印のファイルが無い（frontend の node_modules は作り直された）。backend のイメージの `FROM` が指紋付きの `python:3.11-slim@sha256:…` で作られている（`docker compose build backend` の出力） | Claude |  | 手元の DB の中身は消さない（件数を読むだけ） |
| 2 | `RATELIMIT_ENABLE=false docker compose --profile e2e run --rm e2e`（手元の `e2e/.env.e2e` のパスワード） | e2e の command の `npx playwright install chromium` がブラウザをダウンロードせずに終わり（イメージと `@playwright/test` が同じ 1.59.1）、Playwright のテストが全件 passed | Claude |  | 終わったら `docker compose up -d backend` で戻す（frontend-verify.md の手順） |
| 3 | PR #374 の CI の `E2E Tests (Playwright)` のログを `gh run view <run> --log` で読む | ジョブが success。「Generate one-time E2E password」の step があり、後の step の `E2E_TEST_PASSWORD:` の値が `***`（伏せ字）。`secrets` から読む行がワークフローに無い | Claude |  |  |
| 4 | 指紋で固定した土台イメージ 6 種類（`python:3.11-slim`・`node:18-alpine`・`nginx:alpine`・`postgres:15-alpine`・`redis:7-alpine`・`mcr.microsoft.com/playwright:v1.59.1-jammy`。Dockerfile 4 か所と compose 4 か所の計 8 か所から重複を除いたもの）を `docker buildx imagetools inspect <タグ@指紋>` で引く | すべてで `Digest:` が書いた指紋と一致し、`linux/amd64` の一覧がある | Claude |  |  |
| 5 | `docs/runbooks/dependency-audit.md` の Dependabot の節を、届いた PR 1 件（#368 `djangorestframework` 3.18.2 → 3.18.3）に当てはめて読む | 「CI が緑か赤か・minor/patch か major か」で、マージ／イシューにする、のどちらかに迷わず決まる。取り込んだあと手元でやることが標準の起動コマンド 1 つ | Claude |  |  |
| 6 | （マージ後）`gh api "repos/osushi0404-dev/study-app-multitenant/actions/workflows/<Dependabot Updates の id>/runs"` でマージ後の実行を読む | 8 つの対象（pip /backend・npm /frontend・npm /e2e・docker /backend・docker /frontend・docker-compose /・github_actions /・pre_commit /）の実行がすべて success。失敗があれば直すイシューを立てる | Claude |  | ユーザーのマージの後に行う |
| 7 | （マージ後）開いている Dependabot の PR を一覧し、新しい設定のまとめ PR に含まれたもの・ignore に当たるものを、理由をコメントして閉じる | #360〜#373 のうち置き換わったものが閉じられ、コメントに置き換え先の PR 番号か ignore の理由がある。major で残るものの一覧を close の報告に書く | Claude |  | 閉じた PR は開き直せる |
| 8 | （マージ後）新しい設定で届いた Dependabot の PR の CI を `gh pr checks <番号>` で読む | `E2E Tests (Playwright)` が pass（パスワード未設定で落ちない） | Claude |  | 新しい PR が来るまで待つ（待つ日数の後になることがある） |

## 画面確認
<!-- frontend/src を変えないので画面確認は不要 -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
| - | - | - | - | - | - | 理由: frontend/src を変えない（Dockerfile の書き方だけ） |

結論: （未実施）
