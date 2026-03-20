"""
ユーザーが登録した科目を取得するAPIビュー
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.subject_service import subject_service


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_subjects(request):
    """
    ユーザーが会員登録時に選択した科目一覧を取得
    ダッシュボード・統計画面のプルダウン用
    """
    # SubjectServiceの新メソッドを使用
    subjects = subject_service.get_user_selected_subjects(
        request.user,
        use_cache=True
    )

    # プルダウン用にid, nameのみ返す
    subject_list = [
        {
            'id': subject.id,
            'name': subject.name,
        }
        for subject in subjects
    ]

    return Response(subject_list)