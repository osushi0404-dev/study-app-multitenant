"""
会員登録で作る、本人ひとりの組織（個人用の組織）の作り方（I539）

名前・slug・カテゴリの決まりをここ 1 か所に置く。データマイグレーション 0023 は過去のモデルで
同じ決まりを自分の中に書く（後でここが変わってもマイグレーションの意味が変わらないように）。
"""
import itertools
import secrets
from typing import Iterable, Optional

from .models import Organization, OrganizationCategory

PERSONAL_ORG_SLUG_PREFIX = 'p-'


def personal_org_name(user_id: str) -> str:
    """個人用の組織の名前（ユーザー ID は 3〜30 文字なので name の 100 文字に収まる）"""
    return f'{user_id}さんの学習'


def pick_unused_slug(candidates: Iterable[str]) -> str:
    """候補のうち、どの組織の slug とも重ならない最初のもの（画像の置き場所 org/<slug>/ を重ねない）"""
    for candidate in candidates:
        if not Organization.objects.filter(slug=candidate).exists():
            return candidate
    raise ValueError('使える slug の候補がありません')


def new_personal_org_slug() -> str:
    """推測されない slug（p- と 12 桁の 16 進）。ユーザー ID は URL・画像の置き場所に出さない"""
    return pick_unused_slug(
        PERSONAL_ORG_SLUG_PREFIX + secrets.token_hex(6) for _ in itertools.count())


def get_personal_category() -> Optional[OrganizationCategory]:
    """「個人利用」カテゴリ（マイグレーション 0017 が作る）。無ければ None（環境の異常）"""
    return OrganizationCategory.objects.filter(slug=OrganizationCategory.PERSONAL_SLUG).first()


def create_personal_organization(*, user_id: str, category: OrganizationCategory) -> Organization:
    """本人ひとりの組織を作る（呼ぶ側のトランザクションの中で使う）"""
    return Organization.objects.create(
        name=personal_org_name(user_id),
        slug=new_personal_org_slug(),
        type=Organization.TYPE_PERSONAL,
        is_individual=True,
        category=category,
        is_active=True,
    )
