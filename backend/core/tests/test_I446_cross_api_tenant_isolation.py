"""
I446: アプリの全経路を表に載せ、組織・本人の境界を横断で確かめる。

- 番号を受け取る経路: 他組織・全体共有（科目・問題のとき）・同じ組織の別の利用者（本人の記録のとき）の
  番号を、存在しない番号と同じ応答（ステータスと、番号を伏せた本文）で断る（IdCheck）
- 番号を受け取らない一覧・集計: 他組織・別の利用者の中身が出ない（ListCheck）
- 自分の古い記録（他組織の問題への回答を持つクイズの回）からも他組織の中身が出ない（OwnCheck）
- 運用者専用の経路は、組織管理者・一般の利用者が断られる（StaffOnlyCheck）
- 表に無い経路・実在しない表の行があれば落ちる（test_route_table_matches_urlconf）

新しい経路を足したら、ROUTE_TABLE（確かめる）か OUT_OF_SCOPE（理由）に 1 行足す。
- 番号（URL・本文・クエリ）を受け取る → IdCheck（相手の記録の種類・期待するステータス）
- 一覧・集計を返す → ListCheck
- 運用者専用 → StaffOnlyCheck
- 問題・科目・記録の番号を受け取らず中身も返さない → OUT_OF_SCOPE に理由

TC-01〜TC-06（docs/tests/open/I446_auto_test.md）に対応。
"""
import json
import re
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.urls import URLResolver, get_resolver
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from problems.models import (
    Choice, MediaAsset, Problem, ProblemMediaAsset, QuizAnswer, QuizSession, Subject,
    UserSubjectAccess,
)
from studylogs.models import (
    DailyStudySummary, LearningSuggestion, LearningWeakness, MistakePattern, ProblemAttempt,
    SpacedRepetitionCard, SpacedRepetitionReview, StudyGoal, StudyLog,
)

User = get_user_model()

# 他組織・全体共有・同じ組織の別の利用者の記録は 446xxxx の番号で作る（本文の番号を伏せるときに
# 日時などほかの数字を誤って伏せないため）。存在しない番号は 4469999
MISSING_ID = 4469999
FOREIGN_UUID = "00000000-0000-4000-8000-000000446001"
MISSING_UUID = "00000000-0000-4000-8000-000000446999"
ID_PATTERN = re.compile(r"(?<!\d)446\d{4}(?!\d)|00000000-0000-4000-8000-000000446\d{3}")
FOREIGN_MARK = "越境I446"
SAME_ORG_MARK = "別人I446"

FOREIGN_PK = {
    "subject": 4460001, "problem": 4460002, "session": 4460003, "log": 4460004,
    "goal": 4460005, "card": 4460006, "review": 4460007, "suggestion": 4460008,
    "weakness": 4460009,
}
SAME_ORG_PK = {key: pk + 100 for key, pk in FOREIGN_PK.items()
               if key not in ("subject", "problem")}  # 同じ組織の科目・問題は作らない
SHARED_PK = {"subject": 4460201, "problem": 4460202}

MODELS = {
    "subject": Subject, "problem": Problem, "session": QuizSession, "log": StudyLog,
    "goal": StudyGoal, "card": SpacedRepetitionCard, "review": SpacedRepetitionReview,
    "suggestion": LearningSuggestion, "weakness": LearningWeakness, "asset": MediaAsset,
    "User": User, "QuizAnswer": QuizAnswer,
}


# ---------------------------------------------------------------- 確かめ方 ----
@dataclass(frozen=True)
class IdCheck:
    """番号を入れて、他組織・全体共有・同じ組織の別の利用者を存在しない番号と比べる"""
    actor: str  # "user"・"org_admin"・"anon"
    where: str  # "path"・"body"・"query"
    param: str
    target: str  # MODELS のキー（相手の記録の種類）
    status: int
    same_org: bool = False
    fmt: str = "json"
    path_extra: tuple = ()  # ((名前, 値), ...)。値が "@" で始まれば world の参照
    body_extra: tuple = ()
    writes: Optional[tuple] = None  # ("same", "")・("own", 種類)・("count", モデル)
    list_param: bool = False
    own_status: Optional[int] = None  # 正の対照（自分・自組織の番号で呼んだときのステータス）
    xfail: str = ""


