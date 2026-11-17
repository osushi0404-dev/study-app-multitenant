"""
I466: 苦手の判定（problems/services/weakness.py）

- 苦手の基準（5 問以上・正答率 70% 未満）の境界
- 難易度別の苦手（全科目・正答率の低い順）
- 急いだ間違い（直近 30 日・20 問以上・平均の半分未満の間違いが 25% 以上）
- 組織の境界（本人・自組織の答えだけ）

TC-01〜TC-06・TC-16（docs/tests/open/I466_auto_test.md）に対応。
"""
import pytest

from problems.services.weakness import (
    is_weak, rushed_mistakes, user_answers, weak_difficulties,
)
from problems.tests.i466_data import (
    EASY, HARD, MEDIUM, NOW, answer, answers, days_ago, make_problem, make_world,
)


@pytest.fixture
def world(db):
    return make_world()


@pytest.mark.parametrize("answered,correct,expected", [
    (4, 0, False),
    (5, 3, True),
    (5, 4, False),
    (10, 7, False),
    (5, 0, True),
    (0, 0, False),
])
def test_is_weak_boundaries(answered, correct, expected):
    """TC-01"""
    assert is_weak(answered, correct) is expected


def test_weak_difficulties_lists_weak_levels_lowest_first(world):
    """TC-02: 上級は 数学 と 英語 にまたがって数える"""
    user = world["user_a"]
    answers(user, make_problem(world["math"], user, "易", EASY), 6, 5)
    answers(user, make_problem(world["math"], user, "中", MEDIUM), 5, 2)
    answers(user, make_problem(world["math"], user, "難1", HARD), 4, 1)
    answers(user, make_problem(world["english"], user, "難2", HARD), 6, 2)

    assert weak_difficulties(user_answers(user)) == [
        {"difficulty": "hard", "answered_count": 10, "accuracy_rate": 0.3},
        {"difficulty": "medium", "answered_count": 5, "accuracy_rate": 0.4},
    ]


def test_weak_difficulties_ties_and_empty(world):
    """TC-03"""
    user, other = world["user_a"], world["user_a2"]
    # ① 同じ 40% は易しい順
    answers(user, make_problem(world["math"], user, "易", EASY), 5, 2)
    answers(user, make_problem(world["math"], user, "難", HARD), 5, 2)
    assert [d["difficulty"] for d in weak_difficulties(user_answers(user))] == ["easy", "hard"]
    # ② 答えなし
    assert weak_difficulties(user_answers(other)) == []
    # ③ 5 問未満
    answers(other, make_problem(world["math"], user, "中", MEDIUM), 4, 0)
    assert weak_difficulties(user_answers(other)) == []


def _rushed_base(world, *, correct_count=16, rushed_wrong=2, slow_wrong=2):
    """正解 correct_count 問（40 秒）・不正解 rushed_wrong 問（5 秒）・不正解 slow_wrong 問（40 秒）"""
    user = world["user_a"]
    problem = make_problem(world["math"], user, "急")
    answers(user, problem, correct_count, correct_count, seconds=40, at=days_ago(1))
    answers(user, problem, rushed_wrong, 0, seconds=5, at=days_ago(1))
    answers(user, problem, slow_wrong, 0, seconds=40, at=days_ago(1))
    return user, problem


def test_rushed_mistakes_reports_share(world):
    """TC-04: 平均 36.5 秒・半分 18.25 秒未満の間違いが 2"""
    user, _ = _rushed_base(world)
    assert rushed_mistakes(user_answers(user), NOW) == {
        "mistake_count": 4, "rushed_count": 2, "rushed_rate": 0.5,
    }


def test_rushed_mistakes_too_few_answers(world):
    """TC-05 ①: 19 問"""
    user, _ = _rushed_base(world, correct_count=15)
    assert rushed_mistakes(user_answers(user), NOW) is None


def test_rushed_mistakes_ignores_zero_seconds(world):
    """TC-05 ②: 0 秒の答えは急いだにも平均にも入らない（間違い 9・急いだ 2 で 22%）"""
    user, problem = _rushed_base(world)
    answers(user, problem, 5, 0, seconds=0, at=days_ago(1))
    assert rushed_mistakes(user_answers(user), NOW) is None


def test_rushed_mistakes_caps_long_answers(world):
    """TC-05 ③: 平均は 300 秒で頭打ち（25.5 秒）。頭打ちしないと 30 秒の間違いが急いだになる"""
    user = world["user_a"]
    problem = make_problem(world["math"], user, "放置")
    answers(user, problem, 18, 18, seconds=10, at=days_ago(1))
    answer(user, problem, correct=True, seconds=3000, at=days_ago(1))
    answer(user, problem, correct=False, seconds=30, at=days_ago(1))
    assert rushed_mistakes(user_answers(user), NOW) is None


def test_rushed_mistakes_exactly_quarter(world):
    """TC-05 ④: ちょうど 25% は出す"""
    user, _ = _rushed_base(world, rushed_wrong=1, slow_wrong=3)
    assert rushed_mistakes(user_answers(user), NOW) == {
        "mistake_count": 4, "rushed_count": 1, "rushed_rate": 0.25,
    }


def test_rushed_mistakes_window_is_30_days(world):
    """TC-05 ⑤: 31 日前の答えは数えない（期間内は 19 問）"""
    user, problem = _rushed_base(world, correct_count=15)
    answer(user, problem, correct=True, seconds=40, at=days_ago(31))
    assert rushed_mistakes(user_answers(user), NOW) is None


def test_rushed_mistakes_none_without_mistakes(world):
    """TC-06"""
    user, _ = _rushed_base(world, correct_count=20, rushed_wrong=0, slow_wrong=0)
    assert rushed_mistakes(user_answers(user), NOW) is None


def test_other_org_and_other_people_are_not_counted(world):
    """TC-16"""
    user_a, user_a2 = world["user_a"], world["user_a2"]
    # ① B科目 の問題への user_a の答え（不具合で残った想定）
    b_problem = make_problem(world["subject_b"], world["user_b"], "B", HARD)
    answers(user_a, b_problem, 25, 0, seconds=5, at=days_ago(1))
    assert weak_difficulties(user_answers(user_a)) == []
    assert rushed_mistakes(user_answers(user_a), NOW) is None
    # ② 同じ組織の別人の答えは入らない
    answers(user_a2, make_problem(world["math"], user_a, "難", HARD), 10, 0)
    assert weak_difficulties(user_answers(user_a)) == []
