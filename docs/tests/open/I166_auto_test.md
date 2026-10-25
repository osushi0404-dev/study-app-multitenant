# I166 自動テスト（クイズの組織境界）

- 関連: docs/issues/open/I166.md / docs/plans/open/plan_I166.md / GitHub #284 / Draft PR #330
- 対象: `backend/problems/tests/test_I166_quiz_tenant_isolation.py`（新規）
- 実行: `docker compose exec -T backend python -m pytest problems/tests/test_I166_quiz_tenant_isolation.py -q`（app-1 ワークツリーのコンテナ）

## fixture 方針
既存テスト（`test_I158_quiz_session_start.py`）に倣い、組織・科目・問題・ユーザーを fixture で作る。**出題の判定を乱数に頼らないよう、自組織の問題は少なく、他組織の問題は多くする**（自組織の問題を答え終えた後、現行コードは他組織の未回答の問題を必ず返し、修正後は自組織の問題の復習を必ず返す）。

```python
def _problem(subject, user, question, is_deleted=False):
    problem = Problem.objects.create(
        subject=subject, organization=subject.organization, created_by=user,
        question=question, problem_type="single", difficulty=1,
        explanation=f"{question}の解説", is_deleted=is_deleted,
    )
    Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    Choice.objects.create(problem=problem, text="不正解", is_correct=False, order=2)
    return problem


@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="テストI166", slug="test-cat-i166")
    org_a = Organization.objects.create(name="組織I166A", slug="org-i166-a", type="school", category=cat, is_active=True)
    org_b = Organization.objects.create(name="組織I166B", slug="org-i166-b", type="school", category=cat, is_active=True)
    user_a = User.objects.create_user(email="a_i166@example.com", user_id="a_i166", password="pass", organization=org_a, role="user")
    user_b = User.objects.create_user(email="b_i166@example.com", user_id="b_i166", password="pass", organization=org_b, role="user")
    subject_a1 = Subject.objects.create(name="科目I166A1", slug="subj-i166-a1", organization=org_a)
    subject_a2 = Subject.objects.create(name="科目I166A2", slug="subj-i166-a2", organization=org_a)
    subject_b = Subject.objects.create(name="科目I166B", slug="subj-i166-b", organization=org_b)
    # 組織 A: subject_a1 に未削除 1 件＋削除済み 1 件、subject_a2 に 1 件（自組織の未削除は計 2 件）
    problem_a1 = _problem(subject_a1, user_a, "A1")
    _problem(subject_a1, user_a, "A1削除済み", is_deleted=True)
    problem_a2 = _problem(subject_a2, user_a, "A2")
    # 組織 B: 3 件
    problems_b = [_problem(subject_b, user_b, f"B{i}") for i in range(1, 4)]
    # 全体共有科目（organization が空・クイズでは使わない）に 1 件。TC-03・TC-10 の判定と注入確認に使う
    subject_shared = Subject.objects.create(name="共有科目I166", slug="subj-i166-shared", organization=None)
    problem_shared = _problem(subject_shared, user_a, "共有1")
    return {...}  # 上の値をすべて dict で返す
```
- 共通の定数:
```python
QUIZ_URL = "/api/quiz/"
BODY_404_PROBLEM = {"error": "Problem not found"}
```
- 「存在しない ID」は `Subject.objects.order_by("-id").first().id + 1000`（`Problem` も同様）で作る。
- `organization` が空のユーザー（TC-10）は `User.objects.create_user(..., organization=None, role="user")` で作る。

## テストケース（Backend・API 結合）