@dataclass(frozen=True)
class ListCheck:
    """番号を入れずに呼び、200 で、他組織・別の利用者の中身が出ない"""
    actor: str = "user"
    xfail: str = ""


@dataclass(frozen=True)
class OwnCheck:
    """他組織を指す古いデータを持つ自分の記録の番号で呼び、他組織の中身が出ない"""
    own: str  # world のキー（URL の <pk> に入れる・一般の利用者で呼ぶ）


@dataclass(frozen=True)
class StaffOnlyCheck:
    """運用者専用。組織管理者・一般の利用者は断られる"""
    status: int


XFAIL_452 = "#452: difficulty の型（'easy' を数字の欄で絞る）で 500。#452 で直ったら印を外す"
XFAIL_452_INSIGHTS = (
    "#452: LearningInsightsSerializer の period_days の KeyError で 500（#452 に同梱を依頼）"
)
DRF_STAFF = [StaffOnlyCheck(403)]
DJANGO_STAFF = [StaffOnlyCheck(302)]
LIST = [ListCheck()]


def _subj_body(param="subject", status=400, actor="user", **kw):
    return IdCheck(actor, "body", param, "subject", status, **kw)


def _detail(target, actor="user", same_org=False, method="GET", body=(), fmt="json"):
    """URL の <pk> の確かめ（GET は正の対照つき・書き込みは相手が変わらない）"""
    if method == "GET":
        return IdCheck(actor, "path", "pk", target, 404, same_org=same_org, own_status=200)
    return IdCheck(actor, "path", "pk", target, 404, same_org=same_org, body_extra=body,
                   fmt=fmt, writes=("same", ""))


PROBLEM_FIELDS = (("question", "I446"), ("problem_type", "single"), ("difficulty", 1),
                  ("explanation", "I446"))
REGISTER_FIELDS = (("email", "reg_i446@example.com"), ("user_id", "reg_i446"),
                   ("password", "Passw0rd!i446"), ("password_confirm", "Passw0rd!i446"))
SR = "api/study/spaced-repetition/"
MA = "api/study/mistake-analysis/"
AL = "api/study/adaptive-learning/"

