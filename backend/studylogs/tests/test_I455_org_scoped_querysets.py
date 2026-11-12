"""
I455: 学習記録まわりの 8 モデルの、組織の境界つきの取り出し方（objects.for_user）

- 各モデルの境界の決まり（科目への経路・科目が空の記録を残すか）を直接確かめる
- 組織に属さない利用者・同じ組織の別の利用者・提案の 2 経路を確かめる
- studylogs・dashboard で 8 モデルを絞らずに読む行に、理由のコメントがあることを確かめる
  （付け忘れを止める。関連の取り出し・変数に入れたモデルなど、普通でない書き方は見ない）

TC-01〜TC-04・TC-06（docs/tests/open/I455_auto_test.md）に対応。
"""
import ast
import io
import tokenize
from pathlib import Path

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from accounts.models import Organization, OrganizationCategory
from problems.models import Problem, QuizSession, Subject
from problems.querysets import OrgScopedQuerySet
from studylogs.models import (
    LearningSuggestion, LearningWeakness, MistakePattern, ProblemAttempt,
    SpacedRepetitionCard, SpacedRepetitionReview, StudyLog,
)

User = get_user_model()

BACKEND_DIR = Path(__file__).resolve().parents[2]
REASON_MARK = "組織で絞らない"


@pytest.fixture(autouse=True)
def _clear_caches():
    for alias in settings.CACHES:
        caches[alias].clear()
    yield
    for alias in settings.CACHES:
        caches[alias].clear()


@pytest.fixture
def setup(db):
    cat = OrganizationCategory.objects.create(name="テストI455", slug="test-cat-i455")
    org_a = Organization.objects.create(
        name="組織I455A", slug="org-i455-a", type="school", category=cat, is_active=True)
    org_b = Organization.objects.create(
        name="組織I455B", slug="org-i455-b", type="school", category=cat, is_active=True)

    def user(name, org):
        return User.objects.create_user(
            email=f"{name}_i455@example.com", user_id=f"{name}_i455", password="pass",
            organization=org, role="user",
        )

    subjects = {
        "own": Subject.objects.create(name="科目I455A", slug="subj-i455-a", organization=org_a),
        "foreign": Subject.objects.create(name="科目I455B", slug="subj-i455-b", organization=org_b),
        "shared": Subject.objects.create(name="共有I455", slug="subj-i455-s", organization=None),
    }
    return {
        "user_a": user("a", org_a), "user_a2": user("a2", org_a),
        "user_noorg": user("n", None), "subjects": subjects,
    }


def _problem(user, subject):
    return Problem.objects.create(
        subject=subject, organization=subject.organization, created_by=user,
        question=f"問題{subject.slug}", problem_type="single", difficulty=1,
    )


def _card(user, problem):
    card, _ = SpacedRepetitionCard.objects.get_or_create(
        user=user, problem=problem, defaults={"next_review_date": timezone.now()})
    return card


def _review(user, problem):
    return SpacedRepetitionReview.objects.create(
        card=_card(user, problem), user=user, problem=problem, quality_score=3,
        response_time_seconds=5, is_correct=True, previous_ease_factor=2.5,
        previous_interval=1, previous_repetition_count=0, new_ease_factor=2.5, new_interval=1,
        new_repetition_count=1, next_review_date=timezone.now(),
    )


