from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
from .models import SpacedRepetitionCard, SpacedRepetitionReview, LearningAnalytics
from .serializers import (
    SpacedRepetitionCardSerializer, SpacedRepetitionReviewSerializer,
    SpacedRepetitionSubmissionSerializer, LearningAnalyticsSerializer,
    DailyStudyPlanSerializer, LearningInsightsSerializer, UserStatisticsSerializer,
    ReviewSummaryQuerySerializer, ReviewSummarySerializer,
)
from core.exceptions import create_error_response
from .services import SpacedRepetitionService
from problems.services.tenant_scope import available_problems


class SpacedRepetitionViewSet(viewsets.ViewSet):
    """間隔反復学習システムのAPIエンドポイント"""
    permission_classes = [permissions.IsAuthenticated]

    def get_service(self):
        """ユーザー用のSpacedRepetitionServiceインスタンスを取得"""
        return SpacedRepetitionService(self.request.user)

    @action(detail=False, methods=['get'])
    def due_cards(self, request):
        """復習が必要なカードを取得"""
        service = self.get_service()
        limit = int(request.query_params.get('limit', 20))

        due_cards = service.get_due_cards(limit=limit)
        serializer = SpacedRepetitionCardSerializer(due_cards, many=True)

        return Response({
            'cards': serializer.data,
            'count': len(due_cards),
            'has_more': len(due_cards) == limit
        })

    @action(detail=False, methods=['get'])
    def review_summary(self, request):
        """今日の復習の件数と次の復習日（科目の指定は自組織で選べる科目だけ）"""
        query = ReviewSummaryQuerySerializer(
            data=request.query_params, context={'request': request})
        if not query.is_valid():
            # 数字でない・他組織・全体共有・存在しない科目は同じ 400（違いを見せない）
            return create_error_response(
                '科目の指定が正しくありません',
                'ダッシュボードの科目の選択からやり直してください',
                status.HTTP_400_BAD_REQUEST,
            )

        summary = self.get_service().review_summary(query.validated_data.get('subject_id'))
        return Response(ReviewSummarySerializer(summary).data)

    @action(detail=False, methods=['get'])
    def daily_plan(self, request):
        """1日の学習プランを取得"""
        service = self.get_service()
        available_time = int(request.query_params.get('available_time_minutes', 30))

        plan = service.get_daily_study_plan(available_time_minutes=available_time)
        serializer = DailyStudyPlanSerializer(plan)

        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def submit_review(self, request):
        """復習結果を提出"""
        service = self.get_service()
        serializer = SpacedRepetitionSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            # カードを取得（他組織の問題のカードは存在しないカードと同じ扱い）
            card = SpacedRepetitionCard.objects.for_user(request.user).get(id=data['card_id'])

            # 復習を記録
            review = service.review_card(
                card=card,
                quality_score=data['quality_score'],
                response_time_seconds=data['response_time_seconds'],
                hint_used=data['hint_used'],
            )

            # 学習分析データを更新
            service.update_daily_analytics()

            review_serializer = SpacedRepetitionReviewSerializer(review)
            card_serializer = SpacedRepetitionCardSerializer(card)

            return Response({
                'review': review_serializer.data,
                'updated_card': card_serializer.data,
                'message': '復習を記録しました'
            }, status=status.HTTP_201_CREATED)

        except SpacedRepetitionCard.DoesNotExist:
            return Response(
                {'error': 'カードが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'復習の記録に失敗しました: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def create_card(self, request):
        """新しい問題用のカードを作成"""
        service = self.get_service()
        problem_id = request.data.get('problem_id')

        if not problem_id:
            return Response(
                {'error': 'problem_idが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from problems.models import Problem
            # 他組織・削除済み・全体共有科目の問題は、存在しない問題と同じ 404
            problem = available_problems(request.user).get(id=problem_id)

            # カードを作成
            card = service.create_card_for_problem(problem)
            serializer = SpacedRepetitionCardSerializer(card)

            return Response({
                'card': serializer.data,
                'message': 'カードを作成しました'
            }, status=status.HTTP_201_CREATED)

        except Problem.DoesNotExist:
            return Response(
                {'error': '問題が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def user_statistics(self, request):
        """ユーザーの学習統計を取得"""
        service = self.get_service()
        stats = service.get_user_statistics()
        serializer = UserStatisticsSerializer(stats)

        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def learning_insights(self, request):
        """学習洞察を取得"""
        service = self.get_service()
        days = int(request.query_params.get('days', 7))

        insights = service.get_learning_insights(days=days)
        serializer = LearningInsightsSerializer(insights)

        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """学習分析データを取得"""
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days-1)

        analytics = LearningAnalytics.objects.filter(
            user=request.user,
            date__range=[start_date, end_date]
        ).order_by('date')

        serializer = LearningAnalyticsSerializer(analytics, many=True)

        return Response({
            'analytics': serializer.data,
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': days
            }
        })

    @action(detail=False, methods=['post'])
    def update_analytics(self, request):
        """学習分析データを手動更新"""
        service = self.get_service()
        target_date_str = request.data.get('date')

        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': '日付の形式が正しくありません (YYYY-MM-DD)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = None

        analytics = service.update_daily_analytics(target_date=target_date)
        serializer = LearningAnalyticsSerializer(analytics)

        return Response({
            'analytics': serializer.data,
            'message': '分析データを更新しました'
        })


class SpacedRepetitionCardViewSet(viewsets.ReadOnlyModelViewSet):
    """間隔反復学習カードの読み取り専用ビューセット"""
    serializer_class = SpacedRepetitionCardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = SpacedRepetitionCard.objects.for_user(self.request.user).select_related(
            'problem', 'problem__subject')

        # フィルタリングオプション
        is_due = self.request.query_params.get('is_due')
        mastery_level = self.request.query_params.get('mastery_level')
        subject_id = self.request.query_params.get('subject_id')

        if is_due == 'true':
            queryset = queryset.filter(
                next_review_date__lte=timezone.now(),
                is_active=True
            )

        if mastery_level:
            # カスタムフィルタリングが必要な場合
            cards = [card for card in queryset if card.mastery_level == mastery_level]
            return cards

        if subject_id:
            queryset = queryset.filter(problem__subject_id=subject_id)

        return queryset.order_by('next_review_date', '-ease_factor')


class SpacedRepetitionReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """間隔反復学習復習記録の読み取り専用ビューセット"""
    serializer_class = SpacedRepetitionReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = SpacedRepetitionReview.objects.for_user(self.request.user).select_related(
            'card', 'problem', 'problem__subject')

        # フィルタリングオプション
        card_id = self.request.query_params.get('card_id')
        days = self.request.query_params.get('days')

        if card_id:
            queryset = queryset.filter(card_id=card_id)

        if days:
            try:
                days_int = int(days)
                start_date = timezone.now() - timedelta(days=days_int)
                queryset = queryset.filter(reviewed_at__gte=start_date)
            except ValueError:
                pass

        return queryset.order_by('-reviewed_at')