ROUTE_TABLE = {
    # ---- 運用者専用 ----
    **{f"GET {p}": DJANGO_STAFF for p in (
        "monitoring/status/", "monitoring/errors/", "monitoring/performance/",
        "monitoring/activity/", "monitoring/alerts/", "cache/stats/")},
    "POST cache/clear/": DJANGO_STAFF,
    "GET api/admin/users/": DRF_STAFF,
    "POST api/admin/users/": DRF_STAFF,
    "GET api/admin/users/statistics/": DRF_STAFF,
    **{f"{m} api/admin/users/<pk>/": DRF_STAFF for m in ("GET", "PUT", "PATCH", "DELETE")},
    "POST api/admin/users/<pk>/reset_password/": DRF_STAFF,
    "POST api/admin/users/<pk>/toggle_active/": DRF_STAFF,
    # ---- 登録 ----
    **{f"POST {p}": [IdCheck(
        "anon", "body", "subject_ids", "subject", 400, list_param=True,
        path_extra=(("organization_slug", "org-i446-a"),), body_extra=REGISTER_FIELDS,
        writes=("count", "User"))] for p in (
        "api/auth/register/", "api/auth/register/<organization_slug>/")},
    # ---- 本人の情報 ----
    "GET api/auth/me/": LIST,
    "GET api/settings/": LIST,
    "GET api/streak/": LIST,
    # ---- 科目 ----
    **{k: v for prefix in ("api/subjects/", "api/organizations/subjects/") for k, v in {
        f"GET {prefix}": LIST,
        f"GET {prefix}<pk>/": [_detail("subject")],
        **{f"{m} {prefix}<pk>/": [_detail("subject", "org_admin", method=m,
                                          body=(("name", "I446"),))]
           for m in ("PUT", "PATCH", "DELETE")},
    }.items()},
    # ---- 問題 ----
    "GET api/problems/": [ListCheck("org_admin"),
                          IdCheck("org_admin", "query", "subject", "subject", 200)],
    "POST api/problems/": [_subj_body(actor="org_admin", fmt="multipart",
                                      body_extra=PROBLEM_FIELDS, writes=("count", "problem"))],
    "POST api/problems/generate_ai/": [_subj_body(
        "subject_id", 404, "org_admin", fmt="multipart", body_extra=(("save_to_db", "false"),),
        writes=("count", "problem"))],
    "POST api/problems/generate_adaptive/": [_subj_body(
        "subject_id", 404, "org_admin", fmt="multipart", writes=("count", "problem"))],
    "GET api/problems/<pk>/": [_detail("problem", "org_admin")],
    "DELETE api/problems/<pk>/": [_detail("problem", "org_admin", method="DELETE")],
    **{f"{m} api/problems/<pk>/": [
        _detail("problem", "org_admin", method=m, body=PROBLEM_FIELDS, fmt="multipart"),
        _subj_body(actor="org_admin", fmt="multipart", path_extra=(("pk", "@own.problem"),),
                   body_extra=PROBLEM_FIELDS if m == "PUT" else (), writes=("own", "problem")),
    ] for m in ("PUT", "PATCH")},
    "POST api/problems/<pk>/images/upload/": [IdCheck(
        "org_admin", "path", "pk", "problem", 404, fmt="multipart",
        body_extra=(("usage_kind", "problem"),))],
    "DELETE api/problems/<pk>/images/delete/<asset_id>/": [
        IdCheck("org_admin", "path", "pk", "problem", 404,
                path_extra=(("asset_id", "@foreign.asset"),)),
        IdCheck("org_admin", "path", "asset_id", "asset", 404,
                path_extra=(("pk", "@own.problem"),), writes=("same", "")),
    ],
    # ---- クイズ ----
    "GET api/quiz/": LIST,
    "POST api/quiz/": [_subj_body(writes=("count", "session"))],
    "GET api/quiz/<pk>/": [_detail("session", same_org=True), OwnCheck("own.session_mixed")],
    "POST api/quiz/<pk>/end/": [_detail("session", same_org=True, method="POST"),
                                OwnCheck("own.session_mixed")],
    "GET api/quiz/<pk>/next_problem/": [
        IdCheck("user", "path", "pk", "session", 404, same_org=True)],
    "POST api/quiz/<pk>/submit_answer/": [
        _detail("session", same_org=True, method="POST",
                body=(("problem_id", "@own.problem"), ("selected_choice_ids", []))),
        IdCheck("user", "body", "problem_id", "problem", 404,
                path_extra=(("pk", "@own.session_mixed"),),
                body_extra=(("selected_choice_ids", []),),
                writes=("count", "QuizAnswer")),
    ],
    "GET api/user/subjects/": LIST,
    # ---- 学習記録 ----
    "GET api/study/logs/": LIST,
    "POST api/study/logs/": [_subj_body(writes=("count", "log"))],
    "GET api/study/logs/<pk>/": [_detail("log", same_org=True)],
    "DELETE api/study/logs/<pk>/": [_detail("log", same_org=True, method="DELETE")],
    **{f"{m} api/study/logs/<pk>/": [
        _detail("log", same_org=True, method=m, body=(("notes", "I446"),)),
        _subj_body(path_extra=(("pk", "@own.log"),), writes=("own", "log")),
    ] for m in ("PUT", "PATCH")},
    "POST api/study/logs/<pk>/end/": [_detail("log", same_org=True, method="POST")],
    "GET api/study/statistics/overview/": LIST,
    "GET api/study/statistics/by_subject/": LIST,
    "GET api/study/statistics/daily_summary/": LIST,
    "GET api/study/goals/": LIST,
    "POST api/study/goals/update_progress/": LIST,
    "GET api/study/goals/<pk>/": [_detail("goal", same_org=True)],
    **{f"{m} api/study/goals/<pk>/": [_detail(
        "goal", same_org=True, method=m,
        body=(("goal_type", "daily_time"), ("target_value", 5)))]
       for m in ("PUT", "PATCH", "DELETE")},
    # ---- 間隔反復 ----
    **{f"GET {SR}{a}/": LIST for a in ("analytics", "daily_plan", "due_cards", "user_statistics")},
    f"GET {SR}learning_insights/": [ListCheck(xfail=XFAIL_452_INSIGHTS)],
    f"POST {SR}update_analytics/": [ListCheck(xfail=XFAIL_452)],
    f"POST {SR}create_card/": [IdCheck("user", "body", "problem_id", "problem", 404,
                                       writes=("count", "card"))],
    f"POST {SR}submit_review/": [IdCheck(
        "user", "body", "card_id", "card", 404, same_org=True,
        body_extra=(("quality_score", 4), ("response_time_seconds", 10)), writes=("same", ""))],
    "GET api/study/sr-cards/": [ListCheck(),
                                IdCheck("user", "query", "subject_id", "subject", 200)],
    "GET api/study/sr-cards/<pk>/": [_detail("card", same_org=True)],
    "GET api/study/sr-reviews/": [ListCheck(),
                                  IdCheck("user", "query", "card_id", "card", 200, same_org=True)],
    "GET api/study/sr-reviews/<pk>/": [_detail("review", same_org=True)],
    # ---- 間違い分析 ----
    f"GET {MA}analyze/": [ListCheck(xfail=XFAIL_452)],
    f"POST {MA}refresh_analysis/": [ListCheck(xfail=XFAIL_452)],
    f"GET {MA}improvement_trends/": LIST,
    f"GET {MA}suggestions/": LIST,
    **{f"GET {MA}{a}/": [ListCheck(), IdCheck("user", "query", "subject_id", "subject", 200)]
       for a in ("patterns", "weaknesses")},
    f"POST {MA}mark_suggestion_read/": [IdCheck(
        "user", "body", "suggestion_id", "suggestion", 404, same_org=True, writes=("same", ""))],
    f"POST {MA}provide_feedback/": [IdCheck(
        "user", "body", "suggestion_id", "suggestion", 404, same_org=True,
        body_extra=(("effectiveness_rating", 3),), writes=("same", ""))],
    f"POST {MA}resolve_weakness/": [IdCheck(
        "user", "body", "weakness_id", "weakness", 404, same_org=True, writes=("same", ""))],
    # ---- 適応的学習 ----
    **{f"GET {AL}{a}/": [IdCheck("user", "query", "subject_id", "subject", 404),
                         ListCheck(xfail=XFAIL_452)]
       for a in ("proficiency_analysis", "personalized_recommendation", "learning_path",
                 "difficulty_distribution")},
    f"POST {AL}select_problems/": [_subj_body("subject_id", 404), ListCheck(xfail=XFAIL_452)],
    # ---- ダッシュボード ----
    "GET api/dashboard/overview/": LIST,
    "GET api/dashboard/analytics/": LIST,
    "GET api/dashboard/recommendations/": LIST,
}

