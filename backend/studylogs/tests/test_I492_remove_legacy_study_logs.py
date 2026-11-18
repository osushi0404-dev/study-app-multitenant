"""
I492: 古い学習記録の表（StudyLog・DailyStudySummary・StudyGoal・ProblemAttempt）の片付け

- TC-05: 夜の学習分析の更新は、直近 7 日にクイズに答えた人・復習をした人を対象にする
- TC-06: 間隔反復の復習の提出は今までどおり記録する
- TC-07: マイグレーション 0002 は 4 つの表と study_session の列だけを消し、復習の記録を減らさない。
  戻す（unapply）とテーブルと列が戻る（戻し方の試し）
- TC-08: 消した学習記録の API は 404

docs/tests/open/I492_auto_test.md に対応。
"""
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from problems.models import Problem, Subject
from problems.tests.i466_data import answer
from studylogs import tasks
from studylogs.models import SpacedRepetitionCard, SpacedRepetitionReview

User = get_user_model()

MIGRATION = ("studylogs", "0002_remove_legacy_study_logs")
BEFORE = ("studylogs", "0001_initial")
EXPECTED_OPERATIONS = [
    ("RemoveField", "spacedrepetitionreview", "study_session"),
    ("DeleteModel", "ProblemAttempt"),
    ("DeleteModel", "DailyStudySummary"),
    ("DeleteModel", "StudyGoal"),
    ("DeleteModel", "StudyLog"),
]
LEGACY_TABLES = {
    "studylogs_studylog", "studylogs_dailystudysummary",
    "studylogs_dailystudysummary_subjects_studied", "studylogs_studygoal",
    "studylogs_problemattempt",
}
REVIEW_TABLE = "studylogs_spacedrepetitionreview"


@pytest.fixture(autouse=True)
def _clear_caches():
    """Redis があるときに、利用者 ID が同じ別テストの cache を拾わない"""
    for alias in settings.CACHES:
        caches[alias].clear()
    yield
    for alias in settings.CACHES:
        caches[alias].clear()


@pytest.fixture
def world(db):
    cat = OrganizationCategory.objects.create(name="テストI492", slug="test-cat-i492")
    org = Organization.objects.create(
        name="組織I492", slug="org-i492", type="school", category=cat, is_active=True)
    subject = Subject.objects.create(name="科目I492", slug="subj-i492", organization=org)

    def user(name):
        return User.objects.create_user(
            email=f"{name}_i492@example.com", user_id=f"{name}_i492", password="pass",
            organization=org, role="user",
        )

    owner = user("owner")
    problem = Problem.objects.create(
        subject=subject, organization=org, created_by=owner, question="問題I492",
        problem_type="single", difficulty=1,
    )
    return {"org": org, "subject": subject, "problem": problem, "user": user, "owner": owner}


def _card(user, problem):
    card, _ = SpacedRepetitionCard.objects.get_or_create(
        user=user, problem=problem, defaults={"next_review_date": timezone.now()})
    return card


def _review(user, problem, at=None):
    review = SpacedRepetitionReview.objects.create(
        card=_card(user, problem), user=user, problem=problem, quality_score=4,
        response_time_seconds=5, is_correct=True, previous_ease_factor=2.5,
        previous_interval=1, previous_repetition_count=0, new_ease_factor=2.5, new_interval=1,
        new_repetition_count=1, next_review_date=timezone.now(),
    )
    if at is not None:
        SpacedRepetitionReview.objects.filter(pk=review.pk).update(reviewed_at=at)
    return review


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---- TC-05: 夜の学習分析の更新の対象 ----
def test_daily_analytics_targets_quiz_and_review_learners(world, monkeypatch):
    now = timezone.now()
    problem = world["problem"]
    quiz_only = world["user"]("a")       # 6 日 23 時間前に答えた
    review_only = world["user"]("b")     # 1 日前に復習
    too_old = world["user"]("c")         # 7 日 1 時間前にだけ答えた
    idle = world["user"]("d")            # 何も無い
    both = world["user"]("e")            # 2 日前に答え 2 件と復習
    answer(quiz_only, problem, correct=True, at=now - timedelta(days=6, hours=23))
    _review(review_only, problem, now - timedelta(days=1))
    answer(too_old, problem, correct=True, at=now - timedelta(days=7, hours=1))
    answer(both, problem, correct=True, at=now - timedelta(days=2))
    answer(both, problem, correct=True, at=now - timedelta(days=2))
    _review(both, problem, now - timedelta(days=2))

    called = []

    class RecordingService:
        def __init__(self, user):
            self.user = user

        def update_daily_analytics(self):
            called.append(self.user.id)

    monkeypatch.setattr(tasks, "SpacedRepetitionService", RecordingService)

    result = tasks.update_daily_analytics_task()

    assert sorted(called) == sorted([quiz_only.id, review_only.id, both.id])
    assert idle.id not in called and too_old.id not in called
    assert result == {"updated_count": 3, "error_count": 0, "total_users": 3}


