"""
ダッシュボードの確かめ用のデータ（開発の DB だけ・I513）

確かめ用の利用者のクイズの解答を、乱数（種つき）で毎回作り直し、作った解答から画面に出るはずの値（期待値）を数える。
期待値は、ダッシュボードの集計を使わずに、作った解答の一覧だけから数える（集計の誤りや、画面が決め打ちの値を
出していることに気づけるように）。

- 計画（plan_answers）と期待値（summarize）は DB を読まない純粋な関数
- 書き込み（seed_verify_data）は DEBUG が偽なら何もしない。消すのは確かめ用の利用者のクイズのセッション（と解答）だけ
- 日付は日本時間（settings.TIME_ZONE）で区切る
"""
import math
import random
import dataclasses
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Organization, OrganizationCategory, UserSettings
from problems.models import Choice, Problem, QuizAnswer, QuizSession, Subject, UserSubjectAccess

# 今あるデータ（2026-11-13 に手で作ったもの）と同じ名前・slug にして、そのまま引き継ぐ
CATEGORY_SLUG = 'verify-i487-cat'
CATEGORY_NAME = '確かめI487分類'
ORG_SLUG = 'verify-i487-org'
ORG_NAME = '確かめI487組織'
USER_EMAIL = 'verify_i487@example.com'
USER_ID = 'verify_i487'
SUBJECTS = (('verify-i487-math', '確かめ数学'), ('verify-i487-english', '確かめ英語'))

PROBLEMS_PER_SUBJECT = 5  # 同じセッションで同じ問題は 1 回までなので、1 日 1 科目の解答数の上限にもなる
HISTORY_DAYS = 14         # 今日を含む 14 日（前半の 7 日は直近 7 日の範囲の外）
RECENT_DAYS = 7           # 画面の「直近 7 日」
CAP_SECONDS = 300         # 1 問の学習時間の上限（画面の仕様。ここでは集計を使わずに同じ規則で数える）

# 乱数の割合（日ごと・科目ごとに値がばらつくように）
OUTSIDE_DAY_RATE = 0.5    # 範囲の外の日に解く割合
SUBJECT_RATE = 0.7        # 解く日に、その科目を解く割合
CORRECT_RATE = 0.6
SECONDS_RANGE = (20, 240)
OVER_CAP_RANGE = (CAP_SECONDS + 1, 900)
DAYTIME_FROM_HOUR = 7     # 過去の日の解答は 7:00〜22:59（日付の境目のすぐ近くは作らない）
DAYTIME_HOURS = 16

WEEKDAYS = '月火水木金土日'


@dataclass(frozen=True)
class PlannedAnswer:
    subject_slug: str
    answered_at: datetime
    is_correct: bool
    time_taken: int


def _start_of(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, time.min))


def _random_time(rng: random.Random, day: date, now: datetime) -> datetime:
    """
    その日の解答の時刻。今日は 0:00〜今の 1 分前（今より後の解答を作らない）、過去の日は 7:00〜22:59

    乱数は rng.random() を 1 回だけ使う（randint は範囲の大きさで乱数を捨て直す回数が変わり、
    今日の範囲は今の時刻で変わるので、同じ種でも流す時刻で後の乱数がずれる）
    """
    start = _start_of(day)
    if day == timezone.localdate(now):
        span = max(0, int((now - timedelta(minutes=1) - start).total_seconds()))
    else:
        start += timedelta(hours=DAYTIME_FROM_HOUR)
        span = DAYTIME_HOURS * 3600 - 1
    return start + timedelta(seconds=int(rng.random() * span))


def plan_answers(rng: random.Random, now: datetime) -> list:
    """
    今日を基準に、HISTORY_DAYS 日ぶんの解答の計画を作る（DB を読まない）

    境目（範囲の外の日・解答の無い日・今日）を先に確定してから、乱数で日・科目・問題数を足す。
    最後に、直近 7 日の中の解答のどれか 1 つを 300 秒超えにする。どの種でもすべての境目が入る。
    """
    today = timezone.localdate(now)
    outside_days = [today - timedelta(days=n) for n in range(HISTORY_DAYS - 1, RECENT_DAYS - 1, -1)]
    recent_past_days = [today - timedelta(days=n) for n in range(RECENT_DAYS - 1, 0, -1)]

    # 境目を先に確定する
    empty_days = set(rng.sample(recent_past_days, rng.randint(1, 2)))
    forced_outside_day = rng.choice(outside_days)

    studied_days = [d for d in outside_days if d == forced_outside_day or rng.random() < OUTSIDE_DAY_RATE]
    studied_days += [d for d in recent_past_days if d not in empty_days]
    studied_days.append(today)

    slugs = [slug for slug, _ in SUBJECTS]
    planned = []
    for day in studied_days:
        day_subjects = [slug for slug in slugs if rng.random() < SUBJECT_RATE] or [rng.choice(slugs)]
        for slug in day_subjects:
            for _ in range(rng.randint(1, PROBLEMS_PER_SUBJECT)):
                planned.append(PlannedAnswer(
                    subject_slug=slug,
                    answered_at=_random_time(rng, day, now),
                    is_correct=rng.random() < CORRECT_RATE,
                    time_taken=rng.randint(*SECONDS_RANGE),
                ))

    recent_first = today - timedelta(days=RECENT_DAYS - 1)
    recent_indexes = [i for i, a in enumerate(planned) if timezone.localdate(a.answered_at) >= recent_first]
    over = rng.choice(recent_indexes)  # 今日は必ず解くので空にならない
    planned[over] = dataclasses.replace(planned[over], time_taken=rng.randint(*OVER_CAP_RANGE))
    return sorted(planned, key=lambda a: a.answered_at)