OUT_OF_SCOPE = {
    "ANY health/": "DB の接続の確認だけで、データを返さない",
    "GET api/": "ルーターの入口。経路の一覧だけを返す",
    "GET api/study/": "ルーターの入口。経路の一覧だけを返す",
    "GET api/organizations/": "ルーターの入口。経路の一覧だけを返す",
    **{f"POST api/auth/{p}/": "認証・本人の資格情報だけを扱い、問題・科目・記録の番号を受け取らない"
       for p in ("login", "logout", "refresh", "verify-email", "password-reset",
                 "password-reset-confirm", "validate-field", "change-password")},
    "GET api/organizations/validate-slug/<slug>/":
        "登録画面のために slug から組織名を返す仕様（#446 の設計確認メモ）",
    **{f"{m} api/auth/me/": "本人の情報の書き換え。組織・役割は読み取り専用で、番号を受け取らない"
       for m in ("PUT", "PATCH")},
    **{f"{m} api/settings/": "本人の設定の書き換え。番号を受け取らない" for m in ("PUT", "PATCH")},
    **{f"POST {p}": "番号を受け取らない。組織は利用者の組織に固定（SubjectViewSet.perform_create）"
       for p in ("api/subjects/", "api/organizations/subjects/")},
    **{f"GET {p}": "登録画面用。slug を知る人に科目名だけを出す仕様（#446 の設計確認メモ）"
       for p in ("api/subjects/public/", "api/organizations/subjects/public/")},
    "POST api/study/goals/": "番号を受け取らない（目標の種類と値だけ）。持ち主は本人に固定",
}