# ---- TC-06: 復習の提出 ----
def test_submit_review_records_review(world):
    learner = world["user"]("r")
    card = _card(learner, world["problem"])

    response = _client(learner).post(
        "/api/study/spaced-repetition/submit_review/",
        {"card_id": card.id, "quality_score": 4, "response_time_seconds": 10},
        format="json")

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["message"] == "復習を記録しました"
    assert body["review"]["quality_score"] == 4
    assert body["updated_card"]["total_reviews"] == 1
    assert SpacedRepetitionReview.objects.filter(user=learner, card=card).count() == 1


# ---- TC-07: マイグレーション 0002 の流し・戻し ----
def _tables():
    with connection.cursor() as cursor:
        return set(connection.introspection.table_names(cursor))


def _columns(table):
    with connection.cursor() as cursor:
        return {c.name for c in connection.introspection.get_table_description(cursor, table)}


def _operations(migration):
    result = []
    for op in migration.operations:
        name = type(op).__name__
        if name == "RemoveField":
            result.append((name, op.model_name, op.name))
        else:
            result.append((name, getattr(op, "name", None)))  # RunSQL などは名前を持たない
    return result


def _run(step, state):
    """遅延の外部キーの検査を済ませてから DDL を流す（残っていると ALTER TABLE が失敗する）"""
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    with connection.schema_editor() as editor:
        step(state.clone(), editor)


def test_migration_0002_drops_legacy_tables_and_keeps_reviews(world, settings):
    settings.MIGRATION_MODULES = {}  # pytest の --no-migrations を外し、本物のマイグレーションを読む
    loader = MigrationLoader(connection)
    migration = loader.get_migration(*MIGRATION)
    assert _operations(migration) == EXPECTED_OPERATIONS

    before = loader.project_state(BEFORE)
    old = before.apps
    # テストの DB は今のモデルから作られるので、まず 0001 の形（古い表と列がある）に戻す
    _run(migration.unapply, before)
    try:
        learner = world["user"]("m")
        problem = world["problem"]
        linked = _review(learner, problem)
        _review(learner, problem)
        OldLog = old.get_model("studylogs", "StudyLog")
        log = OldLog.objects.create(user_id=learner.id, subject_id=world["subject"].id)
        old.get_model("studylogs", "ProblemAttempt").objects.create(
            user_id=learner.id, problem_id=problem.id, study_log_id=log.id)
        old.get_model("studylogs", "DailyStudySummary").objects.create(
            user_id=learner.id, date=timezone.localdate())
        old.get_model("studylogs", "StudyGoal").objects.create(
            user_id=learner.id, goal_type="daily_time", target_value=30)
        old.get_model("studylogs", "SpacedRepetitionReview").objects.filter(
            pk=linked.pk).update(study_session_id=log.id)
        reviews = SpacedRepetitionReview.objects.count()
        assert reviews == 2

        _run(migration.apply, before)
        assert not LEGACY_TABLES & _tables()
        assert "study_session_id" not in _columns(REVIEW_TABLE)
        assert SpacedRepetitionReview.objects.count() == reviews

        # 戻し方の試し（計画書 7 の 1）: テーブルと列が空で戻り、行を入れ直せる
        _run(migration.unapply, before)
        assert LEGACY_TABLES <= _tables()
        assert "study_session_id" in _columns(REVIEW_TABLE)
        assert OldLog.objects.count() == 0
        OldLog.objects.create(user_id=learner.id, subject_id=world["subject"].id)
        assert OldLog.objects.count() == 1
        assert SpacedRepetitionReview.objects.count() == reviews
    finally:
        if "studylogs_studylog" in _tables():
            _run(migration.apply, before)  # テストの DB を今のモデルの形に戻す


# ---- TC-08: 消した学習記録の API ----
@pytest.mark.parametrize("method, path", [
    ("get", "/api/study/logs/"),
    ("get", "/api/study/logs/1/"),
    ("post", "/api/study/logs/"),
    ("get", "/api/study/statistics/overview/"),
    ("get", "/api/study/statistics/by_subject/"),
    ("get", "/api/study/statistics/daily_summary/"),
    ("get", "/api/study/goals/"),
    ("post", "/api/study/goals/update_progress/"),
])
def test_removed_study_routes_are_404(world, method, path):
    response = getattr(_client(world["owner"]), method)(path, {}, format="json")

    assert response.status_code == status.HTTP_404_NOT_FOUND