| TC | 内容 | 手順 | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-01 | 他組織の科目での開始は「存在しない科目」と同じ 400・セッションを作らない（本バグの再発防止） | `user_a` で `POST QUIZ_URL`・`{"subject": subject_b.id}`・`format="json"`。続けて `{"subject": <存在しない ID>}` で同じ POST | どちらも `status.HTTP_400_BAD_REQUEST`。`QuizSession.objects.filter(user=user_a).count() == 0`。2 つの `response.json()` を `json.dumps(..., ensure_ascii=False)` した文字列で、それぞれの ID を `"<pk>"` に置き換えると完全一致する。`response.json()["error"]["details"]` のキーが `["subject"]`。続けて `{"subject": subject_shared.id}`（全体共有科目）で POST しても 400・セッション 0 件（敵対的レビュー第 2 周の Medium で追加） | Claude |
| TC-02 | 自組織の科目での開始は従来どおり（無退行） | `user_a` で `POST QUIZ_URL`・`{"subject": subject_a1.id}` | `status.HTTP_201_CREATED`・`response.data["subject"] == subject_a1.id`・`response.data["total_problems"] == 1`（subject_a1 の未削除の問題数・削除済みを数えない） | Claude |
| TC-03 | 科目なしの開始は受け付け、問題数は自組織の未削除の問題数（本バグの再発防止） | `user_a` で `POST QUIZ_URL`・`{}` と `{"subject": None}` の 2 通り（2 回目の前に 1 回目のセッションは後勝ちで終了する） | どちらも 201・`response.data["subject"] is None`・`response.data["total_problems"] == 2`（組織 A の未削除 2 件。組織 B の 3 件・全体共有科目の 1 件・削除済みを数えない） | Claude |
| TC-04 | 科目なしのセッションでは他組織の問題が出ない（本バグの再発防止・乱数に頼らない判定） | `user_a` で科目なしで開始 → `problem_a1`・`problem_a2` に `submit_answer` で回答（正解の選択肢）→ `GET /api/quiz/<id>/next_problem/` を 3 回 | 3 回とも `status.HTTP_200_OK`・`response.data["id"] in {problem_a1.id, problem_a2.id}`・`response.data["is_review_mode"] is True`・`response.data["total_problems_in_subject"] == 2`。（現行コードは組織 B の未回答の問題を `is_review_mode False` で必ず返すため RED になる） | Claude |
| TC-05 | 他組織の問題への回答は「存在しない問題」と同じ 404・保存しない・正解と解説を返さない（本バグの再発防止） | `user_a` で科目なしで開始 → `POST /api/quiz/<id>/submit_answer/`・`{"problem_id": problems_b[0].id, "selected_choice_ids": [<その問題の正解の選択肢 ID>]}`。続けて `{"problem_id": <存在しない ID>}` で同じ POST | どちらも `status.HTTP_404_NOT_FOUND`・`response.json() == BODY_404_PROBLEM`（`explanation`・`correct_choices` を含まない）。`QuizAnswer.objects.filter(session_id=<id>).count() == 0`。セッションを再取得して `completed_problems == 0`・`correct_answers == 0` | Claude |
| TC-06 | セッションの科目と違う問題への回答は 404（同じ組織でも） | `user_a` で `{"subject": subject_a1.id}` で開始 → `problem_a2`（同じ組織の別の科目）で `submit_answer`。続けて `problems_b[0]` で `submit_answer` | どちらも 404・`response.json() == BODY_404_PROBLEM`。`QuizAnswer` は 0 件 | Claude |
| TC-07 | 自組織・セッションの科目の問題への回答は従来どおり（無退行） | `user_a` で `{"subject": subject_a1.id}` で開始 → `GET next_problem` → 返った問題に正解の選択肢で `submit_answer` | `next_problem` は 200・`response.data["id"] == problem_a1.id`。`submit_answer` は `status.HTTP_200_OK`・`is_correct is True`・`explanation == "A1の解説"`・`correct_choices == [{"id": <正解の選択肢 ID>, "text": "正解"}]`・`session["completed_problems"] == 1` | Claude |
| TC-08 | 終えたセッションの科目での開始し直し（完了画面の「もう一度挑戦」）にも同じ検査がかかる | ① `user_a` で `subject_a1` で開始 → `POST /api/quiz/<id>/end/` → 終えたセッションの `subject` を送って開始。② `QuizSession.objects.create(user=user_a, subject=subject_b, is_active=False)` で他組織の科目を持つ終了済みセッションを直接作り、その `subject` を送って開始 | ① 201・`response.data["subject"] == subject_a1.id`。② 400・新しいセッションは作られない（`user_a` のセッションは ① の 2 件と ② の直接作成分の計 3 件のまま） | Claude |
| TC-09 | 他組織の科目を持つセッションが既にあっても、他組織の問題は出ない・答えられない（多層防御） | `QuizSession.objects.create(user=user_a, subject=subject_b, is_active=True)` を直接作る → `GET next_problem` → `submit_answer`（`problems_b[0]`） | `next_problem` は `status.HTTP_404_NOT_FOUND`・`response.json() == {"error": "No problems available in this subject"}`。`submit_answer` は 404・`BODY_404_PROBLEM`・`QuizAnswer` は 0 件 | Claude |
| TC-12 | 他組織の問題への過去の回答があっても、復習モードで他組織の問題は出ない（多層防御・敵対的レビュー延長周の High で追加） | 科目なしで開始 → `problems_b` の 3 件の回答を `QuizAnswer.objects.create` で直接入れ、`answered_at` を 1 日前にする → 自組織の問題にすべて回答（`extra_own=0`: 2 件＝回答計 5 件で「最近の 5 問を除外」後の候補が空になり後段の分岐を通る／`extra_own=4`: 自組織の問題を 4 件足して 6 件＝除外の分岐で他組織 3 件＋自組織 1 件が候補）→ `next_problem` を 20 回 | 20 回とも 200・`is_review_mode is True`・`id` が自組織の回答済みの問題 ID の中（乱数のため、絞り込みが外れたときに見逃す確率は 1e-8 未満） | Claude |
| TC-10 | 組織に属さないユーザーは何も使えない（fail-closed） | `organization=None` のユーザーで ① 科目なしで開始 → `next_problem` ② `{"subject": subject_a1.id}` で開始 ③ `{"subject": subject_shared.id}` で開始 | ① 開始は 201・`total_problems == 0`、`next_problem` は 404・`{"error": "No problems available in this subject"}`。② ③ とも 400（組織の無い科目どうしでも一致扱いにしない） | Claude |
| TC-11 | context の無いシリアライザは科目を受け付けない（fail-closed）・出力は従来どおり | ① `QuizSessionSerializer(data={"subject": subject_a1.id}).is_valid()` ② `user_a` の `subject_a1` のセッションを `QuizSessionSerializer(session).data` で出力 | ① `False`・`errors` のキーに `"subject"`。② `data["subject"] == subject_a1.id`・`data["subject_name"] == "科目I166A1"` | Claude |

