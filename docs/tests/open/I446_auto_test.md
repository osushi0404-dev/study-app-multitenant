# I446 自動テスト: 問題・科目と本人の記録を扱う全 API の横断の越境テスト

- 関連: docs/issues/open/I446.md / docs/plans/open/plan_I446.md / GitHub #446 / Draft PR #456
- 対象: `backend/core/tests/test_I446_cross_api_tenant_isolation.py`（新規）・`backend/problems/tests/test_I103_cross_org_create.py`（期待値の更新）・`backend/problems/tests/test_I166_quiz_tenant_isolation.py`（TC-09 の期待値の更新）
- 実行コマンド（例）: `docker compose exec -T backend python -m pytest core/tests/test_I446_cross_api_tenant_isolation.py problems/tests/ studylogs/tests/ -q`（app-1 ワークツリーのコンテナ）。全テストは CI（PR #456）が正。

結果:
- backend: 実装前のため未実行
- frontend: 対象外（変更なし）

## 実行記録
| 日時 | コマンド | 終了コード | 結果 |
|---|---|---|---|
| 2026-11-12 | 下調べ（scratchpad の使い捨てのテスト・リポジトリに入れない）をコンテナの `/tmp` で実行 | 0 | 計画書「調査結果」の S1〜S6 と、500 になる経路の一覧を得た |

## TC 一覧

