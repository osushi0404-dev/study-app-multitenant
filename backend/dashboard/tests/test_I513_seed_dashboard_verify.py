"""
I513: ダッシュボードの確かめ用データの管理コマンド（seed_dashboard_verify）

- 種が同じなら同じデータ・違えば違うデータ・境目（範囲の外・300 秒超え・解答の無い日・今日）が毎回入る
- コマンドが出す期待値（集計を使わずに数えたもの）が overview の応答と一致する
- 作り直しでほかの利用者のデータは変わらない・DEBUG が偽／パスワードが無い／ほかの組織の同じメールでは止まる

TC-40〜TC-48（docs/tests/open/I513_auto_test.md）に対応。
"""
import inspect
import os
import random
from collections import Counter
from datetime import datetime, timedelta
from io import StringIO
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from accounts.models import Organization, OrganizationCategory
from dashboard import verify_data
from dashboard.selectors import build_overview
from dashboard.verify_data import (
    CAP_SECONDS,
    ORG_SLUG,
    PROBLEMS_PER_SUBJECT,
    USER_EMAIL,
    PlannedAnswer,
    VerifyDataError,
    format_summary,
    plan_answers,
    seed_verify_data,
    summarize,
)
from problems.models import Choice, Problem, QuizAnswer, QuizSession, Subject

User = get_user_model()

JST = ZoneInfo("Asia/Tokyo")
NOW = datetime(2026, 11, 15, 15, 0, tzinfo=JST)
TODAY = NOW.date()
PASSWORD = "pw-for-test"  # pragma: allowlist secret - テスト用の仮の値
ENV = {"VERIFY_PW": PASSWORD}


@pytest.fixture(autouse=True)
def _clear_caches():
    """科目の選択のキャッシュ（subject_service）を別テストから持ち越さない"""
    for alias in settings.CACHES:
        caches[alias].clear()
    yield
    for alias in settings.CACHES:
        caches[alias].clear()


def _seed(seed):
    with override_settings(DEBUG=True):
        return seed_verify_data(seed=seed, password=PASSWORD, now=NOW)


def _command(*args):
    out = StringIO()
    with override_settings(DEBUG=True), mock.patch.dict(os.environ, ENV):
        call_command("seed_dashboard_verify", "--password-env", "VERIFY_PW", *args, stdout=out)
    return out.getvalue()


def _verify_user():
    return User.objects.get(email=USER_EMAIL)


def _rows(user):
    return [
        (a.problem.subject.slug, a.answered_at, a.is_correct, a.time_taken)
        for a in QuizAnswer.objects.filter(session__user=user)
        .select_related("problem__subject").order_by("answered_at", "id")
    ]


def _answer_ids(user):
    return set(QuizAnswer.objects.filter(session__user=user).values_list("id", flat=True))


def _session_ids(user):
    return set(QuizSession.objects.filter(user=user).values_list("id", flat=True))


def _other_user(email, org, user_id):
    user = User.objects.create_user(
        email=email, user_id=user_id, password="pass", organization=org, role="user")
    subject = Subject.objects.create(name=f"科目{user_id}", slug=f"s-{user_id}", organization=org)
    problem = Problem.objects.create(
        subject=subject, organization=org, created_by=user, question="問題",
        problem_type="single", difficulty=1, explanation="解説")
    Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    session = QuizSession.objects.create(user=user, subject=subject, is_active=False)
    QuizAnswer.objects.create(session=session, problem=problem, is_correct=True, time_taken=30)
    return user


# ---- TC-40: 同じ種なら同じデータ ----
@pytest.mark.django_db
def test_same_seed_makes_same_data():
    _seed(7)
    user = _verify_user()
    first = _rows(user)
    first_sessions = QuizSession.objects.filter(user=user).count()

    _seed(7)

    assert _rows(user) == first
    assert QuizSession.objects.filter(user=user).count() == first_sessions
    assert len(first) > 0


# ---- TC-41: 違う種なら違うデータ ----
@pytest.mark.django_db
def test_different_seed_makes_different_data():
    _seed(1)
    first = _rows(_verify_user())

    _seed(2)

    assert _rows(_verify_user()) != first


