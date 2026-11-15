"""
I524: ダッシュボードの確かめ用データの量と、開発の起動から呼ぶときの止まり方

- 直近 7 日は、今日より前の 1 日だけが解答なしで、ほかの 6 日（今日を含む）は全科目 10〜20 問
- 科目ごとに、解答のある 6 日の数がすべて違う。同じ日・同じ科目の解答はすべて違う問題
- --soft-stop は、止まる理由があれば作らずに案内を出して正常に終わる
- 時刻の範囲（F6）・ほかの組織の同じメールでコマンドが CommandError になる（F10）

TC-01〜TC-07（docs/tests/open/I524_auto_test.md）に対応。
"""
import os
import random
from collections import Counter
from datetime import datetime, time, timedelta
from io import StringIO
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from accounts.models import Organization, OrganizationCategory
from dashboard.verify_data import (
    ORG_SLUG,
    SUBJECTS,
    USER_EMAIL,
    _random_time,
    plan_answers,
    seed_verify_data,
)
from problems.models import Choice, Problem, QuizAnswer, QuizSession, Subject

User = get_user_model()

JST = ZoneInfo("Asia/Tokyo")
NOW = datetime(2026, 11, 16, 15, 0, tzinfo=JST)
TODAY = NOW.date()
PASSWORD = "pw-for-test"  # pragma: allowlist secret - テスト用の仮の値
SLUGS = [slug for slug, _ in SUBJECTS]
RECENT_PAST = [TODAY - timedelta(days=n) for n in range(6, 0, -1)]
RECENT = RECENT_PAST + [TODAY]
LAST_FRACTION = 1 - 2 ** -53  # random() が返しうる最大の値


def _counts(planned):
    return Counter((a.answered_at.astimezone(JST).date(), a.subject_slug) for a in planned)


def _command(*args, env):
    out = StringIO()
    with mock.patch.dict(os.environ, env, clear=True):
        call_command("seed_dashboard_verify", "--password-env", "VERIFY_PW", *args, stdout=out)
    return out.getvalue()


def _answer_ids():
    return set(QuizAnswer.objects.filter(session__user__email=USER_EMAIL).values_list("id", flat=True))


# ---- TC-01: 解答の無い日はちょうど 1 日・ほかの 6 日は全科目 10〜20 問・範囲の外は 1〜5 問 ----
@pytest.mark.parametrize("seed", range(100))
def test_recent_days_have_one_empty_day_and_ten_or_more_per_subject(seed):
    planned = plan_answers(random.Random(seed), NOW)
    counts = _counts(planned)
    day_totals = Counter(a.answered_at.astimezone(JST).date() for a in planned)

    empty = [day for day in RECENT_PAST if day_totals[day] == 0]
    assert len(empty) == 1
    for day in RECENT:
        if day in empty:
            continue
        for slug in SLUGS:
            assert 10 <= counts[(day, slug)] <= 20, (day, slug, counts[(day, slug)])

    outside = {key: n for key, n in counts.items() if key[0] < RECENT[0]}
    assert outside
    assert all(1 <= n <= 5 for n in outside.values())
    assert all(a.answered_at < NOW for a in planned)


# ---- TC-02: 科目ごとに、解答のある 6 日の数がすべて違う ----
@pytest.mark.parametrize("seed", range(100))
def test_recent_counts_differ_by_day_within_subject(seed):
    counts = _counts(plan_answers(random.Random(seed), NOW))

    for slug in SLUGS:
        per_day = [counts[(day, slug)] for day in RECENT if counts[(day, slug)]]
        assert len(per_day) == 6
        assert len(set(per_day)) == 6, (slug, per_day)


# ---- TC-03: 同じ日・同じ科目の解答はすべて違う問題・問題は科目ごとに 20 問 ----
@pytest.mark.django_db
def test_same_day_same_subject_uses_different_problems():
    with override_settings(DEBUG=True):
        for seed in (3, 11, 3):
            seed_verify_data(seed=seed, password=PASSWORD, now=NOW)

            groups = {}
            for answer in QuizAnswer.objects.filter(session__user__email=USER_EMAIL).select_related(
                    "problem__subject"):
                key = (answer.answered_at.astimezone(JST).date(), answer.problem.subject.slug)
                groups.setdefault(key, []).append(answer.problem_id)
            assert groups
            for key, problem_ids in groups.items():
                assert len(problem_ids) == len(set(problem_ids)), key

            for slug, name in SUBJECTS:
                questions = set(Problem.objects.filter(
                    subject__organization__slug=ORG_SLUG, subject__slug=slug).values_list("question", flat=True))
                assert questions == {f"{name}の確かめ問題 {n}" for n in range(1, 21)}


