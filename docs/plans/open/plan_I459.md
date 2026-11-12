# 計画書: I459 学習統計の画面が、解いた問題が 0 件の日があると 500 になる不具合を直す（dashboard/analytics）

## 基本情報
- **計画書ID**: plan_I459
- **関連イシュー**: #459
- **Draft PR**: #478
- **作成根拠資料**: docs/issues/open/I459.md（GitHub #459 の本文の写し）
- **実装後評価**: docs/reviews/open/I459_review.md
- **作成日**: 2026-11-12

## 1. 背景/目的
イシューの「背景/目的」と同じ。`GET /api/dashboard/analytics/` は、日々のまとめ（`DailyStudySummary`）に解いた問題数が 0 の日が 1 日でもあると、データベースで 0 で割って 500 になる。学習統計の画面（`frontend/src/pages/Statistics.tsx:72`）はこの API を呼ぶので、画面全体の読み込みが失敗する。同じ API は `days` に数字でない値を渡しても 500 になり、大きな値では 1 日 1 回の問い合わせが走って応答がとても遅くなる。

この計画で、(1) 週ごとの正答率を「週の正解数の合計 ÷ 週の解いた問題数の合計 × 100」で出し（週の合計が 0 問なら `0`）、(2) `days` を確かめて、整数でない・1 未満・365 を超える値を 400 にする（設計確認メモ 2026-11-12）。

### 調査結果
**原因の概要**: 週ごとの正答率を「日ごとの正答率の平均」としてデータベースで計算していて、問題を解かなかった日（解いた数 0）でも割り算をしてしまう。`days` は文字を数字に直すとき、失敗を受け止めていない。

**エラーの詳細**（2026-11-12 にこのワークツリーのコンテナで使い捨てのテストを流して再現）:
- 解いた数 0 の日のまとめを 1 件だけ持つ利用者で `GET /api/dashboard/analytics/` → 500。`django.db.utils.DataError: division by zero`（`backend/dashboard/views.py:243` の `.aggregate(` ／ `_get_performance_trends` から）
- `GET /api/dashboard/analytics/?days=abc` → 500。`ValueError: invalid literal for int() with base 10: 'abc'`（`views.py:186` の `int(request.query_params.get('days', 30))`）
- おすすめ（`GET /api/dashboard/recommendations/`）は、解いた数 0 の学習記録と 4 問中 1 問の学習記録を持つ利用者で 200（`current_accuracy` 25.0 の 1 件）。`views.py:277` の割り算は `filter(total_problems__gt=0)`（集計の後の HAVING）を通った行だけで計算され、0 で割らない

**詳細な原因分析**:
1. エラーの流れ: 画面が `GET /api/dashboard/analytics/`（`days` なし → 30）を呼ぶ → `DashboardAnalyticsView.get` → `_get_performance_trends`（`views.py:232-260`）が 7 日ずつ `DailyStudySummary` を `aggregate(avg_accuracy=Avg(F('total_problems_correct') * 100.0 / F('total_problems_attempted')))` で集計 → 行ごとに割り算が評価され、分母 0 の行で PostgreSQL が `division by zero` → 500
2. 0 件の行ができる経路: 学習記録の終了 API（`POST /api/study/logs/<id>/end/`・`backend/studylogs/views.py:64-104` の `_update_daily_summary`）が、問題を 0 問のまま終えた学習記録でもその日のまとめを `get_or_create` し、解いた数 0 の行を作る。学習時間だけの日は正しいデータなので、作る側は直さない
3. なぜ気づかなかったか: `backend/dashboard/` にテストが無かった。#446 の横断テストは、この不具合を踏まないよう日々のまとめの解いた数を 1 以上にしていた（`backend/core/tests/test_I446_cross_api_tenant_isolation.py:440-443`）。dev DB の `DailyStudySummary` は 0 件（#473 の調査・2026-10-24）
4. `days`（`views.py:186`）: `int()` の失敗を受け止めていない。上限も無く、`days` 日分の 1 日 1 回の問い合わせ（`views.py:195-209`）と 7 日ごとの集計が走る
5. 画面との関係: 画面は `period`（`daily`／`weekly`／`monthly`）と科目を送り、`days` は送らない（`Statistics.tsx:68`）。画面は `study_time_trend`・`accuracy_trend` を読み、`performance_trends` は読まない（名前のずれは #473 の範囲）。このため、正答率の出し方の変更と `days` の確かめは今の画面の表示を変えない。変わるのは「500 で画面の読み込みが失敗する」のが無くなることだけ