# ---- TC-42: どの種でも境目が入る（DB を使わない） ----
@pytest.mark.parametrize("seed", range(50))
def test_every_plan_has_boundaries(seed):
    planned = plan_answers(random.Random(seed), NOW)
    days = {a.answered_at.astimezone(JST).date() for a in planned}
    recent_first = TODAY - timedelta(days=6)

    assert any(day < recent_first for day in days)
    assert any(
        a.time_taken > CAP_SECONDS and a.answered_at.astimezone(JST).date() >= recent_first
        for a in planned)
    assert any(TODAY - timedelta(days=n) not in days for n in range(1, 7))
    assert TODAY in days
    assert all(a.answered_at < NOW for a in planned)
    per_group = {}
    for a in planned:
        key = (a.answered_at.astimezone(JST).date(), a.subject_slug)
        per_group[key] = per_group.get(key, 0) + 1
    assert max(per_group.values()) <= PROBLEMS_PER_SUBJECT


# ---- TC-49: 同じ種なら、同じ日のうちは流す時刻が違っても同じデータ（fix-loop F1） ----
def _shape(planned):
    """時刻を除いた解答の集まり（同じ秒に丸まった解答の並びの入れ替わりに依らない・I524 F5）"""
    return Counter((a.subject_slug, a.answered_at.astimezone(JST).date(), a.is_correct, a.time_taken) for a in planned)


@pytest.mark.parametrize("seed", range(20))
def test_same_seed_same_data_at_different_time_of_day(seed):
    early = datetime(2026, 11, 15, 0, 30, tzinfo=JST)
    late = datetime(2026, 11, 15, 23, 0, tzinfo=JST)

    assert _shape(plan_answers(random.Random(seed), early)) == _shape(plan_answers(random.Random(seed), late))


# ---- TC-43: 期待値が overview の応答と一致する ----
def _assert_scope_matches(expected, overview):
    assert expected["today"]["seconds"] == overview["today"]["study_seconds"]
    assert expected["today"]["answered"] == overview["today"]["answered_count"]
    assert [
        (d["date"].isoformat(), d["seconds"], d["answered"], d["correct"]) for d in expected["days"]
    ] == [
        (d["date"], d["study_seconds"], d["answered_count"], d["correct_count"])
        for d in overview["last_7_days"]
    ]
    week = expected["week"]
    assert week["seconds"] == sum(d["study_seconds"] for d in overview["last_7_days"])
    assert week["answered"] == sum(d["answered_count"] for d in overview["last_7_days"])
    assert week["correct"] == sum(d["correct_count"] for d in overview["last_7_days"])
    assert expected["totals"]["answered"] == overview["totals"]["answered_count"]
    assert expected["totals"]["correct"] == overview["totals"]["correct_count"]
    assert expected["streak"] == overview["streak"]["current_days"]


@pytest.mark.django_db
@pytest.mark.parametrize("seed", [3, 11, 29])
def test_expected_values_match_overview(seed):
    summary = _seed(seed)
    user = _verify_user()

    scopes = {scope["subject_slug"]: scope for scope in summary["scopes"]}
    _assert_scope_matches(scopes[None], build_overview(user, now=NOW))
    for slug in ("verify-i487-math", "verify-i487-english"):
        subject = Subject.objects.get(organization__slug=ORG_SLUG, slug=slug)
        _assert_scope_matches(scopes[slug], build_overview(user, subject, now=NOW))


def test_expected_values_do_not_use_selectors():
    assert "dashboard.selectors" not in inspect.getsource(verify_data)
    assert "build_overview" not in inspect.getsource(verify_data)


# ---- TC-44: ほかの利用者のデータは変わらない ----
@pytest.mark.django_db
def test_rebuild_keeps_other_users_data():
    _seed(5)
    verify_org = Organization.objects.get(slug=ORG_SLUG)
    outside_org = Organization.objects.create(
        name="ほかの組織", slug="outside-org", type="school",
        category=OrganizationCategory.objects.create(name="ほか", slug="outside-cat"))
    other = _other_user("other@example.com", verify_org, "other_i513")
    outside = _other_user("outside@example.com", outside_org, "outside_i513")
    before = {u.pk: (_session_ids(u), _answer_ids(u)) for u in (other, outside)}
    first_answers = _answer_ids(_verify_user())

    _seed(6)

    assert {u.pk: (_session_ids(u), _answer_ids(u)) for u in (other, outside)} == before
    assert not first_answers & _answer_ids(_verify_user())