| TC | 内容 | 期待値 | 対応 AC |
|---|---|---|---|
| TC-01 | `test_id_check`: 表の `IdCheck` の全ケース（約 70）。他組織の記録・全体共有の科目と問題（科目・問題が相手のとき）の番号を、存在しない番号（`4469999`・画像は固定の UUID）と比べる | 各ケースで、他組織・全体共有・存在しない番号の応答のステータスが表の値（404・400・200 のどれか。例: `GET api/study/logs/<pk>/` は 404、`POST api/problems/` の `subject` は 400、`GET api/problems/?subject=` は 200）と一致し、本文の番号を `<id>` に伏せた JSON の文字列が存在しない番号のときと一致する。`writes="unchanged"` のケースは、相手の記録の `values()` が呼ぶ前後で同じ。`no_create:<モデル>` のケースは、そのモデルの件数が増えない。`own_status` のあるケース（GET の詳細）は、自分・自組織の記録の番号で 200 になる（正の対照） | AC1 |
| TC-02 | `test_id_check` のうち `same_org=True` のケース（クイズの回・学習記録・目標・カード・復習の記録・提案・弱点）。同じ組織の別の利用者（`user_a2`）の記録の番号でも比べる | 同じ組織の別の利用者の番号の応答が、存在しない番号の応答とステータス・伏せた本文とも一致する（例: `GET api/study/goals/<pk>/` は 404 の `{"error": {"main_message": "リソースが見つかりません", "sub_message": "要求されたデータが存在しません", "details": {}}}`）。書き込みは相手の記録が変わらない | AC2 |
| TC-03 | `test_list_check`（約 35）・`test_own_check`（2）: 番号を受け取らない一覧・集計と、自分の古い記録（他組織の問題への回答を持つクイズの回）を呼ぶ | `ListCheck` はステータスが表の値（すべて 200）。両方とも、本文に `越境I446`・`別人I446` と、他組織・同じ組織の別の利用者・全体共有の記録の番号（`4460001` 以降の値）が 1 つも無い。`xfail` の 9 ケース（`learning_insights`・`update_analytics`・`analyze`・`refresh_analysis`・適応的学習の 4 つの GET と `select_problems` の番号なし）は今は 500 で XFAIL | AC3 |
| TC-04 | `test_route_table_matches_urlconf`: 収集した経路の集合と、表（`ROUTE_TABLE` ∪ `OUT_OF_SCOPE`）のキーの集合を比べる | 2 つの集合が一致する（差分が空）。両方に載る行・理由が空の対象外・確かめ方が空の行が無い | AC4 |
| TC-05 | `test_staff_only_check`: `api/admin/users/` の下（403）と `monitoring/*`・`cache/*`（302）を、組織管理者（`role='admin'`・`is_staff=False`）と一般の利用者で呼ぶ | ステータスが表の値（403 または 302）と一致し、本文に目印が無い | AC4 |
| TC-06 | `test_noorg_org_admin_sees_no_problems`: 組織が空で `role='admin'` の利用者で、問題の一覧と全体共有の問題の詳細を呼ぶ | 一覧が 200 の `[]`。詳細が 404 で、存在しない番号（`4469999`）のときと伏せた本文が同じ。修正前（4-6 の前）は一覧に全体共有の問題が出て、詳細が 200 で RED | AC1 |
| TC-10 | CI の Backend Tests で新しいテストが流れる | PR #456 の CI の `Backend Tests` が success で、ログに `core/tests/test_I446_cross_api_tenant_isolation.py` の結果が出る | AC1 |
| TC-11 | `problems/tests/test_I103_cross_org_create.py`（更新後） | 5 件 passed。他組織の科目での作成は 400 で、存在しない科目と伏せた本文が同じ・問題が作られない。AI 生成 2 経路は 404 `{"error": "指定された科目が見つかりません"}`・問題が作られない | AC1・AC7 |
| TC-12 | `problems/tests/test_I166_quiz_tenant_isolation.py`（TC-09 の更新後） | 13 件 passed。TC-09 で、他組織の科目の既存の回の出題・回答が、存在しない回の番号と同じ 404 の本文になり、回答が保存されない | AC7 |
| TC-20 | RED: 4-2〜4-4 の修正の前に、新しいテストを流す | 終了コード 1。落ちるのは次の 8 ケースだけ: `IdCheck` の `POST api/problems/`（subject）・`PUT`／`PATCH api/problems/<pk>/`（subject）・`POST api/problems/generate_ai/`・`POST api/problems/generate_adaptive/`、`ListCheck` の `GET api/quiz/`、`OwnCheck` の `GET api/quiz/<pk>/`・`POST api/quiz/<pk>/end/`（ほかに TC-06 の 1 件）。xfail の 9 ケースは XFAIL | AC1・AC3 |
| TC-21 | FG1（表の漏れ）: (a) `backend/core/urls.py` に確かめ用の経路 `path('api/i446-probe/', health)` を一時的に足して TC-04 を流す (b) 表から `GET api/study/goals/` の行を一時的に消して TC-04 を流す。どちらも流した後に Edit で元の記述に戻す（`git checkout`・`git restore` は使わない・コミットしない） | (a)(b) とも終了コード 1。(a) は「表に無い経路: GET api/i446-probe/」、(b) は「表に無い経路: GET api/study/goals/」を出して落ちる | AC5 |
| TC-22 | FG2（組織の絞り込みを外す）: (a) `ProblemViewSet.get_queryset` の `subject__organization=…` を一時的に消して TC-01 を流す (b) `SpacedRepetitionCardViewSet.get_queryset` の `scope_to_user_org(...)` を一時的に外して TC-03 を流す。流した後に Edit で元の記述に戻す（`git checkout`・`git restore` は使わない） | (a)(b) とも終了コード 1。(a) は `IdCheck` の `GET api/problems/<pk>/` などが（他組織の問題が 200 で返り）落ちる。(b) は `ListCheck` の `GET api/study/sr-cards/` が（自分の古いカードの他組織の問題文 `越境I446` が出て）落ちる | AC6 |
| TC-23 | FG3（本人の絞り込みを外す）: `StudyGoalViewSet.get_queryset` を一時的に `StudyGoal.objects.all()` にして TC-01・TC-02 を流す。流した後に Edit で元の記述に戻す（`git checkout`・`git restore` は使わない） | 終了コード 1。`IdCheck` の `api/study/goals/<pk>/` の各メソッドが、同じ組織の別の利用者・他組織の目標が 200・204 で返って落ちる | AC6 |
| TC-24 | 修正後に、新しいテスト・`problems/tests/`・`studylogs/tests/` を流す | 終了コード 0（xfail の 9 ケースは XFAIL・XPASS が無い） | AC1〜AC4・AC7 |
| TC-25 | commit 時の pre-commit（ruff・bandit を含む） | すべて Passed | — |
| TC-30 | CI（PR #456）の全ジョブ | すべて success | AC7 |

## fixture 方針
- 計画書 4-1 (3) のとおり。乱数に頼らない。他組織・同じ組織の別の利用者・全体共有の記録は主キーを `4460001` 以降で明示して作る。存在しない番号は `4469999`
- 目印の文字: 他組織・全体共有は `越境I446`、同じ組織の別の利用者は `別人I446`
- `APIClient(raise_request_exception=False)`。DRF のビューは `force_authenticate`、Django の View は `force_login` も行う
- キャッシュは各ケースの前後で消す