# モデルの鍵: (モデル, 記録を作る関数〔利用者・科目〕, 科目が空の記録を残すか)
# 問題を指すモデルは、その科目の問題を作って指す（問題は必須なので科目が空の記録は無い）
SPECS = {
    "StudyLog": (StudyLog, lambda u, s: StudyLog.objects.create(user=u, subject=s), True),
    # 進行中の回は利用者ごとに 1 つまでなので、終了済みの回で作る
    "QuizSession": (
        QuizSession,
        lambda u, s: QuizSession.objects.create(user=u, subject=s, is_active=False),
        True,
    ),
    "MistakePattern": (
        MistakePattern,
        lambda u, s: MistakePattern.objects.create(
            user=u, subject=s, pattern_type="subject_difficulty", description="d"),
        True,
    ),
    "LearningSuggestion": (
        LearningSuggestion,
        lambda u, s: LearningSuggestion.objects.create(
            user=u, subject=s, suggestion_type="study_method", title="t", description="d"),
        True,
    ),
    "LearningWeakness": (
        LearningWeakness,
        lambda u, s: LearningWeakness.objects.create(user=u, subject=s, concept_name="c"),
        False,
    ),
    "ProblemAttempt": (
        ProblemAttempt,
        lambda u, s: ProblemAttempt.objects.create(user=u, problem=_problem(u, s)),
        False,
    ),
    "SpacedRepetitionCard": (
        SpacedRepetitionCard, lambda u, s: _card(u, _problem(u, s)), False),
    "SpacedRepetitionReview": (
        SpacedRepetitionReview, lambda u, s: _review(u, _problem(u, s)), False),
}


def _ids(queryset):
    return set(queryset.values_list("id", flat=True))


@pytest.mark.parametrize("key", list(SPECS))
def test_for_user_scopes_by_org(setup, key):
    """TC-01: 本人の、自組織の科目（と、空を許すモデルは科目が空）の記録だけ"""
    model, make, allow_null = SPECS[key]
    user_a, subjects = setup["user_a"], setup["subjects"]
    own = make(user_a, subjects["own"])
    make(user_a, subjects["foreign"])
    make(user_a, subjects["shared"])
    make(setup["user_a2"], subjects["own"])
    expected = {own.id}
    if allow_null:
        expected.add(make(user_a, None).id)

    assert _ids(model.objects.for_user(user_a)) == expected


@pytest.mark.parametrize("key", list(SPECS))
def test_for_user_noorg_user(setup, key):
    """TC-02: 組織に属さない利用者は、空を許すモデルなら科目が空の記録だけ、ほかは空"""
    model, make, allow_null = SPECS[key]
    user_noorg = setup["user_noorg"]
    make(user_noorg, setup["subjects"]["own"])
    expected = {make(user_noorg, None).id} if allow_null else set()

    assert _ids(model.objects.for_user(user_noorg)) == expected


def test_learning_suggestion_both_paths(setup):
    """TC-03: 提案の科目とパターンの科目の両方で絞る"""
    user_a, subjects = setup["user_a"], setup["subjects"]
    own, foreign = subjects["own"], subjects["foreign"]
    patterns = {
        "own": MistakePattern.objects.create(
            user=user_a, subject=own, pattern_type="subject_difficulty", description="d"),
        "foreign": MistakePattern.objects.create(
            user=user_a, subject=foreign, pattern_type="subject_difficulty", description="d"),
        "null": MistakePattern.objects.create(
            user=user_a, subject=None, pattern_type="subject_difficulty", description="d"),
    }

    def suggestion(subject, pattern):
        return LearningSuggestion.objects.create(
            user=user_a, subject=subject, mistake_pattern=pattern,
            suggestion_type="study_method", title="t", description="d").id

    kept = {
        suggestion(own, patterns["own"]),
        suggestion(None, patterns["null"]),
        suggestion(own, None),
    }
    suggestion(own, patterns["foreign"])
    suggestion(foreign, patterns["own"])

    assert _ids(LearningSuggestion.objects.for_user(user_a)) == kept


def test_base_without_subject_paths_raises(setup):
    """TC-04: 境界の決まりを書かない QuerySet は、絞らずに返さず例外にする"""
    with pytest.raises(ImproperlyConfigured):
        OrgScopedQuerySet(model=StudyLog).for_user(setup["user_a"])


def _scoped_model_names():
    """既定の取り出し口が OrgScopedQuerySet のモデル（表に足し忘れたモデルも見張るため登録から集める）"""
    return {
        model.__name__ for model in apps.get_models()
        if isinstance(model._default_manager.get_queryset(), OrgScopedQuerySet)
    }