注:
- 期待値の status は `rest_framework.status` の定数で assert する（規約準拠）。
- TC-01 の「同じ応答」は文言の翻訳に依存しないよう、2 つの応答どうしを比べる（固定の文言とは比べない）。現在の文言は `主キー "{pk_value}" は不正です - データが存在しません。`（`LANGUAGE_CODE = "ja"`・2026-10-25 に確認）。
- TC-04 の回答は `selected_choice_ids` に文字列でなく整数の ID を渡す（`SubmitAnswerSerializer` は `IntegerField` の配列）。

## テストケース（決定論コマンド）

| TC | 内容 | コマンド | 合否（exit code） | 実施者 |
|----|------|---------|------------------|--------|
| TC-20 | 本イシューのテストが全件合格 | `docker compose exec -T backend python -m pytest problems/tests/test_I166_quiz_tenant_isolation.py -q` | exit 0（TC-01〜TC-11 合格） | Claude |
| TC-21 | Backend 全体回帰 | `docker compose exec -T backend python -m pytest --tb=short -q` | exit 0。既存 **123 件**（baseline 2026-10-25）＋新規すべて合格 | Claude |
| TC-22 | lint・セキュリティスキャン（変更ファイル） | `pre-commit run --files backend/problems/services/quiz_service.py backend/problems/serializers.py backend/problems/views.py backend/problems/tests/test_I166_quiz_tenant_isolation.py` | exit 0（ruff・bandit を含む全フックが Passed／Skipped。bandit は MEDIUM 以上を修正対象） | Claude |
| TC-23 | E2E 全体回帰（画面からのクイズの開始・回答・組織の分離） | ローカル: `docker compose --profile e2e run --rm e2e`／CI: `E2E Tests (Playwright)` ジョブ | exit 0（全件合格）。CI のジョブが成功 | Claude |

## TDD RED 確認（実装前に実施）
テストを書いた後、**実装前の現行コード**に対して実行し、RED / GREEN の内訳を記録してから実装する。これが「否定・回帰の判定が実際に不合格を返す」ことの確認（失敗条件の注入）を兼ねる。
- 想定 RED: TC-01（201 で作成される）・TC-03（`total_problems == 6`）・TC-04（組織 B か共有科目の問題が `is_review_mode False` で返る）・TC-05（200 で正解・解説が返る）・TC-06（200）・TC-08 ②（201）・TC-09（組織 B の問題が返る・200）・TC-10（`total_problems == 6`・問題が返る・② ③ は 201）・TC-11 ①（`True`）
- 想定 GREEN（現行でも通る・振る舞いを固定する TC）: TC-02・TC-07・TC-08 ①・TC-11 ②
- 記録欄（2026-10-25・実装前）: **10 failed / 2 passed**（12 件＝TC-03 は 2 パターン）。GREEN は TC-02・TC-07（想定どおり）。RED の理由はすべて想定どおり: TC-01 `201 == 400`・TC-03 ×2 `6 == 2`（全組織＋共有科目を数える）・TC-04 `33 in {29, 31}`（他組織か共有科目の未回答の問題が返る＝乱数に頼らず RED）・TC-05 / TC-06 `200 == 404`・TC-08 ② `201 == 400`（① は通過）・TC-09 `200 == 404`・TC-10 `6 == 0`・TC-11 ① `True is False`。

