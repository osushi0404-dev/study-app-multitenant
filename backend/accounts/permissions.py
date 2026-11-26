from rest_framework.permissions import BasePermission

from .passkeys import has_valid_reauth

REAUTH_HEADER = 'X-Reauth-Token'


class HasRecentReauth(BasePermission):
    """パスキーの登録・削除の前に、5 分以内の本人確認の印（ヘッダー X-Reauth-Token）を求める（I619）"""
    message = '続けるには、本人であることを確かめてください'

    def has_permission(self, request, view):
        return has_valid_reauth(user=request.user, token=request.headers.get(REAUTH_HEADER))