# ------------------------------------------------------------ 経路の収集 ----
_NAMED_GROUP = re.compile(r"\(\?P<(\w+)>[^)]*\)")
_CONVERTER = re.compile(r"<(?:\w+:)?(\w+)>")
_FORMAT_SUFFIX = re.compile(r"\(\?P<format>|<(?:\w+:)?format>")
HTTP_METHODS = ("get", "post", "put", "patch", "delete")


def _walk(patterns, prefix=""):
    for pattern in patterns:
        raw = str(pattern.pattern)
        if _FORMAT_SUFFIX.search(raw):  # ルーターの形式の接尾辞（同じビューの別名）
            continue
        if isinstance(pattern, URLResolver):
            yield from _walk(pattern.url_patterns, prefix + raw)
        else:
            yield prefix + raw, pattern.callback


def _normalize(raw):
    path = _NAMED_GROUP.sub(r"<\1>", raw).replace("^", "").replace("$", "")
    return _CONVERTER.sub(r"<\1>", path)


def _methods(callback):
    cls = getattr(callback, "cls", None) or getattr(callback, "view_class", None)
    if cls is None:  # クラスの無い関数ビュー（メソッドを決められない）
        return {"ANY"}
    allowed = set(getattr(cls, "http_method_names", HTTP_METHODS))
    actions = getattr(callback, "actions", None)
    if actions:  # DRF は初回の要求のときに actions へ head（get と同じ処理）を足すので除く
        return {m.upper() for m in actions if m in allowed and m in HTTP_METHODS}
    return {m.upper() for m in HTTP_METHODS if m in allowed and hasattr(cls, m)}


def _collect_routes():
    seen = {}
    for raw, callback in _walk(get_resolver().url_patterns):
        path = _normalize(raw)
        if path.startswith("admin/") or path in seen:  # 管理画面・先に当たる方だけ残す
            continue
        seen[path] = callback
    return {f"{method} {path}" for path, cb in seen.items() for method in _methods(cb)}


# -------------------------------------------------------------- 下準備 ----
@pytest.fixture(autouse=True)
def _clear_caches():
    """Redis があるときに、利用者 ID が同じ別テストの cache を拾わない"""
    for alias in settings.CACHES:
        caches[alias].clear()
    yield
    for alias in settings.CACHES:
        caches[alias].clear()


def _problem(subject, user, text, pk=None):
    problem = Problem.objects.create(
        pk=pk, subject=subject, organization=subject.organization, created_by=user,
        question=f"{text}問題", problem_type="single", difficulty=1, explanation=f"{text}解説",
    )
    Choice.objects.create(problem=problem, text=f"{text}選択肢正", is_correct=True, order=1)
    Choice.objects.create(problem=problem, text=f"{text}選択肢誤", is_correct=False, order=2)
    return problem


