from rest_framework.permissions import BasePermission

from .passkeys import has_valid_reauth

REAUTH_HEADER = 'X-Reauth-Token'


class HasRecentReauth(BasePermission):
    """パスキーの登録・削除の前に、5 分以内の本人確認の印（ヘッダー X-Reauth-Token）を求める（I619）"""
    message = '続けるには、本人であることを確かめてください'

    def has_permission(self, request, view):
        return has_valid_reauth(user=request.user, token=request.headers.get(REAUTH_HEADER))


class IsOrgMemberManager(BasePermission):
    """メンバー管理（I620）: 招待で人を迎えられる組織（本人ひとりの組織・共有の personal 組織を除く）の管理者"""
    message = 'メンバーを管理する権限がありません'

    def has_permission(self, request, view):
        user = request.user
        return getattr(user, 'is_authenticated', False) and user.can_manage_members
