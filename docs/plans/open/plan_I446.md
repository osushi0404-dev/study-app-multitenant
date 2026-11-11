# I446 計画書: 問題・科目と本人の記録を扱う全 API の横断の越境テスト

## 基本情報
- **計画書ID**: plan_I446
- **関連イシュー**: #446
- **Draft PR**: #456
- **作成根拠資料**: docs/issues/open/I446.md（GitHub #446 の本文の写し・2026-11-12）
- **実装後評価**: docs/reviews/open/I446_review.md
- **作成日**: 2026-11-12

## 1. 背景/目的
- I166 でクイズ、I431（#431・PR #453）で学習記録・ダッシュボードの組織の境界を塞いだ。どちらも、境界の不備を見つけるのは設計確認と計画での洗い出しに頼っていて、新しい API が増えたときに組織や本人の絞り込みを忘れても、CI では気づけない。
- 目的: アプリの全経路を表に載せた横断のテストを 1 本作り、CI で毎回流す。
  - 他組織の番号、本人の記録では同じ組織の別の利用者の番号も送り、存在しない番号と同じ応答で断られることを確かめる
  - 番号を受け取らない一覧・集計では、他組織・別の利用者の中身が出ないことを確かめる
  - 表に無い経路が増えたら、テストが落ちるようにする
- テストで見つかった越境は、1 経路の絞り込みの追加で済むものをこのイシューで直す（イシューのスコープ「含む」）。

## 2. 受け入れ条件（イシューの AC と対応）
- AC1: 問題・科目と本人の記録を扱うすべての API（クイズを含む）について、他組織の ID を送ると、存在しない ID と同一の応答（ステータスと、ID・URL を伏せた本文）になることを確かめる横断のテストがあり、CI で毎回実行される → TC-01・TC-02・TC-10
- AC2: 本人の記録を扱う API では、同じ組織の別の利用者の ID を送っても、存在しない ID と同一の応答になることを確かめる → TC-02
- AC3: 番号を受け取らない一覧・集計の API では、他組織・同じ組織の別の利用者のデータを置いた状態で、応答に問題文・解説・選択肢・科目名・ID が出てこないことを確かめる → TC-03
- AC4: アプリの全経路（メソッド別）が、テストの中の表に「確かめる」か「対象外（理由）」として載っている。今は壊れている経路は #452 の番号付きの `xfail(strict=True)`。`admin/users/` の下は、組織管理者と一般の利用者が 403 で断られることを確かめる → TC-04・TC-05
- AC5: 表に載っていない新しい経路を足すと、テストが落ちる（失敗注入で確かめる。確かめ用の経路はコミットに残さない）→ TC-21（FG1）
- AC6: 組織の絞り込み・本人の絞り込みをわざと外すと、テストが落ちる（それぞれ失敗注入で RED）→ TC-22（FG2）・TC-23（FG3）
- AC7: 既存のテストがすべて pass する → TC-30（CI）

## 調査結果

### 環境前提
- app-1 ワークツリーのコンテナ（compose のプロジェクト名 `app-1`・`/app` はこのワークツリーの `backend`）が動いている（`docker compose ps` で backend・db・redis が Up）。pytest はコンテナの中で流せる（下の下調べで実証）。
- 基準: このブランチの元の develop（fba609bb）の CI は success（2026-11-11 15:15・`gh run list --branch develop`）。手元で全テストは流し直さない（CI が正）。
- CI の Backend Tests は `backend` で `pytest` を流す（`.github/workflows/ci.yml` の `backend-test`・`pytest.ini` の `testpaths = .`）。新しいテストファイルは追加の設定なしで流れる → `ci.yml` は変えない。

### 経路の実数（2026-11-12・`get_resolver()` で実測）
`api/` の下が 79 本（ルーターの形式の接尾辞〔`\.(?P<format>…)`〕の重複を除く）、メソッド別に約 120 通り。`api/` の外に `health/`・`monitoring/*`・`cache/*`（`core/monitoring_urls.py`・運用者〔`is_staff`〕専用）と Django の管理画面 `admin/` がある。

### 下調べ（スパイク）の結果
scratchpad に置いた使い捨てのテスト（リポジトリに入れない）をコンテナの `/tmp` で流し、他組織・同じ組織の別の利用者・存在しない番号の応答を並べた（2026-11-12）。

**番号を受け取る経路（他組織・同じ組織の別の利用者・存在しない番号）**: 次の 4 つ以外は、すでにステータスも本文も同じだった（科目・問題の詳細と更新・削除、画像の追加・削除、クイズの回の詳細・終了・出題・回答、クイズの開始の科目、回答の問題、学習記録・目標・カード・復習の記録の詳細と更新・削除、カード作成の問題、復習の提出のカード、提案の既読・評価、弱点の解決、一覧の絞り込みの科目・カード、適応的学習の科目、登録の科目）。

| No | 経路 | 他組織の科目 | 存在しない科目 | 漏れるもの |
|---|---|---|---|---|
| S1 | `POST /api/problems/`（科目） | 403「この操作を実行する権限がありません」 | 400「主キー "…" は不正です」 | 他組織に、その番号の科目があること（存在の確認） |
| S2 | `PUT`・`PATCH /api/problems/<自組織の問題>/`（科目の付け替え） | 400「他組織の科目には変更できません」 | 400「主キー "…" は不正です」 | 同上 |
| S3 | `POST /api/problems/generate_ai/`（`subject_id`） | 403「他組織の科目には問題を作成できません」 | 404「指定された科目が見つかりません」 | 同上 |
| S4 | `POST /api/problems/generate_adaptive/`（`subject_id`） | 403（同上） | 404（同上） | 同上 |

**番号を受け取らない一覧・集計（他組織・同じ組織の別の利用者のデータと、自分の古い記録が他組織の科目・問題を指すデータを置いて呼んだ）**:

| No | 経路 | 結果 |
|---|---|---|
| S5 | `GET /api/quiz/` | 自分の古いクイズの回が他組織の科目を指していると、`subject_name` に他組織の科目名が出る |
| S6 | `GET /api/quiz/<自分の回>/`・`POST …/end/` | 自分の回に他組織の問題への古い回答（I166 より前のデータ。I166 の TC-12 と同じ形）があると、`answers[].problem` に他組織の問題文・解説・選択肢が出る（`QuizSessionDetailSerializer` が `ProblemSerializer` を入れ子で返す。コードの読解で確定・TC-03 の RED で実測する） |
| — | ほかの一覧・集計 | 漏れなし。ただし次は 500（漏れの確認にならない）: `learning_insights`（`LearningInsightsSerializer` の `period_days` の KeyError）・`mistake-analysis/analyze`・`refresh_analysis`・`adaptive-learning` の 4 つの GET と `select_problems`・`spaced-repetition/update_analytics`（difficulty の型・#452） |
| — | `GET /api/dashboard/analytics/` | 日々のまとめ（`DailyStudySummary`）に解いた問題が 0 件の日があると 500（`dashboard/views.py:252-254` の `F('total_problems_correct') * 100.0 / F('total_problems_attempted')` が 0 で割る）。組織の境界とは関係のない既存の不具合。統計の画面（`frontend/src/pages/Statistics.tsx:72`）が呼ぶので、利用者に見える |

### 原因の概要
組織の判定がビューやシリアライザごとの手書きで、経路によって「他組織だから断る（403・専用の文言）」と「存在しない（400・404）」が分かれていた。また、クイズの回は「本人のもの」だけで絞っていて、その中身（科目・回答した問題）が組織の中かを見ていなかった。

### 詳細な原因分析
1. S1・S2: `ProblemSerializer.subject`（`backend/problems/serializers.py:83-104`）は ModelSerializer が作る `PrimaryKeyRelatedField(queryset=Subject.objects.all())`。全組織の科目を受け付け、その後で `ProblemViewSet.perform_create`（`backend/problems/views.py:256-260`・I103）が 403、`perform_update`（同 309-312・SEC-1）が専用の文言の 400 を返す。存在しない科目はシリアライザが先に断るので、応答が分かれる。
2. S3・S4: `generate_ai`（`views.py:384-396`）・`generate_adaptive`（同 514-525）は `Subject.objects.get(id=subject_id)` で全組織から探し、見つかってから組織を比べて 403 を返す。
3. S5・S6: `QuizSessionViewSet.get_queryset`（`views.py:819-820`）は `QuizSession.objects.filter(user=…)` だけ。I166 は新しく他組織の科目・問題を指す回・回答を作れないようにしたが、既にあるもの（I166 より前のデータ）を読み出しから外していない。I431 の扱いの基準 2（他組織の科目・問題の中身を返しうる読み出しは、それを指す記録を外す）がクイズの回には当てはまっていなかった。
4. なぜ起きたか: 「存在しない番号と同じ応答」という揃え方は I166 から始まり、I103（問題の作成）はその前の「他組織なら 403」の書き方のままだった。全経路を同じ物差しで見る仕組みが無いので、ずれが残った（このイシューの根本原因と同じ）。

## 3. 影響範囲
| 区分 | 内容 |
|---|---|
| Backend | 新規テスト 1 本・`problems`（serializers・views）・既存テストの期待値の更新 2 本 |
| Frontend | なし（問題の管理画面は、他組織の科目を送らない。エラーの文言の違いは他組織の番号を送ったときだけ） |
| DB | なし（スキーマ・データとも変えない） |
| Config/Infra | なし（`ci.yml` は変えない） |

振る舞いの変化（利用者から見える違い）:
- 問題の作成・科目の付け替え・AI 生成で他組織の科目を指定したとき、403 や専用の文言ではなく、存在しない科目と同じ 400・404 になる（自組織の科目での操作は変わらない）
- 自分のクイズの回のうち、他組織の科目を指す古い回は、一覧・詳細・終了・出題・回答で「存在しない」扱い（404）になる。自分の回の中の、他組織の問題への古い回答は、詳細・終了の応答の `answers` に出ない（回の件数・正解数の数字は変えない）

## 4. 変更点一覧

### 修正アプローチ
横断のテスト（表・経路の収集・3 種類の確かめ方）を先に作り、今の作りで落ちる箇所（S1〜S6）を RED として記録する。その後、S1〜S6 をそれぞれ 1 か所の絞り込みで直し、既存のテストの期待値をこのイシューの物差し（存在しない番号と同じ応答）に合わせる。

### 4-1. 横断のテスト（新規）`backend/core/tests/test_I446_cross_api_tenant_isolation.py`
**修正方針**: アプリの全経路を自動で集め、テストの中の表と突き合わせる。表の各行に確かめ方を書き、行ごとに 1 つの pytest のケースにする（ケースごとに DB の巻き戻しが入るので、ある経路の 500 が別の経路に連鎖しない。下調べで、1 つのテストの中で続けて呼ぶと DB のエラーが連鎖することを確かめた）。

置き場所を `backend/core/tests/` にする理由: URL の定義（`core/urls.py`）が core にあり、特定のアプリに属さない横断のテストのため。

**(1) 経路の収集** `_collect_routes()`:
- `django.urls.get_resolver().url_patterns` を再帰でたどり、パターンの文字列をつなぐ
- 正規表現の形（`^logs/(?P<pk>[^/.]+)/$`）は `^`・`$` を外し、名前付きの部分を `<名前>` に置き換えて、`api/study/logs/<pk>/` の形にそろえる。`path()` の形（`auth/register/<slug:organization_slug>/`）はそのまま
- 除くもの: `admin/` で始まるもの（Django の管理画面。運用者用でアプリの API ではない）、`(?P<format>` を含むもの（ルーターの形式の接尾辞。同じビューの別名で、接尾辞の無い経路が必ずある）、`settings.DEBUG` のときだけ足される `media/`（テストでは足されない）
- メソッドを決める: ViewSet は `callback.actions` のキーのうち、ビューの `http_method_names` に含まれるもの（`QuizSessionViewSet` の put・patch・delete は除かれる）。APIView・`@api_view`・Django の View は、クラスに定義のある `get`・`post`・`put`・`patch`・`delete`
- 同じ経路が 2 回出たら（`health/` は `core/urls.py` と `monitoring_urls.py` の両方にある）、先に当たるもの（Django が実際に使う方）だけを残す
- 戻り値: `{"GET api/study/logs/<pk>/", …}` の集合（`"<メソッド> <経路>"`）

**(2) 表** `ROUTE_TABLE: dict[str, list[Check]]`（キーは上の `"<メソッド> <経路>"`）。値は確かめ方の並び。`OUT_OF_SCOPE` は `dict[str, str]`（キー → 対象外の理由）。確かめ方は次の 5 種類（dataclass）:

| 種類 | 何を確かめるか | 期待値 |
|---|---|---|
| `IdCheck` | 番号を URL・本文・クエリのどこかに入れて呼び、「他組織の記録」「（本人の記録なら）同じ組織の別の利用者の記録」「（科目・問題なら）全体共有〔組織が空〕の科目・問題」を、存在しない番号と比べる | 3 つの応答のステータスが表に書いた値（例: 404）と一致し、本文の中の番号を `<id>` に伏せた文字列が、存在しない番号のときと一致する。書き込みの経路は、相手の記録が変わっていない（呼ぶ前後で `Model.objects.filter(pk=…).values()` が同じ）。作成の経路は、対象の表の件数が増えていない |
| `ListCheck` | 番号を入れずに呼ぶ | ステータスが表に書いた値（例: 200）で、本文に「他組織・別の利用者の目印」（下の (3)）が 1 つも無い |
| `OwnCheck` | 自分の記録のうち、他組織の科目・問題を指す古いデータを持つものの番号で呼ぶ（クイズの回） | 本文に目印が無い（ステータスは問わない。隠すか、中身を伏せるかのどちらでもよい） |
| `StaffOnlyCheck` | 運用者専用の経路を、組織管理者（`role='admin'`・`is_staff=False`）と一般の利用者で呼ぶ | 表に書いた値（DRF の `IsAdminUser` は 403、Django の `staff_member_required` は 302）。本文に目印が無い |
| （`OUT_OF_SCOPE`） | 確かめない | 理由を必ず書く（空文字は表の検査で落とす） |

`IdCheck` の項目: `actor`（`"user"`・`"org_admin"`・`"anon"`）、`where`（`"path"`・`"body"`・`"query"`）、`param`（入れる名前。path は URL の `<pk>` などの名前）、`target`（相手の記録の種類: `"subject"`・`"problem"`・`"session"`・`"log"`・`"goal"`・`"card"`・`"review"`・`"suggestion"`・`"weakness"`・`"asset"`）、`status`（期待するステータス）、`same_org`（同じ組織の別の利用者の記録も試すか・本人の記録だけ True）、`extra`（ほかの必須の入力。例: 画像の削除の自分の問題の番号）、`fmt`（`"json"`・`"multipart"`）、`writes`（`None`・`"unchanged"`・`"no_create:<モデル名>"`）、`list_param`（本文の番号を `[番号]` で送るか・登録の `subject_ids`）、`xfail`（理由の文字列・空なら無し）。

**表の中身**（全行。メソッドはこの表の「メソッド」列。`<pk>` 等は URL の番号）:

| 経路 | メソッド | 確かめ方 | 期待値・理由 |
|---|---|---|---|
| `health/` | GET | 対象外 | DB の接続の確認だけで、データを返さない |
| `monitoring/status/`・`errors/`・`performance/`・`activity/`・`alerts/`・`cache/stats/` | GET | StaffOnly | 302（`staff_member_required`）。運用者専用 |
| `cache/clear/` | POST | StaffOnly | 302（同上） |
| `api/`・`api/study/`・`api/organizations/` | GET | 対象外 | ルーターの入口で、経路の一覧だけを返す |
| `api/auth/login/`・`logout/`・`refresh/`・`verify-email/`・`password-reset/`・`password-reset-confirm/`・`validate-field/`・`change-password/` | POST | 対象外 | 認証・本人の資格情報だけを扱い、問題・科目・記録の番号を受け取らない |
| `api/auth/register/`・`api/auth/register/<organization_slug>/` | POST | IdCheck（anon・body・`subject_ids`・list_param・subject・400・`no_create:User`）。slug 付きは自組織 A の slug、slug 無しは個人用の組織 | 他組織・全体共有・存在しない科目が同じ 400 で、利用者が作られない |
| `api/organizations/validate-slug/<slug>/` | GET | 対象外 | 登録画面のために、slug から組織名を返す仕様（grill-me の自己解決） |
| `api/auth/me/` | GET | List（user・200） | |
| `api/auth/me/` | PUT・PATCH | 対象外 | 本人の情報の書き換え。組織・役割は読み取り専用（`UserSerializer.read_only_fields`）で番号を受け取らない |
| `api/settings/` | GET | List（user・200） | |
| `api/settings/` | PUT・PATCH | 対象外 | 本人の設定の書き換え。番号を受け取らない |
| `api/streak/` | GET | List（user・200） | |
| `api/admin/users/`・`statistics/`・`<pk>/`・`<pk>/reset_password/`・`<pk>/toggle_active/` | 各メソッド（GET・POST・PUT・PATCH・DELETE） | StaffOnly | 403（`IsAdminUser`）。全組織の利用者を扱う運用者用の仕様（grill-me の自己解決） |
| `api/subjects/`・`api/organizations/subjects/` | GET | List（user・200） | |
| 同上 | POST | 対象外 | 番号を受け取らない。組織は利用者の組織に固定（`SubjectViewSet.perform_create`） |
| `api/subjects/public/`・`api/organizations/subjects/public/` | GET | 対象外 | 登録画面用。slug を知る人に科目名だけを出す仕様（grill-me の自己解決） |
| `api/subjects/<pk>/`・`api/organizations/subjects/<pk>/` | GET | IdCheck（user・path・pk・subject・404） | |
| 同上 | PUT・PATCH・DELETE | IdCheck（org_admin・path・pk・subject・404・unchanged） | |
| `api/problems/` | GET | List（org_admin・200）＋ IdCheck（org_admin・query・`subject`・subject・200） | 絞り込みの科目が他組織でも空の一覧 |
| `api/problems/` | POST | IdCheck（org_admin・body・`subject`・subject・400・multipart・`no_create:Problem`） | **S1**（修正前は 403） |
| `api/problems/generate_ai/` | POST | IdCheck（org_admin・body・`subject_id`・subject・404・multipart・`no_create:Problem`・extra `save_to_db=false`） | **S3** |
| `api/problems/generate_adaptive/` | POST | IdCheck（org_admin・body・`subject_id`・subject・404・multipart・`no_create:Problem`） | **S4** |
| `api/problems/<pk>/` | GET・DELETE | IdCheck（org_admin・path・pk・problem・404・DELETE は unchanged） | |
| `api/problems/<pk>/` | PUT・PATCH | IdCheck（同上・unchanged）＋ IdCheck（org_admin・body・`subject`・subject・400・multipart・extra 自組織の問題の pk・unchanged〔自組織の問題の科目が変わらない〕） | **S2** |
| `api/problems/<pk>/images/upload/` | POST | IdCheck（org_admin・path・pk・problem・404・multipart） | |
| `api/problems/<pk>/images/delete/<asset_id>/` | DELETE | IdCheck（org_admin・path・pk・problem・404・extra 相手の組織の画像）＋ IdCheck（org_admin・path・asset_id・asset・404・extra 自組織の問題・unchanged） | |
| `api/quiz/` | GET | List（user・200） | **S5** |
| `api/quiz/` | POST | IdCheck（user・body・`subject`・subject・400・`no_create:QuizSession`） | |
| `api/quiz/<pk>/` | GET | IdCheck（user・path・pk・session・404・same_org）＋ Own（自分の回〔科目なし〕に他組織の問題への古い回答） | **S6** |
| `api/quiz/<pk>/end/` | POST | IdCheck（同上・unchanged）＋ Own（同上） | **S6** |
| `api/quiz/<pk>/next_problem/` | GET | IdCheck（user・path・pk・session・404・same_org） | |
| `api/quiz/<pk>/submit_answer/` | POST | IdCheck（user・path・pk・session・404・same_org・unchanged）＋ IdCheck（user・body・`problem_id`・problem・404・extra 自分の回〔科目なし〕・`no_create:QuizAnswer`） | |
| `api/user/subjects/` | GET | List（user・200） | |
| `api/study/logs/` | GET | List（user・200） | |
| `api/study/logs/` | POST | IdCheck（user・body・`subject`・subject・400・`no_create:StudyLog`） | |
| `api/study/logs/<pk>/` | GET・DELETE | IdCheck（user・path・pk・log・404・same_org・DELETE は unchanged） | |
| `api/study/logs/<pk>/` | PUT・PATCH | IdCheck（同上・unchanged）＋ IdCheck（user・body・`subject`・subject・400・extra 自分の記録の pk・unchanged） | |
| `api/study/logs/<pk>/end/` | POST | IdCheck（user・path・pk・log・404・same_org・unchanged） | |
| `api/study/statistics/overview/`・`by_subject/`・`daily_summary/` | GET | List（user・200） | |
| `api/study/goals/` | GET | List（user・200） | |
| `api/study/goals/` | POST | 対象外 | 番号を受け取らない（目標の種類と値だけ）。持ち主は本人に固定（`perform_create`） |
| `api/study/goals/update_progress/` | POST | List（user・200） | |
| `api/study/goals/<pk>/` | GET・PUT・PATCH・DELETE | IdCheck（user・path・pk・goal・404・same_org・GET 以外は unchanged） | |
| `api/study/spaced-repetition/analytics/`・`daily_plan/`・`due_cards/`・`user_statistics/` | GET | List（user・200） | |
| `api/study/spaced-repetition/learning_insights/` | GET | List（user・200・xfail） | xfail: `LearningInsightsSerializer` の `period_days` の KeyError で 500（#452 に同梱する・retro） |
| `api/study/spaced-repetition/update_analytics/` | POST | List（user・200・xfail） | xfail: difficulty の型で 500（#452） |
| `api/study/spaced-repetition/create_card/` | POST | IdCheck（user・body・`problem_id`・problem・404・`no_create:SpacedRepetitionCard`） | |
| `api/study/spaced-repetition/submit_review/` | POST | IdCheck（user・body・`card_id`・card・404・same_org・unchanged・extra `quality_score=4`・`response_time_seconds=10`） | |
| `api/study/sr-cards/` | GET | List（user・200）＋ IdCheck（user・query・`subject_id`・subject・200） | |
| `api/study/sr-cards/<pk>/` | GET | IdCheck（user・path・pk・card・404・same_org） | |
| `api/study/sr-reviews/` | GET | List（user・200）＋ IdCheck（user・query・`card_id`・card・200・same_org） | |
| `api/study/sr-reviews/<pk>/` | GET | IdCheck（user・path・pk・review・404・same_org） | |
| `api/study/mistake-analysis/analyze/` | GET | List（user・200・xfail） | xfail: difficulty の型で 500（#452） |
| `api/study/mistake-analysis/refresh_analysis/` | POST | List（user・200・xfail） | xfail: 同上（#452） |
| `api/study/mistake-analysis/improvement_trends/` | GET | List（user・200） | |
| `api/study/mistake-analysis/patterns/`・`weaknesses/` | GET | List（user・200）＋ IdCheck（user・query・`subject_id`・subject・200） | |
| `api/study/mistake-analysis/suggestions/` | GET | List（user・200） | |
| `api/study/mistake-analysis/mark_suggestion_read/` | POST | IdCheck（user・body・`suggestion_id`・suggestion・404・same_org・unchanged） | |
| `api/study/mistake-analysis/provide_feedback/` | POST | IdCheck（同上・extra `effectiveness_rating=3`） | |
| `api/study/mistake-analysis/resolve_weakness/` | POST | IdCheck（user・body・`weakness_id`・weakness・404・same_org・unchanged） | |
| `api/study/adaptive-learning/proficiency_analysis/`・`personalized_recommendation/`・`learning_path/`・`difficulty_distribution/` | GET | IdCheck（user・query・`subject_id`・subject・404）＋ List（user・200・xfail） | List の xfail: difficulty の型で 500（#452） |
| `api/study/adaptive-learning/select_problems/` | POST | IdCheck（user・body・`subject_id`・subject・404）＋ List（user・200・xfail） | 同上 |
| `api/dashboard/overview/`・`analytics/`・`recommendations/` | GET | List（user・200） | |

（`api/quiz/<pk>/` の PUT・PATCH・DELETE は `QuizSessionViewSet.http_method_names` で無効のため、収集で除かれ表にも載せない）