**根本原因（コード）**: `backend/dashboard/views.py:246-248`（行ごとの割り算の平均）と `views.py:186`（`days` の `int()`）。

**同じファイルのほかの割り算**（スコープ「ほかの集計の確認」）:
| 場所 | 式 | 0 で割るか |
|---|---|---|
| `views.py:42` 最近のクイズ | `quiz.correct_answers / quiz.completed_problems` | 割らない（`if quiz.completed_problems > 0`） |
| `views.py:80` 今日 | `.../ max(today_study['total_problems'] or 1, 1)` | 割らない（`max(…, 1)`） |
| `views.py:94` 週のまとめ | `.../ max(weekly_summary['total_problems'] or 1, 1)` | 割らない（`max(…, 1)`） |
| `views.py:150` 科目別 | `totals['total_correct'] / totals['total_problems']` | 割らない（`if totals['total_problems']`） |
| `views.py:246-248` 週ごとの正答率 | 行ごとの `F() / F()` の平均 | **割る（本イシューで直す）** |
| `views.py:277` おすすめ | `F('total_correct') * 100.0 / F('total_problems')` | 割らない（HAVING `total_problems > 0` の後。上の再現で 200） |

直すのは `246-248` だけ。おすすめは再発防止のテスト（TC-05）だけを足す。

### 環境前提
- app-1 のコンテナ（backend・db・frontend・redis）が動いている（2026-11-12 `docker compose ps`・作業フォルダはこのワークツリー）。テストの DB は PostgreSQL（`backend/core/settings.py:89`・CI も `postgres:15-alpine`）。SQLite は 0 で割っても NULL になり再現しないが、使っていない
- `gh` は Draft PR #478 の作成で確認済み
- 画面確認は Playwright MCP（`docs/runbooks/frontend-verify.md`）
- テストは CI が正。手元では新しいテストと、守りにする既存のテストのファイルだけを流す（全テストは流さない）

## 2. 受け入れ条件（Acceptance Criteria）
- AC1: 解いた問題数が 0 の日を含む利用者で `GET /api/dashboard/analytics/` が 200 を返す
- AC2: そのときの週ごとの正答率（`performance_trends[].avg_accuracy`）が「週の合計の正解数 ÷ 週の合計の解いた問題数 × 100」（小数第 2 位で丸め）になる（例: 同じ週に 10 問中 8 問の日・1 問中 0 問の日・0 問の日 → `72.73`）
- AC3: 週の合計が 0 問の週（0 問の日だけの週・まとめが無い週）の `avg_accuracy` は `0`
- AC4: `days` が整数でない・1 未満・365 を超えるとき 400（`core.exceptions.create_error_response` の形）。省略時は 30 日で 200
- AC5: 上の点を確かめる回帰テストが CI で流れる
- AC6: #446 のテストの下準備で 0 件の日を避けている注記を、直した後の実態に合わせる（0 件の日を足しても通ることを確かめ、避ける注記は外す）

## 3. 影響範囲
| 区分 | 対象 | 内容 |
|---|---|---|
| Backend | `backend/dashboard/views.py` | `DashboardAnalyticsView.get`（`days` の確かめ）・`_get_performance_trends`（正答率の出し方） |
| Backend | `backend/dashboard/serializers.py`（新規） | `days` を確かめる `AnalyticsQuerySerializer` |
| Backend | `backend/dashboard/tests/__init__.py`・`backend/dashboard/tests/test_I459_analytics_zero_division.py`（新規） | 回帰テスト |
| Backend | `backend/core/tests/test_I446_cross_api_tenant_isolation.py` | 下準備に 0 件の日を足し、避ける注記を外す |
| Frontend | なし | 画面は `performance_trends` を読まず `days` も送らないので、表示は変わらない |
| DB | なし | マイグレーションなし |
| Config/Infra | なし | 依存の追加なし |
| 変更しない（参照だけ） | `backend/studylogs/views.py`・`frontend/src/pages/Statistics.tsx` | 0 件の日を作る経路（正しいデータ）・画面 |

