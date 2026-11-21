"""
I609: 問題の解説を任意にし、出典（source）の欄を足す。

- 解説・出典が無いときは空の文字（null にしない）
- 出典は問題管理の API・クイズの出題の応答・import_problems で扱う（上限 Problem.SOURCE_MAX_LENGTH）
- import_problems は消えた列 points を渡さず、科目の組織を付ける（今は 1 問も登録できなかった）
- マイグレーションは既存の行の解説を変えない

TC-01〜TC-14（docs/tests/open/I609_auto_test.md）に対応。
"""
import json
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from problems.models import Choice, Problem, QuizAnswer, QuizSession, Subject
from problems.tests.migration_helpers import column_names, load_migrations, run_migration

User = get_user_model()

PROBLEMS_URL = "/api/problems/"
QUIZ_URL = "/api/quiz/"
SOURCE = "令和6年度 春期 データベーススペシャリスト試験 午前Ⅱ 問1"
MIGRATION = "0028_problem_source_optional_explanation"
PREVIOUS = "0027_remove_subject_image_directory"


@pytest.fixture
def world(db):
    cat = OrganizationCategory.objects.create(name="テストI609", slug="test-cat-i609")
    org_a = Organization.objects.create(name="組織A_I609", slug="org-a-i609", category=cat)
    org_b = Organization.objects.create(name="組織B_I609", slug="org-b-i609", category=cat)
    admin_a = User.objects.create_user(
        email="admin_a_i609@example.com", user_id="admin_a_i609", password="pass",
        organization=org_a, role="admin")
    user_a = User.objects.create_user(
        email="user_a_i609@example.com", user_id="user_a_i609", password="pass",
        organization=org_a, role="user")
    admin_b = User.objects.create_user(
        email="admin_b_i609@example.com", user_id="admin_b_i609", password="pass",
        organization=org_b, role="admin")
    subject_a = Subject.objects.create(name="科目A_I609", slug="subj-a-i609", organization=org_a)
    return {"org_a": org_a, "admin_a": admin_a, "user_a": user_a, "admin_b": admin_b,
            "subject_a": subject_a}


