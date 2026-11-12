# 計画書: I455 学習記録まわりのモデルに組織の境界つきの取り出し方を持たせる

## 基本情報
- **計画書ID**: plan_I455
- **関連イシュー**: #455
- **Draft PR**: #462
- **作成根拠資料**: docs/issues/open/I455.md（GitHub #455 の本文の写し）
- **実装後評価**: docs/reviews/open/I455_review.md
- **作成日**: 2026-11-12

## 1. 背景/目的
イシューの「背景/目的」と同じ。I431 で学習記録・ダッシュボードに組織の絞り込みを足したが、絞り込みは呼び出し側ごとに `scope_to_user_org(<queryset>, user, subject_path=..., allow_null=...)` を書く作りで、書き忘れや指定の取り違えを作りで防げていない。I452 で同じ周辺に新しい処理を足す前に、各モデルに「利用者本人の記録で、かつ組織の境界の中のもの」を返す取り出し方（`for_user(user)`）を持たせ、それを使うのを標準にする。振る舞いは変えない。

### 調査結果
**原因の概要**: 組織の境界の決まり（科目への経路・科目が空の記録を残すか）がモデルではなく呼び出し側に書かれているため、呼び出しのたびに同じ値を正しく書く注意が要る。

**詳細**:
1. `scope_to_user_org` の呼び出しは、学習記録とダッシュボードの側に 22 か所（`backend/studylogs/views.py` 9・`services.py` 1・`mistake_analysis.py` 8〔`scope_learning_suggestions` の 2 を含む〕・`backend/dashboard/views.py` 4）、ほかに `backend/problems/views.py:812`（QuizSession）・`:818`（QuizAnswer の先読み）にある（2026-11-12・`grep -rn "scope_to_user_org("`）。どれも `X.objects.filter(user=...)` を作ってから渡す形で、利用者を 2 回書く
2. モデルごとの境界の決まり（呼び出しのたびに同じ値を書いている。モデルの欄の定義と一致を確かめた）:
   | モデル | 科目への経路 | 科目が空の記録 | 根拠（欄） |
   |---|---|---|---|
   | StudyLog | `subject` | 残す | `subject` は null 可（studylogs/models.py:10） |
   | QuizSession | `subject` | 残す | `subject` は null 可（problems/models.py:200） |
   | MistakePattern | `subject` | 残す | null 可（studylogs/models.py:271） |
   | LearningWeakness | `subject` | 外す | 必須（studylogs/models.py:404） |
   | SpacedRepetitionCard | `problem__subject` | 外す | `problem` は必須（:115） |
   | SpacedRepetitionReview | `problem__subject` | 外す | `problem` は必須（:186） |
   | ProblemAttempt | `problem__subject` | 外す | `problem` は必須（:66） |
   | LearningSuggestion | `subject` と `mistake_pattern__subject` の両方 | 残す | どちらも null 可（:341・:355）。I431 の `scope_learning_suggestions`（mistake_analysis.py:23-33） |
3. 8 モデルとも独自の Manager・QuerySet を持っていない（`objects` は Django の既定）
4. 循環 import: `problems/services/tenant_scope.py` は `problems.models` を import する。QuizSession（`problems/models.py`）の QuerySet が `tenant_scope` を import すると循環する。`scope_to_user_org` は Q を組み立てるだけでモデルを使わない
5. 絞らずに読む箇所（`backend/studylogs/`・`backend/dashboard/` の、8 モデルの `objects.<読み出し>` で `scope_to_user_org` を通らないもの）を全件調べ、下の「扱いの表」に分けた（`grep -nE "(StudyLog|ProblemAttempt|…|QuizSession)\.objects\."` と各関数の通読）
6. #446 の横断テストは `backend/core/tests/test_I446_cross_api_tenant_isolation.py`（PR #456・develop にマージ済み）。経路の表で全 API を確かめる。非同期処理と、API を通らないサービスの内部は見ない