API の形の変化: `avg_accuracy` の値の意味（日ごとの平均 → 週の合計で割る）と丸め（小数第 2 位）が変わる。キー・型（数値）は変わらない。`days` の不正な値は 500 → 400。

## 4. 変更点一覧

### 修正アプローチ
正答率は、行ごとに割って平均する代わりに、週の正解数と解いた問題数をそれぞれ合計してから Python で 1 回だけ割る。分母が 0 なら割らずに 0 を返す。ダッシュボードの「週のまとめ」（`views.py:93-95`）と同じ「合計で割る」出し方になる。`days` は DRF の serializer で整数・範囲を確かめ、不正なら I452 の `review_summary`（`backend/studylogs/views.py:381-395`）と同じ形の 400 を返す。

### 4-1. `days` の確かめ（`backend/dashboard/serializers.py`・新規）
**修正方針**: クエリの値の確かめを serializer に寄せ、範囲を定数で持つ（ビューに数字を書かない）。

```python
from rest_framework import serializers

ANALYTICS_DEFAULT_DAYS = 30
ANALYTICS_MAX_DAYS = 365


class AnalyticsQuerySerializer(serializers.Serializer):
    """学習統計（analytics）のクエリ。days は 1〜365 の整数・省略時は 30"""

    days = serializers.IntegerField(
        min_value=1, max_value=ANALYTICS_MAX_DAYS, default=ANALYTICS_DEFAULT_DAYS)
```
- `default` があるので `required=False` になる。`?days=`（空）は DRF の決まりで省略と同じ扱い（30）
- `"30.0"` のように小数点以下が 0 の文字は DRF の `IntegerField` が 30 として受ける（DRF の既定のまま）。`"1.5"`・`"abc"` は不正

### 4-2. `DashboardAnalyticsView.get`（`backend/dashboard/views.py`）
**修正方針**: `int()` をやめ、serializer の結果を使う。不正なら 400。

```python
from rest_framework import permissions, status, views
from core.exceptions import create_error_response
from .serializers import AnalyticsQuerySerializer

    def get(self, request):
        user = request.user
        query = AnalyticsQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return create_error_response(
                '期間の指定が正しくありません',
                '日数は 1〜365 の整数で指定してください',
                status.HTTP_400_BAD_REQUEST,
            )
        days = query.validated_data['days']
        # 以下は今のまま（end_date・start_date・daily_data・subject_stats・…）
```
- 400 の body: `{"error": {"main_message": "期間の指定が正しくありません", "sub_message": "日数は 1〜365 の整数で指定してください", "details": {}}}`
- 認可は今のまま（`permission_classes = [permissions.IsAuthenticated]`・未認証は 401）

### 4-3. `_get_performance_trends`（`backend/dashboard/views.py`）
**修正方針**: 行ごとの割り算をやめ、週の合計で 1 回だけ割る。

```python
def _accuracy_percent(correct, attempted):
    """正解数 ÷ 解いた問題数 × 100（小数第 2 位）。解いた問題数が 0・空なら 0"""
    if not attempted:
        return 0
    return round((correct or 0) * 100 / attempted, 2)

    # _get_performance_trends の中
            week_summary = DailyStudySummary.objects.filter(
                user=user,
                date__range=[current_week_start, week_end]
            ).aggregate(
                avg_time=Avg('total_study_time'),
                avg_problems=Avg('total_problems_attempted'),
                total_attempted=Sum('total_problems_attempted'),
                total_correct=Sum('total_problems_correct'),
            )

            weeks.append({
                'week_start': current_week_start.isoformat(),
                'avg_study_time': week_summary['avg_time'] or 0,
                'avg_problems': week_summary['avg_problems'] or 0,
                'avg_accuracy': _accuracy_percent(
                    week_summary['total_correct'], week_summary['total_attempted']),
            })
```
- `_accuracy_percent` はモジュールの関数（`views.py` の import の下）。今は週ごとの正答率だけで使う。ダッシュボードの overview（`views.py:79-81・93-95`）の同じ計算は #473 が作り直すので、本イシューでは触らない
- `F` の import が使われなくなる（おすすめの `views.py:277` で使っているので残る）