def _client(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


def _make_problem(world, explanation="元の解説", source=""):
    problem = Problem.objects.create(
        subject=world["subject_a"], organization=world["org_a"], created_by=world["admin_a"],
        question="I609の問題文", problem_type="single", difficulty=1,
        explanation=explanation, source=source)
    correct = Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    Choice.objects.create(problem=problem, text="不正解", is_correct=False, order=2)
    return problem, correct


def _payload(world, **extra):
    data = {
        "subject": world["subject_a"].id,
        "question_text": "新しい問題",
        "problem_type": "single_choice",
        "difficulty": "easy",
        "choices": [
            json.dumps({"text": "A", "is_correct": True}),
            json.dumps({"text": "B", "is_correct": False}),
        ],
    }
    data.update(extra)
    return data


# ---- TC-01: 解説・出典を渡さずに作ると空の文字 ----
def test_model_defaults_are_empty_strings(world):
    problem = Problem.objects.create(
        subject=world["subject_a"], organization=world["org_a"], created_by=world["admin_a"],
        question="解説も出典も無い問題", problem_type="single", difficulty=1)
    problem.refresh_from_db()
    assert problem.explanation == ""
    assert problem.source == ""


# ---- TC-02: 空の解説・出典つきで作成 ----
def test_create_with_empty_explanation_and_source(world):
    response = _client(world["admin_a"]).post(
        PROBLEMS_URL, _payload(world, explanation="", source=SOURCE), format="multipart")
    assert response.status_code == 201
    body = response.json()
    assert body["explanation"] == ""
    assert body["source"] == SOURCE
    problem = Problem.objects.get(pk=body["id"])
    assert problem.explanation == ""
    assert problem.source == SOURCE


# ---- TC-03: 解説・出典を送らずに作成 ----
def test_create_without_explanation_and_source_keys(world):
    response = _client(world["admin_a"]).post(PROBLEMS_URL, _payload(world), format="multipart")
    assert response.status_code == 201
    body = response.json()
    assert body["explanation"] == ""
    assert body["source"] == ""


# ---- TC-04: 上限を 1 文字超えた出典は 400 ----
def test_source_over_limit_is_rejected(world):
    over = "あ" * (Problem.SOURCE_MAX_LENGTH + 1)
    assert len(over) == 2001
    response = _client(world["admin_a"]).post(
        PROBLEMS_URL, _payload(world, source=over), format="multipart")
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["main_message"] == "入力内容にエラーがあります"
    assert "source" in error["details"]
    assert Problem.objects.count() == 0


# ---- TC-05: 上限ちょうどの出典は登録できる ----
def test_source_at_limit_is_accepted(world):
    at_limit = "あ" * Problem.SOURCE_MAX_LENGTH
    assert len(at_limit) == 2000
    response = _client(world["admin_a"]).post(
        PROBLEMS_URL, _payload(world, source=at_limit), format="multipart")
    assert response.status_code == 201
    assert len(response.json()["source"]) == 2000


# ---- TC-06: PUT で解説を空に・出典を入れる ----
def test_put_clears_explanation_and_sets_source(world):
    problem, _ = _make_problem(world)
    response = _client(world["admin_a"]).put(
        f"{PROBLEMS_URL}{problem.id}/", _payload(world, explanation="", source="出典X"),
        format="multipart")
    assert response.status_code == 200
    problem.refresh_from_db()
    assert problem.explanation == ""
    assert problem.source == "出典X"


# ---- TC-07: 出典を送らない PATCH では出典が変わらない ----
def test_patch_without_source_keeps_source(world):
    problem, _ = _make_problem(world, source="出典X")
    response = _client(world["admin_a"]).patch(
        f"{PROBLEMS_URL}{problem.id}/", {"question_text": "直した問題文"}, format="multipart")
    assert response.status_code == 200
    problem.refresh_from_db()
    assert problem.question == "直した問題文"
    assert problem.source == "出典X"


def _start_session(client, subject):
    response = client.post(QUIZ_URL, {"subject": subject.id}, format="json")
    assert response.status_code == 201
    return response.json()["id"]


# ---- TC-08: 出題の応答に出典が入り、正解・解説は入らない ----
def test_next_problem_includes_source_without_answers(world):
    _make_problem(world, explanation="答えの解説", source="出典X")
    client = _client(world["user_a"])
    session_id = _start_session(client, world["subject_a"])

    response = client.get(f"{QUIZ_URL}{session_id}/next_problem/")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "出典X"
    assert "explanation" not in body
    assert body["choices"]
    assert all("is_correct" not in choice for choice in body["choices"])


# ---- TC-09: 解説が空の問題に答えても採点は今までどおり・解説は "" ----
def test_answer_with_empty_explanation(world):
    problem, correct = _make_problem(world, explanation="")
    client = _client(world["user_a"])
    session_id = _start_session(client, world["subject_a"])

    response = client.post(
        f"{QUIZ_URL}{session_id}/submit_answer/",
        {"problem_id": problem.id, "selected_choice_ids": [correct.id]}, format="json")

    assert response.status_code == 200
    body = response.json()
    assert body["is_correct"] is True
    assert body["explanation"] == ""
    assert [choice["id"] for choice in body["correct_choices"]] == [correct.id]
    assert QuizAnswer.objects.filter(session_id=session_id, problem=problem).count() == 1
    assert QuizSession.objects.get(pk=session_id).correct_answers == 1


# ---- TC-10: 他組織の管理者・一般の利用者・未ログインは出典を書き換えられない ----
@pytest.mark.parametrize("who, expected", [("admin_b", 404), ("user_a", 403), (None, 401)])
def test_source_update_is_scoped(world, who, expected):
    problem, _ = _make_problem(world, source="元の出典")
    client = _client(world[who] if who else None)
    response = client.patch(
        f"{PROBLEMS_URL}{problem.id}/", {"source": "書き換えた出典"}, format="multipart")
    assert response.status_code == expected
    problem.refresh_from_db()
    assert problem.source == "元の出典"


IMPORT_MARKDOWN = f"""# 取り込みの確かめ

### Q1
**問題文**：解説の見出しが無く、出典がある問題です。
**選択肢**：
- A. 正しい選択肢
- B. 誤った選択肢
**正解**：A
**出典**：{SOURCE}

### Q2
**問題文**：解説の値が空になっている問題です。
**選択肢**：
- A. 誤った選択肢
- B. 正しい選択肢
**正解**：B
**解説**：

### Q3
**問題文**：解説があり、出典が無い問題です。
**選択肢**：
- A. 正しい選択肢
- B. 誤った選択肢
**正解**：A
**解説**：Q3の解説です。
"""

OVER_LIMIT_MARKDOWN = """
### Q4
**問題文**：出典が上限を超える問題です。
**選択肢**：
- A. 正しい選択肢
- B. 誤った選択肢
**正解**：A
**出典**：{source}
"""


def _import(world, path, *extra):
    out = StringIO()
    call_command("import_problems", "--file", str(path), "--subject-id", str(world["subject_a"].id),
                 "--created-by", world["admin_a"].email, *extra, stdout=out)
    return out.getvalue()


# ---- TC-11: 解説なし・空の解説・出典つきの Markdown を取り込める（組織も付く） ----
def test_import_problems_without_explanation_and_with_source(world, tmp_path):
    path = tmp_path / "problems.md"
    path.write_text(IMPORT_MARKDOWN, encoding="utf-8")

    output = _import(world, path)

    assert "成功: 3問" in output
    assert "エラー" not in output
    problems = {p.question: p for p in Problem.objects.filter(subject=world["subject_a"])}
    assert len(problems) == 3
    first = problems["解説の見出しが無く、出典がある問題です。"]
    assert (first.explanation, first.source) == ("", SOURCE)
    assert problems["解説の値が空になっている問題です。"].explanation == ""
    third = problems["解説があり、出典が無い問題です。"]
    assert (third.explanation, third.source) == ("Q3の解説です。", "")
    assert {p.organization_id for p in problems.values()} == {world["org_a"].id}


# ---- TC-12: 上限を超えた出典の問題は取り込まず、試し実行と本番の件数が合う ----
def test_import_dry_run_count_matches_and_skips_over_limit(world, tmp_path):
    over = "あ" * (Problem.SOURCE_MAX_LENGTH + 1)
    path = tmp_path / "problems.md"
    path.write_text(IMPORT_MARKDOWN + OVER_LIMIT_MARKDOWN.format(source=over), encoding="utf-8")

    dry_run = _import(world, path, "--dry-run")
    assert "パースされた問題: 3問" in dry_run
    assert f"出典: {SOURCE}" in dry_run
    assert Problem.objects.count() == 0

    _import(world, path)
    assert Problem.objects.filter(subject=world["subject_a"]).count() == 3


# ---- TC-15: 取り込んだ問題が、キャッシュ済みの問題管理の一覧にすぐ出る（手動テスト No.7 の再発防止） ----
def test_import_invalidates_problem_list_cache(world, tmp_path):
    client = _client(world["admin_a"])
    assert client.get(PROBLEMS_URL).json() == []  # 一覧の応答をキャッシュさせる
    path = tmp_path / "problems.md"
    path.write_text(IMPORT_MARKDOWN, encoding="utf-8")

    _import(world, path)

    listed = {p["question_text"] for p in client.get(PROBLEMS_URL).json()}
    assert listed == {
        "解説の見出しが無く、出典がある問題です。",
        "解説の値が空になっている問題です。",
        "解説があり、出典が無い問題です。",
    }


# ---- TC-13: マイグレーションは既存の解説を変えず、戻すと出典の列が消える ----
def test_migration_keeps_explanation_and_reverts(world, settings):
    loader = load_migrations(settings)
    migration = loader.get_migration("problems", MIGRATION)
    before = loader.project_state(("problems", PREVIOUS))
    run_migration(migration.unapply, before)
    try:
        assert "source" not in column_names("problems_problem")
        OldProblem = before.apps.get_model("problems", "Problem")
        row = OldProblem.objects.create(
            subject_id=world["subject_a"].id, organization_id=world["org_a"].id,
            created_by_id=world["admin_a"].id, question="移行の前からある問題",
            problem_type="single", difficulty=1, explanation="既存の解説")

        run_migration(migration.apply, before)
        assert "source" in column_names("problems_problem")
        migrated = Problem.objects.get(pk=row.pk)
        assert (migrated.explanation, migrated.source) == ("既存の解説", "")

        run_migration(migration.unapply, before)
        assert "source" not in column_names("problems_problem")
        assert OldProblem.objects.get(pk=row.pk).explanation == "既存の解説"
    finally:
        if "source" not in column_names("problems_problem"):
            run_migration(migration.apply, before)


# ---- TC-14: 既存の形の問題（解説つき・出典なし）の応答は変わらない ----
def test_existing_problem_response_unchanged(world):
    problem, _ = _make_problem(world, explanation="元の解説")
    client = _client(world["admin_a"])

    detail = client.get(f"{PROBLEMS_URL}{problem.id}/")
    listing = client.get(PROBLEMS_URL)

    assert detail.status_code == 200
    assert listing.status_code == 200
    for body in (detail.json(), next(p for p in listing.json() if p["id"] == problem.id)):
        assert body["explanation"] == "元の解説"
        assert body["source"] == ""
        assert body["question_text"] == "I609の問題文"
        assert body["difficulty"] == "easy"
        assert [(c["text"], c["is_correct"]) for c in body["choices"]] == [
            ("正解", True), ("不正解", False)]