# ---- TC-45: DEBUG が偽なら何も作らず・消さずに止まる ----
@pytest.mark.django_db
def test_stops_when_debug_is_false_on_empty_db():
    with override_settings(DEBUG=False), pytest.raises(VerifyDataError, match="DEBUG が偽"):
        seed_verify_data(seed=1, password=PASSWORD, now=NOW)

    assert not Organization.objects.filter(slug=ORG_SLUG).exists()
    assert not User.objects.filter(email=USER_EMAIL).exists()
    assert not Subject.objects.filter(slug__startswith="verify-i487").exists()
    assert not QuizAnswer.objects.exists()


@pytest.mark.django_db
def test_stops_when_debug_is_false_keeps_existing_data():
    _seed(1)
    before = _answer_ids(_verify_user())

    with override_settings(DEBUG=False), mock.patch.dict(os.environ, ENV), \
            pytest.raises(CommandError, match="DEBUG が偽"):
        call_command("seed_dashboard_verify", "--password-env", "VERIFY_PW", stdout=StringIO())

    assert _answer_ids(_verify_user()) == before


# ---- TC-46: パスワードの環境変数 ----
@pytest.mark.django_db
@pytest.mark.parametrize("env", [{}, {"VERIFY_PW": ""}])
def test_stops_without_password(env):
    _seed(1)
    before = _answer_ids(_verify_user())
    orgs = Organization.objects.count()

    with override_settings(DEBUG=True), mock.patch.dict(os.environ, env, clear=True), \
            pytest.raises(CommandError):
        call_command("seed_dashboard_verify", "--password-env", "VERIFY_PW", stdout=StringIO())

    assert _answer_ids(_verify_user()) == before
    assert Organization.objects.count() == orgs


@pytest.mark.django_db
def test_stops_without_password_on_empty_db():
    with override_settings(DEBUG=True), mock.patch.dict(os.environ, {}, clear=True), \
            pytest.raises(CommandError):
        call_command("seed_dashboard_verify", "--password-env", "VERIFY_PW", stdout=StringIO())

    assert not Organization.objects.filter(slug=ORG_SLUG).exists()
    assert not User.objects.filter(email=USER_EMAIL).exists()


@pytest.mark.django_db
def test_sets_password_without_printing_it():
    output = _command("--seed", "4")

    assert _verify_user().check_password(PASSWORD)
    assert PASSWORD not in output
    assert "--seed 4" in output


# ---- TC-47: 同じメールの利用者がほかの組織にいれば止まる ----
@pytest.mark.django_db
def test_stops_when_email_belongs_to_other_org():
    cat = OrganizationCategory.objects.create(name="ほか", slug="other-cat")
    org = Organization.objects.create(name="ほかの組織", slug="other-org", type="school", category=cat)
    user = _other_user(USER_EMAIL, org, "verify_i487")
    before = (_session_ids(user), _answer_ids(user), user.password)

    with pytest.raises(VerifyDataError):
        _seed(1)

    user.refresh_from_db()
    assert user.organization_id == org.pk
    assert (_session_ids(user), _answer_ids(user), user.password) == before


# ---- TC-48: 期待値の表記 ----
def _at(days_ago, hour=12):
    day = TODAY - timedelta(days=days_ago)
    return datetime(day.year, day.month, day.day, hour, tzinfo=JST)


def test_summary_lines_use_screen_notation():
    math, english = "verify-i487-math", "verify-i487-english"
    planned = [
        PlannedAnswer(math, _at(0, 9), True, 400),
        PlannedAnswer(english, _at(0, 10), False, 100),
        PlannedAnswer(math, _at(2), True, 59),
        PlannedAnswer(english, _at(10), True, 60),
    ]

    lines = format_summary(summarize(planned, TODAY, goal_minutes=30), seed=123)
    text = "\n".join(lines)

    assert lines[0] == "種: 123（同じデータを作り直すには --seed 123）"
    all_part, math_part, english_part = text.split("[")[1:]
    assert "今日: 6分・2問" in all_part
    assert "直近 7 日の合計: 7分・3問・正答率67%" in all_part
    assert "全期間: 4問・正答率75%" in all_part
    assert "連続日数: 1日" in all_part
    assert "目標（全科目）: 30分 → あと24分（20%）" in all_part
    yesterday = TODAY - timedelta(days=1)
    assert f"{yesterday.month}/{yesterday.day}（土） 学習時間: 0分・解答数: 0問・正答率: —" in all_part
    assert math_part.startswith("確かめ数学]")
    assert english_part.startswith("確かめ英語]")
    assert "直近 7 日の合計: 1分・1問・正答率0%" in english_part