# ---- 期待値（集計を使わずに数える）----
def _rate_text(correct: int, answered: int) -> str:
    """画面の Math.round(correct / answered * 100) と同じ。0 件は「—」"""
    if not answered:
        return '—'
    return f'{math.floor(correct / answered * 100 + 0.5)}%'


def _counts(answers: list) -> dict:
    seconds = sum(min(a.time_taken, CAP_SECONDS) for a in answers)
    correct = sum(1 for a in answers if a.is_correct)
    return {
        'seconds': seconds,
        'minutes': seconds // 60,
        'answered': len(answers),
        'correct': correct,
        'rate_text': _rate_text(correct, len(answers)),
    }


def _streak(days_with_answers: set, today: date) -> int:
    cursor = today if today in days_with_answers else today - timedelta(days=1)
    streak = 0
    while cursor in days_with_answers:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _scope(label: str, subject_slug: Optional[str], answers: list, today: date) -> dict:
    by_day = {}
    for a in answers:
        by_day.setdefault(timezone.localdate(a.answered_at), []).append(a)
    recent = [today - timedelta(days=n) for n in range(RECENT_DAYS - 1, -1, -1)]
    days = [{'date': day, **_counts(by_day.get(day, []))} for day in recent]
    return {
        'label': label,
        'subject_slug': subject_slug,
        'today': _counts(by_day.get(today, [])),
        'days': days,
        'week': _counts([a for day in recent for a in by_day.get(day, [])]),
        'totals': _counts(answers),
        'streak': _streak(set(by_day), today),
    }


def summarize(planned: list, today: date, goal_minutes: int) -> dict:
    """全科目と科目ごとの期待値（画面の表記に使う値）"""
    scopes = [_scope('全科目', None, planned, today)]
    for slug, name in SUBJECTS:
        scopes.append(_scope(name, slug, [a for a in planned if a.subject_slug == slug], today))
    today_minutes = scopes[0]['today']['minutes']
    goal = None
    if goal_minutes > 0:
        goal = {
            'minutes': goal_minutes,
            'remaining': max(goal_minutes - today_minutes, 0),
            'percent': math.floor(today_minutes / goal_minutes * 100),
        }
    return {'today': today, 'scopes': scopes, 'goal': goal}


def _day_title(day: date) -> str:
    return f'{day.month}/{day.day}（{WEEKDAYS[day.weekday()]}）'


def format_summary(summary: dict, seed: int) -> list:
    """画面と同じ表記の行（見比べ用）"""
    lines = [
        f'種: {seed}（同じデータを作り直すには --seed {seed}）',
        f'基準の日（日本時間）: {summary["today"].isoformat()}',
    ]
    for scope in summary['scopes']:
        today, week, totals = scope['today'], scope['week'], scope['totals']
        lines.append(f'[{scope["label"]}]')
        lines.append(f'  今日: {today["minutes"]}分・{today["answered"]}問')
        lines.append(
            f'  直近 7 日の合計: {week["minutes"]}分・{week["answered"]}問・正答率{week["rate_text"]}')
        for day in scope['days']:
            lines.append(
                f'    {_day_title(day["date"])} 学習時間: {day["minutes"]}分・'
                f'解答数: {day["answered"]}問・正答率: {day["rate_text"]}')
        lines.append(f'  全期間: {totals["answered"]}問・正答率{totals["rate_text"]}')
        lines.append(f'  連続日数: {scope["streak"]}日')
        goal = summary['goal']
        if scope['subject_slug'] is None and goal is not None:
            state = '達成' if goal['remaining'] == 0 else f'あと{goal["remaining"]}分'
            lines.append(f'  目標（全科目）: {goal["minutes"]}分 → {state}（{goal["percent"]}%）')
    return lines


# ---- 書き込み（開発の DB だけ）----
def ensure_debug() -> None:
    if not settings.DEBUG:
        raise CommandError('DEBUG が偽のため、確かめ用のデータは作りません（開発の環境だけで使うコマンドです）')