**(3) 下準備（fixture）** `world`（関数ごと）:
- 組織 A・B（`OrganizationCategory` を 1 つ）。A に一般の利用者 `user_a`・同じ組織の別の利用者 `user_a2`・組織管理者 `admin_a`（`role='admin'`・`is_staff=False`）、B に `user_b`。個人用の組織（`type='personal'`・slug `personal`。登録の slug 無しの経路が使う）
- 科目: `subject_a`（A）・`subject_b`（B）・`subject_shared`（組織が空）。問題: 各科目に 1 つ（選択肢 2 つ）
- 記録の 3 組: `user_b`（他組織）・`user_a2`（同じ組織の別の利用者）・`user_a`（自分）それぞれに、クイズの回・学習記録・目標・カード・復習の記録・提案・弱点・画像（`MediaAsset`＋`ProblemMediaAsset`）を作る。`user_b` は B の科目・問題、`user_a2`・`user_a` は A の科目・問題を指す
- 自分の古いデータ（他組織を指す。S5・S6 と一覧の確かめ用）: `user_a` の、B の科目を指すクイズの回（終了済み）、科目なしの回の中の B の問題への回答、B の科目の学習記録、B の問題のカード、B の科目の登録（`UserSubjectAccess`）、日々のまとめの `subjects_studied` に B の科目
- 日々のまとめは解いた問題数を 1 以上にする（`dashboard/analytics` の 0 で割る不具合は境界と関係ないため、このテストでは踏まない。不具合は別に起票する・9 章）
- **番号は区別しやすい値を明示する**: 他組織・同じ組織の別の利用者・全体共有の記録の主キーを `4460001` から順に明示して作る（存在しない番号は `4469999`）。本文の中の番号を伏せるときに、日時やほかの数字を誤って伏せないため。画像（UUID）は固定の UUID を使う
- **目印**: 他組織・全体共有の科目名・問題文・解説・選択肢の文字に `越境I446`、同じ組織の別の利用者の記録の文字（学習記録のメモ・提案の題・弱点の概念名）に `別人I446` を入れる。`ListCheck`・`OwnCheck` は、本文に `越境I446`・`別人I446` と、他組織・別の利用者・全体共有の記録の番号（`4460001` 以降の値）が 1 つも無いことを確かめる
- キャッシュは各ケースの前後で消す（I431 のテストと同じ `_clear_caches`）
- 呼び出し: `APIClient(raise_request_exception=False)`（500 を例外ではなく応答として受け取る）。DRF のビューは `force_authenticate`、Django の View（`monitoring/*`・`cache/*`）は `force_login` も行う

**(4) テストの関数**:
- `test_route_table_matches_urlconf`: `_collect_routes()` の集合 ＝ `ROUTE_TABLE` のキー ∪ `OUT_OF_SCOPE` のキー。表に無い経路（新しい経路）と、表にあって実在しない経路（古い行）の両方を、差分を出して落とす。両方に載っている行・空の理由・空の確かめ方の並びも落とす
- `test_id_check`（`ROUTE_TABLE` の `IdCheck` で parametrize・id は `"<メソッド> <経路> <param>"`）
- `test_list_check`（`ListCheck` で parametrize）
- `test_own_check`（`OwnCheck` で parametrize）
- `test_staff_only_check`（`StaffOnlyCheck` で parametrize）
- xfail は `pytest.param(…, marks=pytest.mark.xfail(strict=True, reason="#452 …"))`。#452 で直ると XPASS で落ちるので、印の外し忘れに気づける

### 4-2. S1・S2 の修正 `backend/problems/serializers.py`
**修正方針**: 問題の科目の入力を、クイズ・学習記録と同じ `OrgSubjectField`（利用者の組織の科目だけを受け付ける・context に request が無ければ何も受け付けない）にする。他組織・全体共有の科目は、存在しない科目と同じ 400「主キー "…" は不正です - データが存在しません。」になる。
- `OrgSubjectField`（今は 307-318 行目）を `ProblemSerializer` より前（`ProblemFieldConversionMixin` の前）に移す。説明の「クイズのセッションと学習記録の科目で使う」を「クイズのセッション・学習記録・問題の科目で使う」に直す
- `ProblemSerializer` に `subject = OrgSubjectField()` を足す（`required` は既定の True のまま。部分更新〔PATCH〕では DRF が必須を外す）。出力（`to_representation`）は科目の番号のままで変わらない。`ProblemAdminSerializer` は継承で同じになる
- 出力だけで使う箇所（`studylogs/serializers.py:115`・`problems/serializers.py` の `QuizAnswerDetailSerializer`・`views.py` の AI 生成の応答）は、書き込みをしないので影響しない
- 調査（2026-11-12）: `grep -rn -E "Problem(Admin)?Serializer\(data|ProblemSerializer\(.*context" backend --include=*.py` は 0 件。`ProblemSerializer`・`ProblemAdminSerializer` を書き込みに使うのは `ProblemViewSet`（`get_serializer` が context に request を入れる）だけ。AI 生成の保存（`_save_ai_problem_to_db`）・`ProblemService` はシリアライザを通さずモデルを直接作る。`OrgSubjectField` の他の使用は `QuizSessionSerializer`・`studylogs/serializers.py` の 2 つ（既存）
- 画面の依存の調査（2026-11-12）: `frontend/src` を「他組織の科目には」「generate_ai」「403」で検索した。問題の管理・AI 生成の画面（`components/AIQuestionGenerator.tsx:150`）はエラー時に `error.response?.data?.error` をそのまま出すだけで、403 や文言で分岐しない。共通の処理（`services/api.ts:180`・`utils/apiResponseUtils.ts:87`）はステータスごとの一般の文言を出すだけ。科目は自組織の科目の一覧から選ぶので、通常の操作では変化が見えない
- 別件の発見（範囲外）: `AIQuestionGenerator.tsx:121・131` は JSON で送るが、`ProblemViewSet.parser_classes` は multipart・form だけで、画面からの AI 生成は今も 415 になる（下調べで JSON は 415 を確認）。境界と関係ないので直さず、retro で扱う（9 章）

```python
class ProblemSerializer(ProblemFieldConversionMixin, serializers.ModelSerializer):
    # 他組織・全体共有の科目は、存在しない科目と同じ 400 で断る（I446）
    subject = OrgSubjectField()
    choices = ChoiceSerializer(many=True, required=False)
    ...
```

### 4-3. S1〜S4 の修正 `backend/problems/views.py`
**修正方針**: AI 生成の 2 経路で、科目を利用者の組織の科目の中から探す。他組織・全体共有の科目は、存在しない科目と同じ 404「指定された科目が見つかりません」になる。作成・更新の組織の確かめ（I103・SEC-1）は、4-2 でシリアライザが先に断るので届かなくなるが、多層防御として残し、説明を直す。
- `generate_ai`（384-396 行目）・`generate_adaptive`（514-525 行目）:
  ```python
  try:
      # 他組織・全体共有の科目は、存在しない科目と同じ 404（I446）
      subject = available_subjects(request.user).get(id=subject_id)
  except Subject.DoesNotExist:
      return Response({'error': '指定された科目が見つかりません'}, status=status.HTTP_404_NOT_FOUND)
  ```
  直後の「`subject.organization_id != request.user.organization_id` なら 403」の分岐は消す（`available_subjects` が組織で絞るので常に偽）
