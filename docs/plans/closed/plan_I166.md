## 基本情報
- **計画書ID**: plan_I166
- **関連イシュー**: #284
- **Draft PR**: #330
- **作成根拠資料**: docs/issues/closed/I166.md（起点イシュー・grill-me 実施済み 2026-10-25）
- **実装後評価**: docs/reviews/closed/I166_review.md
- **作成日**: 2026-10-25

---

## 1. 背景/目的

クイズの開始・出題・回答で組織の境界を確かめておらず、他組織の科目でクイズを始めたり、他組織の問題の正解・解説を取得したりできる。これを塞ぎ、回帰テストで固定する。

- **原因の概要**: クイズの API だけが「その科目・問題がユーザーの組織のものか」を確かめていない。科目・問題の管理 API は確かめているが、クイズの経路では書き漏れていた。
- **詳細な原因分析**:
  1. 開始（`POST /api/quiz/`）: `QuizSessionSerializer.subject`（`backend/problems/serializers.py:306-319`）は `ModelSerializer` が自動で作る `PrimaryKeyRelatedField(queryset=Subject.objects.all())`。どの組織の科目 ID でも通り、`QuizService.start_session`（`backend/problems/services/quiz_service.py:24-68`）がそのままセッションを作る。
  2. 開始時の問題数: `start_session` の `Problem.objects.filter(is_deleted=False)`（56 行目）は、科目なしのとき全組織の問題を数える。
  3. 出題（`GET /api/quiz/<id>/next_problem/`）: `QuizService.get_next_problem`（90-94 行目）は `session.subject` で絞るだけで、科目なしのセッションでは全組織の問題から出す。
  4. 回答（`POST /api/quiz/<id>/submit_answer/`）: `backend/problems/views.py:911-917` が `Problem.objects.get(id=problem_id, is_deleted=False)` で、組織もセッションの科目も照合しない。応答に正解の選択肢（`correct_choices`）と解説（`explanation`・`explanation_image`）を含めて返す（964-976 行目）。
- **根本原因（コードレベル）**: 「クイズで扱ってよい科目・問題」を決める処理が 1 か所に無く、各所で `Subject.objects` / `Problem.objects` をそのまま使っている。

**解決方針（grill-me で確定・2026-10-25）**: 「クイズで扱ってよい科目・問題」＝ユーザーの組織の科目・問題を `QuizService` の 2 つのメソッドに集め、開始（シリアライザ）・開始時の問題数・出題・回答のすべてがそれを通るようにする。他組織のものは「存在しない」と同じ応答で断る。

## 調査結果

### 環境前提確認（2026-10-25 実施）
- app-1 ワークツリー用に `bash scripts/claude/wt-ports.sh`（offset=20・backend 8020・frontend 3020・db 5452）→ `docker compose up -d db redis backend` で起動（backend healthy）。frontend は手動テスト No.3 の前に `docker compose up -d frontend` で起動する。
- DB は PostgreSQL（CI も `postgres:15-alpine`）。lint は pre-commit（ruff・bandit。`.pre-commit-config.yaml`）でホストの `pre-commit` が使える（コミット時のフックで動作を確認済み）。
- E2E は `docker compose --profile e2e run --rm e2e`（`e2e-init` が `seed_e2e --scenario tenant_isolation` と `quiz_session` を実行）。ホストの Playwright は chromium が起動できない（I158 の記録）ため compose の e2e コンテナで実行する。

### 既存テストの事前実行（baseline・2026-10-25）
- Backend: `docker compose exec -T backend python -m pytest --tb=short -q` → **123 passed**（app-1 のコンテナ）。

### 既存データ（primary の dev DB・読み取りのみ・2026-10-25）
- セッション 124 件（科目なし 28 件）・回答 44 件。他組織の科目のセッション **0 件**、他組織の問題への回答 **0 件**、セッションの科目と違う問題への回答 **0 件**、問題と科目で組織が食い違う問題 **0 件**、`organization` が空の問題 0 件。
- `organization` が空の科目（モデル上は「全体共有科目」）**0 件**・その問題 0 件。`organization` が空のユーザー 0 件。
- → 削除・修正するデータは無い（Danger Ops なし）。