**扱いの表**（絞らずに読む箇所・`扱い` の (A)〜(C) は 4 章の基準）:
| 箇所 | 中身 | 扱い |
|---|---|---|
| studylogs/views.py:51 `StudyLogViewSet.create` の進行中の記録を終える `update` | 自分の記録に終了の印を付ける。応答に出ない | (C) 理由のコメント |
| studylogs/views.py:118 `overview` の `study_logs`（合計・件数） | 数だけ | (C) |
| studylogs/views.py:158 `overview` の `recent_logs` | 科目名を返す（今は `scope_to_user_org`） | (A) `for_user` |
| studylogs/views.py:215・225・239 連続日数 | 数だけ | (C) |
| studylogs/views.py:264 `_get_subject_statistics` の `subject=subject`（科目は組織で絞った一覧から） | 科目別の数 | (B) `for_user`（結果は同じ） |
| studylogs/views.py:328・335 `update_progress` | 数だけ | (C) |
| studylogs/views.py:688 `mark_suggestion_read`・:760 `resolve_weakness` の `get(id=…, user=…)` | 印付け。応答は固定の文言 | (C) |
| studylogs/views.py:788 `improvement_trends` | 数だけ | (C) |
| studylogs/services.py:61 `get_new_cards` の既存カードの問題 ID（候補は `available_problems` から除くだけ） | 応答に出ない | (B) `for_user`（候補は組織の問題だけなので結果は同じ） |
| studylogs/services.py:195・196 `get_user_statistics`・:263 連続日数・:285・286 `update_daily_analytics` | 数だけ | (C) |
| studylogs/mistake_analysis.py:110・116・167・172 誤答率の分母 | 数だけ | (C) |
| studylogs/mistake_analysis.py:206 `avg_time_by_user` | 数だけ | (C) |
| studylogs/mistake_analysis.py:267・273 `update_learning_weaknesses` の `problem__subject=subject`（科目は `available_subjects`） | 科目別の数 | (B) `for_user` |
| studylogs/mistake_analysis.py:403・443 提案の重複の確かめ（`exists()`） | 応答に出ない。提案の科目がパターン・弱点の科目と違う古いデータでは結果が変わりうる | (C)（同じ結果を言い切れないため変えない） |
| studylogs/mistake_analysis.py:466 `_generate_general_suggestions`・:535 `_calculate_improvement_trends`・:554 `_calculate_overall_improvement_rate` | 数だけ | (C) |
| studylogs/mistake_analysis.py:568 `provide_suggestion_feedback` の `get` | 印付け | (C) |
| studylogs/adaptive_selection.py:92・93 `analyze_user_proficiency` | 正答率などの数（科目別はキーを組織の科目に絞り済み・I431 R12） | (C)（`for_user` にすると全体の正答率が変わる） |
| studylogs/adaptive_selection.py:251 `_calculate_growth_rate` | 数だけ | (C) |
| studylogs/adaptive_selection.py:297・302 `_get_problem_pool` の最近の問題 ID（候補は `available_problems` から除くだけ） | 応答に出ない | (B) `for_user` |
| studylogs/adaptive_selection.py:417 `_calculate_problem_score` の `problem=problem`（問題は組織の候補から） | 数 | (B) `for_user` |
| studylogs/tasks.py:164 `cleanup_expired_suggestions_task`・:245 `bulk_update_spaced_repetition_task` | 利用者を持たない一括処理。中身を外に出さない | (C) |
| studylogs/tasks.py:276-278 `export_user_data_task` | 応答は件数だけ（`record_counts`） | (C) |
| dashboard/views.py:23 `today_study`・:115・124 連続日数 | 数だけ | (C) |
| dashboard/views.py:143 `_get_subject_progress` の `subject=subject`（科目は I431 で組織に絞った `get_user_selected_subjects`） | 科目別の数 | (B) `for_user` |
| dashboard/views.py:302 `studied_subject_ids`（組織の科目の一覧から除くだけ） | 応答に出ない | (B) `for_user` |
| 書き込み（`create`・`get_or_create`）: services.py:72・123、mistake_analysis.py:130・185・220・247・287・410・451・473 | 取り出しではない。キーの科目・問題は組織で絞った読み出しから来る | 対象外（コメント不要・5 章の静的テストも除く） |

### 環境前提
- app-1 のコンテナ（backend・db・redis・frontend）が動いている（2026-11-12 `docker compose ps`）。`gh` は Draft PR #462 の作成で確認済み
- CI の `makemigrations --check --dry-run`（`.github/workflows/ci.yml:38`）がモデルと migration のずれを見る
- テストは CI が正。手元では新しいテストと、守りにする I431・I166・I446 のテストのファイルだけを流す（全テストは流さない）

## 2. 受け入れ条件（Acceptance Criteria）
イシューの受け入れ条件と同じ。この計画での合格の基準:
- [ ] AC1: 8 モデルの組織の境界が、それぞれの QuerySet のクラス属性（`subject_paths`・`allow_null`）の 1 か所で決まり、`for_user(user)` で取り出せる（TC-01〜TC-04）
- [ ] AC2: `backend/studylogs/` と `backend/dashboard/` の、テスト以外のコードの呼び出し側に、`scope_to_user_org`・`scope_learning_suggestions` の呼び出し（とその引数 `subject_path=`・`allow_null=`）が残らない（境界の決まりは 4-3 の QuerySet のクラス属性 `subject_paths = …`・`allow_null = …` だけに書く。TC-05）
- [ ] AC3: 組織で絞らずに取り出す箇所に、`組織で絞らない` で始まる理由のコメントがある。8 モデルの取り出しが `for_user` でもコメントつきでもないとテストが落ちる（TC-06・TC-07）
- [ ] AC4: I431（`backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py`）・I166（`backend/problems/tests/test_I166_quiz_tenant_isolation.py`）・#446（`backend/core/tests/test_I446_cross_api_tenant_isolation.py`）のテストが、ファイルを変えずにすべて pass する（TC-08・TC-13）
- [ ] AC5: 各 QuerySet の単体テストが、科目への経路・空を許すか・組織に属さない利用者・別の利用者を確かめる。LearningSuggestion は 2 つの経路の両方で絞ることを確かめる。失敗の注入で RED になる（TC-01〜TC-04・TC-09）
- [ ] AC6: migration が増えない（TC-10）
- [ ] AC7: 全テストが pass する（CI・TC-11）

