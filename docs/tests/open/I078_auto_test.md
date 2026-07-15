# I078 自動テスト（is_correct の管理経路露出／出題・結果・AI 応答の非露出）

- 関連: docs/issues/open/I078.md / docs/plans/open/plan_I078.md / GitHub #156 / Draft PR #218
- 対象: `backend/problems/tests/test_I078_is_correct_exposure.py`（新規）
- 実行: `docker compose exec -T backend python -m pytest problems/tests/test_I078_is_correct_exposure.py -q`
- テストレベル: API 結合（DRF `APIClient`）＋ シリアライザ単体（AI 応答経路の構造的担保）

## fixture 方針
`test_I102_problem_authz.py` に倣う。1組織で足りる（越境は I103 でカバー済み・本イシューは露出経路の検証）:
- org: admin（`role='admin'`）＋ normal（`role='user'`）
- subject 1 件・problem 1 件（choices: 正解1＋不正解1、`order` 付き）
- 結果経路用に `QuizSession`（normal ユーザー・`is_active=True`）＋ `QuizAnswer`（`selected_choices` に正解 choice を設定）を ORM で作成
- create/update 用ペイロードは `test_I102_problem_authz.py` の `_valid_payload(subject_id)` パターン（multipart・choices は JSON 文字列リスト）を流用

```python
@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="I078", slug="cat-i078")
    org = Organization.objects.create(name="org_I078", slug="org-i078", category=cat)
    admin = User.objects.create_user(
        email="admin_i078@example.com", user_id="admin_i078", password="pass",
        organization=org, role="admin")
    normal = User.objects.create_user(
        email="user_i078@example.com", user_id="user_i078", password="pass",
        organization=org, role="user")
    subject = Subject.objects.create(name="科目I078", slug="subj-i078", organization=org)
    problem = Problem.objects.create(
        subject=subject, organization=org, created_by=admin, question="問題I078",
        problem_type="single", difficulty=1, explanation="解説")
    correct = Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    wrong = Choice.objects.create(problem=problem, text="不正解", is_correct=False, order=2)
    # 出題・結果経路用（TC-AUTO-05/06）: normal ユーザーのセッションと回答
    session = QuizSession.objects.create(user=normal, subject=subject, is_active=True)
    answer = QuizAnswer.objects.create(session=session, problem=problem)
    answer.selected_choices.set([correct])
    return {"org": org, "admin": admin, "normal": normal, "subject": subject,
            "problem": problem, "correct": correct, "wrong": wrong,
            "session": session, "answer": answer}
```

注: `QuizSession` は `subject` 紐づけ・`is_active=True` を明示する（`next_problem` は非アクティブセッションで 400、subject 未設定だと全科目出題になるため）。`QuizAnswer.selected_choices` は M2M のため `create` 後に `.set()` で設定する。

## テストケース