### コード読解による確定事項
- `QuizSessionViewSet`（`backend/problems/views.py:813-993`）: `permission_classes = [permissions.IsAuthenticated]`・`get_queryset` は `QuizSession.objects.filter(user=self.request.user)`（本人のセッションのみ）・`http_method_names = ['get', 'post', 'head', 'options']`。`self.get_serializer()` は `context` に `request` を入れる（DRF の `GenericAPIView.get_serializer_context`）。
- 他の API の組織の絞り方: 問題一覧 `ProblemViewSet.get_queryset`（`views.py:166-171`）は `subject__organization=self.request.user.organization`。科目一覧は `SubjectService.get_user_subjects`（`backend/core/subject_service.py:24-74`・`Subject.objects.filter(organization=org_id)`・組織なしのユーザーは `none()`）。どちらも「全体共有科目（`organization` が空）」は含めない。
- `Problem.organization` は null 可（`models.py:116-123`・「データ移行中」）。既存テスト `backend/problems/tests/test_views.py:39-46` は `organization` を付けずに問題を作っている。→ 問題の組織は **`subject__organization_id` で判定する**（`Problem.organization_id` は使わない）。
- `SubjectService.get_user_subjects` はキャッシュ（`subjects_org_{org_id}_count_*`）から ID を復元する経路を持つ。境界の判定に使うと、キャッシュの内容が判定を左右する。→ 判定はキャッシュを通さない。
- DRF の `PrimaryKeyRelatedField` は `get_queryset()` を上書きすると `queryset` 引数なしで使える（`RelatedField.__init__` が上書きを検出して assert を省く）。存在しない ID と queryset の外の ID は同じ `does_not_exist` エラー（400）になる。
- エラーの形: シリアライザの検証エラーは `custom_exception_handler`（`backend/core/exceptions.py:7-71`）で `{"error": {"main_message": "入力内容にエラーがあります", "sub_message": <最初のエラー>, "details": {"subject": [<エラー>]}}}` になる。`submit_answer` の「問題が無い」は `Response({'error': 'Problem not found'}, status=404)`（既存の形）。
- 呼び出し元: `QuizService.start_session` は `views.py:842` と `test_I158_quiz_session_start.py:361` から。`QuizService.get_next_problem` は `views.py:877` のみ。`QuizSessionSerializer` は `create`（入力・出力）・`submit_answer` の応答（出力のみ・context なし）・`test_serializers.py`（出力のみ）から使われる。
- 画面の科目なし開始: 問題管理の「クイズを実行」（`frontend/src/pages/QuizManagement.tsx:476`）・ダッシュボードのおすすめ「練習する」（`frontend/src/pages/Dashboard.tsx:499`）。科目ありの開始はダッシュボードの「クイズを始める」（`Dashboard.tsx:191,202`・`/api/user/subjects/` の科目＝自組織の科目）と完了画面の「もう一度挑戦」（`frontend/src/pages/QuizSession.tsx:349`・終えたセッションの `subject`）。
- 既存テストへの影響: 既存のクイズのテスト（`test_views.py`・`test_I078_is_correct_exposure.py`・`test_I158_quiz_session_start.py`・`test_serializers.py`）は、すべてユーザーと科目が同じ組織。今回の変更で期待値は変わらない。

### 適用規約（rules/ 抽出）
- Django（`rules/ultimate_django_coding_standards.md`）: 業務ロジックはサービス層・ビューは薄く（§6）。クエリは ORM のみ。テストは pytest＋fixture・`rest_framework.status` の定数で assert（§9）。
- 読み取り専用の絞り込みは規約上「セレクタ」（§6）だが、このアプリには `selectors.py` が無く、クイズの読み取り処理（`get_next_problem`）も `QuizService` にある。境界の判定を 1 ファイルに集めるため `QuizService` に置く（設計判断の明示を参照）。

## 2. 受け入れ条件（Acceptance Criteria）
イシューの AC（grill-me 後）。具体値はテスト文書で固定する:
- [ ] 他組織の科目 ID でクイズを開始すると、存在しない科目 ID と同じ 400 で拒否され、セッションが作られない（TC-01）
- [ ] 科目なしでクイズを開始できる（従来どおり）が、`total_problems` と出題は自組織の問題だけになり、他組織の問題が出題されない（TC-03・TC-04・手動 No.3）
- [ ] 他組織の問題、またはセッションの科目外の問題の `problem_id` で回答すると、存在しない問題と同じ 404 で拒否され、回答が保存されず、正解・解説が返らない（TC-05・TC-06）
- [ ] 終えたセッションの `subject` で開始し直す経路（完了画面の「もう一度挑戦」）にも同じ組織チェックがかかる（TC-08）
- [ ] 自組織の科目では、従来どおりクイズを開始・出題・回答できる（無退行）（TC-02・TC-07・TC-21・TC-23・手動 No.4）
- [ ] 上記を検証するバックエンドの回帰テスト（`test_I166_quiz_tenant_isolation.py`）が追加され、全テストが pass する（既存テストの件数を減らさない）（TC-21）
- [ ] dev DB の既存データの調査結果（越境 0 件）が記録されている（本計画「調査結果」・手動 No.1）

## 3. 影響範囲
- **Backend**: `problems/services/quiz_service.py`（境界の判定メソッド 2 つを追加・開始時の問題数と出題で使う）・`problems/serializers.py`（`QuizSessionSerializer.subject` の受け付けを限定）・`problems/views.py`（`submit_answer` の問題の取得）・テスト 1 ファイル追加
- **Frontend**: なし（科目なしの開始は従来どおり動く。他組織の科目は画面の通常操作では送らない）
- **E2E**: なし（既存 E2E の全件 pass で無退行を確かめる・TC-23）
- **DB**: なし（スキーマ変更なし・既存データは越境 0 件）
- **API 契約**: 正常な使い方（自組織の科目・問題）の応答は変わらない。他組織の科目での開始は 201 → 400、他組織・科目外の問題への回答は 200 → 404 になる。科目なしセッションの `total_problems`・`total_problems_in_subject` が自組織の問題数になる
- **Config/Infra**: なし。依存関係ファイルの変更なし → Dockerfile / compose への波及なし
- **Docs**: なし

## 4. 変更点一覧

| ファイル | 対象 | 変更内容 |
|---------|------|---------|
| `backend/problems/services/quiz_service.py` | `QuizService` | `available_subjects(user)`・`available_problems(user, subject)` を追加。`start_session` の問題数（56-58 行目）と `get_next_problem` の出題対象（90-94 行目）をこれに置き換える |
| `backend/problems/serializers.py` | 新規クラス `QuizSubjectField`・`QuizSessionSerializer`（306 行目〜） | `subject = QuizSubjectField(required=False, allow_null=True)` を宣言し、受け付ける科目を `QuizService.available_subjects(request.user)` に限定する |
| `backend/problems/views.py` | `QuizSessionViewSet.submit_answer`（911-917 行目） | 問題の取得を `QuizService.available_problems(session.user, session.subject).get(id=problem_id)` にする（無ければ既存どおり 404） |
| `backend/problems/tests/test_I166_quiz_tenant_isolation.py`（新規） | — | TC-01〜TC-11 |

`QuizSessionViewSet` の `create`・`next_problem`・`end`・`retrieve`・`list` は変更しない（`create` はシリアライザ、`next_problem` はサービスの変更で守られる。`end`・`retrieve`・`list` は本人のセッションだけを扱い、越境したデータも無い）。

### 修正アプローチ
「クイズで扱ってよい科目・問題」を `QuizService` の 2 つのメソッドで定義し、入口（開始の科目）とデータの取り出し（開始時の問題数・出題・回答）の両方をそれに通す。入口で断るだけでなく取り出しでも絞るので、もし他組織の科目を持つセッションが何かの経路でできても、他組織の問題は出ない・答えられない（多層防御）。他組織のものは、存在しないものと同じ応答で断り、あるかどうかを推測させない。

### 修正項目 1: 境界の判定を `QuizService` に集める
**修正方針**: 「ユーザーの組織の科目」と「ユーザーの組織の未削除の問題（科目の指定があればその科目）」を返すメソッドを足す。組織に属さないユーザーは何も使えない（`none()`）。全体共有科目（`organization` が空）は、他の API と同じく含めない。判定はキャッシュを通さず DB を直接引く。

```python
from django.db.models import QuerySet


class QuizService:
    """クイズセッション関連のビジネスロジック"""

    @staticmethod
    def available_subjects(user) -> QuerySet[Subject]:
        """
        クイズで指定してよい科目（ユーザーの組織の科目）

        組織に属さないユーザーは空。境界の判定のためキャッシュは使わない。
        """
        if user.organization_id is None:
            return Subject.objects.none()
        return Subject.objects.filter(organization_id=user.organization_id)

    @staticmethod
    def available_problems(user, subject: Optional[Subject]) -> QuerySet[Problem]:
        """
        クイズで出題・回答してよい問題（ユーザーの組織の未削除の問題・科目の指定があればその科目）

        問題の組織は subject 経由で判定する（Problem.organization は null 可のため使わない）。
        """
        if user.organization_id is None:
            return Problem.objects.none()
        problems = Problem.objects.filter(
            is_deleted=False, subject__organization_id=user.organization_id
        )
        if subject is not None:
            problems = problems.filter(subject=subject)
        return problems
```

`start_session` の 56-58 行目:
```python
                session = QuizSession.objects.create(
                    user=user,
                    subject=subject,
                    client_request_id=client_request_id,
                    total_problems=QuizService.available_problems(user, subject).count(),
                )
```

`get_next_problem` の 89-94 行目:
```python
        # 出題対象（セッション所有者の組織の問題・科目の指定があればその科目）
        total_problems_queryset = QuizService.available_problems(
            session.user, session.subject
        )
```
- `get_next_problem` は以降の処理（未回答の選択・復習モード）を変えない。
- `start_session` には「科目が組織のものか」の検査を足さない。入口の検査はシリアライザが行い、サービスはどの科目が渡されても自組織の問題しか数えない・出さない（二重の判定を作らない）。

### 修正項目 2: 開始で受け付ける科目を限定する（シリアライザ）
**修正方針**: `subject` の受け付け対象を `QuizService.available_subjects(request.user)` にする。DRF の主キー指定のフィールドの検証に乗せるので、他組織の科目と存在しない科目は同じ 400（`does_not_exist`）になり、セッションは作られない。応答の `subject`（科目 ID）の形は変わらない。

```python
from problems.services.quiz_service import QuizService


class QuizSubjectField(serializers.PrimaryKeyRelatedField):
    """クイズで指定できる科目（リクエストユーザーの組織の科目）だけを受け付ける"""

    def get_queryset(self):
        request = self.context.get('request')
        if request is None:
            return Subject.objects.none()
        return QuizService.available_subjects(request.user)


class QuizSessionSerializer(serializers.ModelSerializer):
    subject = QuizSubjectField(required=False, allow_null=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    ...（以降は現行どおり）
```
- `required=False, allow_null=True` は、現在 `ModelSerializer` が null 可の FK に自動で付けているものと同じ（科目なしの開始・`"subject": null` の両方を従来どおり受け付ける）。
- `request` が無い（context なし）ときは何も受け付けない（fail-closed）。出力（`to_representation`）は `get_queryset` を使わないため、`submit_answer` の応答や `test_serializers.py` のような context なしの出力は変わらない。
- `QuizSessionDetailSerializer` は `QuizSessionSerializer` を継承するため同じフィールドになる（`retrieve` の出力のみで、入力には使われない）。

### 修正項目 3: 回答で受け付ける問題を限定する（ビュー）
**修正方針**: 回答する問題を「セッション所有者の組織の問題・セッションに科目があればその科目の問題」から取る。外れていれば、存在しない問題と同じ `404 {'error': 'Problem not found'}` を返し、回答を保存せず、正解・解説を返さない。

```python
        try:
            problem = QuizService.available_problems(
                session.user, session.subject
            ).get(id=problem_id)
        except Problem.DoesNotExist:
            return Response(
                {'error': 'Problem not found'},
                status=status.HTTP_404_NOT_FOUND
            )
```
- `session` は `get_object()`（本人のセッションに限定）で取るため `session.user == request.user`。出題と同じ `session.user` を渡し、出題と回答で同じ判定になるようにする。
- 以降の処理（回答済みの判定・採点・集計・応答）は変えない。

**API 仕様（変更後）**

| URL | メソッド | 認可 | 応答 |
|-----|---------|------|------|
| `/api/quiz/` | POST（body `{"subject": <科目ID> \| null \| 省略}`・任意ヘッダ `Idempotency-Key`） | `IsAuthenticated` | 201 / 200: `QuizSessionSerializer`（従来どおり。科目なしの `total_problems` は自組織の未削除の問題数）／**400: `subject` が存在しない・他組織の科目**（`{"error": {"main_message": "入力内容にエラーがあります", "sub_message": <does_not_exist の文言>, "details": {"subject": [<同じ文言>]}}}`・両者で ID 以外の文言が同じ）／400（キー不正）・401・409・422 は従来どおり |
| `/api/quiz/<id>/next_problem/` | GET | `IsAuthenticated`（本人のセッションのみ・他人は 404） | 200: `ProblemDisplaySerializer`＋`total_problems_in_subject`（自組織の問題数）・`is_review_mode`／404 `{"error": "No problems available in this subject"}`（自組織に出題できる問題が無い）／400 `{"error": "Session is not active"}`（従来どおり） |
| `/api/quiz/<id>/submit_answer/` | POST（body `{"problem_id", "selected_choice_ids", "text_answer", "time_taken"}`） | `IsAuthenticated`（本人のセッションのみ） | 200: 従来どおり（`is_correct`・`explanation`・`explanation_image`・`correct_choices`・`session`・`session_stats`）／**404 `{"error": "Problem not found"}`: 存在しない・削除済み・他組織・セッションの科目外の問題**（回答は保存しない）／400（回答済み・セッション終了）は従来どおり |
| `/api/quiz/`（GET）・`/api/quiz/<id>/`（GET）・`/api/quiz/<id>/end/`（POST） | — | `IsAuthenticated` | 変更なし |

## 5. 実装手順（TDD・垂直スライス）

- **ステップ1: テストを先に書き、現行コードで RED を記録する**
  1. `backend/problems/tests/test_I166_quiz_tenant_isolation.py` に TC-01〜TC-11 を書き、現行コードで実行して RED / GREEN の内訳を記録する → auto_test「TDD RED 確認」参照。未知リスクは無い（DRF・Django の標準機能のみ）が、TC-04 が「直したかどうか」を乱数に頼らず判定できること（現行コードで必ず RED になること）をここで確かめる。
- **ステップ2: 境界の判定と全経路への適用（ステップ1 の完了が前提・サービス → シリアライザ → ビューを 1 本で貫通）**
  1. 修正項目 1（サービス）・2（シリアライザ）・3（ビュー）を実装する → TC-01〜TC-11 参照。
  2. → TC-20〜TC-22 参照。
- **ステップ3: 全体回帰と画面の確認（ステップ2 の完了が前提）**
  1. → TC-23 参照。
  2. 手動テスト No.1〜No.4 → manual_test 参照。

依存関係: ステップ1 → 2 → 3 は直列。サービス再起動: 不要（backend は開発サーバーの自動再読み込み）。

## 6. テスト計画