## 3. 影響範囲
- Backend:
  - `backend/problems/querysets.py`（新規・`scope_to_user_org` の移設と `OrgScopedQuerySet`）
  - `backend/problems/services/tenant_scope.py`（`scope_to_user_org` を新しいモジュールから読み込んで公開し続ける）
  - `backend/problems/models.py`（QuizSession の QuerySet・Manager）
  - `backend/problems/views.py`（`QuizSessionViewSet.get_queryset` を `for_user` に）
  - `backend/studylogs/models.py`（7 モデルの QuerySet・Manager）
  - `backend/studylogs/views.py`・`services.py`・`mistake_analysis.py`・`adaptive_selection.py`・`tasks.py`
  - `backend/dashboard/views.py`
  - `backend/studylogs/tests/test_I455_org_scoped_querysets.py`（新規）
- Frontend: なし（応答の形・中身は変えない）
- DB: なし（欄・制約は変えない。Manager の変更は migration に出ない見込みで TC-10 で確かめる）
- Config/Infra: なし（依存の追加なし）

## 4. 変更点一覧

### 修正アプローチ
境界の決まりを、モデルごとの QuerySet のクラス属性に 1 回だけ書く。共通の土台 `OrgScopedQuerySet` が `for_user(user)`（`filter(user=user)` と、属性の経路すべてでの組織の絞り込み）を持ち、各モデルは属性だけを書いたサブクラスを `objects = XQuerySet.as_manager()` にする。呼び出し側は `X.objects.for_user(user)` に置き換え、`subject_path`・`allow_null` を書かなくする。

絞らずに読む箇所は次の基準で扱う（I431 の扱いの基準を変えない）:
- (A) 今 `scope_to_user_org` を通っている読み出し → `for_user` に置き換える（同じ条件なので結果は同じ）
- (B) 今は絞っていないが、`for_user` にしても結果が変わらないと言い切れる読み出し（科目・問題を組織で絞った一覧から渡している／組織の候補から除く ID を集めるだけ）→ `for_user` に置き換える（安全側を標準にする）
- (C) 数だけの集計・印付け・利用者を持たない一括処理・結果が変わりうる重複の確かめ → `objects` のまま残し、直前に `# 組織で絞らない: <理由>` のコメントを書く（`for_user` にすると自組織の数字が変わりうるため・振る舞いを変えない）

既定の `objects` そのものを絞る形は採らない（9 章）。

### 4-1. 土台の QuerySet（`backend/problems/querysets.py`・新規）
**修正方針**: 境界の判定を、モデルを import しないモジュールに置く（QuizSession の循環 import を避ける）。`scope_to_user_org` の本体をここへ移し、`OrgScopedQuerySet` がそれを呼ぶ。

```python
"""
組織の境界つきの取り出し方の土台（モデルを import しない。problems.models から使うため）
"""
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q, QuerySet


def scope_to_user_org(queryset, user, *, subject_path, allow_null=False):
    # 本体は tenant_scope.py から移す（中身・docstring は変えない）
    ...


class OrgScopedQuerySet(QuerySet):
    """
    利用者本人の記録を、組織の境界の中に絞る取り出し方を持つ QuerySet の土台

    サブクラスは subject_paths（記録から科目への経路。複数なら全部で絞る）と
    allow_null（科目が空の記録を残すか）を書く。
    """
    subject_paths: tuple[str, ...] = ()
    allow_null: bool = False

    def for_user(self, user):
        """user 本人の記録で、user の組織の科目を指すもの（allow_null なら科目が空のものも）"""
        if not self.subject_paths:
            raise ImproperlyConfigured(f'{type(self).__name__} に subject_paths がありません')
        queryset = self.filter(user=user)
        for path in self.subject_paths:
            queryset = scope_to_user_org(
                queryset, user, subject_path=path, allow_null=self.allow_null)
        return queryset
```

### 4-2. `backend/problems/services/tenant_scope.py`
**修正方針**: `scope_to_user_org` の定義を消し、`from problems.querysets import scope_to_user_org` で読み込んで公開し続ける（`problems/views.py:818` の QuizAnswer の先読みと、I431 のテスト〔`test_I431_…py:583`〕がここから import するため。I431 のテストのファイルを変えない）。モジュールの docstring に「記録の絞り込みの本体は problems.querysets」を 1 行足す。`available_subjects`・`available_problems` は変えない。

### 4-3. 各モデルの QuerySet と Manager
**修正方針**: 2 章の表の値をクラス属性に書く。`objects = XQuerySet.as_manager()` をモデルの欄の後（`Meta` の前）に置く。

`backend/studylogs/models.py`（`from problems.querysets import OrgScopedQuerySet` を足す）:
```python
class StudyLogQuerySet(OrgScopedQuerySet):
    subject_paths = ('subject',)
    allow_null = True

class ProblemAttemptQuerySet(OrgScopedQuerySet):
    subject_paths = ('problem__subject',)

class SpacedRepetitionCardQuerySet(OrgScopedQuerySet):
    subject_paths = ('problem__subject',)

class SpacedRepetitionReviewQuerySet(OrgScopedQuerySet):
    subject_paths = ('problem__subject',)

class MistakePatternQuerySet(OrgScopedQuerySet):
    subject_paths = ('subject',)
    allow_null = True

class LearningSuggestionQuerySet(OrgScopedQuerySet):
    # 応答の mistake_pattern_description がパターン側の文言を出すため、パターンの科目でも絞る
    subject_paths = ('subject', 'mistake_pattern__subject')
    allow_null = True

class LearningWeaknessQuerySet(OrgScopedQuerySet):
    subject_paths = ('subject',)
```
各モデルに `objects = <名前>QuerySet.as_manager()` を足す。

`backend/problems/models.py`（`from problems.querysets import OrgScopedQuerySet`）:
```python
class QuizSessionQuerySet(OrgScopedQuerySet):
    subject_paths = ('subject',)
    allow_null = True
```
QuizSession に `objects = QuizSessionQuerySet.as_manager()`。

### 4-4. 呼び出し側の置き換え（(A)・(B)）
**修正方針**: `scope_to_user_org(X.objects.filter(user=u, <条件>), u, subject_path=…, allow_null=…)` を `X.objects.for_user(u).filter(<条件>)` に置き換える。並べ替え・`select_related`・`first()`・`get()` などの続きはそのまま。

| ファイル:行 | 置き換え後 |
|---|---|
| studylogs/views.py:39 | `StudyLog.objects.for_user(self.request.user)` |
| studylogs/views.py:158 | `StudyLog.objects.for_user(user).filter(started_at__gte=seven_days_ago).order_by('-started_at')[:10]` |
| studylogs/views.py:264 | `StudyLog.objects.for_user(user).filter(subject=subject)` (B) |
| studylogs/views.py:400 | `SpacedRepetitionCard.objects.for_user(request.user).get(id=data['card_id'])` |
| studylogs/views.py:406 | `StudyLog.objects.for_user(request.user).filter(is_active=True).first()` |
| studylogs/views.py:550 | `SpacedRepetitionCard.objects.for_user(self.request.user).select_related(...)` |
| studylogs/views.py:583 | `SpacedRepetitionReview.objects.for_user(self.request.user).select_related(...)` |
| studylogs/views.py:628 | `MistakePattern.objects.for_user(request.user).filter(is_active=True).order_by(...)` |
| studylogs/views.py:653 | `LearningSuggestion.objects.for_user(request.user).filter(is_active=True)`（続きはそのまま） |
| studylogs/views.py:730 | `LearningWeakness.objects.for_user(request.user).filter(is_resolved=False).order_by(...)` |
| studylogs/services.py:43 | `SpacedRepetitionCard.objects.for_user(self.user).filter(is_active=True, next_review_date__lte=timezone.now())` |
| studylogs/services.py:61 | `SpacedRepetitionCard.objects.for_user(self.user).values_list('problem_id', flat=True)` (B) |
| studylogs/mistake_analysis.py:78・87 | `SpacedRepetitionReview`／`ProblemAttempt` の `.objects.for_user(self.user).filter(<期間>, is_correct=False)` |
| studylogs/mistake_analysis.py:267・273 | `ProblemAttempt`／`SpacedRepetitionReview` の `.objects.for_user(self.user).filter(problem__subject=subject, <期間>)` (B) |
| studylogs/mistake_analysis.py:311・320・493・498・503 | 各 `.objects.for_user(self.user).filter(<条件>)`。`scope_learning_suggestions` の関数は消す |
| studylogs/adaptive_selection.py:297・302 | `ProblemAttempt`／`SpacedRepetitionReview` の `.objects.for_user(self.user).filter(<期間>).values_list(...)` (B) |
| studylogs/adaptive_selection.py:417 | `ProblemAttempt.objects.for_user(self.user).filter(problem=problem, <期間>).count()` (B) |
| dashboard/views.py:34・40・217・278 | `StudyLog`／`QuizSession` の `.objects.for_user(user).filter(<条件>)` |
| dashboard/views.py:143 | `StudyLog.objects.for_user(user).filter(subject=subject)` (B) |
| dashboard/views.py:302 | `StudyLog.objects.for_user(user).filter(started_at__date__gte=week_ago).values_list(...)` (B) |
| problems/views.py:812 | `QuizSession.objects.for_user(user)`（:818 の QuizAnswer は 8 モデル外なので `scope_to_user_org` のまま） |

使わなくなった import（`scope_to_user_org`・`scope_learning_suggestions`）は消す。

### 4-5. 絞らない箇所の理由のコメント（(C)）
**修正方針**: 1 章の「扱いの表」で (C) の各取り出しの直前（呼び出しの先頭の行から 3 行以内）に、次のどれかを書く。同じ関数の中で続く複数の取り出しは、最初の 1 つの前の 1 行で足りる場合も、静的テスト（4-6）がそれぞれの行を見るので、それぞれの直前に書く。
- `# 組織で絞らない: 件数・時間・正答率だけの集計（中身を返さない・I431 扱いの基準 3）`
- `# 組織で絞らない: 自分の記録への印付け（応答は固定の文言・I431 扱いの基準 3）`
- `# 組織で絞らない: 利用者を持たない一括処理（中身を外に出さない）`
- `# 組織で絞らない: 重複の確かめだけ（応答に出ない。絞ると古いデータで結果が変わりうる）`