def _ensure_user(password: str):
    category, _ = OrganizationCategory.objects.get_or_create(
        slug=CATEGORY_SLUG,
        defaults={
            'name': CATEGORY_NAME,
            'description': 'ダッシュボードの確かめ用（開発の DB だけ）',
            'display_order': 99,
        },
    )
    org = Organization.objects.filter(slug=ORG_SLUG).first()
    if org is None:
        org = Organization.objects.create(name=ORG_NAME, slug=ORG_SLUG, type='school', category=category)

    User = get_user_model()
    user = User.objects.filter(email=USER_EMAIL).first()
    if user is None:
        return User.objects.create_user(
            email=USER_EMAIL, user_id=USER_ID, password=password, organization=org, role='user'), org
    if user.organization_id != org.pk:
        raise CommandError(f'{USER_EMAIL} が確かめ用の組織（{ORG_SLUG}）にいないため、何もしません')
    user.set_password(password)
    user.save(update_fields=['password'])
    return user, org


def _ensure_subjects(user, org) -> dict:
    """科目 slug → (科目, 問題の並び)。問題・選択肢・科目の利用権は無ければ作る（今ある問題は消さない）"""
    subjects = {}
    for slug, name in SUBJECTS:
        subject, _ = Subject.objects.get_or_create(organization=org, slug=slug, defaults={'name': name})
        UserSubjectAccess.objects.get_or_create(user=user, subject=subject)
        problems = []
        for number in range(1, PROBLEMS_PER_SUBJECT + 1):
            problem, created = Problem.objects.get_or_create(
                subject=subject,
                question=f'{name}の確かめ問題 {number}',
                defaults={
                    'organization': org, 'created_by': user, 'problem_type': 'single',
                    'difficulty': 1, 'explanation': '確かめ用の問題です。',
                },
            )
            if created:
                Choice.objects.bulk_create([
                    Choice(problem=problem, text='正解', is_correct=True, order=0),
                    Choice(problem=problem, text='不正解', is_correct=False, order=1),
                ])
            problems.append(problem)
        subjects[slug] = (subject, problems)
    return subjects


def _write_answers(user, subjects: dict, planned: list) -> None:
    """(日・科目) ごとに終わったセッションを 1 つ作り、計画の時刻で解答を入れる"""
    groups = {}
    for a in planned:
        groups.setdefault((timezone.localdate(a.answered_at), a.subject_slug), []).append(a)

    sessions, answers = [], []
    for (_, slug), items in groups.items():
        subject, problems = subjects[slug]
        session = QuizSession.objects.create(
            user=user, subject=subject, is_active=False, mode=QuizSession.MODE_NORMAL,
            total_problems=len(problems), completed_problems=len(items),
            correct_answers=sum(1 for a in items if a.is_correct), ended_at=items[-1].answered_at,
        )
        session.started_at = items[0].answered_at
        sessions.append(session)
        created = QuizAnswer.objects.bulk_create([
            QuizAnswer(session=session, problem=problems[i], is_correct=a.is_correct, time_taken=a.time_taken)
            for i, a in enumerate(items)
        ])
        # answered_at・started_at は作るときに今になる（auto_now_add）ので、bulk_update で計画の時刻に直す
        for answer, a in zip(created, items):
            answer.answered_at = a.answered_at
        answers.extend(created)
    # 組織で絞らない: 確かめ用の利用者（確かめ用の組織にいることを確かめ済み）に今作ったセッションの時刻を直すだけ
    QuizSession.objects.bulk_update(sessions, ['started_at'])
    QuizAnswer.objects.bulk_update(answers, ['answered_at'])


def seed_verify_data(*, seed: int, password: str, now: datetime) -> dict:
    """確かめ用のデータを作り直し、期待値を返す。DEBUG が偽・パスワードが空なら何もせずに止まる"""
    ensure_debug()
    if not password:
        raise CommandError('パスワードが空です。--password-env で渡す環境変数に値を入れてください')

    planned = plan_answers(random.Random(seed), now)  # nosec B311 - 確かめ用データの乱数（暗号の用途ではない）
    with transaction.atomic():
        user, org = _ensure_user(password)
        subjects = _ensure_subjects(user, org)
        # 消すのはこの利用者のセッションだけ（解答は CASCADE で消える。ほかの利用者は条件に入らない）
        # 組織で絞らない: 確かめ用の組織にいることを確かめた利用者 1 人のセッションを消すだけ（中身を返さない）
        QuizSession.objects.filter(user=user).delete()
        _write_answers(user, subjects, planned)
        goal_minutes = UserSettings.objects.get_or_create(user=user)[0].daily_study_goal_minutes
    return summarize(planned, timezone.localdate(now), goal_minutes)