# ---- TC-04: --soft-stop・DEBUG が偽 → 作らずに正常に終わる ----
@pytest.mark.django_db
def test_soft_stop_when_debug_is_false():
    with override_settings(DEBUG=False):
        output = _command("--soft-stop", env={"VERIFY_PW": PASSWORD})

    assert "確かめ用のデータは作りませんでした: DEBUG が偽" in output
    assert not Organization.objects.filter(slug=ORG_SLUG).exists()
    assert not User.objects.filter(email=USER_EMAIL).exists()
    assert not Subject.objects.filter(slug__startswith="verify-i487").exists()
    assert not QuizAnswer.objects.exists()


# ---- TC-05: --soft-stop・パスワードが無い／空 → 作らず・消さずに正常に終わる ----
@pytest.mark.django_db
@pytest.mark.parametrize("env", [{}, {"VERIFY_PW": ""}])
def test_soft_stop_without_password(env):
    with override_settings(DEBUG=True):
        seed_verify_data(seed=1, password=PASSWORD, now=NOW)
        before = _answer_ids()
        orgs = Organization.objects.count()

        output = _command("--soft-stop", env=env)

    assert "確かめ用のデータは作りませんでした: パスワードが空" in output
    assert PASSWORD not in output
    assert _answer_ids() == before
    assert Organization.objects.count() == orgs


# ---- TC-06: 時刻の範囲（開始以上・終わり未満。F6） ----
class _FixedRandom(random.Random):
    def __init__(self, value):
        super().__init__(0)
        self.value = value

    def random(self):
        return self.value


def _local_time(rng_value, day, now):
    return _random_time(_FixedRandom(rng_value), day, now).astimezone(JST)


def test_random_time_range_matches_docstring():
    past = TODAY - timedelta(days=2)
    assert _local_time(0.0, past, NOW).time() == time(7, 0, 0)
    assert _local_time(LAST_FRACTION, past, NOW).time() == time(22, 59, 59)
    assert _local_time(0.0, TODAY, NOW).time() == time(0, 0, 0)
    assert _local_time(LAST_FRACTION, TODAY, NOW).time() == time(14, 58, 59)

    just_after_midnight = datetime(2026, 11, 16, 0, 0, 30, tzinfo=JST)
    for value in (0.0, LAST_FRACTION):
        assert _local_time(value, TODAY, just_after_midnight) == datetime(2026, 11, 16, 0, 0, tzinfo=JST)


# ---- TC-07: 同じメールの利用者がほかの組織にいれば、コマンドは CommandError（F10） ----
@pytest.mark.django_db
def test_command_stops_when_email_belongs_to_other_org():
    cat = OrganizationCategory.objects.create(name="ほか", slug="other-cat")
    org = Organization.objects.create(name="ほかの組織", slug="other-org", type="school", category=cat)
    user = User.objects.create_user(
        email=USER_EMAIL, user_id="verify_i487", password="pass", organization=org, role="user")
    subject = Subject.objects.create(name="科目", slug="s-other", organization=org)
    problem = Problem.objects.create(
        subject=subject, organization=org, created_by=user, question="問題",
        problem_type="single", difficulty=1, explanation="解説")
    Choice.objects.create(problem=problem, text="正解", is_correct=True, order=1)
    session = QuizSession.objects.create(user=user, subject=subject, is_active=False)
    QuizAnswer.objects.create(session=session, problem=problem, is_correct=True, time_taken=30)
    before = (_answer_ids(), set(QuizSession.objects.filter(user=user).values_list("id", flat=True)),
              user.password)

    with override_settings(DEBUG=True), pytest.raises(
            CommandError, match="が確かめ用の組織（verify-i487-org）にいないため"):
        _command(env={"VERIFY_PW": PASSWORD})

    user.refresh_from_db()
    assert user.organization_id == org.pk
    assert (_answer_ids(), set(QuizSession.objects.filter(user=user).values_list("id", flat=True)),
            user.password) == before