- `perform_create`（256-260 行目）・`perform_update`（309-312 行目）の組織の確かめ: コードは残し、コメントを「シリアライザ（`OrgSubjectField`）が先に存在しない科目と同じ 400 で断る。ここは多層防御」に直す
- import に `from .services.tenant_scope import available_subjects, scope_to_user_org` を足す（`QuizAnswer`・`Prefetch` も 4-4 で使う）

### 4-4. S5・S6 の修正 `backend/problems/views.py` `QuizSessionViewSet.get_queryset`（819-820 行目）
**修正方針**: I431 の扱いの基準 2 をクイズの回に当てはめる。他組織・全体共有の科目を指す回は存在しないものとして扱い（科目なしの回は残す）、回の中の回答は組織の問題のものだけを読み込む。
```python
def get_queryset(self):
    user = self.request.user
    # 他組織・全体共有の科目の回は存在しないものとして扱い、回答は組織の問題のものだけを出す（I446）
    answers = scope_to_user_org(QuizAnswer.objects.all(), user, subject_path='problem__subject')
    return scope_to_user_org(
        QuizSession.objects.filter(user=user), user, subject_path='subject', allow_null=True,
    ).prefetch_related(Prefetch('answers', queryset=answers))
```
- 影響の確認（コードの読解）: `submit_answer` の「回答済みか」（`session.answers.filter(...)`）と `QuizService` の `session.answers.values_list(...)`・`order_by(...)` は新しい問い合わせを作るので、先読み（prefetch）の絞り込みの影響を受けない。回の件数・正解数（`completed_problems`・`correct_answers`）は欄の値なので変わらない。`end` の応答（`QuizSessionDetailSerializer(session)`）は先読みした回答を使う

### 権限のクラス（変えない）
- `ProblemViewSet`: `[permissions.IsAuthenticated, IsOrgAdmin]`（全アクション）
- `QuizSessionViewSet`: `[permissions.IsAuthenticated]`
- `SubjectViewSet`: 参照は `[permissions.IsAuthenticated]`、作成・更新・削除は `[permissions.IsAuthenticated, IsOrgAdmin]`、`public` は `[permissions.AllowAny]`
- `AdminUserViewSet`: `[IsAdminUser]`。`core/views.py` の監視・キャッシュの View: `login_required`＋`staff_member_required`

### エラー応答（修正後）
| 経路 | 他組織・全体共有・存在しない科目 | 本文 |
|---|---|---|
| `POST /api/problems/`・`PUT`／`PATCH /api/problems/<pk>/` の `subject` | 400 | `{"error": {"main_message": "入力内容にエラーがあります", "sub_message": "主キー \"<id>\" は不正です - データが存在しません。", "details": {"subject": ["主キー \"<id>\" は不正です - データが存在しません。"]}}}`（ほかの欄の誤りがあればそれも並ぶ） |
| `POST /api/problems/generate_ai/`・`generate_adaptive/` の `subject_id` | 404 | `{"error": "指定された科目が見つかりません"}` |
| `api/quiz/<pk>/` の各アクション（他組織・全体共有の科目の回） | 404 | `{"error": {"main_message": "リソースが見つかりません", "sub_message": "要求されたデータが存在しません", "details": {}}}` |

### 4-5. 既存のテストの期待値の更新
**修正方針**: このイシューの物差し（他組織の番号は存在しない番号と同じ応答）に合わせる。「作られない・変わらない」の確かめはそのまま残す。
- `backend/problems/tests/test_I103_cross_org_create.py`: TC-AUTO-01（作成）を 403 → 400 にし、存在しない科目の応答と伏せた本文が同じことを足す。TC-AUTO-02a・02b・03（AI 生成）を 403 → 404・本文 `{"error": "指定された科目が見つかりません"}` にする。TC-AUTO-05 の「403 でない」はそのまま（自組織は通る）。冒頭の説明を「存在しない科目と同じ応答で断る（I446 で 403 から変更）」に直す
- `backend/problems/tests/test_I166_quiz_tenant_isolation.py` TC-09: 他組織の科目を持つ既存の回は、出題・回答とも 404 の共通の本文（`{"error": {"main_message": "リソースが見つかりません", …}}`）になる。期待値を、存在しない回の番号の応答と同じことに変える。「回答が保存されない」の確かめは残す
- `backend/problems/tests/test_I073_image_update.py` TC-AUTO-12: ステータス 400 だけを見ているので変えない（4-2 の後も 400）

## 5. 実装手順
1. ステップ1（未知リスク先行・テストの土台）: 4-1 の経路の収集と `test_route_table_matches_urlconf` と表を書く。表の分類が実在の経路とずれていないかを先に固める → TC-04・TC-05
2. ステップ2: 4-1 の fixture と 4 種類の確かめ方を書き、修正前のコードで流して RED を記録する（落ちるのは S1〜S6 に当たるケースだけのはず。それ以外が落ちたら、表の期待値の誤りか新しい越境かを切り分け、新しい越境なら計画書を直す）→ TC-20
3. ステップ3: 4-2〜4-4 の修正 → TC-01〜TC-03 が GREEN
4. ステップ4: 4-5 の既存のテストの更新 → TC-11・TC-12
5. ステップ5: 失敗注入（FG1〜FG3）で、テストが落ちることを確かめて戻す → TC-21〜TC-23
6. 依存: ステップ2 はステップ1 の後。ステップ3・4 はステップ2 の RED の記録の後。ステップ5 はステップ3 の後
- サービスの再起動は不要（ファイルの削除・設定の変更なし。コンテナは開発用の自動再読み込み）

## 6. テスト計画
- テストのレベル: 結合（API を `APIClient` で呼ぶ・DB あり）。単体は境界の判定の部品（`tenant_scope`）が I431 の TC-22 で済んでいるので足さない。E2E は画面を変えないので不要
- 認可・テナント境界: 他組織（AC1）・同じ組織の別の利用者（AC2）・全体共有の科目・問題・運用者専用（AC4）を表で網羅する
- 再発防止: 表と経路の突き合わせ（AC5）・失敗注入（AC6）
- 手元では、このテストと `problems/tests/` だけを流す（全体は CI）
- 詳細は `docs/tests/open/I446_auto_test.md`・`docs/tests/open/I446_manual_test.md`