SCOPED_MODELS = _scoped_model_names()
NOT_READS = {"for_user", "create", "get_or_create", "update_or_create", "bulk_create"}


def _model_name(node):
    """`StudyLog`・`models.StudyLog` のどちらの書き方でもモデル名を返す"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _missing_reasons(source):
    """
    8 モデルを絞らずに読み、理由のコメントが無い行番号

    <モデル>.objects.<メソッド> の形を見る（基準の行はモデル名の書かれた行。複数行の呼び出しでも先頭）。
    理由は、直前のコメントだけの行か、同じ行のコメントに書く。前の行の行末コメント（その行の
    呼び出しの理由）や文字列の中の印は、別の呼び出しの理由に数えない。
    """
    lines = source.splitlines()
    marked = {  # 印を含むコメントのある行
        tok.start[0] for tok in tokenize.generate_tokens(io.StringIO(source).readline)
        if tok.type == tokenize.COMMENT and REASON_MARK in tok.string
    }

    def has_reason(lineno):
        if lineno in marked:
            return True
        prev = lineno - 1
        return prev in marked and lines[prev - 1].lstrip().startswith("#")

    missing = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "objects"
                and _model_name(node.value.value) in SCOPED_MODELS
                and node.attr not in NOT_READS):
            continue
        if not has_reason(node.lineno):
            missing.append(node.lineno)
    return sorted(missing)


def _unscoped_reads_without_reason():
    """studylogs・dashboard のテスト以外で、8 モデルを絞らずに読み、理由のコメントが無い行"""
    missing = []
    for app in ("studylogs", "dashboard"):
        for path in sorted((BACKEND_DIR / app).rglob("*.py")):
            rel = path.relative_to(BACKEND_DIR)
            if {"tests", "migrations"} & set(rel.parts):
                continue
            missing += [f"{rel}:{n}" for n in _missing_reasons(path.read_text(encoding="utf-8"))]
    return missing


def test_reason_check_catches_unmarked_reads():
    """TC-07: 検出器そのものが、普通の書き方の付け忘れを見落とさない"""
    source = "\n".join([
        f"# {REASON_MARK}: 件数だけ",                          # 1
        "a = StudyLog.objects.filter(user=u).count()",          # 2 理由あり
        "b = StudyLog.objects.filter(user=u).count()",          # 3 直前の理由を共有しない
        "c = models.ProblemAttempt.objects.filter(user=u)",     # 4 models.X の形
        "d = QuizSession.objects.filter(",                      # 5 複数行の呼び出し
        "    user=u,",
        ")",
        "e = LearningWeakness.objects.filter(**kw)",            # 8
        "f = SpacedRepetitionCard.objects.all()",               # 9
        "g = StudyLog.objects.for_user(u)",                     # 10 絞っている
        "h = StudyLog.objects.create(user=u)",                  # 11 書き込み
        f"i = MistakePattern.objects.get(id=1)  # {REASON_MARK}: 印付け",  # 12 同じ行の理由
        "j = StudyLog.objects.values()",                        # 13 前の行の行末の理由を共有しない
        f"k = '{REASON_MARK}'",                                 # 14 文字列の中の印
        "m = StudyLog.objects.values()",                        # 15 文字列の印を理由に数えない
    ])
    assert _missing_reasons(source) == [3, 4, 5, 8, 9, 13, 15]


def test_specs_cover_all_scoped_models():
    """境界つきの取り出し方を持つモデルは、すべて TC-01・TC-02 の表で確かめる"""
    assert SCOPED_MODELS == set(SPECS)


def test_unscoped_reads_have_reason_comment():
    """TC-06: 絞らずに読むなら、直前の行に「# 組織で絞らない: <理由>」を書く"""
    missing = _unscoped_reads_without_reason()
    assert missing == [], (
        "8 モデルを組織で絞らずに読んでいます。objects.for_user(user) を使うか、"
        f"直前に「# {REASON_MARK}: <理由>」を書いてください: {missing}"
    )