### 4-4. テスト（`backend/dashboard/tests/__init__.py`（空）・`backend/dashboard/tests/test_I459_analytics_zero_division.py`・新規）
- 下準備: 組織（slug `org-i459`）・利用者（`user_id="u_i459"`・`email="u_i459@example.com"`・組織あり・`role="user"`）・科目（slug `subj-i459`・同じ組織）。`APIClient.force_authenticate`。キャッシュは I431 のテストと同じく前後で消す（`subject_service` が Redis を使うため）
- TC の中身は `docs/tests/open/I459_auto_test.md`

### 4-5. #446 の横断テスト（`backend/core/tests/test_I446_cross_api_tenant_isolation.py:440-444`）
**修正方針**: 0 件の日を避ける理由は無くなるので、注記を外し、0 件の日のまとめを 1 件足す（直した後も横断のテストが通ることを、0 件の日を含む形で確かめる）。

```python
    # 解いた問題が 0 件の日も入れる（I459 で dashboard/analytics の 0 で割る不具合を直した）
    summary = DailyStudySummary.objects.create(
        user=user_a, date=timezone.now().date(), total_problems_attempted=4,
        total_problems_correct=3)
    summary.subjects_studied.add(subject_a, subject_b)
    DailyStudySummary.objects.create(
        user=user_a, date=timezone.now().date() - timedelta(days=1),
        total_study_time=600)
```
- `timedelta` は同じファイルで import 済み（`:434` で使用）。ほかの下準備と期待値（表）は変えない

## 5. 実装手順
- ステップ 1（未知リスク先行・縦の 1 本）: 4-4 のテストを先に書き、直す前のコードで TC-01〜TC-03 が落ちる（Red）ことを確かめる。続けて 4-1・4-2・4-3 を直し、TC-01〜TC-06 を通す（Green）。→ TC-01〜TC-06
- ステップ 2（ステップ 1 が前提）: TC-05 の失敗の注入（FG）。→ TC-05
- ステップ 3（ステップ 1 と並行可）: 4-5 を直し、#446・I431 のテストを流す。→ TC-07
- ステップ 4: /simplify の後に TC-01〜TC-07 の流し直し。→ TC-08
- 実装の後のサービスの再起動: 不要（コードだけの変更。dev の backend は自動で読み直す）

## 6. テスト計画
- 自動: `docs/tests/open/I459_auto_test.md`。テストレベル: API の結合テスト（`APIClient` で `GET /api/dashboard/analytics/`・`/recommendations/` を呼び、状態コードと応答の値を確かめる・PostgreSQL）。正答率の計算は応答の値で確かめる（関数の単体テストは足さない。応答で全分岐〔0 問・空・ふつう〕を通る）。E2E は足さない（画面は変えない）
- 再発防止: TC-01（0 件の日で 500 に戻ると落ちる）・TC-02（週の合計 0 問で 0 以外・500 になると落ちる）・TC-03（`days` の不正な値で 400 以外になると落ちる）・TC-05（おすすめの HAVING を外すと落ちる・FG で確かめる）・TC-07（#446 の下準備に 0 件の日を入れる）
- 手動: `docs/tests/open/I459_manual_test.md`（Claude が dev のデータと Playwright MCP で行う。Human の項目なし）
- 認可・テナント: 認可は変えない（`IsAuthenticated`）。未認証の 401 を TC-06 で確かめる。集計は本人（`user=user`）のまま。組織の境界は #446 の横断テスト（TC-07）が見る

## 7. ロールバック
コードとテストだけの変更（DB の形は変えない）。PR を revert すれば戻る。サービスの再起動は通常のデプロイだけ。手動テストで dev DB に足す 0 件の日のまとめ（1 件）は、学習統計に出る正しい形のデータなので残す（消すのは物理削除になり危険操作に当たるため行わない。CI は毎回新しい DB なので影響しない）。