### 4-6. テスト（`backend/studylogs/tests/test_I455_org_scoped_querysets.py`・新規）
**修正方針**: 各 QuerySet の境界の決まりを直接確かめる単体テストと、付け忘れを止める静的テストを足す。データの作り方は I431 のテストのやり方（組織 A・B、各組織の科目・問題、組織に属さない利用者、各テストの前後で cache を消す）にそろえる。
- `test_for_user_scopes_by_org`（8 モデルでパラメータ化）: 組織 A の利用者 `user_a` の記録として、自組織の科目（問題）を指すもの・他組織の科目を指すもの・科目が空のもの（空を許すモデルだけ）を作り、同じ組織の別の利用者 `user_a2` の自組織の記録も作る。`for_user(user_a)` が自組織の記録と（allow_null なら）科目が空の記録だけを返す（TC-01）
- `test_for_user_noorg_user`（8 モデル）: 組織に属さない利用者は、allow_null なら科目が空の自分の記録だけ、そうでなければ空（TC-02）
- `test_learning_suggestion_both_paths`: 提案の科目が自組織でもパターンの科目が他組織なら外れ、パターンの科目が自組織でも提案の科目が他組織なら外れる。両方自組織・両方空は残る（TC-03）
- `test_base_without_subject_paths_raises`: `OrgScopedQuerySet` をそのまま使う Manager で `for_user` を呼ぶと `ImproperlyConfigured`（TC-04）
- `test_unscoped_reads_have_reason_comment`: `backend/studylogs/`・`backend/dashboard/` のテスト以外の `.py` を `ast` で読み、`<8 モデル名>.objects.<メソッド>` の呼び出しのうち、メソッドが `for_user`・`create`・`get_or_create`・`update_or_create`・`bulk_create` 以外のものについて、その行と直前 3 行のどこかに `組織で絞らない` があることを確かめる（基準の行は、モデル名が書かれた行＝`<モデル>.objects` の `ast.Attribute` の `lineno`。複数行の呼び出しでも先頭の行）。無ければファイル名と行番号を並べて落ちる（TC-06）

## 5. 実装手順
- ステップ 1（未知リスク先行・土台）: 4-1・4-2・4-3（8 モデルの QuerySet と Manager）を入れる。migration が出ないこと（TC-10）、循環 import が無いこと（TC-08 の収集が通る）を先に確かめる。出たら計画を直す
- ステップ 2（ステップ 1 が前提）: 4-6 の単体テスト（TC-01〜TC-04）を足して通し、失敗の注入（TC-09）で RED を確かめる
- ステップ 3（ステップ 1 が前提）: 4-4 の置き換えと、使わなくなった import の削除 → TC-05・TC-08
- ステップ 4（ステップ 3 が前提）: 4-5 のコメントと 4-6 の静的テスト → TC-06・TC-07
- ステップ 5: /simplify の後に TC-05・TC-08・TC-10・TC-13 を流し直す（→ TC-12）

## 6. テスト計画
- 自動: docs/tests/open/I455_auto_test.md（単体テスト・静的テスト・守りにする既存の越境テスト・migration の確かめ・grep の不在の確かめ）。テストレベルは単体（QuerySet）と結合（既存の API の越境テスト）。新しい E2E は無し（画面の振る舞いを変えないため）
- 手動: docs/tests/open/I455_manual_test.md（ダッシュボード・学習の画面の無退行。Claude が Playwright MCP で行う）
- 再発防止: 静的テスト（TC-06）が、8 モデルを絞らずに読む新しい行を、理由のコメントなしでは通さない

## 7. ロールバック
コードだけの変更（DB の形は変えない）。PR を revert すれば戻る。サービスの再起動は通常のデプロイだけ。

## 8. Risk & 回避策
- R1 置き換えで条件を落とす・取り違える → 既存の I431・I166・#446 のテストを変えずに流す（TC-08）。(A) は I431 と同じ値をモデルに書き、TC-01〜TC-03 で直接確かめる
- R2 (B) の置き換えで結果が変わる → (B) に入れたのは、渡す科目・問題がもう組織で絞られている／組織の候補から除く ID を集めるだけの箇所に限った（1 章の表に根拠）。言い切れないもの（重複の確かめ）は (C) にした
- R3 Manager の変更で migration が出る → Django は名前が `objects` で `use_in_migrations` の無い Manager を migration に書かない。TC-10 と CI（ci.yml:38）で確かめる
- R4 循環 import → 4-1 のモジュールはモデルを import しない。TC-08 のテストの収集で確かめる
- R5 静的テストのすり抜け（`user.studylog_set` などの関連の取り出し・変数に入れたモデル・`getattr`）→ 普通の書き方（`<モデル>.objects.<メソッド>`）の付け忘れを止める範囲と割り切る（わざとの回避は対象外）。API の経路は #446 の横断テストが別に見る
- R6 既存の `objects.filter(user=...)` の呼び出しを、このイシュー以外の場所（`backend/core/tasks.py:127-130` など）で変えない → 対象は `studylogs`・`dashboard` と `problems/views.py:812` だけ（イシューのスコープ）

## 9. 確定事項と自律判断
**イシューに明記されていること**:
- 8 モデルに QuerySet と Manager を持たせ、呼び出し側を `for_user` にする・`scope_learning_suggestions` を LearningSuggestion の QuerySet に移す
- 判定の部品は problems に残し、problems から studylogs への依存を作らない
- 振る舞いを変えない・数だけの集計は残して理由をコメントで書く・DB の形は変えない
- 守りのテスト（I431・I166・#446）と、各 QuerySet の単体テスト（LearningSuggestion の 2 経路・失敗の注入）

