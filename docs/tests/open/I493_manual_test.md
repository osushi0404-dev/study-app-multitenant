# I493 手動テスト: API のスキーマから画面の型を作る（ダッシュボードの overview から）

手順は `docs/runbooks/frontend-verify.md`（Playwright MCP・幅 1440×900・画像は `.evidence/I493/`）。アカウントは `e2e_user_a`（組織 A・管理者・科目 2 件・答えの記録あり）と `e2e_user_c`（組織 A・一般ユーザー・科目 0 件・答えの記録なし）。I473 の手動テストと同じアカウント。無ければ `seed_e2e` で作り直す（`docs/runbooks/common-commands.md`「ローカル E2E テスト実行手順」）。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | backend・celery のイメージを作り直した後、`e2e_user_a` でログインし、http://localhost:3000/dashboard を開く。続けて `e2e_user_c` でも開く | `e2e_user_a`: 「今日」「連続学習」「累計」の数字が 0 以外（答えの記録の数）で出て、直近 7 日のグラフが出る。エラーの文（「ダッシュボードの応答の形が違います」に当たるトースト・表示）が出ない。`e2e_user_c`: データが無いときの案内が出て、「不正解 100%」の赤い円が出ない。どちらもブラウザのコンソールにエラーが無い | Claude |  | 型の読み込み先を変えたことの退行の確認（I473 の手動テスト No.1 と同じ観点） |
| 2 | 2 つの作ったファイルがコミット済みの状態で、`docker compose exec -T backend python manage.py spectacular --file openapi.yaml --validate --fail-on-warn` と `npm --prefix tools/api-types run generate` を、手順書（`docs/runbooks/common-commands.md`）のとおり流し、`git diff --exit-code -- backend/openapi.yaml frontend/src/types/api/schema.d.ts` を流す | 2 つのコマンドがどちらも終了コード 0。`git diff --exit-code` も終了コード 0（作り直しても中身が変わらない＝手元と CI の作り方が同じ） | Claude |  | 手順書のコマンドがそのまま動くことの確認。未コミットだと新しいファイルが差分に出ないので、コミット後に行う |
| 3 | 起動中の backend に、ログインせずに `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/schema/` と `http://localhost:8000/api/schema/swagger-ui/` を送る | どちらも `404` | Claude |  | スキーマを見せる URL を足していないことの確認（grill-me で「出さない」と確定） |

## 画面確認
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
|  |  | ダッシュボード（/dashboard）を開く | e2e_user_a |  |  |  |
|  |  | ダッシュボード（/dashboard）を開く | e2e_user_c |  |  |  |

結論:
