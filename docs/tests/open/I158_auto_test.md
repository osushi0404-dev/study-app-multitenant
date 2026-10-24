# I158 自動テスト（クイズ開始時のセッション二重作成の是正）

- 関連: docs/issues/open/I158.md / docs/plans/open/plan_I158.md / GitHub #275 / Draft PR #317
- 対象:
  - Backend: `backend/problems/tests/test_I158_quiz_session_start.py`（新規）
  - Frontend: `frontend/src/pages/__tests__/QuizSession.start.test.tsx`（新規）
  - E2E: `e2e/tests/quiz-session.spec.ts`（テスト 1 件追加）
- 実行:
  - Backend: `docker compose exec -T backend python -m pytest problems/tests/test_I158_quiz_session_start.py -q`
  - Frontend: `cd frontend && CI=true npx react-scripts test --watchAll=false src/pages/__tests__/QuizSession.start.test.tsx`
  - E2E: `cd e2e && npx playwright test tests/quiz-session.spec.ts`（frontend コンテナ起動後）

## fixture 方針（Backend）
既存テスト（`test_I078_is_correct_exposure.py` など）に倣い、組織・科目・問題・ユーザーを fixture で作る。

```python
@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="テストI158", slug="test-cat-i158")
    org = Organization.objects.create(
        name="組織I158", slug="org-i158", type="school", category=cat, is_active=True)
    subject_a = Subject.objects.create(name="科目I158A", slug="subj-i158-a", organization=org)
    subject_b = Subject.objects.create(name="科目I158B", slug="subj-i158-b", organization=org)
    # total_problems の検証用: subject_a に未削除 2 件＋削除済み 1 件、subject_b に 1 件
    Problem.objects.create(subject=subject_a, organization=org, question="A1", ...)
    Problem.objects.create(subject=subject_a, organization=org, question="A2", ...)
    Problem.objects.create(subject=subject_a, organization=org, question="A3", is_deleted=True, ...)
    Problem.objects.create(subject=subject_b, organization=org, question="B1", ...)
    user = User.objects.create_user(...)   # 組織 org 所属
    other = User.objects.create_user(...)  # 同じ組織の別ユーザー
    return {...}
```
- 並行実行テスト（TC-07・TC-08）は `@pytest.mark.django_db(transaction=True)` を付け、fixture もそのテスト内で作る（`transaction=True` ではテスト外のトランザクションが無いため、各スレッドからデータが見える）。
- 共通の定数:
```python
QUIZ_URL = "/api/quiz/"
KEY = "6f1c2a7e-3b9d-4c55-8a10-2f4e6d8b9c01"
```
- 期待エラー本文（`create_error_response` の形・完全一致で assert）:
```python
BODY_400_KEY = {"error": {"main_message": "入力内容にエラーがあります",
                          "sub_message": "Idempotency-Key は UUID 形式で指定してください", "details": {}}}
BODY_409 = {"error": {"main_message": "クイズの開始が競合しました",
                      "sub_message": "しばらくしてから再度お試しください", "details": {}}}
BODY_422 = {"error": {"main_message": "Idempotency-Key が別の内容で使用されています",
                      "sub_message": "新しいキーで再度お試しください", "details": {}}}
```

## テストケース（Backend）

| TC | 内容 | 手順 | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-01 | キー無しの新規開始 | `user` で `POST QUIZ_URL`・`{"subject": subject_a.id}`・`format='json'` | `status_code == status.HTTP_201_CREATED`。`QuizSession.objects.filter(user=user, is_active=True).count() == 1`。作成行の `client_request_id is None`・`response.data["total_problems"] == 2`（subject_a の未削除問題数・削除済みと subject_b の問題を数えない）・`"client_request_id" not in response.data` | Claude |
| TC-02 | キー無しの開始は後勝ち（既存の有効セッションを終了） | 事前に `user` の有効セッション S0 を作成 → TC-01 と同じリクエスト | 201。S0 を再取得して `is_active is False` かつ `ended_at is not None`。有効セッションは新規の 1 件のみ（`count() == 1`・id が S0 と異なる） | Claude |
| TC-03 | 同じキーの再送は既存を返す（冪等） | ヘッダ `HTTP_IDEMPOTENCY_KEY=KEY` 付きで同じ POST を 2 回 | 1 回目 201・2 回目 `status.HTTP_200_OK`。2 回の `response.data["id"]` が同じ。`QuizSession.objects.filter(user=user).count() == 1` | Claude |
| TC-04 | 異なるキーは後勝ち | `KEY` で POST（201）→ 別の UUID で POST | 2 回目も 201・id が異なる。1 回目のセッションは `is_active is False`。有効セッションは 1 件 | Claude |
| TC-05 | UUID でないキーは 400 | `HTTP_IDEMPOTENCY_KEY="not-a-uuid"` と `HTTP_IDEMPOTENCY_KEY=""` の 2 通りで POST | どちらも `status.HTTP_400_BAD_REQUEST`・`response.json() == BODY_400_KEY`。`QuizSession.objects.count() == 0`（作成されない） | Claude |
| TC-06 | 同じキーで科目が違う再送は 422 | `KEY`・subject_a で POST（201）→ `KEY`・subject_b で POST | 2 回目 `status.HTTP_422_UNPROCESSABLE_ENTITY`・`response.json() == BODY_422`。セッション総数 1・1 回目のセッションは `is_active is True` のまま | Claude |
| TC-07 | 同時 2 回（キー無し）でも有効は 1 件（本バグの再発防止） | `transaction=True`。`threading.Barrier(2)` で揃えた 2 スレッドから、それぞれ `force_authenticate(user)` した `APIClient` で `POST QUIZ_URL`。各スレッドの最後で `connection.close()` | 2 応答とも 201。`QuizSession.objects.filter(user=user, is_active=True).count() == 1`・`QuizSession.objects.filter(user=user).count() == 2` | Claude |
| TC-08 | 同時 2 回（同じキー）は 1 件だけ作成 | TC-07 と同じ方法で、両スレッドとも `HTTP_IDEMPOTENCY_KEY=KEY` | 応答コードの組が `{201, 200}`。2 応答の `id` が同じ。`QuizSession.objects.filter(user=user).count() == 1` | Claude |
| TC-09 | DB 制約で有効 2 件目を拒否 | `QuizSession.objects.create(user=user, is_active=True)` の後、`transaction.atomic()` 内で同じ create | 2 回目が `django.db.IntegrityError`（`pytest.raises`） | Claude |
| TC-10 | 制約違反は 500 ではなく 409・途中の更新は取り消される | 事前に `user` の有効セッション S0 を作成 → `unittest.mock.patch.object(QuizSession.objects, "create", side_effect=IntegrityError)` 下で TC-01 と同じ POST | `status.HTTP_409_CONFLICT`・`response.json() == BODY_409`。S0 を再取得して `is_active is True`・`ended_at is None`（`create` の前に走った `update(is_active=False)` が `transaction.atomic` の例外終了で取り消されている）。`QuizSession.objects.filter(user=user).count() == 1` | Claude |
| TC-11 | 書き換え・削除は 405 | 有効セッション S を作成 → `PUT`・`PATCH`（body `{"is_active": False}`）・`DELETE` を `/api/quiz/{S.id}/` に送る | 3 つとも `status.HTTP_405_METHOD_NOT_ALLOWED`。S を再取得して `is_active is True`・行が存在する | Claude |
| TC-12 | 作成時に `is_active` を送っても無視される | `POST QUIZ_URL`・`{"subject": subject_a.id, "is_active": False}` | 201・`response.data["is_active"] is True`・DB の行も `is_active is True` | Claude |
| TC-13 | CORS preflight で `idempotency-key` が許可される | `APIClient().options(QUIZ_URL, HTTP_ORIGIN="http://localhost:3000", HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST", HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type,idempotency-key")` | `status_code == 200`。`"idempotency-key" in response["Access-Control-Allow-Headers"].lower()` | Claude |
| TC-14 | データマイグレーション関数が最新以外だけを終了する | `importlib.import_module("problems.migrations.0020_deactivate_duplicate_active_quizsessions")` の `deactivate_duplicate_active_sessions(django.apps.apps, None)` を呼ぶ。事前データ: user に有効 3 件（`started_at` を `update()` で 3 段階にずらす）＋終了済み 1 件（`ended_at` 設定済み）、other に有効 1 件。**制約があるテスト DB で有効 3 件を作るため、本 TC は制約をいったん外す**（下記注） | user の有効は `started_at` 最新の 1 件のみ。他の 2 件は `is_active is False` かつ `ended_at is not None`。終了済み 1 件の `ended_at` は元の値のまま。other の 1 件は有効のまま | Claude |
| TC-15 | 同じキーのセッションが終了済みでもそのまま返す | `KEY` で POST（201）→ `POST /api/quiz/{id}/end/` → `KEY` で再 POST | 3 回目 `status.HTTP_200_OK`・同じ id・`response.data["is_active"] is False`。セッション総数 1 | Claude |
| TC-16 | キーはユーザーごと（他人のセッションは返らない） | user が `KEY` で POST（201）→ other が同じ `KEY` で POST | other も 201・id が異なる・`response.data` の id が other のセッション。user のセッションは `is_active is True` のまま | Claude |
| TC-17 | 未認証は 401 | 認証なしの `APIClient()` で `POST QUIZ_URL` | `status.HTTP_401_UNAUTHORIZED`・`QuizSession.objects.count() == 0` | Claude |
| TC-18 | 回答送信・終了は開始処理が終了させた状態を書き戻さない（security-review 由来） | 有効セッション S を作成し、`stale = QuizSession.objects.get(pk=S.pk)` で古い実体を保持 → `QuizService.start_session(user=user, subject=subject_a, client_request_id=None)` で新規開始（S は終了）→ `stale.completed_problems += 1` の後、計画 修正項目 8 と同じ `stale.save(update_fields=['completed_problems', 'correct_answers'])` | 例外なし。S を再取得して `is_active is False`・`completed_problems == 1`。有効セッションは新規の 1 件のみ | Claude |

注:
- ヘッダは Django テストクライアントの書式 `HTTP_IDEMPOTENCY_KEY=...`（`request.headers["Idempotency-Key"]` として届く）で渡す。
- TC-14 の制約の外し方: テスト内で `connection.schema_editor()` を使い `QuizSession._meta.constraints` の `uniq_active_quizsession_per_user` を `remove_constraint` → データ作成 → 関数実行（`transaction=True` は不要・テストのトランザクション内で完結し、最後のロールバックで制約も元に戻る）。重複の解消は `QuizSession.objects.filter(user=user, is_active=True).count() == 1` で確かめる。（/implement 時に変更: 当初は関数実行後に `add_constraint` で戻して解消の証拠にする予定だったが、行の更新と同じトランザクションで制約を足すと PostgreSQL が `cannot CREATE INDEX ... pending trigger events` で拒否することを実測したため。これは本番のマイグレーションを 0020/0021 に分けた理由そのもの）
- 期待値の status は `rest_framework.status` の定数で assert する（規約準拠）。
- TC-07・TC-08 の応答の集め方: スレッド関数の中で `results.append((response.status_code, response.data.get("id")))` とし、`results` は外側で用意したリスト（`list.append` は GIL 下で単体として安全）。例外も握りつぶさず `errors.append(exc)` で集め、最後に `assert errors == []` とする。`thread.join(timeout=30)` の後に `assert not thread.is_alive()` でハングを検出する。
- TC-10 だけ `unittest.mock.patch` を使う理由: ロックがある限り実際には起きない守りの分岐で、実 DB で決定論的に起こす方法が無いため（計画「設計判断の明示」）。

## テストケース（決定論コマンド・Backend）

| TC | 内容 | コマンド | 合否（exit code） | 実施者 |
|----|------|---------|------------------|--------|
| TC-19 | `QuizSessionViewSet` に全列保存の `session.save()` が残っていない（TC-18 の書き方が実コードで守られていることの固定） | `! grep -qE "session\.save\(\)" backend/problems/views.py` | exit 0（合格）。**計画時（2026-10-24・実装前）の実行で exit 1（NG）を確認済み**（現行の 840・942・971 行目を検出）＝失敗注入は現行コードそのもの | Claude |
| TC-20 | モデルとマイグレーションが一致 | `docker compose exec -T backend python manage.py makemigrations --check --dry-run` | exit 0（合格）。計画時点（実装前）の実行で exit 0・`No changes detected` を確認済み（2026-10-24）。失敗注入は下記「false-green 自己検証」 | Claude |
| TC-21 | まっさらな DB で全マイグレーションが通る | `docker compose exec -T backend python -m pytest --migrations --create-db -q problems/tests/test_I158_quiz_session_start.py` | exit 0（テスト DB を作り直して 0001〜0021 を適用し、そのうえで TC-01〜17 が合格） | Claude |
| TC-22 | Backend 全体回帰 | `docker compose exec -T backend python -m pytest --tb=short -q` | exit 0。既存 **103 件**（baseline 2026-10-24）＋新規すべて合格 | Claude |