## 7. ロールバック
- PR の revert（コードとテストだけ。マイグレーション・データの変更なし）

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| 表のメンテが重く、新しい経路を足す人が表の書き方で迷う | テストのファイルの冒頭に「新しい経路を足したら、ここに 1 行足す。確かめ方の選び方」を書く。落ちたときのメッセージに、足りない経路と載せ方の例を出す |
| 本文の番号を伏せるときに、関係ない数字まで伏せる | 他組織などの番号を `4460001` 以降の区別しやすい値で明示して作る |
| ケースが多く（約 130）CI が遅くなる | 1 ケースの下準備は 50 件ほどの作成。下調べの 9 ケースが 5 秒強（初期化込み）で、全体で 1 分ほどの見込み。新しいテストだけで 2 分を超えたら（CI のログの所要時間で見る）、fixture を `django_db_setup` 相当のまとめた下準備に変える |
| 修正で、クイズの回の古いデータが見えなくなる | 他組織・全体共有の科目を指す回だけ（I166 の後は作れない）。I431 の手動 No.1 で、primary の dev DB の QuizSession 124 件はどれも越境 0 件 |
| AI 生成・作成の応答が 403 から 400・404 に変わり、画面の表示が変わる | 画面は自組織の科目しか送らない（科目の選択肢は `api/subjects/` から）。他組織の番号を手で送ったときだけ変わる |
| 0 で割る不具合（`dashboard/analytics`）をテストの下準備で避けたことで、不具合が隠れる | 別に起票する（retro・9 章） |

## 9. 確定事項と自律判断

### イシューに明記されていること
- 全経路を表に載せ、「確かめる」か「対象外（理由）」に分ける・表に無い経路で落ちる（設計確認メモ）
- 他組織・同じ組織の別の利用者（本人の記録）・番号を受け取らない一覧の 3 つを確かめる（設計確認メモ Q1〜Q3）
- `admin/users/` は組織管理者と一般の利用者が 403・公開の科目一覧は対象外（設計確認メモ・2 回目）
- 今は壊れている経路は #452 の番号付きの `xfail(strict=True)`
- 見つかった越境のうち、1 経路の絞り込みの追加で済むものは同梱
- 境界の考え方は I166・I431 にそろえる（キャッシュを通さない・組織に属さないユーザーは空・全体共有科目は含めない・問題の組織は `subject__organization_id`）

### Claude が決めたこと（技術的な判断と理由）
- 対象の経路を `api/` の下だけでなく、`admin/`（Django の管理画面）以外の全経路にする — `api/` の外に新しい経路が足されても気づけるようにするため（fail-closed）。`api/` の外は今 `health/`・`monitoring/*`・`cache/*` だけで、表に 8 行足すだけ。受け入れ条件の範囲は広げるが、仕様は変えない
- テストの置き場所を `backend/core/tests/` にする — URL の定義が core にあり、横断のテストのため
- 番号を区別しやすい値（`4460001` 以降）で明示して作る — 伏せるときの誤りを無くすため
- 全体共有の科目・問題も「組織の外」として確かめる — 境界の考え方（全体共有科目は含めない）を表で守るため。追加の費用は fixture の 2 件だけ
- 自分の古いデータ（他組織を指す記録）を fixture に入れ、一覧と `OwnCheck` で確かめる — 組織の絞り込みは「本人の記録の中身が組織の中か」を見るものなので、他人の番号を送るだけでは確かめられない（下調べの S5・S6 はこの形でしか見つからない）
- S1〜S6 の修正をこのイシューに同梱する — どれも 1 か所の絞り込みの追加（S1・S2 はシリアライザの欄 1 つ、S3・S4 はビューの探し方、S5・S6 は `get_queryset`）で、境界の判定の置き場所は変えない（イシューのスコープ「含む」の条件に合う）
- S1〜S4 の応答を 403 から「存在しない科目と同じ」に変える（I103 の決まりを変える）— 受け入れ条件 AC1 の物差しで、grill-me で確定した方針。OWASP の推奨（存在するかどうかを他のテナントに知らせない）にも合う
- 作成・更新の組織の確かめ（I103・SEC-1）を多層防御として残す — シリアライザの欄を誤って戻しても、他組織への作成は止まる
- 0 で割る不具合（`dashboard/analytics`）はこのイシューで直さず、retro で新しいイシューに起票する — 境界と関係なく、イシューの範囲外。統計の画面で利用者に見える 500 なので、価値は低くない
- 画面からの AI 生成が 415 になる件（`AIQuestionGenerator.tsx` が JSON で送る）は直さず、retro で起票か既存イシューへの同梱を決める — 境界と関係なく、画面とバックエンドの両方にまたがる
- `learning_insights` の KeyError（`period_days`）は #452（学習記録の機能を直す）に同梱する（retro でコメント）— #452 が同じ機能を直すイシューのため
- 1 つの経路に複数の確かめ方を持てる表にする（`dict[str, list[Check]]`）— 1 つの経路が「URL の番号」と「本文の科目」の 2 つの入口を持つ（問題の更新など）ため
- 運用者専用の経路は、組織管理者と一般の利用者で断られることだけを確かめ、運用者（`is_staff`）が全組織を見られることは確かめない — 仕様（grill-me の自己解決）で、境界ではないため

### 設計判断の区別
| 判断 | 区別 |
|---|---|
| 全経路を表に載せる・表に無ければ落ちる | イシューに明記 |
| 3 種類の確かめ（他組織・同じ組織の別の利用者・一覧） | イシューに明記 |
| 運用者専用・公開の科目一覧・slug の確かめの扱い | イシューに明記（設計確認メモ） |
| `admin/` 以外の全経路に広げる | 仮定で決めた（技術） |
| 置き場所・番号の決め方・fixture の形・全体共有も確かめる | 仮定で決めた（技術） |
| S1〜S4 の応答の変更（403 → 存在しない科目と同じ） | イシューに明記（AC1 の物差し）。I103 の個別の決まりは AC1 に従って変える |
| S5・S6 の修正（古い回・回答を読み出しから外す） | 仮定で決めた（技術。I431 の扱いの基準 2 を当てはめる） |
| 0 で割る不具合は別に起票・`learning_insights` は #452 に同梱 | 仮定で決めた（範囲の判断。価値判断ではない） |

要件・基本設計・UI/UX の価値判断に当たる仮定は無い（画面を変えない。応答の変更は AC1 で決まっている）。