def _records(user, subject, problem, pks, mark):
    """クイズの回・学習記録・目標・カード・復習の記録・提案・弱点を 1 組作る"""
    pks = pks or {}
    card = SpacedRepetitionCard.objects.create(
        pk=pks.get("card"), user=user, problem=problem,
        next_review_date=timezone.now() - timedelta(days=1))
    return {
        "session": QuizSession.objects.create(
            pk=pks.get("session"), user=user, subject=subject, is_active=True),
        "log": StudyLog.objects.create(
            pk=pks.get("log"), user=user, subject=subject, is_active=True, notes=mark),
        "goal": StudyGoal.objects.create(
            pk=pks.get("goal"), user=user, goal_type="daily_time", target_value=10),
        "card": card,
        "review": SpacedRepetitionReview.objects.create(
            pk=pks.get("review"), card=card, user=user, problem=problem, quality_score=4,
            response_time_seconds=10, is_correct=True, previous_ease_factor=2.5,
            previous_interval=1, previous_repetition_count=0, new_ease_factor=2.5,
            new_interval=1, new_repetition_count=1, next_review_date=timezone.now()),
        "suggestion": LearningSuggestion.objects.create(
            pk=pks.get("suggestion"), user=user, subject=subject,
            suggestion_type="concept_review", title=f"{mark}提案", description=mark),
        "weakness": LearningWeakness.objects.create(
            pk=pks.get("weakness"), user=user, subject=subject, concept_name=f"{mark}概念",
            severity="high"),
    }


@pytest.fixture
def world(db):
    cat = OrganizationCategory.objects.create(name="テストI446", slug="test-cat-i446")
    org_a = Organization.objects.create(
        name="組織I446A", slug="org-i446-a", type="school", category=cat, is_active=True)
    org_b = Organization.objects.create(
        name="組織I446B", slug="org-i446-b", type="school", category=cat, is_active=True)
    Organization.objects.create(
        name="個人I446", slug="personal-i446", type="personal", category=cat, is_active=True)

    def user(name, org, role="user"):
        return User.objects.create_user(
            email=f"{name}@example.com", user_id=name, password=None, organization=org,
            role=role)

    user_a, user_a2 = user("a_i446", org_a), user("a2_i446", org_a)
    admin_a, user_b = user("admin_a_i446", org_a, "admin"), user("b_i446", org_b)
    subject_a = Subject.objects.create(name="科目I446A", slug="subj-i446-a", organization=org_a)
    subject_b = Subject.objects.create(
        pk=FOREIGN_PK["subject"], name=f"{FOREIGN_MARK}科目", slug="subj-i446-b",
        organization=org_b)
    subject_shared = Subject.objects.create(
        pk=SHARED_PK["subject"], name=f"{FOREIGN_MARK}共有科目", slug="subj-i446-shared",
        organization=None)
    problem_a = _problem(subject_a, admin_a, "I446A")
    problem_b = _problem(subject_b, user_b, FOREIGN_MARK, FOREIGN_PK["problem"])
    _problem(subject_shared, admin_a, f"{FOREIGN_MARK}共有", SHARED_PK["problem"])

    foreign = _records(user_b, subject_b, problem_b, FOREIGN_PK, FOREIGN_MARK)
    same = _records(user_a2, subject_a, problem_a, SAME_ORG_PK, SAME_ORG_MARK)
    own = _records(user_a, subject_a, problem_a, None, "自分I446")
    asset = MediaAsset.objects.create(
        id=uuid.UUID(FOREIGN_UUID), organization=org_b, subject=subject_b,
        storage_key="org/i446b/problem/a.png")
    ProblemMediaAsset.objects.create(
        problem=problem_b, asset=asset, usage_kind="problem", position=1, organization=org_b)

    # 自分の古いデータ（他組織の科目・問題を指す。I166・I431 より前に作られうる形）
    # 進行中の回は 1 人 1 つ（uniq_active_quizsession_per_user）。終了・回答の経路でも中身まで
    # 届くよう、他組織の問題への回答を持つ回を進行中にし、通常の回は終了済みにする
    QuizSession.objects.filter(pk=own["session"].pk).update(is_active=False)
    QuizSession.objects.create(user=user_a, subject=subject_b, is_active=False)
    mixed = QuizSession.objects.create(user=user_a, subject=None, is_active=True)
    for problem in (problem_a, problem_b):
        QuizAnswer.objects.create(session=mixed, problem=problem)
        ProblemAttempt.objects.create(user=user_a, problem=problem, is_correct=False)
    StudyLog.objects.create(user=user_a, subject=subject_b, duration=60)
    SpacedRepetitionCard.objects.create(
        user=user_a, problem=problem_b, next_review_date=timezone.now() - timedelta(days=1))
    MistakePattern.objects.create(
        user=user_a, pattern_type="subject_difficulty", subject=subject_b,
        description=f"{FOREIGN_MARK}パターン", confidence_score=0.1)
    for subject in (subject_a, subject_b):
        UserSubjectAccess.objects.create(user=user_a, subject=subject)
    # 解いた問題を 1 以上にする（dashboard/analytics の 0 で割る不具合は境界と関係ないので踏まない）
    summary = DailyStudySummary.objects.create(
        user=user_a, date=timezone.now().date(), total_problems_attempted=4,
        total_problems_correct=3)
    summary.subjects_studied.add(subject_a, subject_b)

    refs = {f"foreign.{k}": v.pk for k, v in foreign.items()}
    refs.update({f"same.{k}": v.pk for k, v in same.items()})
    refs.update({f"own.{k}": v.pk for k, v in own.items()})
    refs.update({
        "foreign.subject": subject_b.pk, "foreign.problem": problem_b.pk,
        "foreign.asset": FOREIGN_UUID, "shared.subject": subject_shared.pk,
        "shared.problem": SHARED_PK["problem"], "own.subject": subject_a.pk,
        "own.problem": problem_a.pk, "own.session_mixed": mixed.pk,
        "user_b": user_b.pk,
    })
    return {"refs": refs, "actors": {"user": user_a, "org_admin": admin_a, "anon": None}}