**Claude が技術的に決めたこと（理由）**:
- 既定の `objects` を絞る形ではなく、別名のメソッド `for_user(user)` にした — 既定の取り出し口は利用者を受け取れず、絞るにはスレッドごとの「今の利用者」を持つ仕組みが要る（暗黙の状態で、管理画面・非同期処理・一括処理・関連の取り出しが壊れるか、知らずに素通りになる）。`for_user` を標準にし、絞らない読み出しを静的テスト（TC-06）で止めて「安全側を標準」を作りで担保する
- 土台 `OrgScopedQuerySet` をクラス属性で設定する形にした — モデルごとの決まりがクラス定義の 2 行に集まり、AC1 の「1 か所で決まる」を満たす。8 個の別々の `for_user` の実装は、取り違えの余地を増やす
- `scope_to_user_org` を `problems/querysets.py` に移し、`tenant_scope.py` から読み込んで公開し続ける — QuizSession（`problems/models.py`）から使うと `tenant_scope` → `problems.models` の循環 import になるため。公開し続けるのは QuizAnswer の先読みと I431 のテストのファイルを変えないため（AC4）
- `problems/views.py:812`（QuizSession）も `for_user` にした — イシューの実装対象の表には無いが、QuizSession の QuerySet を足す以上、同じモデルの同じ形の呼び出しを残すと境界が 2 か所になる（AC1 の趣旨）。結果は同じ（I446 の TC-01 で守る）。QuizService（`problems/services/quiz_service.py`）の書き込み・更新は変えない（イシューの「含まない」）
- 絞らない箇所の扱いを (A)・(B)・(C) に分けた（4 章）。(B) を `for_user` にするのは結果が同じと言い切れる箇所だけ — 「安全側を標準」に寄せつつ、振る舞いを変えない
- `tasks.py` は、イシューの「含む」に「利用者を受け取る非同期処理は `for_user` を使う」とあるが、利用者を受け取るタスク（`update_user_proficiency_task`・`generate_learning_insights_task`・`export_user_data_task`）のうち、8 モデルを直接読むのは `export_user_data_task`（件数だけを返す）だけで、ほかはサービス（4-4 で `for_user` 済み）を呼ぶ。`export_user_data_task` を `for_user` にすると件数が変わる（振る舞いを変えない、のほうを優先）ので (C) にした
- 書き込み（`create`・`get_or_create`）は「取り出し」に含めない — キーの科目・問題は組織で絞った読み出しから来る。静的テストも除く
- 付け忘れを止める静的テスト（TC-06）を CI に常設する — 新しい処理で絞らずに読むのは「普通の書き方で気づかずに壊し、気づきにくく、壊れると他組織のデータが漏れる」決まりに当たる（plan-writing-rules の決定論テストの選び方）。#446 は API の経路だけを見て、サービスの内部と非同期処理を見ない
- テストの置き場所は `backend/studylogs/tests/test_I455_org_scoped_querysets.py`（QuizSession もここ）— 8 モデルのうち 7 つが studylogs で、I431 のテストと同じ場所にそろえる
- `for_user` に組織に属さない利用者・匿名の利用者を渡したとき: 組織に属さない利用者は I431 のまま（allow_null なら科目が空の記録だけ・そうでなければ空）。匿名の利用者は呼び出し元がすべて `IsAuthenticated` の後なので扱わない（今と同じ）

**要件適合性・業務ロジック**: 受け入れ条件を超える仕様の追加・変更は無い。閲覧範囲は I431 のまま（本人の記録で、組織の科目を指すもの＋モデルによっては科目が空のもの。全体共有の科目は含めない）。ステータス遷移・承認条件は扱わない。境界の値: 組織に属さない利用者・科目が空の記録・同じ組織の別の利用者・提案の 2 経路の食い違いをテストで確かめる。

**セキュリティ・BP**: 入力の検証は変えない（読み出しの絞り込みの整理だけ）。認可は「本人＋組織」を 1 か所に集める変更で、最小権限は変わらない。機密データの扱い・OWASP（A01 の再発を作りで防ぐ方向）・Django の推奨（独自の QuerySet と `as_manager()`）に沿う。依存の追加なし。bandit は MEDIUM 以上を直す（新しいコードに該当なし見込み）。

**P3/P5/P8 影響なし**: DB の形・外部 API・非同期処理の動き・インフラは変えない（tasks.py はコメントだけ）。
**P6 影響なし**: UI の変更なし。クエリは同じ条件のまま（(B) は条件が 1 つ増えるだけで、JOIN は既存の `problem__subject`／`subject` と同じ）。
**P9（プライバシー）**: テナントデータの読み出しの整理。閲覧範囲は変えない（15 章は不要と判断。越境は増えず、静的テストで新しい越境の付け忘れを止める）。