| TC | 内容 | 手順 | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-AUTO-01 | 管理 list で is_correct 露出 | admin で `GET /api/problems/` | `status_code == 200`。全 choice dict に `'is_correct'` キーが存在し、`text=="正解"` の choice は `is_correct is True`・`text=="不正解"` は `False` | Claude |
| TC-AUTO-02 | 管理 retrieve で is_correct 露出 | admin で `GET /api/problems/{problem.id}/` | `status_code == 200`。choices に `'is_correct'` キーが存在し値が DB と一致 | Claude |
| TC-AUTO-03 | create の読み書き両可 | admin で `POST /api/problems/`（multipart・`_valid_payload` 形式・choices に `is_correct` 指定・`settings.MEDIA_ROOT=tmp_path`） | `status_code == 201`。レスポンス choices に `'is_correct'` キーが存在し送信値と一致。DB でも `Choice.objects.get(problem_id=resp['id'], text="A").is_correct is True` | Claude |
| TC-AUTO-04 | 正解保持（テキストのみ編集） | admin で `PUT /api/problems/{id}/`（multipart。`question_text` のみ変更し choices は取得値どおり `is_correct` 付きで再送＝FE の編集保存と同型） | `status_code == 200`。DB で正解 choice が `text=="正解"` のまま（取り違えなし）。レスポンス choices にも `is_correct` が返る | Claude |
| TC-AUTO-05 | 出題経路の非露出（回帰） | normal で fixture の `session` に対し `GET /api/quiz/{session.id}/next_problem/` | `status_code == 200`。レスポンス `choices` の**全要素に `'is_correct'` キーが存在しない**（`all('is_correct' not in c for c in resp['choices'])`）。※fixture は回答済み1問のみだが、復習モードのフォールバック（`quiz_service.py:67-73`）により決定論的に同問題が 200 で返る（確認済み） | Claude |
| TC-AUTO-06 | 結果経路の非露出（回帰） | normal で fixture の `session`（`answer`＝selected_choices 設定済み）に対し `GET /api/quiz/{session.id}/` | `status_code == 200`。`answers[].problem['choices']` と `answers[].selected_choices` の全要素に `'is_correct'` キーが存在しない | Claude |
| TC-AUTO-07 | AI 応答が使う ProblemSerializer の非露出（単体・回帰） | `ProblemSerializer(problem).data` と `ChoiceSerializer(correct).data` を直接評価（`generate_ai`/`generate_adaptive` 応答はこのクラスを直接使用＝`views.py:422/446/551`） | `data['choices']` の全要素・`ChoiceSerializer` 出力に `'is_correct'` キーが存在しない | Claude |
| TC-AUTO-08 | 全体回帰 | `problems/tests/` 全体実行 | 新規 TC 全 PASS ＋ 既存 61 件 PASS（回帰なし） | Claude |

## TDD RED 確認（露出系 TC・実装前に実施）
露出系 TC-AUTO-01〜04 は、**実装前の現行コード**に対して先に実行し RED を確認・記録してから実装する:
- TC-AUTO-01/02: 現行は `write_only` により choices に `is_correct` キーが無い → キー存在アサートで**失敗（RED）**
- TC-AUTO-03/04: 現行は 201/200 自体は成功するが、レスポンス choices の `is_correct` キー存在アサートで**失敗（RED）**

## false-green 自己検証（非露出系 TC・実装後に失敗注入で確認）
否定 TC（TC-AUTO-05/06/07）は現行コードでも合格するため、**失敗条件を注入して RED になることを確認**してから採用する（正常系合格だけの false-green 防止）:
- TC-AUTO-05: `ProblemDisplaySerializer.choices` を一時的に `ChoiceAdminSerializer(many=True, read_only=True)` へ差し替え → TC-AUTO-05 が**RED（非ゼロ終了）**になることを確認 → 戻す。
- TC-AUTO-06/07: `ChoiceSerializer` の `extra_kwargs`（write_only）を一時的に削除 → TC-AUTO-06/07 が**RED**になることを確認 → 戻す。
- **復元は必ず Edit ツールで注入前の内容に戻す**（`git restore` / `git checkout -- <file>` は禁止＝実装差分が未コミットの場合、注入と実装差分が共に失われるため）。復元後に `git diff` が実装差分のみであることを確認する。結果（RED 確認の有無）を本文書に記録する。

## 注記
- list（TC-AUTO-01）はユーザー別キャッシュを通るが、fixture のユーザーはテストごとに新規作成されるためキャッシュキー（user_id）が衝突しない。同一テスト内の再 GET はキャッシュヒットし得る点に留意。
- `ProblemViewSet.parser_classes = [MultiPartParser, FormParser]`（JSON 非対応）のため、create/update は multipart で送る（I103 と同様）。
- quiz 経路（`/api/quiz/...`）は `IsAuthenticated`（非admin 到達可）のため normal ユーザーで実行し、「学生が到達し得る経路に正解が無い」ことをそのまま表現する。