## 8. Risk & 回避策
- R1 `avg_accuracy` の値が変わる（日ごとの平均 → 週の合計で割る・丸め） → 設計確認メモで決めた変更。今の画面・E2E・テストは `performance_trends`・`avg_accuracy` を読まない（2026-11-12 の同じ grep で当たるのは `backend/dashboard/views.py` だけ）
- R2 `days` の不正な値が 400 になることで、今 `days` を送っている呼び出しが壊れる → 画面は送らない（`Statistics.tsx:68`・`dashboard.service.ts`）。analytics に `days` を送る画面・E2E・テストは無い（2026-11-12 `grep -rn "days=\|performance_trends\|avg_accuracy" frontend/src e2e backend`: 当たるのは `timedelta(days=…)` と、別の API の `Monitoring.tsx:95` の `/monitoring/errors/?days=7` だけ）
- R3 `days=365` の応答の遅さ → 上限は 365 で、1 日 1 回の問い合わせ（最大 366 回）と週ごとの集計（最大 53 回）が残る。今の上限なしよりは限られる。問い合わせの数を減らす作り直しは #473（集計の作り直し・クエリ数の固定）に任せる
- R4 #446 の下準備に行を足すことで、表の期待値が変わる → 足すのは本人（`user_a`）の日々のまとめで、組織をまたぐ値を持たない（科目を付けない）。応答に他組織の値が混ざるかの判定は変わらない。TC-07 で確かめる

## 9. 確定事項と自律判断
**イシューに明記されていること**（設計確認メモ 2026-11-12）:
- 週ごとの正答率は週の合計で割る（`Sum('total_problems_correct') * 100 / Sum('total_problems_attempted')`）。解かなかった日は自然に外れる
- 1 問も解かなかった週は `0`（API の形は変えない。「0」と「データ無し」の区別は #473）
- `days` が整数でない・1 未満・365 を超える場合は 400（`core.exceptions.create_error_response` の形）。省略時は 30
- 0 件の日を作る `backend/studylogs/views.py` と画面 `Statistics.tsx` は変えない
- 同じファイルのほかの割り算を確かめ、見つかれば同じ形で直す

**Claude が技術的に決めたこと（理由）**:
- 割り算は集計の後に Python で 1 回だけ行う（`NullIf`・`Case` でデータベースの中で割る案は採らない） — 合計の割り算は週に 1 回だけで、0 の扱いが `if not attempted` の 1 行で読める。overview の週のまとめと同じ書き方
- 正答率を小数第 2 位で丸める — overview・科目別・最近のクイズ・日ごとの `accuracy`（`DailyStudySummary.accuracy`）がどれも `round(…, 2)`。AC2 の値（72.73）をそろえる。今の画面は読まないので見え方は変わらない
- `days` の確かめは DRF の `Serializer`（`AnalyticsQuerySerializer`）にする（ビューで `try: int()` する案は採らない） — I452 の `review_summary` が同じ形（クエリの serializer → `create_error_response`）。範囲を宣言で持てて、定数がビューに散らない
- 400 の文言: `main_message='期間の指定が正しくありません'`・`sub_message='日数は 1〜365 の整数で指定してください'` — 画面は `days` を送らないので利用者の目には触れない。API を直接呼ぶ人に何を直せばよいかが分かる文言にした（UI の文言の価値判断には当たらない）
- 範囲の定数（30・365）は `dashboard/serializers.py` のモジュールの定数にする — 使うのはこの serializer だけで、設定（settings）にするほどの切り替えの必要は無い
- `serializers.py` を `dashboard` に新しく作る — `dashboard` に serializer の置き場が無かった。#473 の応答の serializer もここに足せる
- `_accuracy_percent` はモジュールの関数にし、overview の同じ計算には使わない — overview の作り直しは #473。本イシューで overview の行を変えると #473 との食い違いが増える
- Fat View の解消（集計をサービス層へ移す）はしない — #473 が `backend/dashboard/services.py` を新しく作って集計を移す計画。本イシューは不具合の修正に絞る
- テストの置き場は `backend/dashboard/tests/`（新規・`__init__.py` を置く）。ファイル名は `test_I459_analytics_zero_division.py`（ほかのアプリと同じ `test_I###_*.py`）
- #446 の下準備は注記を外すだけでなく、0 件の日のまとめを 1 件足す — イシューの「直した後は、0 件の日を含めても横断のテストが通ることを確かめる」を、横断のテストの中で毎回確かめる形にする
- おすすめ（`views.py:277`）は直さず、0 問の学習記録で 200 のテスト（TC-05）だけ足す — 再現で 0 で割らないことを確かめた（HAVING の後）。ただし `filter(total_problems__gt=0)` を外すと 0 で割ることになり、気づきにくいので回帰テストで止める
- 手動テストのアカウントは `e2e_user_c@example.com`（組織 A・一般ユーザー。`docs/runbooks/frontend-verify.md` の表）。0 件の日のまとめは `manage.py shell` で 1 件足す（学習記録の API を画面から呼ぶ経路が無いため）