### 自動テスト（詳細: `docs/tests/closed/I166_auto_test.md`）
- **テストレベル**:
  - API 結合（DRF `APIClient`・PostgreSQL のテスト DB）: 開始・出題・回答・再挑戦の各経路の越境と無退行（TC-01〜TC-11）。境界はサーバー側にあるため、API を直接呼ぶ結合テストで決定論的に固定する（grill-me で確定）。
  - E2E（Playwright）: 新規テストは足さない。既存 E2E の全件 pass で、画面からのクイズの無退行を確かめる（TC-23）。
- **再発防止**: TC-01・TC-03・TC-04・TC-05・TC-06・TC-09・TC-10 は現行コードで RED になることを記録してから実装する。
- **認可・テナント境界**: 他組織の科目での開始（TC-01）・科目なしの出題と問題数（TC-03・TC-04）・他組織／科目外の問題への回答（TC-05・TC-06）・他組織の科目を持つセッションが既にある場合（TC-09・多層防御）・組織に属さないユーザー（TC-10）・応答が「存在しない」と区別できないこと（TC-01・TC-05）。

### 手動テスト（詳細: `docs/tests/closed/I166_manual_test.md`）
- すべて Claude 実施（dev DB の読み取り・Playwright MCP での画面確認）。画面の見た目は変わらないため、Human の目視は不要。

## 7. ロールバック
- コード: 本 PR の revert で元に戻る。DB の変更・データの更新は無い。

## 8. Risk & 回避策
- **リスク1（全体共有科目を使っている利用者がいて開始できなくなる）**: `organization` が空の科目はモデル上「全体共有科目」だが、dev DB に 0 件で、科目一覧（`get_user_subjects`）・問題管理もこれを含めない（画面に出ない）。→ 回避: 他の API と同じ扱いにそろえる。共有科目を使う機能を作るときは、別イシューで `available_subjects` / `available_problems` に足す（判定が 1 か所なので変更箇所も 1 か所）。
- **リスク2（科目なしのクイズの問題数が減ったように見える）**: これまで全組織の問題数を数えていたため、科目なしで始めたときの「全 N 問」の表示が自組織の数になる。→ 正しい値への是正であり、受け入れ条件どおり。
- **リスク3（I190 との関係）**: I190（ダッシュボードの実データ化）はクイズの回答を集計する。本イシューで他組織の問題がクイズの記録に入らなくなる（I190 が前提とする状態）。I190 は本 PR のマージ後の develop から計画する（ユーザー決定）。
- **補足（範囲外の既知事項）**: 問題の作成・更新の越境は 403（存在が分かる形）のまま（grill-me で範囲外と決定）。`completed_problems += 1` の同時更新での取りこぼし（I158 で範囲外と記録）も扱わない。

## 13. 性能・UX設計
- **画面**: 見た目・ラベル・配置の変更なし。開始失敗時は現行どおり「クイズセッションの作成に失敗しました」のトースト＋ダッシュボードへ戻る（他組織の科目は画面の通常操作では送らない）。
- **性能**: 出題・回答の問題の取得に `subject` との結合（`subject__organization_id`）が 1 つ増えるだけ。`Subject.organization` は FK でインデックスがあり、件数（組織あたり数百件程度）からも N+1 等の懸念はない。開始時の科目の検証は主キーと組織での 1 件取得。
- **破壊的操作の確認導線・アクセシビリティ**: 該当なし（UI 変更なし）。

## セキュリティ・ベストプラクティスチェック
- **入力バリデーション**: `subject` は DRF の主キーのフィールドで、自組織の科目だけを受け付ける（型の不正・存在しない・他組織はすべて 400）。`problem_id` は `IntegerField` で検証済み（既存）で、取得は自組織・セッションの科目の範囲から。
- **認証・認可**: `permission_classes = [permissions.IsAuthenticated]` は変更なし。対象のセッションは `get_queryset` で本人のものだけ（変更なし）。科目・問題の範囲をユーザーの組織に限定する（最小権限）。組織に属さないユーザーは何も使えない（fail-closed）。context の無いシリアライザも何も受け付けない（fail-closed）。
- **存在の秘匿**: 他組織の科目・問題は「存在しない」と同じ応答（400 の `does_not_exist`・404 `Problem not found`）で、ID を変えて試しても有無が分からない（TC-01・TC-05 で同一性を固定）。
- **機密データ**: 他組織の問題文・正解・解説を返す経路を塞ぐのが本イシューの目的。新しい個人情報の取得・保存・ログ出力は無い。
- **OWASP**: A01（Broken Access Control）の是正。SQL は ORM のみ（SQL インジェクションなし）。CSRF: JWT（Authorization ヘッダ）の API で変更なし。XSS: 表示の変更なし。
- **フレームワーク推奨パターン**: DRF の `PrimaryKeyRelatedField.get_queryset` の上書き（公式に想定された方法）で入力を絞る。
- **依存ライブラリ**: 追加なし → pip-audit / npm audit の新規対象なし。
- **スキャン基準**: bandit は MEDIUM 以上を修正対象（LOW は `# nosec` で理由付き抑制）、npm audit は high/critical を修正対象（pre-commit / CI で検証・TC-22）。

## 高リスク判定
- **判定: Yes**。理由: マルチテナントの境界（テナントデータの越境）と認可の変更で、API の直叩きで事故になりうる。`plan-issue` の P9 の条件「テナント越境がある場合は高リスク（I043）で `/security-review` の対象」に当たる。
- **確定フロー**: `/plan-issue-review I166`（本スキル内で実施）→ `/security-review I166` → `/implement I166`。code-review では敵対的レビューの対象（`docs/runbooks/review-rules.md`）。

## 各種チェック結果
- **P3（データ整合性）影響なし**: スキーマ変更・データの更新なし。トランザクション境界（`start_session` の `transaction.atomic`）は変えない。
- **P5（運用設計）影響なし**: 外部 API・非同期処理・バッチの追加なし。
- **P6（性能・UX）**: 上記「13. 性能・UX設計」に記載（UI 変更なし・クエリの結合が 1 つ増えるだけ）。
- **P8（コスト）影響なし**: 新規インフラ・外部サービスなし。
- **P9（プライバシー）**: テナントデータ（他組織の問題・正解・解説）の越境を塞ぐ変更。新しい個人情報の取得・保存・目的外利用は無い。テナント越境の是正のため高リスク判定 Yes とし、`/security-review` を行う（「高リスク判定」参照）。プライバシー設計（セクション 15）で新たに決める同意・保持期間・削除権の項目は無い。
- **学習効果設計（14）**: 出題順・採点のロジックは変えない。科目なしのクイズが自組織の問題だけになり、学習記録に他組織の問題が混ざらなくなる（品質基準 C1 の前提となるデータの正しさ・C4 マルチテナント）。

## 設計判断の明示
| 設計判断 | 出所 |
|---------|------|
| 範囲は「ユーザーの組織の科目・問題」・登録時に選んだ科目での絞り込みはしない | イシュー明記（grill-me） |
| 判定はキャッシュを通さない | イシュー明記（grill-me） |
| 科目なしセッションは残し、問題数・出題・回答を自組織の問題に限定 | イシュー明記（grill-me） |
| 開始の他組織の科目は存在しない ID と同じ 400・セッションを作らない | イシュー明記（grill-me） |
| 回答の他組織・科目外の問題は存在しない問題と同じ 404・回答を保存しない・正解と解説を返さない | イシュー明記（grill-me） |
| 出題は常にセッション所有者の組織で絞る（多層防御） | イシュー明記（grill-me） |
| 既存の 403 は変えない・E2E は足さない・バックエンドの API テストのみ | イシュー明記（grill-me） |
| 判定を `QuizService.available_subjects` / `available_problems` の 2 つに置く（`selectors.py` を新設しない） | 仮定で決めた（既存の読み取り処理 `get_next_problem` も `QuizService` にあり、境界の判定を 1 ファイルに集めるため） |
| 問題の組織は `subject__organization_id` で判定する（`Problem.organization_id` は使わない） | 仮定で決めた（`Problem.organization` は null 可で、既存テストも空で作っている。問題一覧 API と同じ絞り方） |
| 全体共有科目（`organization` が空）は含めない・組織に属さないユーザーは何も使えない | 仮定で決めた（`get_user_subjects`・問題一覧 API と同じ扱い。dev DB に 0 件） |
| 開始の検査は `PrimaryKeyRelatedField.get_queryset` の上書き（`QuizSubjectField`）で行い、`start_session` に二重の検査を足さない | 仮定で決めた（DRF 標準の検証に乗せると「存在しない」と同じ応答に自然になる。サービスは取り出しを絞るので、検査をすり抜けても漏れない） |
| context の無いシリアライザは科目を受け付けない（fail-closed） | 仮定で決めた（入力に使う経路は `create` のみで、必ず `request` がある） |
| 回答の照合には `session.user` を渡す（`request.user` と同じ人） | 仮定で決めた（出題と同じ引数にして、出題と回答の判定を一致させる） |
| 高リスク判定 Yes（security-review を挟む） | 仮定で決めた（plan-issue の P9「テナント越境は高リスク」に該当） |

→ 「仮定で決めた」項目は、ユーザー指示「ループエンジニアリング・ハーネスエンジニアリングのベストプラクティスと開発をサクサク進める観点で問題ないやり方で進めて」（2026-10-25）に基づき Claude が決定した。いずれも既存のコード・API の扱いにそろえたもので、受け入れ条件の範囲を超える仕様の追加はない。承認ポイントで一括確認する。

## 9. 承認ポイント（チェックリスト）
- [ ] 修正方式: 「クイズで扱ってよい科目・問題」を `QuizService.available_subjects` / `available_problems` に集め、開始（`QuizSubjectField`）・開始時の問題数・出題・回答のすべてに通す — でよいか
- [ ] 応答: 他組織の科目での開始は存在しない ID と同じ 400、他組織・科目外の問題への回答は `404 {"error": "Problem not found"}`（回答を保存せず正解・解説を返さない）— でよいか
- [ ] 範囲: 全体共有科目（dev DB に 0 件）は含めない・組織に属さないユーザーは何も使えない — でよいか
- [ ] UI: 見た目・配置・ラベルの変更なし（科目なしで始めたクイズの「全 N 問」が自組織の数になる）— でよいか
- [ ] 手動テスト: すべて Claude 実施（dev DB の読み取り・Playwright MCP での画面確認）・Human の目視なし — でよいか
- [ ] 高リスク判定 Yes（承認の後に `/security-review I166`）— でよいか

## レビュー結果
- [20261025_1150 判定: ✅ 完了](../../reviews/closed/I166_plan_review_20261025_1150.md)
- [20261025_1145 判定: ✅ 完了](../../reviews/closed/I166_plan_review_20261025_1145.md)（VERDICT: HIGHRISK・Blocker 0・Info 1）
- 指摘への対応（2026-10-25）: Info（false-green 自己検証の「開始の検査」に TC-10 ② の記載が無い）→ auto_test の該当行に TC-10 ② を追記。記録の補完のみで方式・範囲・AC は変わらないため、再レビューはしない。

## セキュリティレビュー結果

**実施日**: 2026-10-25

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Medium | マルチテナント | 判定を 1 か所に集めても、クイズの経路に `Problem.objects` / `Subject.objects` を直接使う取得が残ると、そこから他組織の問題・正解・解説が漏れる（今回の不具合と同じ型の再発） | **必須防御条件**: `QuizSessionViewSet` と `QuizService` で科目・問題を取るときは必ず `available_subjects` / `available_problems` を通す。TC-04・TC-05・TC-06・TC-09 と false-green 注入（取得を元に戻すと RED）で固定。**禁止事項**: クイズの経路に組織で絞らない `Problem.objects.get/filter`・`Subject.objects.get/filter` を新たに書かない（code-review・敵対的レビューの観点 1・4 で確認） |
| Low | マルチテナント | 問題の組織を `Problem.organization_id` で判定すると、null の問題（データ移行中・既存テストも空）で判定が崩れる。`Problem.organization` と `Subject.organization` が食い違うデータがあると判定が割れる | 判定は `subject__organization_id` に統一する（計画の修正項目 1）。dev DB の食い違い 0 件を確認済み。**禁止事項**: 境界の判定に `Problem.organization_id` を使わない |
| Low | マルチテナント | `retrieve`（`QuizSessionDetailSerializer` の `answers.problem` は `ProblemSerializer` で解説を含む）は、セッションに他組織の問題への回答が既にあると、それを返す | 本変更で他組織の問題への回答は作られなくなる（TC-05・TC-06・TC-09）。既存データは dev DB で 0 件（手動 No.1 で再確認）。本番など別の環境へ出す前に、手動 No.1 と同じ件数確認を行う（0 でなければ扱いを決めてから出す） |
| Low | 認証・認可 | 組織に属さないユーザー・context の無いシリアライザで、判定が「組織の無い科目」と一致して全体共有科目が使えてしまう（`organization_id=None` どうしの一致） | `organization_id is None` は `none()` を返す（fail-closed）。context なしは `Subject.objects.none()`。TC-10・TC-11 と false-green 注入で固定 |
| Low | 入力検証 | `subject` に文字列・負数・巨大な数・配列などを送る | DRF の `PrimaryKeyRelatedField` の型検証で 400（`incorrect_type` / `does_not_exist`）。`problem_id` は既存の `IntegerField`（不正は 400）。ORM のみで SQL を組み立てない |
| Low | 機密情報（存在の秘匿） | 他組織の科目・問題と存在しない ID で応答が違うと、ID を総当たりして他組織のデータの有無が分かる | 両者を同じ応答にする（400 `does_not_exist`・404 `{"error": "Problem not found"}`）。TC-01・TC-05 で応答の同一性を固定。応答時間の差は 1 件取得のクエリ 1 本どうしで実質なし |
| — | OWASP Top 10 | A01（Broken Access Control・IDOR）の是正が本変更の目的。SQLi: ORM のみ。XSS: 表示の変更なし。CSRF: JWT（Authorization ヘッダ）の API で変更なし。セキュリティ設定の変更なし | — |
| — | ファイル操作 | なし（`explanation_image` の URL を返す処理は変えず、他組織の問題では返さなくなる） | — |
| — | 外部通信 | なし | — |
| — | 依存ライブラリ | なし（追加なし） | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `POST /api/quiz/` | 一般（組織 A） | 組織 B の科目 ID を送って開始し、組織 B の問題を出させる | 存在しない ID と同じ 400・セッションを作らない | Yes: TC-01 | No | なし | Low |
| 2 | `POST /api/quiz/` → `GET .../next_problem/` | 一般（組織 A） | 科目なし（省略・`null`）で開始し、全組織の問題を出させる | 問題数・出題は自組織の未削除の問題だけ | Yes: TC-03・TC-04 | Yes: 手動 No.3（画面の「クイズを実行」） | なし | Low |
| 3 | `POST /api/quiz/<id>/submit_answer/` | 一般（組織 A） | 自分のセッションに組織 B の `problem_id` を送り、正解と解説を取る | 存在しない問題と同じ 404・回答を保存しない・正解と解説を返さない | Yes: TC-05 | No | なし | Low |
| 4 | `POST /api/quiz/<id>/submit_answer/` | 一般（組織 A） | 科目ありのセッションで同じ組織の別の科目の問題に回答し、集計を水増しする | セッションの科目外は 404 | Yes: TC-06 | No | なし | Low |
| 5 | `POST /api/quiz/`（完了画面の「もう一度挑戦」と同じ送り方） | 一般（組織 A） | 他組織の科目を持つ終了済みセッションの `subject` を送って開始し直す | 他組織の科目は 400 | Yes: TC-08 | Yes: 手動 No.4（自組織の再挑戦が動く） | なし | Low |
| 6 | `GET .../next_problem/`・`POST .../submit_answer/` | 一般（組織 A） | 何かの経路で他組織の科目を持つセッションができた状態で出題・回答させる | 取り出しでも自組織に絞る（多層防御）・404 | Yes: TC-09 | No | なし | Low |
| 7 | `POST /api/quiz/`・`next_problem` | 一般（組織なし） | 組織に属さないユーザーで、全体共有科目（`organization` が空）を使う | 何も使えない（問題数 0・出題 404・科目指定は 400） | Yes: TC-10 | No | なし | Low |
| 8 | `POST /api/quiz/`・`submit_answer` | 一般（組織 A） | ID を順に変えて送り、応答の違いから組織 B の科目・問題の有無を調べる | 他組織と存在しないで同じ応答 | Yes: TC-01・TC-05（応答の同一性） | No | 応答時間の差は実質なし（どちらも 1 件取得 1 本） | Low |
| 9 | `GET /api/quiz/<id>/`（`retrieve`）・`GET /api/quiz/` | 一般（組織 A） | 他人のセッション ID を指定して回答・解説を見る | `get_queryset` で本人のセッションだけ（404・変更なし） | No（既存の挙動・本変更で触らない） | No | なし | Low |
| 10 | `GET /api/quiz/<id>/`（`retrieve`） | 一般（組織 A） | 過去に作られた他組織の問題への回答の解説を見る | 他組織の問題への回答が存在しない | Yes: TC-05・TC-06・TC-09（新たに作られない） | Yes: 手動 No.1（既存データ 0 件） | 別の環境の既存データは未確認（出す前に No.1 と同じ確認） | Low |
| 11 | `POST /api/quiz/` | 未認証 | 開始・出題・回答を呼ぶ | 401（`IsAuthenticated`・変更なし） | No（I158 の TC-17 で固定済み） | No | なし | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 1件 | 0件 |
| Low     | 5件 | 11件 |

### 残余リスク処遇
（2026-10-26 /retro で決定・ユーザー承認）
- Medium（クイズの経路に組織で絞らない `Problem.objects`／`Subject.objects` の取得を書かない）: 受け入れ。TC-04・TC-05・TC-06・TC-09・TC-12 と false-green 注入（出題・回答・開始・組織なし・共有科目・復習モードの 2 分岐を壊すと RED）で固定済み。敵対的レビュー延長周の観点 1 と親の静的確認でも、取得が `available_subjects`／`available_problems` だけであることを確認済み。
- Low（`retrieve` は、過去に作られた他組織の問題への回答があればその解説を返す）: 受け入れ。dev DB の該当データは 0 件（手動 No.1・2026-10-26 に再確認）。**条件**: 本番など別の環境へ出す前に、手動 No.1 と同じ件数確認（①他組織の科目のセッション ②他組織の問題への回答 ③セッションの科目外の問題への回答）を行い、0 でなければ扱いを決めてから出す。
- Low（`Problem.organization_id` ではなく `subject__organization_id` で判定・全体共有科目と組織なしユーザーの扱い・入力の型・存在の秘匿）: 対策済み（設計どおり・TC-01・TC-10・TC-11）のため受け入れ。
- 範囲外で見つかった High（学習記録 API の他組織データの漏れ・以前からの別経路）: 別イシューで最優先（ユーザー決定 2026-10-25）。起票コマンドはデスクトップ。

## 完了情報
- **完了日時**: 2026-10-26
- **対応者**: Claude Code
- **レビュー結果**: OK（code-review 20261025_1230・敵対的レビュー 第 1 周〔報告なし〕／第 2 周／延長周〔ユーザー承認〕で範囲内の High・Medium を修正・/test 全合格・CI 全 pass）