### 要件適合性・業務ロジック
- 受け入れ条件の範囲を超える仕様の追加は無い（応答の変更は AC1 の物差しどおり。対象の経路を `admin/` 以外に広げるのはテストの範囲で、仕様ではない）
- マルチテナントの閲覧・操作の範囲: 一般の利用者は自組織の科目・問題と本人の記録だけ、組織管理者は自組織の科目・問題の管理、運用者（`is_staff`）は全組織（仕様）。全体共有の科目・問題は組織に属する利用者も使えない（I166・I431）
- ステータスの遷移・承認の条件: 変えない
- 端の場合: 組織に属さない利用者は I166・I431 のテストが確かめている（このテストでは扱わない）。科目が空の記録（学習記録・クイズの回）は残す（I431 と同じ）

### セキュリティ・ベストプラクティス
- 入力の検証: 科目の番号をシリアライザの欄（`OrgSubjectField`）で検証し、利用者の組織の科目以外を受け付けない
- 認証・認可: 最小権限を変えない（権限のクラスは変えない）。他組織の存在を応答で知らせない（OWASP A01 の情報の漏れの防止）
- 機密データ: 扱わない（テストの利用者のパスワードは固定のテスト用）
- OWASP Top 10: A01（Broken Access Control）の横断の回帰テスト。SQL は書かない（ORM だけ）
- フレームワークの推奨: DRF の `PrimaryKeyRelatedField.get_queryset` の上書きで入力を絞る（I166 と同じ）
- 依存ライブラリの追加・更新: なし
- セキュリティのスキャンの基準: bandit は MEDIUM 以上を直す・LOW は `# nosec` で抑える（テストの固定のパスワードは LOW の B106 に当たりうる。既存のテストと同じ書き方なら pre-commit で通る）。npm audit は対象外（frontend を変えない）
- 高リスク判定の参考: 認可の振る舞いを変える（S1〜S6）ため、計画レビューで判定を受ける

### 台帳の残り
- 一覧 docs/reviews/backlog/I224.md F9: 残す — ハーネスの実測の話で、このイシューのファイルと関係ない
- 一覧 docs/reviews/backlog/I223.md B1〜B4: 残す — bot の停止まわりの片付けで、このイシューのファイルと関係ない

### データ整合性・運用性・コスト（P3/P5/P8）
- P3/P5/P8 影響なし（DB の変更・外部 API・非同期処理・新しいインフラなし）

### 性能・UX（P6）
- P6 影響なし（画面を変えない）。性能: クイズの回の詳細・終了で、回答の先読みに組織の条件が 1 つ加わるだけ（問い合わせの数は変わらない）

### プライバシー・コンプライアンス（P9）
- テナントのデータの境界を守る変更（下の 15 章）。未成年データ・個人情報の新しい扱いは無い

## 15. プライバシー・コンプライアンス設計
- テナント横断のデータの混在を、テストで機械的に禁止する（他組織・別の利用者の中身が応答に出ないことを、全経路で CI が毎回確かめる）
- 他組織の科目・問題の存在を応答で知らせない（S1〜S4）。他組織の問題文・解説・選択肢を、自分の古い記録を通しても返さない（S5・S6）
- 保持期間・削除権・同意は変えない。既存のデータは消さない（読み出しから外すだけ）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | 組織 A の組織管理者が、組織 B の科目・全体共有の科目で問題を作る（POST）・付け替える（PUT・PATCH）・AI 生成する（2 経路）と、存在しない科目と同じステータスと伏せた本文で断られ、問題が作られない・変わらない（TC-01・TC-11。修正前の FAIL〔TC-20〕と修正後の PASS を実測） |
| V2 | 1 | 実験必須 | 自分のクイズの回のうち、他組織・全体共有の科目の回は一覧・詳細・終了・出題・回答から見えず、科目なしの回の中の他組織の問題への回答は、詳細・終了の応答に出ない（TC-03 の `GET api/quiz/`・`OwnCheck`・TC-12。修正前の FAIL と修正後の PASS を実測） |
| V3 | 2 | 実験必須 | 4-4 の回答の先読みの絞り込みが、自組織の回の出題・回答・終了（`submit_answer` の「回答済みか」・`QuizService` の未回答の判定・終了の応答の回答の数）を変えない（I166 の TC-02〜TC-08・TC-12 が通る〔TC-12〕・手動 No.2） |
| V4 | 2 | 読んで可 | `ProblemSerializer`・`ProblemAdminSerializer` を request の無い文脈で書き込みに使う箇所が無い（4-2 の調査結果の grep。あれば 4-2 で `OrgSubjectField` が何も受け付けず、その経路が壊れる） |
| V5 | 3 | 読んで可 | 表と経路の突き合わせが、新しい経路・古い行の両方で落ち、`OUT_OF_SCOPE` の理由が空の行・両方に載る行も落ちる（TC-04・TC-21 の FG1 の実測） |
| V6 | 3 | 実験必須 | 組織の絞り込み・本人の絞り込みを外すと、テストが落ちる（TC-22・TC-23 の FG の実測）。`IdCheck` が、空を返すだけ・すべて 404 を返すだけの実装で通らないよう、自組織の記録が読めること（`OwnCheck`・I166・I431 のテスト）と組み合わさっている |
| V7 | 3 | 読んで可 | 表の「対象外」の各行の理由が、そのビューのコードと合っている（番号を受け取らない・運用者専用・登録画面用の仕様）。特に `api/auth/me/` の PUT・PATCH で組織・役割が書き換えられない（`UserSerializer.read_only_fields`） |
| V8 | 1 | 読んで可 | 画面（`frontend/src`）が、問題の作成・AI 生成の 403 や「他組織の科目には問題を作成できません」の文言に依存していない（4-2 の調査結果の grep） |

## 計画変更記録
- 2026-11-12 計画レビュー（20261112_0131・Blocker 1・Warning 3・Info 1）に対応: ① 高リスクの必須節「必ず確かめる項目」を足した（Blocker）② 4-2 に `ProblemSerializer` の書き込みの使用箇所と画面の依存の grep の結果を足した（Warning 1・2）③ 失敗注入の戻し方を Edit で元に戻すと明記した（Warning 3）④ CI の時間の目安を 8 章に足した（Info）。範囲・方式・受け入れ条件は変えない。Blocker への対応のため計画レビューはやり直す

## レビュー結果
- [20261112_0131 判定: 差し戻し（Blocker 1件）](../../reviews/I446_plan_review_20261112_0131.md)
