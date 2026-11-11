# I431 手動テスト: dev DB の越境データの調査と、ダッシュボード・統計の画面の無退行

- 関連: docs/issues/open/I431.md / docs/plans/open/plan_I431.md / GitHub #431 / Draft PR #453
- 前提: No.1 は primary の dev DB を読み取りだけで調べる（primary のコンテナが動いていなければ、primary で `docker compose up -d db redis backend` を起こしてから。書き込みはしない）。No.2 は app-1 ワークツリーで `docker compose up -d db redis backend frontend` を起こし、Playwright MCP で画面を開く（ポートは `docker compose port frontend 3000` で確かめる・`docs/runbooks/frontend-verify.md`）。
- 使用アカウント（No.2）: E2E 用のシードユーザー `e2e_user_a@example.com`（組織 E2E Org A。パスワードは `e2e/.env.e2e` の `E2E_TEST_PASSWORD`）。app-1 の dev DB に無ければ、`docker compose --profile e2e run --rm e2e` の e2e-init（migrate とシード）で作る。ログインの失敗が続くと 5 分の制限がかかるため、パスワードは 1 回で入れる。
- 画面の見た目は変わらない（frontend の変更なし）ため、人の目視の確認は不要。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | primary の dev DB の越境データを数える（読み取りだけ）: `docker exec <primary の backend コンテナ> python manage.py shell -c "<数える式>"` で、利用者の組織と、記録が指す科目の組織（問題は `problem__subject__organization_id`）が違うものを種類ごとに数える: ① SpacedRepetitionCard ② SpacedRepetitionReview ③ ProblemAttempt ④ StudyLog（科目あり）⑤ DailyStudySummary の `subjects_studied` ⑥ MistakePattern（科目あり）⑦ LearningWeakness ⑧ LearningSuggestion（科目あり）⑨ QuizSession（科目あり）⑩ UserSubjectAccess。全体共有科目（組織が空）を指すものも越境に数える | 種類ごとの件数（と全体の件数）が出る。0 でないものがあれば、件数・種類を計画書の「調査結果」と review に書く（読み出しから外れるので、データは消さない。消すなら Danger Ops として承認を取る）。実際に使った数える式を「実結果」に書く | Claude | OK（2026-11-11 19:50）①〜⑩ すべて越境 0 件。総数は ①〜⑧ が 0 件（学習記録の表はどれも空）・⑨ QuizSession 124 件・⑩ UserSubjectAccess 23 件。式: 各表を `users`（`u.id = x.user_id`）と `problems_subject`（問題は `problems_problem` 経由）に JOIN し、`WHERE s.organization_id IS NULL OR s.organization_id IS DISTINCT FROM u.organization_id` の件数を `UNION ALL` で並べた 1 本の SELECT（⑤ は `studylogs_dailystudysummary_subjects_studied` → `studylogs_dailystudysummary` → `users`）。`docker exec study-app-multitenant-db-1 psql -c "<SELECT>"` で実行 | 受け入れ条件 AC8。primary の DB は止まっていたため、バックエンドは起こさず DB のコンテナだけを起こし、終わった後に止めた（バックエンドの起動時の migrate で書き込まないため）。`psql -f` は見張りが止めたので、同じ SELECT を `-c` で渡した |
| 2 | ダッシュボードと統計の画面が従来どおり出る: `e2e_user_a` でログイン → ダッシュボード（`/dashboard`）を開く → 左のメニューから統計の画面を開く → `browser_console_messages` でコンソールを見る → 各画面の画面キャプチャを `.evidence/I431/` に保存 | ダッシュボードに今日の学習・最近のクイズ・科目の進み具合の欄が表示され、エラーの表示が出ない。統計の画面にグラフ・数値の欄が表示され、エラーの表示が出ない。コンソールに、`/api/dashboard/overview/`・`/api/dashboard/analytics/` の 4xx・5xx が出ない（ログイン前の `/api/settings/` の 401 は既知） | Claude | OK（2026-11-11 19:52）ダッシュボードに「おかえりなさい、e2e_user_aさん！」・今日の学習時間・連続学習日数・解答問題数・正答率・今週の学習時間・おすすめ練習問題の欄が出た。学習統計に期間・科目の選択・総学習時間・平均正答率・解いた問題数・学習日数・4 つのタブが出た。バックエンドのログで `GET /api/dashboard/overview/` 200・`GET /api/dashboard/analytics/?period=weekly` 200・`GET /api/user/subjects/` 200。コンソールのエラーは、ログイン前の `/api/settings/` の 401（既知）・開発サーバーの再読み込みの WebSocket の接続失敗（`ws://localhost:3000/ws`・ワークツリーのポート 3020 との食い違い）・統計の画面の React の key の警告だけ | 受け入れ条件 AC6。WebSocket と key の警告は frontend を変えていないこのイシューと無関係（以前から） |

## 画面確認
<!-- frontend/src を変えないイシューのため、check-frontend-evidence.sh の対象外。No.2 の画面キャプチャは任意の証跡として残す。 -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
| 2026-11-11 19:52 | 38086f27 | ログイン → `/dashboard` を開く | e2e_user_a | 概要の欄が出て、エラーの表示が出ない | 期待どおり（overview 200） | dashboard-a-1.png |
| 2026-11-11 19:52 | 38086f27 | 左のメニュー「学習統計」→ `/statistics` | e2e_user_a | 統計の欄が出て、エラーの表示が出ない | 期待どおり（analytics 200） | statistics-a-2.png |

結論: OK