## テストケース（Frontend）

`QuizSession.start.test.tsx` は既存テストと同じモック方針（`jest.mock('../../services/api')`・`react-hot-toast`・`react-router-dom`）で、`useParams` を `{}`（id 無し）・`useSearchParams` を `subject=1` に固定する。描画は `<React.StrictMode><BrowserRouter><QuizSessionPage /></BrowserRouter></React.StrictMode>`。

| TC | 内容 | 手順 | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-30 | StrictMode でも開始 POST は 1 回・キー付き（本バグの再発防止） | `apiClient.post` を `{ data: { id: 's1', is_active: true, ... } }` で解決、`apiClient.get`（next_problem）を問題データで解決 → 描画 → 問題文の表示を待つ | `apiClient.post` の `/api/quiz/` 宛て呼び出しが **ちょうど 1 回**。引数が `('/api/quiz/', { subject: '1' }, { headers: { 'Idempotency-Key': expect.stringMatching(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/) } })` | Claude |
| TC-31 | 開始失敗時は現行どおりトースト＋ダッシュボードへ | `apiClient.post` を `{ response: { status: 409 } }` で reject → 描画 | `toast.error` が `'クイズセッションの作成に失敗しました'` で呼ばれる。`mockNavigate` が `'/dashboard'` で呼ばれる。`apiClient.post` は 1 回 | Claude |
| TC-34 | 完了画面の「もう一度挑戦」からの開始にもキーが付く（計画変更 2） | 既存 `QuizSession.test.tsx`（`useParams` = `{ id: 'test-session-id' }`）に追加。`apiClient.get` を `is_active: false` のセッションで解決 → 完了画面の「もう一度挑戦」ボタンをクリック | `apiClient.post` が `('/api/quiz/', { subject: '1' }, { headers: { 'Idempotency-Key': UUID v4 } })` で呼ばれる | Claude |
| TC-32 | 既存の読み込み経路に退行なし | `CI=true npx react-scripts test --watchAll=false src/pages/__tests__/QuizSession.test.tsx` | exit 0（既存 6 件合格） | Claude |
| TC-33 | Frontend 全体回帰・型・lint | ① `CI=true npx react-scripts test --watchAll=false` ② `npx tsc --noEmit` ③ `npx eslint src/pages/QuizSession.tsx src/setupTests.ts src/pages/__tests__/QuizSession.start.test.tsx` | ①〜③ すべて exit 0。①は既存 **10 件**（baseline 2026-10-24）＋新規すべて合格 | Claude |

## テストケース（E2E）

| TC | 内容 | 手順 | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-40 | 実ブラウザ（開発サーバー = StrictMode 有効）で開始 POST は 1 回・キー付き | 既存テストと同じ流れ（ダッシュボード → 「クイズを始める」→ E2E Quiz Subject）。その前に `page.on('request')` で `method() === 'POST'` かつ URL のパスが `/api/quiz/` と完全一致するリクエストを配列に記録する。選択肢の表示を待った後に判定 | 記録件数が `1`。`window.isSecureContext` が true（CI の `http://localhost:3000`）なら `headers()['idempotency-key']` が TC-30 と同じ UUID v4 の正規表現に一致、false（compose 内 e2e コンテナの `http://frontend:3000`）ならヘッダ無し（代替動作・計画変更 3） | Claude |
| TC-41 | E2E 全体回帰 | ローカル: `cd e2e && npx playwright test`／CI: `E2E Tests (Playwright)` ジョブ | exit 0（全件合格）。CI のジョブが成功 | Claude |

