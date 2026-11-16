"""
利用者が学ぶ科目の API

- GET・PUT /api/user/subjects/: 選んだ科目の一覧（ダッシュボード・統計のプルダウン用）と、その置き換え（I494）
- GET /api/user/subjects/available/: 選べる自組織の科目（設定画面の「学ぶ科目」のカード・I494）
"""
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.subject_service import subject_service
from problems.serializers import (
    AvailableSubjectSerializer, UserSubjectSelectionSerializer, UserSubjectSerializer,
)
from problems.services.tenant_scope import available_subjects
from problems.services.user_subject_service import replace_user_subjects


class UserSubjectsView(APIView):
    """利用者が選んだ科目の取得と置き換え（書けるのは本人の分だけ）"""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSubjectSerializer(many=True)})
    def get(self, request):
        subjects = subject_service.get_user_selected_subjects(request.user, use_cache=True)
        return Response(UserSubjectSerializer(subjects, many=True).data)

    @extend_schema(request=UserSubjectSelectionSerializer,
                   responses={200: UserSubjectSerializer(many=True)})
    def put(self, request):
        serializer = UserSubjectSelectionSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        replace_user_subjects(user=request.user, subject_ids=serializer.validated_data['subject_ids'])
        subjects = subject_service.get_user_selected_subjects(request.user, use_cache=False)
        return Response(UserSubjectSerializer(subjects, many=True).data)


class AvailableSubjectsView(APIView):
    """利用者が選べる自組織の科目（名前の順・ページ分けなし。組織に属さない利用者は空）"""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: AvailableSubjectSerializer(many=True)})
    def get(self, request):
        subjects = available_subjects(request.user).order_by('name')
        return Response(AvailableSubjectSerializer(subjects, many=True).data)