## false-green 自己検証（実装後に失敗条件を注入して RED を確認）
復元は必ず Edit ツールで行い、`git restore` は使わない（実装差分の保護）。復元後に `git diff` が実装差分のみであることを確認する。
- **出題の多層防御（TC-04・TC-09）**: `get_next_problem` の `QuizService.available_problems(...)` を一時的に `Problem.objects.filter(is_deleted=False)`（＋`session.subject` の絞り込み）に戻す → TC-04・TC-09 が RED になることを確認 → 復元。
- **回答の照合（TC-05・TC-06）**: `submit_answer` の取得を一時的に `Problem.objects.get(id=problem_id, is_deleted=False)` に戻す → TC-05・TC-06 が RED を確認 → 復元。
- **開始の検査（TC-01・TC-08 ②・TC-10 ②）**: `QuizSessionSerializer` の `subject = QuizSubjectField(...)` の行を一時的に削除（`ModelSerializer` が全科目を受け付ける自動のフィールドに戻る）→ TC-01・TC-08 ②・TC-10 ② が RED（201）を確認 → 復元。
- **組織なしの fail-closed（TC-10）**: `available_problems` と `available_subjects` の `if user.organization_id is None` の分岐を一時的に削除 → 組織の無いユーザーに全体共有科目（`organization` が空）が一致し、TC-10 ①（`total_problems == 1`）と ③（201）が RED になることを確認 → 復元。
- 記録欄（2026-10-25）:
  - 出題: `get_next_problem` の絞り込みを元に戻す → **3 failed**（TC-04・TC-09・TC-10）→ Edit で復元。
  - 回答: `submit_answer` の取得を `Problem.objects.get(id=problem_id, is_deleted=False)` に戻す → **3 failed**（TC-05・TC-06・TC-09）→ Edit で復元。
  - 開始: `subject = QuizSubjectField(...)` の行を削除 → **4 failed**（TC-01・TC-08・TC-10・TC-11）→ Edit で復元。
  - 組織なし: `available_subjects`・`available_problems` の `organization_id is None` の分岐を削除 → **1 failed**（TC-10 `1 == 0`＝共有科目が数えられる）→ Edit で復元。
  - 復元後の `git diff` は実装差分のみ（注入の残りなし）・12 passed を確認済み。

## 実施記録（2026-10-25 /implement）
- TC-20: **12 passed**。
- TC-21: Backend 全体 **135 passed**（baseline 123＋新規 12）。注: `-p no:logging` を付けると既存の `test_I140_personal_org_fallback.py` が `caplog` を使えずエラーになるため、全体実行では付けない。
- TC-22: `pre-commit run --files`（変更 4 ファイル）→ ruff・bandit を含む全フック Passed（exit 0）。
- TC-23: `docker compose --profile e2e run --rm e2e` → **8 passed**（既存 E2E 全件・クイズの開始と回答・組織の分離を含む）。

## 敵対的レビュー第 2 周の対応（2026-10-25）
- Medium（組織に属するユーザーが全体共有科目で開始する経路がテストされていない）→ TC-01 に共有科目での開始（400・セッション 0 件）を追加。`available_subjects` に `| Subject.objects.filter(organization__isnull=True)` を混ぜる注入で **TC-01 が RED**（`201 == 400`）になることを確認 → Edit で復元。TC-20 **12 passed**・TC-21 **135 passed**。

## 敵対的レビュー延長周の対応（2026-10-25）
- High（復習モードの選び直しを確かめるテストが無い。2 か所を `Problem.objects.filter(id__in=answered)` に簡略化しても 12 件合格）→ TC-12（2 パターン）を追加。注入結果: レビュー役の注入 `fg_review.py`（2 か所とも壊す）→ **TC-12 の 2 件が RED**。分岐を片方ずつ壊す `fg_branch.py` → `BRANCH=1` で `exclude-recent-branch` だけ RED・`BRANCH=2` で `fallback-branch` だけ RED（各パターンが狙った分岐を通っている）。注入は pytest のプラグイン（`-p`）で読み込み、作業ツリーは変えていない。TC-20 **14 passed**・TC-21 **137 passed**。