## TDD RED 確認（実装前に実施）
テストを書いた後、**実装前の現行コード**に対して実行し、RED/GREEN の内訳を記録してから実装する。
- 想定 RED: TC-03（2 回目も 201）・TC-05（キーを無視して 201）・TC-06（201）・TC-07（有効 2 件）・TC-08（2 件作成）・TC-09（制約が無く例外にならない）・TC-10（`create` の後に例外 → 500）・TC-11（PUT/PATCH が 200・DELETE が 204）・TC-12（`is_active=False` で作成される）・TC-13（`idempotency-key` が許可ヘッダに無い）・TC-14（マイグレーションファイルが無く import できない）・TC-15（201）・TC-18（`QuizService.start_session` が無い）・TC-19（exit 1）・TC-30（POST 2 回）
- 想定 GREEN（現行でも通る・振る舞いを固定する TC）: TC-01・TC-02・TC-04・TC-16・TC-17・TC-31
- 記録欄（2026-10-24・実装前）:
  - Backend: **15 failed / 4 passed**。GREEN は TC-02・TC-04・TC-16・TC-17（想定どおり）。TC-01 は想定と違い RED（応答・行に `client_request_id` が無く `AttributeError`＝新しい振る舞いの部分）。TC-07 は `assert 2 == 1`（**有効セッション 2 件＝本バグを並行テストで再現**）、TC-08 は `[201, 201]`（2 件作成）。並行テストが pytest-django（`transaction=True`）＋ PostgreSQL で競合を再現できることを確認（計画の最大の未知リスク＝成立）。
  - Frontend: TC-30・TC-31 とも **RED**（`/api/quiz/` への POST が 2 回＝StrictMode の二重送信を再現）。TC-31 は想定（GREEN）と違い POST 回数の assert で RED。

## 決定論 TC の事前検証
- TC-19: 計画時（2026-10-24・実装前）に exit 1（NG）を確認済み。実装後に exit 0 へ転じることで判定する。
- TC-20: 計画時（2026-10-24・実装前）に exit 0 を確認済み。実装後の失敗注入は下記。

## false-green 自己検証（実装後に失敗条件を注入して RED を確認）
復元は必ず Edit ツールで行い、`git restore` は使わない（実装差分の保護）。復元後に `git diff` が実装差分のみであることを確認する。
- **TC-07 / TC-08**: `QuizService.start_session` の `select_for_update` の行を一時的に削除 → TC-07 は制約違反で片方が 409 になり「2 応答とも 201」が RED、TC-08 は片方が 409 か 2 件作成で RED になることを確認 → 復元。
- **TC-20**: `QuizSession` に一時的なフィールド（例 `tmp_i158 = models.IntegerField(default=0)`）を足す → exit 1 になることを確認 → 復元。
- **TC-30**: `startedSubjectRef` のガード（`if (startedSubjectRef.current === subjectId) return;`）を一時的に削除 → POST 2 回で RED を確認 → 復元。
- **TC-40**: TC-30 と同じ注入で、ローカル E2E が記録件数 2 で RED になることを確認 → 復元。
- 記録欄（2026-10-24）:
  - TC-07 / TC-08: `select_for_update` の行を削除 → 3 回連続で **2 failed**（TC-07 `[201, 409]`＝ロック無しで制約違反が 409 に変換されることも同時に実証・TC-08 `[201, 409]`）→ Edit で復元 → 19 passed。
  - TC-20: `tmp_i158` フィールドを追加 → **exit 1**（`0022_quizsession_tmp_i158.py` を検出・`--dry-run` のためファイルは作られない）→ Edit で復元 → `No changes detected`。
  - TC-30: ガードの `if` を削除 → **2 failed**（TC-30・TC-31）→ Edit で復元 → 2 passed。
  - TC-40: （E2E の再実行時に記入）
  - 復元後の `git diff` は実装差分のみ（注入の残りなし）を確認済み。

## 実施記録（2026-10-24 /implement）
- Backend I158: **19 passed**（TC-01〜TC-18・TC-05 は 2 パターン）。並行テスト（TC-07・TC-08）は 10 回連続実行で全回合格（不安定さなし）。
- TC-19: `! grep -qE "session\.save\(\)" backend/problems/views.py` → **exit 0**（実装前 exit 1 → 実装後 exit 0）。
- TC-20: `makemigrations --check --dry-run` → **exit 0**（`No changes detected`）。
- TC-21: `pytest --migrations --create-db` → **19 passed**（まっさらな DB に 0001〜0021 を適用）。
- TC-22: Backend 全体 **122 passed**（baseline 103＋新規 19）。
- TC-33: Frontend 全体 **4 suites / 13 passed**（baseline 10＋TC-30・TC-31・TC-34）・`npx tsc --noEmit` exit 0・`npx eslint`（変更 4 ファイル）exit 0・`react-scripts build` は `Compiled successfully.`（`frontend/build` がコンテナ作成の root 所有で書けないため `BUILD_PATH` をスクラッチ領域に向けて実行）。
- TC-40 / TC-41: （E2E の再実行時に記入）