**要件適合性・業務ロジック**: 受け入れ条件を超える仕様の追加・変更は無い（正答率の出し方・`days` の確かめ・#446 の下準備）。閲覧範囲: 集計は本人（`user=user`）のまま、組織の境界の扱いは変えない。ステータス遷移: 無し。境界の値: 0 問の日・0 問の日だけの週・まとめが無い週・正解 0 の日・`days` の 0／1／365／366／-1／`abc`／`1.5`／空／省略を TC で確かめる。

**セキュリティ・BP**: 入力の検証を足す（`days` を整数・1〜365 に限る。不正な値で 500 にならず、大きな値で重い処理を走らせない）。認可は変えない（`permissions.IsAuthenticated`）。機密データは扱わない（400 の文言に入力の値を入れない）。SQL は ORM のまま（`Sum`・`Avg`）。XSS・CSRF: GET の JSON だけで、画面の変更なし。依存の追加なし。bandit は MEDIUM 以上を直す・LOW は `# nosec` で抑える（新しいコードに該当なし見込み）。npm audit は high／critical を直す（依存を変えないので対象なし）。DRF の推奨（serializer で入力を確かめる）に沿う。

**P3/P5/P8 影響なし**: DB の形・外部 API・非同期処理・インフラ・依存は変えない。
**P6 影響なし**: 画面を変えない。性能は `days` の上限で今より限られる（R3）。N+1 の解消は #473。
**P9 影響なし**: 個人情報・未成年データを新しく扱わない。テナントの閲覧範囲は変えない。

**台帳の残りの一覧**:
- 一覧 I224.md F9: 残す — ハーネスの項目で、このイシューの変更点と関係しない（`FILE=-`）
- 一覧 I223.md B1〜B4: 残す — bot の停止に関する項目で、このイシューの変更点と関係しない（`FILE=-`）
- 実装対象のファイルに当たる行は無し

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | 0 問の日を含む週で 200・`avg_accuracy` が週の合計で割った値（TC-01。直す前のコードで 500 の Red を実測） |
| V2 | 1 | 実験必須 | 週の合計 0 問・まとめが無い週で `avg_accuracy` が `0`（TC-02） |
| V3 | 2 | 実験必須 | `days` の不正な値がどれも同じ 400 の形・正しい値は 200（TC-03・TC-04） |
| V4 | 3 | 読んで可 | 認可（`IsAuthenticated`）と集計の対象（`user=user`）が変わらない（差分と TC-06・TC-07） |

## 計画変更記録
- implement（/simplify・2 体〔再利用／簡潔さ・効率・直す深さ〕。差分が 40 行ほどのため 4 観点を 2 体にまとめた）: 動きを変えずに次を直した — `_accuracy_percent` を `round(correct * 100 / attempted, 2) if attempted else 0` の 1 行に（`attempted` が 0 でなければ同じ行の集計なので `correct` は空にならない）・400 の `sub_message` の上限を `ANALYTICS_MAX_DAYS` から作る（定数と文言の二重持ちをやめる。文言は同じ）。見送り: `status.HTTP_400_BAD_REQUEST` の省略（`create_error_response` の既定値と同じだが、I452 の `review_summary` と同じく呼ぶ側で 400 を見せる）・`_clear_caches` の共通化（5 ファイルの写しで、`conftest.py` に移すのは本イシューの範囲外）。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件を変えない）

## レビュー結果
- [20261112_1832 判定: ✅ 完了](../../reviews/I459_plan_review_20261112_1832.md)
