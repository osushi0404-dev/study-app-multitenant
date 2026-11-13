"""
ダッシュボードの数字（読み取り専用の集計・I473）

数字の出どころはクイズの答えの記録（QuizAnswer）だけ。QuizAnswer を読むのは _answers() の 1 か所に限り、
ほかの集計はすべてその戻り値から作る（本人の答えで、自組織の科目の問題へのものだけになる）。
日付は日本時間（settings.TIME_ZONE）で区切る。
"""
from datetime import date, datetime, time, timedelta
from typing import Optional

from django.db.models import Count, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce, Least, TruncDate
from django.utils import timezone

from core.subject_service import subject_service
from problems.models import QuizAnswer
from problems.querysets import scope_to_user_org
from problems.services.tenant_scope import available_problems

STUDY_SECONDS_CAP_PER_ANSWER = 300  # 1 問あたりの学習時間の上限（秒）。放置した時間を数えない
RECENT_DAYS = 7                     # 直近の日数（推移・「この 7 日間解いていない」）
WEAK_MIN_ANSWERED = 5               # 間違いやすい分野に入れる最低の解答数
WEAK_ACCURACY_BELOW = 0.7           # 間違いやすい分野の正答率のしきい値（未満）
LIST_LIMIT = 3                      # 間違いやすい分野・おすすめの最大件数

KIND_WEAK = 'weak_subject'
KIND_UNSTUDIED = 'unstudied_subject'


def _answers(user) -> QuerySet:
    """本人の答えのうち、自組織の科目の問題へのもの（組織に属さない利用者は空）"""
    return scope_to_user_org(
        QuizAnswer.objects.filter(session__user=user), user, subject_path='problem__subject')


def _answer_counts() -> dict:
    """解答数・正解数の集計式"""
    return {
        'answered_count': Count('id'),
        'correct_count': Count('id', filter=Q(is_correct=True)),
    }


def _counts() -> dict:
    """学習時間（1 問 300 秒まで）・解答数・正解数の集計式"""
    return {
        'study_seconds': Coalesce(
            Sum(Least('time_taken', Value(STUDY_SECONDS_CAP_PER_ANSWER))), 0),
        **_answer_counts(),
    }


def _rate(correct: int, answered: int) -> Optional[float]:
    """正答率（0〜1・小数第 4 位）。答えが 0 件なら None（0% と区別する）"""
    return round(correct / answered, 4) if answered else None


def _percent(rate: float) -> int:
    """画面の Math.round と同じく、0.5 は切り上げる"""
    return int(rate * 100 + 0.5)


def _start_of(day: date) -> datetime:
    """その日（日本時間）の 0 時"""
    return timezone.make_aware(datetime.combine(day, time.min))


def _with_rate(counts: dict) -> dict:
    return {**counts, 'accuracy_rate': _rate(counts['correct_count'], counts['answered_count'])}


def _last_days(answers: QuerySet, today: date) -> list:
    """今日を含む直近 7 日（古い順・答えが無い日も 0 で必ず 7 件）"""
    first = today - timedelta(days=RECENT_DAYS - 1)
    rows = (
        answers.filter(answered_at__gte=_start_of(first),
                       answered_at__lt=_start_of(today + timedelta(days=1)))
        .annotate(day=TruncDate('answered_at'))
        .values('day')
        .annotate(**_counts())
        .order_by()  # 既定の並び（answered_at）で GROUP BY が崩れないように外す
    )
    by_day = {row['day']: row for row in rows}
    days = []
    for offset in range(RECENT_DAYS):
        day = first + timedelta(days=offset)
        row = by_day.get(day, {})
        days.append({
            'date': day.isoformat(),
            'study_seconds': row.get('study_seconds', 0),
            'answered_count': row.get('answered_count', 0),
            'correct_count': row.get('correct_count', 0),
        })
    return days


