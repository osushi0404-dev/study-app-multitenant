"""
苦手の判定（I466）

ダッシュボードの「間違いやすい分野」（科目別・難易度別・急いだ間違い）と、クイズのモード weak（苦手を優先）が
同じ基準で苦手を決めるため、基準の定数と計算をここだけに置く。

材料は本人の、自組織の科目の問題への答え（QuizAnswer.objects.for_user）だけ。結果は保存せず、読むたびに
数本の集計クエリで計算する（クエリの数は答え・問題の件数で変わらない）。
難易度の数字と文字の対応は problems/difficulty.py だけを使う。
"""
from datetime import datetime, timedelta
from typing import Optional

from django.db.models import (
    Avg, Case, Count, F, IntegerField, OuterRef, Q, QuerySet, Subquery, Value, When,
)
from django.db.models.functions import Least

from problems.difficulty import LEVEL_BY_LABEL, label_of
from problems.models import QuizAnswer, Subject

WEAK_MIN_ANSWERED = 5          # 苦手と判定する最低の解答数
WEAK_ACCURACY_BELOW = 0.7      # 苦手とみなす正答率（未満）
ANSWER_SECONDS_CAP = 300       # 1 問の解答時間の上限（秒）。放置した時間を数えない
RUSHED_WINDOW_DAYS = 30        # 急いだ間違いを見る期間（日）
RUSHED_MIN_ANSWERED = 20       # その期間の最低の解答数
RUSHED_TIME_RATIO = 0.5        # 平均の解答時間に対する「急いだ」の比（未満）
RUSHED_SHARE_AT_LEAST = 0.25   # 間違いに占める急いだ間違いの割合（以上）で出す

# 苦手を優先の段（小さいほど先に出す）
TIER_LAST_WRONG = 0
TIER_WEAK_DIFFICULTY = 1
TIER_OTHER = 2


def rate(correct: int, answered: int) -> Optional[float]:
    """正答率などの割合（0〜1・小数第 4 位）。分母が 0 なら None（0% と区別する）。ダッシュボードと共通"""
    return round(correct / answered, 4) if answered else None


def answer_counts() -> dict:
    """解答数・正解数の集計式（ダッシュボードと共通）"""
    return {
        'answered_count': Count('id'),
        'correct_count': Count('id', filter=Q(is_correct=True)),
    }


def user_answers(user) -> QuerySet:
    """本人の、自組織の科目の問題への答え（組織に属さない利用者は空）"""
    return QuizAnswer.objects.for_user(user)


def is_weak(answered: int, correct: int) -> bool:
    """5 問以上答えて正答率 70% 未満なら苦手"""
    return answered >= WEAK_MIN_ANSWERED and correct / answered < WEAK_ACCURACY_BELOW


def weak_difficulties(answers: QuerySet) -> list:
    """苦手な難易度を、正答率の低い順（同じなら易しい順）に返す（1 クエリ）"""
    rows = answers.values('problem__difficulty').annotate(**answer_counts()).order_by()
    weak = []
    for row in rows:
        label = label_of(row['problem__difficulty'])
        if label is None or not is_weak(row['answered_count'], row['correct_count']):
            continue
        weak.append({
            'difficulty': label,
            'answered_count': row['answered_count'],
            'accuracy_rate': rate(row['correct_count'], row['answered_count']),
        })
    weak.sort(key=lambda w: (w['accuracy_rate'], LEVEL_BY_LABEL[w['difficulty']]))
    return weak


def rushed_mistakes(answers: QuerySet, now: datetime) -> Optional[dict]:
    """
    直近 30 日の間違いのうち、平均の解答時間の半分未満で答えたものが 25% 以上なら、その数と割合

    解答時間 0 の答え（記録の無い古い答え）は平均にも急いだ間違いにも入れない。平均は 1 問 300 秒で頭打ちにする。
    当てはまらなければ None（解答 20 問未満・間違い 0・時間の記録なしを含む）。クエリは常に 2 本。
    """
    recent = answers.filter(answered_at__gt=now - timedelta(days=RUSHED_WINDOW_DAYS),
                            answered_at__lte=now)
    totals = recent.aggregate(
        answered=Count('id'),
        mistakes=Count('id', filter=Q(is_correct=False)),
        average=Avg(Least('time_taken', Value(ANSWER_SECONDS_CAP)), filter=Q(time_taken__gt=0)),
    )
    # クエリの数をデータで変えないため（ダッシュボードの決まり・I473）、当てはまらなくても 2 本目を流す
    rushed = recent.filter(
        is_correct=False, time_taken__gt=0,
        time_taken__lt=(totals['average'] or 0) * RUSHED_TIME_RATIO,
    ).count()
    if (totals['answered'] < RUSHED_MIN_ANSWERED or totals['mistakes'] == 0
            or rushed / totals['mistakes'] < RUSHED_SHARE_AT_LEAST):
        return None
    return {
        'mistake_count': totals['mistakes'],
        'rushed_count': rushed,
        'rushed_rate': rate(rushed, totals['mistakes']),
    }


def order_weak_first(problems: QuerySet, user, subject: Optional[Subject]) -> tuple:
    """
    苦手を優先の並べ方。戻り値は (並べた問題, いつもの順にしたか)

    回の科目（科目なしの回は全科目）の本人の答えが 5 問未満なら、苦手を判定できないので、いつもの順（乱数）。
    それ以外は、段（最後の答えが不正解 → 苦手な難易度〔全科目で判定〕→ それ以外）、
    最後に答えた時刻の古い順（未回答が先）、id の順に並べる。
    """
    answers = user_answers(user)
    subject_answers = answers.filter(problem__subject=subject) if subject is not None else answers
    if subject_answers.count() < WEAK_MIN_ANSWERED:
        return problems.order_by('?'), True

    weak_levels = [LEVEL_BY_LABEL[w['difficulty']] for w in weak_difficulties(answers)]
    tiers = [When(last_correct=False, then=Value(TIER_LAST_WRONG))]
    if weak_levels:  # 空の __in を When に渡さない
        tiers.append(When(difficulty__in=weak_levels, then=Value(TIER_WEAK_DIFFICULTY)))
    last = answers.filter(problem=OuterRef('pk')).order_by('-answered_at', '-id')
    ordered = (
        problems
        .annotate(
            last_answered_at=Subquery(last.values('answered_at')[:1]),
            last_correct=Subquery(last.values('is_correct')[:1]),
        )
        .annotate(weak_tier=Case(*tiers, default=Value(TIER_OTHER), output_field=IntegerField()))
        .order_by('weak_tier', F('last_answered_at').asc(nulls_first=True), 'id')
    )
    return ordered, False