**台帳の残りの一覧**:
- 一覧 I224.md F9: 残す — ハーネスの項目で、このイシューの変更点と関係しない（`FILE=-`）
- 一覧 I223.md B1〜B4: 残す — bot の停止に関する項目で、このイシューの変更点と関係しない（`FILE=-`）
- 実装対象のファイルに当たる行は無し

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | 8 モデルの `for_user` が、I431 で各呼び出し側に書いていた条件（2 章の表の科目への経路・空を許すか）と同じ記録を返す。特に LearningSuggestion は `subject` と `mistake_pattern__subject` の両方で絞り、空を許すかの取り違えが無い（TC-01〜TC-03 の PASS と、TC-09 の FG で RED を実測） |
| V2 | 1 | 実験必須 | 置き換えの後も、I431・I166・#446 の越境テストがファイルを変えずにすべて通る（TC-08・TC-13） |
| V3 | 2 | 読んで可 | (B) に分けた箇所（studylogs/views.py:264・services.py:61・mistake_analysis.py:267・273・adaptive_selection.py:297・302・417・dashboard/views.py:143・302）が、渡す科目・問題が組織で絞られている／組織の候補から除く ID を集めるだけで、`for_user` にしても結果が変わらない（1 章の扱いの表の根拠と、各関数のコード。実装の時に各箇所のコードで根拠を確かめ直し、言い切れなければ (C) に戻す。I431 のテストが (B) の箇所の経路〔`by_subject`・ダッシュボード・`daily_plan`〕を通ることは TC-08 で確かめる） |
| V4 | 2 | 読んで可 | (C) に分けた箇所が、数だけ・印付け・利用者を持たない一括処理・応答に出ない重複の確かめで、他組織の科目・問題の名前・本文・ID を応答に出さない（I431 の扱いの基準 3 のまま） |
| V5 | 3 | 実験必須 | 静的テスト TC-06 が、8 モデルの `<モデル>.objects.<読み出し>` を理由のコメントなしで足すと落ち、コメントを消しても落ちる（TC-07 の FG を実測）。複数行の呼び出し・`filter(**kwargs)` の形でも見落とさない |
| V6 | 2 | 実験必須 | Manager の差し替えで migration が出ず（TC-10）、循環 import が無い（TC-08 の収集が通る） |

## 計画変更記録
- plan-review（20261112_0921）の指摘への対応: 「必ず確かめる項目」の節を足した（Blocker）・TC-05 と TC-08 のコマンドを表の外のコードブロックに出し、TC-08 を TC-08（pytest）と TC-13（守りのテストのファイルが変わっていない）に分けた（Warning）・イシューとのずれ（`export_user_data_task` を `for_user` にしない）を下に記録（Warning）。計画レビューのやり直し: 要（Blocker の節の追加）
- イシューとのずれ: イシューの「含む」の「利用者を受け取る非同期処理は `for_user` を使う」のうち、`export_user_data_task` は件数だけを返すため `for_user` にせず理由のコメントにした（件数が変わると「振る舞いを変えない」に反する。9 章）。ほかの利用者を受け取るタスクはサービス経由で `for_user` になる
- plan-review（20261112_0923）の指摘への対応: TC-05 の正規表現を呼び出し側の形（`scope_to_user_org`・`scope_learning_suggestions`・`subject_path=`・`allow_null=`）に絞り、AC2 の文言を合わせた（Blocker。4-3 のクラス属性に当たって正しい実装でも不合格になるため）・TC-06 の基準の行を 4-6 に明記・V3 に実装時の確かめ直しを追記・TC-13 の基点を `99b17757` に固定（Warning・Info）。計画レビューのやり直し: 要（AC2 の文言を変えた）
- plan-review（20261112_0925・HIGHRISK）の Warning への対応: TC-10 の FG の手順を具体化（`Manager.from_queryset` に `use_in_migrations=True` を付けた Manager に一時的に差し替える）。`problems/views.py:812` は 9 章に理由を記録済みで、イシュー（GitHub が正）の表は変えない。(B) の箇所は implement で各箇所のコードを確かめ直し、言い切れなければ (C) に戻して計画変更記録に書く（V3）。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件を変えない）
- implement: TC-05 の正規表現から `allow_null=` を外した — 計画の記載「`scope_to_user_org|scope_learning_suggestions|subject_path=|allow_null=`」が、DRF の入力欄の設定（`backend/studylogs/serializers.py:11・29・304` の `allow_null=True`。境界の指定ではない）に当たり、正しい実装でも不合格になるため。`allow_null=` は `scope_to_user_org` の引数としてしか境界の意味を持たず、その呼び出しが無いことは同じ TC で確かめるので、守る力は変わらない。AC2 の文言を「呼び出し（とその引数）」に合わせた。計画レビューのやり直し: 不要（受け入れ条件の意味・方式・範囲を変えない TC の誤検出の直し）
- implement: (B) の各箇所を実装の時にコードで確かめ直した（V3）。`studylogs/views.py:264`・`dashboard/views.py:143` の科目は `get_user_selected_subjects`（`core/subject_service.py:106-160`・`organization_id=user.organization_id` で絞る）、`mistake_analysis.py:267・273` は `available_subjects`、`adaptive_selection.py:417` の問題は `available_problems` の候補、`services.py:61`・`adaptive_selection.py:297・302`・`dashboard/views.py:302` は組織で絞った一覧から除く ID を集めるだけ。どれも言い切れたので (C) に戻したものは無い
- implement（/simplify）: 静的テストの対象モデルを、テストの表（SPECS）ではなくモデルの登録（既定の取り出し口が `OrgScopedQuerySet` のもの）から集め、表と一致することも確かめるテスト（`test_specs_cover_all_scoped_models`）を足した — 9 つ目のモデルに QuerySet を足したとき、表への足し忘れで静的テストの対象から漏れないため。理由のコメントの言い回しを 5 種類にそろえた。計画レビューのやり直し: 不要（4-6 のテストの対象の集め方の細部・方式は同じ）