def _client(world, actor, login=False):
    client = APIClient(raise_request_exception=False)
    user = world["actors"][actor]
    if user is not None:
        client.force_authenticate(user=user)
        if login:  # Django の View（monitoring・cache）はセッションで見る
            client.force_login(user)
    return client


def _resolve(world, value):
    if isinstance(value, str) and value.startswith("@"):
        return world["refs"][value[1:]]
    return value


def _url(world, route, params):
    path = route
    for name, value in params.items():
        path = path.replace(f"<{name}>", str(_resolve(world, value)))
    return "/" + path


def _text(response):
    try:
        return json.dumps(response.json(), ensure_ascii=False, sort_keys=True)
    except (ValueError, TypeError):
        return response.content.decode(errors="replace")


def _masked(response):
    return ID_PATTERN.sub("<id>", _text(response))


def _leaks(response):
    text = _text(response)
    found = [mark for mark in (FOREIGN_MARK, SAME_ORG_MARK) if mark in text]
    return found + ID_PATTERN.findall(text)


def _call(client, method, url, data, fmt):
    send = getattr(client, method.lower())
    if method == "GET":
        return send(url)
    return send(url, data, format=fmt)


def _params(checks_type):
    params = []
    for key, checks in ROUTE_TABLE.items():
        for check in checks:
            if isinstance(check, checks_type):
                label = f"{key} {getattr(check, 'param', '')}".strip()
                marks = [pytest.mark.xfail(strict=True, reason=check.xfail)] \
                    if getattr(check, "xfail", "") else []
                params.append(pytest.param(key, check, id=label, marks=marks))
    return params


# ---------------------------------------------------------- TC-04 表の突き合わせ ----
def test_route_table_matches_urlconf():
    routes = _collect_routes()
    table = set(ROUTE_TABLE) | set(OUT_OF_SCOPE)

    assert not routes - table, (
        f"表に無い経路: {sorted(routes - table)}。ROUTE_TABLE（確かめる）か OUT_OF_SCOPE（理由）に"
        " 1 行足す（書き方はこのファイルの冒頭）")
    assert not table - routes, f"実在しない表の行: {sorted(table - routes)}"
    assert not set(ROUTE_TABLE) & set(OUT_OF_SCOPE)
    assert all(reason.strip() for reason in OUT_OF_SCOPE.values())
    assert all(ROUTE_TABLE.values())