def _current_streak(answers: QuerySet, today: date) -> int:
    """答えのある日が今日（今日がまだなら昨日）から何日続いているか"""
    days = set(
        answers.filter(answered_at__lt=_start_of(today + timedelta(days=1)))
        .annotate(day=TruncDate('answered_at'))
        .values_list('day', flat=True)
        .order_by()
        .distinct()
    )
    cursor = today if today in days else today - timedelta(days=1)
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _weak_subjects(answers: QuerySet) -> list:
    """5 問以上答えた科目のうち、正答率 70% 未満を低い順（同じなら科目名順）に 3 件"""
    rows = (
        answers.values('problem__subject_id', 'problem__subject__name')
        .annotate(**_answer_counts())
        .filter(answered_count__gte=WEAK_MIN_ANSWERED)
        .order_by()
    )
    weak = [
        {
            'subject_id': row['problem__subject_id'],
            'subject_name': row['problem__subject__name'],
            'answered_count': row['answered_count'],
            'accuracy_rate': _rate(row['correct_count'], row['answered_count']),
        }
        for row in rows
        if row['correct_count'] / row['answered_count'] < WEAK_ACCURACY_BELOW
    ]
    weak.sort(key=lambda w: (w['accuracy_rate'], w['subject_name']))
    return weak[:LIST_LIMIT]


def _recommendations(user, answers: QuerySet, weak: list, today: date) -> list:
    """
    おすすめ（最大 3 件）: 間違いやすい分野の科目 → 利用者が選んだ科目のうち、
    この 7 日間に答えが無く、自組織の未削除の問題がある科目（科目名順）

    クエリ数をデータの量で変えないため、件数が足りていても候補の集計は省かない。
    """
    recent_from = _start_of(today - timedelta(days=RECENT_DAYS - 1))
    recent_subject_ids = set(
        answers.filter(answered_at__gte=recent_from)
        .values_list('problem__subject_id', flat=True)
        .order_by()
        .distinct()
    )
    selected = list(subject_service.get_user_selected_subjects(user, use_cache=True))
    # 組織の問題の全体ではなく、選んだ科目の問題だけを見る
    subjects_with_problems = set(
        available_problems(user).filter(subject__in=selected)
        .values_list('subject_id', flat=True).order_by().distinct())

    recommendations = [
        {
            'kind': KIND_WEAK,
            'subject_id': w['subject_id'],
            'subject_name': w['subject_name'],
            'reason': f"正答率が {_percent(w['accuracy_rate'])}% です。復習しましょう",
        }
        for w in weak
    ]
    weak_ids = {w['subject_id'] for w in weak}
    for subject in selected:
        if (subject.id in weak_ids or subject.id in recent_subject_ids
                or subject.id not in subjects_with_problems):
            continue
        recommendations.append({
            'kind': KIND_UNSTUDIED,
            'subject_id': subject.id,
            'subject_name': subject.name,
            'reason': f'この {RECENT_DAYS} 日間、解いていません',
        })
    return recommendations[:LIST_LIMIT]


def build_overview(user, subject=None, *, now: Optional[datetime] = None) -> dict:
    """
    GET /api/dashboard/overview/ の中身（形は serializers.OverviewSerializer）

    subject があれば、今日・連続日数・直近 7 日・全期間の数字をその科目だけで数える。
    間違いやすい分野とおすすめは、科目をまたいで比べる一覧なので常に全科目から出す。
    now は日付の境界を確かめるテストのため（省略時は今）。
    """
    today = timezone.localdate(now or timezone.now())
    answers = _answers(user)
    scoped = answers.filter(problem__subject=subject) if subject is not None else answers

    last_days = _last_days(scoped, today)
    today_counts = {k: v for k, v in last_days[-1].items() if k != 'date'}
    totals = scoped.aggregate(**_answer_counts())
    weak = _weak_subjects(answers)

    return {
        'has_data': totals['answered_count'] > 0,
        'today': _with_rate(today_counts),
        'streak': {'current_days': _current_streak(scoped, today)},
        'totals': _with_rate(totals),
        'last_7_days': last_days,
        'weak_subjects': weak,
        'recommendations': _recommendations(user, answers, weak, today),
    }