## レビュー結果
- [20261112_0925 判定: ✅ 完了](../../reviews/I455_plan_review_20261112_0925.md)
- [20261112_0923 判定: 差し戻し（Blocker 1件）](../../reviews/I455_plan_review_20261112_0923.md)
- [20261112_0921 判定: 差し戻し（Blocker 1件）](../../reviews/I455_plan_review_20261112_0921.md)

## セキュリティレビュー結果

**実施日**: 2026-11-12

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | マルチテナント | 置き換え（(A)・(B)）で、モデルの QuerySet に書いた経路・空を許すかが I431 の呼び出し側の値と食い違うと、他組織の記録が一覧・詳細に出る（特に LearningSuggestion の 2 経路と、空を許さないモデルに `allow_null = True` を書く取り違え） | 2 章の表の値を各 QuerySet のクラス属性にそのまま書く。TC-01〜TC-03 で 8 モデルを直接確かめ、TC-09 の失敗の注入で RED を実測する。I431・I166・#446 のテストをファイルを変えずに通す（TC-08・TC-13） |
| Medium | マルチテナント | (B) の置き換えは「結果が変わらない」と読んだ判断。根拠が外れると、自組織の数字が変わる（越境は増えない方向） | implement で各箇所のコードを確かめ直し、言い切れなければ (C) に戻す（V3）。`for_user` は絞る方向にしか働かないので、外れても他組織のデータが増えて出ることは無い |
| Low | マルチテナント | 静的テスト（TC-06）は `<モデル>.objects.<メソッド>` の直書きだけを見る。関連の取り出し（`user.study_logs`・`user.quiz_sessions` など `related_name` 経由）・変数に入れたモデルはすり抜ける | 普通の書き方の付け忘れを止める範囲と割り切る（R5）。API の経路は #446 の横断テストが別に見る。関連の取り出しの付け忘れは残余リスクとして retro で処遇を決める |
| Low | 認証・認可 | `for_user` に匿名の利用者を渡すと `organization_id` の参照で例外（500）になる | 呼び出し元はすべて `IsAuthenticated` の後（今と同じ）。例外は他組織のデータを出さない（fail-closed） |
| なし | 入力検証 | 入力の検証は変えない（読み出しの整理だけ） | — |
| なし | 機密情報 | ログ・応答に出す欄は変えない | — |
| なし | OWASP Top 10 | A01（認可の不備）を作りで防ぐ方向の変更。SQL は ORM のまま（Raw SQL なし）。CSRF・XSS は対象外 | — |
| なし | ファイル操作 | 該当なし | — |
| なし | 外部通信 | 該当なし（`send_study_reminders_task` などはコメントだけ） | — |
| なし | 依存ライブラリ | 追加なし | — |

既定の `objects` を差し替えても、管理画面（`backend/studylogs/admin.py`・`backend/problems/admin.py`）・関連の取り出し・`QuizService` の作成と更新は、`for_user` を呼ばない限り今と同じ記録を扱う（`as_manager()` は既定の取り出しを変えない）。

### 攻撃シナリオレビュー

新しいエンドポイントは無い。変わるのは既存の経路の読み出しの書き方。

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `GET /api/study/logs/`・`/api/study/sr-cards/`・`/api/study/sr-reviews/`・間違い分析の `patterns`・`suggestions`・`weaknesses`・`GET /api/quiz/` | 一般（組織 A） | 組織を移った利用者が、前の組織 B の科目・問題を指す自分の記録の一覧・詳細を読む | 他組織の科目・問題を指す記録が出ない（空を許すモデルだけ科目が空の記録が出る） | Yes: TC-01〜TC-03（QuerySet）・TC-08（I431・I166・#446 の API） | No | なし | Medium |
| 2 | 同上の詳細（`<pk>`） | 一般（組織 A） | 同じ組織の別の利用者の記録の番号を入れる | 存在しない番号と同じ 404 | Yes: TC-01 の `user_a2`・TC-08 の #446 の `same_org` | No | なし | Medium |
| 3 | 間違い分析の `suggestions` | 一般（組織 A） | 提案の科目は自組織だが、パターンの科目が組織 B の提案を読み、パターン側の文言（科目名入り）を得る | パターンの科目でも絞られて出ない | Yes: TC-03 | No | なし | Medium |
| 4 | ダッシュボード `GET /api/dashboard/overview/`・`analytics/`・おすすめ | 一般（組織 A） | 前の組織の科目を指す自分の記録から、科目名を得る | 科目名が出ない（数だけの集計は今と同じ） | Yes: TC-08（I431 のダッシュボードの TC） | Yes: 手動 No.1（自組織の表示の無退行） | なし | Medium |
| 5 | 新しく足すサービス・非同期処理（I452 以降） | 開発者の付け忘れ | 8 モデルを `objects.filter(user=...)` で読み、他組織の中身を返す | 理由のコメントの無い読み出しは CI で落ちる | Yes: TC-06・TC-07 | No | 関連の取り出し・変数経由はすり抜ける（R5） | Low |
| 6 | 組織に属さない利用者 | 一般（組織なし） | 自分の記録の一覧を読む | 空を許すモデルは科目が空の記録だけ、ほかは空 | Yes: TC-02 | No | なし | Low |

## レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 2件 | 4件 |
| Low     | 2件 | 2件 |

### 残余リスク処遇
（retro 段階で決定する）