# ---------------------------------------------- TC-01・TC-02 番号を受け取る経路 ----
def _snapshot(world, check, variant_id):
    if check.writes is None:
        return None
    kind, name = check.writes
    if kind == "count":
        return MODELS[name].objects.count()
    if kind == "own":
        return list(MODELS[name].objects.filter(pk=world["refs"][f"own.{name}"]).values())
    if variant_id in (MISSING_ID, MISSING_UUID):
        return None
    return list(MODELS[check.target].objects.filter(pk=variant_id).values())


def _id_request(world, key, check, value):
    method, route = key.split(" ", 1)
    path_params = dict(check.path_extra)
    body = {name: _resolve(world, v) for name, v in check.body_extra}
    url_query = ""
    if check.where == "path":
        path_params[check.param] = value
    elif check.where == "body":
        body[check.param] = [value] if check.list_param else value
    else:
        url_query = f"?{check.param}={value}"
    url = _url(world, route, path_params) + url_query
    return _call(_client(world, check.actor), method, url, body, check.fmt)


@pytest.mark.parametrize("key,check", _params(IdCheck))
def test_id_check(world, key, check):
    refs = world["refs"]
    variants = {"他組織": refs[f"foreign.{check.target}"]}
    if check.target in SHARED_PK:
        variants["全体共有"] = refs[f"shared.{check.target}"]
    if check.same_org:
        variants["同じ組織の別の利用者"] = refs[f"same.{check.target}"]
    missing_id = MISSING_UUID if check.target == "asset" else MISSING_ID

    missing = _id_request(world, key, check, missing_id)
    assert missing.status_code == check.status, _text(missing)
    for name, variant_id in variants.items():
        before = _snapshot(world, check, variant_id)
        response = _id_request(world, key, check, variant_id)
        assert response.status_code == check.status, f"{name}: {_text(response)}"
        assert _masked(response) == _masked(missing), name
        assert _snapshot(world, check, variant_id) == before, f"{name}: 書き込まれた"

    if check.own_status is not None:  # 正の対照（全部断るだけの実装で通らない）
        own = _id_request(world, key, check, refs[f"own.{check.target}"])
        assert own.status_code == check.own_status, _text(own)


# -------------------------------------------------- TC-03 一覧・集計と自分の記録 ----
@pytest.mark.parametrize("key,check", _params(ListCheck))
def test_list_check(world, key, check):
    method, route = key.split(" ", 1)
    response = _call(_client(world, check.actor), method, "/" + route, {}, "json")

    assert response.status_code == 200, _text(response)[:300]
    assert _leaks(response) == []


@pytest.mark.parametrize("key,check", _params(OwnCheck))
def test_own_check(world, key, check):
    method, route = key.split(" ", 1)
    url = _url(world, route, {"pk": f"@{check.own}"})
    response = _call(_client(world, "user"), method, url, {}, "json")

    assert _leaks(response) == []


# -------------------------------------------------------- TC-05 運用者専用 ----
@pytest.mark.parametrize("key,check", _params(StaffOnlyCheck))
@pytest.mark.parametrize("actor", ["org_admin", "user"])
def test_staff_only_check(world, key, check, actor):
    method, route = key.split(" ", 1)
    url = _url(world, route, {"pk": "@user_b"})
    response = _call(_client(world, actor, login=True), method, url, {}, "json")

    assert response.status_code == check.status
    assert _leaks(response) == []


# ------------------------------------------- TC-06 組織に属さない組織管理者 ----
def test_noorg_org_admin_sees_no_problems(world):
    admin = User.objects.create_user(
        email="noorg_admin_i446@example.com", user_id="noorg_admin_i446", password=None,
        organization=None, role="admin")
    world["actors"]["noorg_admin"] = admin
    client = _client(world, "noorg_admin")

    listed = client.get("/api/problems/")
    shared = client.get(f"/api/problems/{SHARED_PK['problem']}/")
    missing = client.get(f"/api/problems/{MISSING_ID}/")

    assert listed.status_code == 200
    assert listed.json() == []
    assert shared.status_code == 404
    assert _masked(shared) == _masked(missing)
