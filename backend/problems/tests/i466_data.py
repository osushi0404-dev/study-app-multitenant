"""
I466 のテストで共通に使うデータの作り方（組織・利用者・科目・問題・答え）

problems と dashboard の両方のテストから使う。答えは回（QuizSession）を答えごとに作る
（QuizAnswer は同じ回・同じ問題で 1 件まで）。
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model

from accounts.models import Organization, OrganizationCategory
from problems.models import Choice, Problem, QuizAnswer, QuizSession, Subject, UserSubjectAccess

User = get_user_model()

JST = ZoneInfo("Asia/Tokyo")
NOW = datetime(2026, 11, 17, 8, 0, tzinfo=JST)
EASY, MEDIUM, HARD = 1, 2, 3


def days_ago(days, now=NOW):
    return now - timedelta(days=days)


def make_world():
    """組織 A・B、A の利用者 2 人・B の利用者 1 人、A の科目 数学・英語、B の科目 B科目"""
    cat = OrganizationCategory.objects.create(name="テストI466", slug="test-cat-i466")
    org_a = Organization.objects.create(
        name="組織I466A", slug="org-i466-a", type="school", category=cat, is_active=True)
    org_b = Organization.objects.create(
        name="組織I466B", slug="org-i466-b", type="school", category=cat, is_active=True)
    user_a = User.objects.create_user(
        email="a_i466@example.com", user_id="a_i466", password="pass",
        organization=org_a, role="user")
    user_a2 = User.objects.create_user(
        email="a2_i466@example.com", user_id="a2_i466", password="pass",
        organization=org_a, role="user")
    user_b = User.objects.create_user(
        email="b_i466@example.com", user_id="b_i466", password="pass",
        organization=org_b, role="user")
    math = Subject.objects.create(name="数学", slug="i466-math", organization=org_a)
    english = Subject.objects.create(name="英語", slug="i466-english", organization=org_a)
    subject_b = Subject.objects.create(name="B科目", slug="i466-b", organization=org_b)
    for user in (user_a, user_a2):
        for subject in (math, english):
            UserSubjectAccess.objects.create(user=user, subject=subject)
    UserSubjectAccess.objects.create(user=user_b, subject=subject_b)
    return {
        "org_a": org_a, "org_b": org_b,
        "user_a": user_a, "user_a2": user_a2, "user_b": user_b,
        "math": math, "english": english, "subject_b": subject_b,
    }


def make_problem(subject, user, question, difficulty=EASY):
    problem = Problem.objects.create(
        subject=subject, organization=subject.organization, created_by=user,
        question=question, problem_type="single", difficulty=difficulty, explanation="解説",
    )
    Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    Choice.objects.create(problem=problem, text="不正解", is_correct=False, order=2)
    return problem


def answer(user, problem, *, correct, seconds=30, at=None, mode=QuizSession.MODE_NORMAL):
    """1 問の答え（at を省くと NOW の 1 時間前）"""
    session = QuizSession.objects.create(
        user=user, subject=problem.subject, is_active=False, mode=mode)
    created = QuizAnswer.objects.create(
        session=session, problem=problem, is_correct=correct, time_taken=seconds)
    QuizAnswer.objects.filter(pk=created.pk).update(
        answered_at=at if at is not None else NOW - timedelta(hours=1))
    return created


def answers(user, problem, total, correct, *, seconds=30, at=None):
    """同じ問題に total 回答える（先頭の correct 回が正解）"""
    for i in range(total):
        answer(user, problem, correct=i < correct, seconds=seconds, at=at)
