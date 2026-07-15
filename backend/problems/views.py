from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.core.exceptions import ValidationError
import json
import uuid
import hashlib
from .models import Subject, Problem, Choice, QuizSession, QuizAnswer, MediaAsset, ProblemMediaAsset
from .serializers import (
    SubjectSerializer, ProblemSerializer, ProblemDisplaySerializer,
    QuizSessionSerializer, QuizSessionDetailSerializer,
    SubmitAnswerSerializer, MediaAssetSerializer
)
from .services import QuizService
from core.cache_service import cache_service
from core.subject_service import subject_service
from core.storage_service import StorageService
from common.mixins import MultipartFormDataMixin


class IsOrgAdmin(permissions.BasePermission):
    """組織管理者（role='admin'）のみを許可するパーミッション"""
    message = '管理者権限が必要です'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )


class SubjectViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 統一サービスを使用して組織フィルタリング付きで取得
        return subject_service.get_user_subjects(
            self.request.user,
            use_cache=True,
            annotate_count=True
        )

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny], url_path='public')
    def public(self, request):
        """
        組織slug指定で科目を取得（未認証アクセス対応）
        新規登録画面用エンドポイント

        Query Parameters:
            slug: 組織slug（'personal'で個人用）

        Returns:
            科目リスト [{'id': int, 'name': str, 'description': str}]
        """
        from accounts.models import Organization

        organization_slug = request.query_params.get('slug', 'personal')

        # 'register'を'personal'に変換（レガシー対応）
        if organization_slug == 'register':
            organization_slug = 'personal'

        # 組織を取得
        organization = Organization.objects.filter(
            slug=organization_slug,
            is_active=True
        ).first()

        if not organization:
            return Response([], status=status.HTTP_200_OK)

        # 組織の科目を取得（キャッシュなし、未認証のため）
        subjects = Subject.objects.filter(
            organization=organization
        ).order_by('name').values('id', 'name', 'description')

        return Response(list(subjects))

    def get_permissions(self):
        """create は org admin のみ許可（update/destroy は別イシュー）"""
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsOrgAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        import os
        import uuid as _uuid
        from django.conf import settings
        from django.db import transaction
        from django.utils.text import slugify

        name = serializer.validated_data.get('name', '')
        slug = slugify(name)
        if not slug:
            slug = f"s-{str(_uuid.uuid4())[:8]}"

        org_id = self.request.user.organization_id
        base_slug, counter = slug, 2
        while Subject.objects.filter(slug=slug, organization_id=org_id).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        from django.db import IntegrityError
        from rest_framework.exceptions import ValidationError as DRFValidationError

        try:
            with transaction.atomic():
                subject = serializer.save(organization_id=org_id, slug=slug)
                subject_service.invalidate_cache(org_id)

                org_slug = subject.organization.slug
                base = os.path.join(
                    settings.MEDIA_ROOT, 'org', org_slug, 'subjects', slug
                )
                for folder in ('problem', 'explanation'):
                    path = os.path.join(base, folder)
                    os.makedirs(path, exist_ok=True)
                    gitkeep = os.path.join(path, '.gitkeep')
                    if not os.path.exists(gitkeep):
                        open(gitkeep, 'w').close()
        except IntegrityError:
            raise DRFValidationError({'name': ['同名の科目が既に存在します']})

    def perform_update(self, serializer):
        serializer.save()
        # 科目更新時にキャッシュを無効化
        subject_service.invalidate_cache(self.request.user.organization_id)

    def perform_destroy(self, instance):
        instance.delete()
        # 科目削除時にキャッシュを無効化
        subject_service.invalidate_cache(self.request.user.organization_id)


class ProblemViewSet(MultipartFormDataMixin, viewsets.ModelViewSet):
    """
    問題管理API（イシュー#031対応: 画像アップロード機能追加）

    Notes:
        - ページネーション: 無効（フロントエンドでクライアントサイドページネーション実装）
        - キャッシュ: user_idベースで分離（全データをキャッシュ）
        - 画像アップロード: multipart/form-data対応（問題登録時）
        - QueryDict変換: MultipartFormDataMixinで自動処理
    """
    serializer_class = ProblemSerializer
    # I102: 問題管理は組織管理者（role=='admin'）限定。参照・更新系・AI生成・画像の
    # 全アクションに一律適用（custom action に permission override は無い）。
    permission_classes = [permissions.IsAuthenticated, IsOrgAdmin]
    pagination_class = None  # ページネーション無効化
    parser_classes = [MultiPartParser, FormParser]  # 画像アップロード対応

    # multipart/form-dataでリストとして受け取るフィールド
    multipart_list_fields = ['choices']

    def get_queryset(self):
        # ユーザーの組織に紐づく科目の問題のみ取得
        queryset = Problem.objects.filter(
            is_deleted=False,
            subject__organization=self.request.user.organization
        )

        # クエリパラメータによるフィルタリング
        subject_id = self.request.query_params.get('subject')
        difficulty = self.request.query_params.get('difficulty')

        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if difficulty:
            # フロントエンドから送られる文字列('easy', 'medium', 'hard')を数値に変換
            difficulty_map = {'easy': 1, 'medium': 2, 'hard': 3}
            difficulty_value = difficulty_map.get(difficulty)
            if difficulty_value:
                queryset = queryset.filter(difficulty=difficulty_value)

        return queryset.select_related('subject', 'created_by').prefetch_related('choices')

    def list(self, request, *args, **kwargs):
        """
        問題一覧取得（全データ返却）

        Returns:
            配列形式: [{"id": 1, ...}, {"id": 2, ...}, ...]

        Future Improvement:
            データ量が増加した場合（500件以上）は、カーソルページネーションへの
            移行を検討。その際はフロントエンドも合わせて改修が必要。
        """
        import logging
        from django.utils import timezone

        logger = logging.getLogger(__name__)
        start_time = timezone.now()

        subject_id = request.query_params.get('subject')
        difficulty = request.query_params.get('difficulty')

        # キャッシュから問題一覧を取得を試みる
        cached_problems = cache_service.get_problems_cache(
            subject_id=int(subject_id) if subject_id else None,
            difficulty=difficulty,
            user_id=request.user.id
        )

        if cached_problems is not None:
            return Response(cached_problems)

        # ページネーションを無効化して全データを取得
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        response_data = serializer.data

        # 全データをキャッシュに保存
        cache_service.set_problems_cache(
            response_data,
            subject_id=int(subject_id) if subject_id else None,
            difficulty=difficulty,
            user_id=request.user.id
        )

        # パフォーマンス監視
        elapsed = (timezone.now() - start_time).total_seconds()
        if elapsed > 2.0:
            logger.warning(
                f"Slow API response: /api/problems/ took {elapsed:.2f}s "
                f"(subject_id={subject_id}, count={len(response_data)})"
            )

        return Response(response_data)

    def perform_create(self, serializer):
        """
        問題作成（イシュー#031対応: 画像アップロード機能統合）

        処理フロー:
            1. バリデーション済みデータの取得
            2. 画像ファイルの取得（問題用・解説用）
            3. ProblemServiceによる一括作成（トランザクション管理）
            4. キャッシュ無効化
        """
        from problems.services import ProblemService

        # バリデーション済みデータ
        validated_data = serializer.validated_data

        # I103: 越境 subject への作成を拒否（テナント境界）。
        # subject は Problem.subject=NOT NULL・serializer required のため create 時は必ず存在。
        subject = validated_data['subject']
        if subject.organization_id != self.request.user.organization_id:
            raise PermissionDenied('他組織の科目には問題を作成できません')

        # 画像ファイルの取得（multipart/form-data）
        question_images = []
        explanation_images = []

        # 問題用画像（最大5枚）
        for i in range(1, 6):
            image_key = f'question_image_{i}'
            if image_key in self.request.FILES:
                question_images.append(self.request.FILES[image_key])

        # 解説用画像（最大5枚）
        for i in range(1, 6):
            image_key = f'explanation_image_{i}'
            if image_key in self.request.FILES:
                explanation_images.append(self.request.FILES[image_key])

        # ProblemServiceを使用して問題・画像を一括作成
        instance = ProblemService.create_problem_with_images(
            validated_data=validated_data,
            question_images=question_images if question_images else None,
            explanation_images=explanation_images if explanation_images else None,
            created_by_user=self.request.user
        )

        # 問題作成時に関連キャッシュを無効化
        cache_service.invalidate_problems_cache(instance.subject.id)

        # シリアライザーにインスタンスを設定（レスポンス用）
        serializer.instance = instance

    def perform_update(self, serializer):
        """
        問題更新（イシュー#073対応: 画像差分の一括更新）

        処理フロー:
            1. SEC-1: subject の他組織付け替えを拒否
            2. 新規ファイル・order 配列の取り出し（multipart）
            3. ProblemService による差分更新（追加・削除・並び替え・トランザクション）
            4. キャッシュ無効化
        """
        from rest_framework.exceptions import ValidationError as DRFValidationError
        from problems.services import ProblemService

        instance = serializer.instance
        validated_data = serializer.validated_data
        request = self.request

        # 1. SEC-1: subject の他組織付け替えを拒否（越境データ注入・越境ファイル書き込み防止）
        new_subject = validated_data.get('subject')
        if new_subject and new_subject.organization_id != request.user.organization_id:
            raise DRFValidationError({'subject': ['他組織の科目には変更できません']})

        # 2. 新規ファイル収集（question_image_* / explanation_image_*）
        question_files = {
            key: request.FILES[key]
            for key in request.FILES
            if key.startswith('question_image_')
        }
        explanation_files = {
            key: request.FILES[key]
            for key in request.FILES
            if key.startswith('explanation_image_')
        }

        # order 配列のパース（フィールド非送信は None＝当該種別無変更）
        def parse_order(field):
            raw = request.data.get(field)
            if raw is None:
                return None
            if isinstance(raw, list):
                return raw
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raise DRFValidationError({field: ['不正なJSON形式です']})
            if not isinstance(parsed, list):
                raise DRFValidationError({field: ['画像の順序指定はJSON配列で指定してください']})
            return parsed

        question_order = parse_order('question_images_order')
        explanation_order = parse_order('explanation_images_order')

        # 3. 差分更新（トランザクション管理）
        instance = ProblemService.update_problem_with_images(
            problem=instance,
            validated_data=validated_data,
            question_files=question_files,
            explanation_files=explanation_files,
            question_order=question_order,
            explanation_order=explanation_order,
        )

        # 4. 問題更新時に関連キャッシュを無効化
        cache_service.invalidate_problems_cache(instance.subject.id)
        serializer.instance = instance

    def perform_destroy(self, instance):
        from problems.services import ProblemService
        subject_id = instance.subject.id
        # 問題削除（論理削除 + 実ファイル即時物理削除）
        ProblemService.delete_problem(instance)
        # 問題削除時に関連キャッシュを無効化
        cache_service.invalidate_problems_cache(subject_id)

    @action(detail=False, methods=['post'])
    def generate_ai(self, request):
        """AI問題生成エンドポイント"""
        from .ai_generator import AIQuestionGenerator
        from core.monitoring import UserActivityMonitor

        subject_id = request.data.get('subject_id')
        difficulty = request.data.get('difficulty', 'medium')
        problem_type = request.data.get('problem_type', 'multiple_choice')
        count = request.data.get('count', 1)
        topic = request.data.get('topic')
        save_to_db = request.data.get('save_to_db', True)

        if not subject_id:
            return Response({
                'error': '科目IDが必要です'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 科目の取得
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({
                'error': '指定された科目が見つかりません'
            }, status=status.HTTP_404_NOT_FOUND)

        # I103: 越境 subject への作成を拒否（save_to_db に関わらず生成前に停止）
        if subject.organization_id != request.user.organization_id:
            return Response({
                'error': '他組織の科目には問題を作成できません'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            # AI生成器の初期化
            generator = AIQuestionGenerator()

            # ユーザーアクティビティログ
            UserActivityMonitor.log_user_activity(
                user=request.user,
                activity_type='ai_generate_problems',
                details={
                    'subject_id': subject_id,
                    'difficulty': difficulty,
                    'count': count
                }
            )

            if count == 1:
                # 単一問題生成
                problem_data = generator.generate_problem(
                    subject=subject,
                    difficulty=difficulty,
                    problem_type=problem_type,
                    topic=topic
                )

                if save_to_db:
                    problem = self._save_ai_problem_to_db(problem_data, request.user)
                    cache_service.invalidate_problems_cache(subject.id)
                    return Response({
                        'success': True,
                        'problem': ProblemSerializer(problem).data
                    })
                else:
                    return Response({
                        'success': True,
                        'problem_data': problem_data
                    })

            else:
                # 複数問題生成
                problems_data = generator.generate_batch_problems(
                    subject=subject,
                    count=count
                )

                if save_to_db:
                    saved_problems = []
                    for problem_data in problems_data:
                        problem = self._save_ai_problem_to_db(problem_data, request.user)
                        saved_problems.append(problem)

                    cache_service.invalidate_problems_cache(subject.id)
                    return Response({
                        'success': True,
                        'problems': ProblemSerializer(saved_problems, many=True).data,
                        'count': len(saved_problems)
                    })
                else:
                    return Response({
                        'success': True,
                        'problems_data': problems_data,
                        'count': len(problems_data)
                    })

        except Exception as e:
            return Response({
                'error': f'AI問題生成に失敗しました: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _save_ai_problem_to_db(self, problem_data, user):
        """生成された問題をデータベースに保存"""

        # Problemインスタンスの作成
        problem = Problem(
            title=problem_data['title'],
            description=problem_data['description'],
            problem_type=problem_data['problem_type'],
            difficulty=problem_data['difficulty'],
            subject=problem_data['subject'],
            estimated_time_minutes=problem_data.get('estimated_time_minutes', 5),
            explanation=problem_data.get('explanation', ''),
            created_by=user,
            created_at=timezone.now(),
            updated_at=timezone.now()
        )

        problem.save()

        # 問題形式別の追加データ（選択肢）
        if problem_data['problem_type'] == 'multiple_choice' and 'choices' in problem_data:
            choices_data = problem_data.get('choices', [])
            correct_answer = problem_data.get('correct_answer', '')

            for i, choice_text in enumerate(choices_data):
                choice = Choice(
                    problem=problem,
                    text=choice_text,
                    is_correct=(choice_text == correct_answer),
                    order=i
                )
                choice.save()

        return problem

    @action(detail=False, methods=['post'])
    def generate_adaptive(self, request):
        """適応的問題生成エンドポイント"""
        from .ai_generator import AIQuestionGenerator
        from core.monitoring import UserActivityMonitor

        subject_id = request.data.get('subject_id')

        if not subject_id:
            return Response({
                'error': '科目IDが必要です'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({
                'error': '指定された科目が見つかりません'
            }, status=status.HTTP_404_NOT_FOUND)

        # I103: 越境 subject への作成を拒否（テナント境界）
        if subject.organization_id != request.user.organization_id:
            return Response({
                'error': '他組織の科目には問題を作成できません'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            # ユーザーの最近のパフォーマンス分析
            recent_performance = self._analyze_user_performance(request.user, subject)

            # AI生成器による適応的問題生成
            generator = AIQuestionGenerator()
            problem_data = generator.generate_adaptive_problem(
                user=request.user,
                subject=subject,
                recent_performance=recent_performance
            )

            # データベースに保存
            problem = self._save_ai_problem_to_db(problem_data, request.user)
            cache_service.invalidate_problems_cache(subject.id)

            # ユーザーアクティビティログ
            UserActivityMonitor.log_user_activity(
                user=request.user,
                activity_type='adaptive_problem_generation',
                details={
                    'subject_id': subject_id,
                    'problem_id': problem.id,
                    'performance_data': recent_performance
                }
            )

            return Response({
                'success': True,
                'problem': ProblemSerializer(problem).data,
                'adaptation_info': {
                    'user_accuracy': recent_performance.get('accuracy', 0),
                    'difficulty_selected': problem_data['difficulty'],
                    'weak_areas_targeted': recent_performance.get('weak_topics', [])
                }
            })

        except Exception as e:
            return Response({
                'error': f'適応的問題生成に失敗しました: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _analyze_user_performance(self, user, subject):
        """ユーザーの最近のパフォーマンスを分析"""
        from django.db.models import Avg, Count
        from datetime import timedelta

        # 過去30日間のデータを分析
        recent_date = timezone.now() - timedelta(days=30)

        # 科目別の回答履歴
        recent_answers = QuizAnswer.objects.filter(
            session__user=user,
            problem__subject=subject,
            created_at__gte=recent_date
        )

        if not recent_answers.exists():
            return {
                'accuracy': 0.7,  # デフォルト値
                'weak_topics': [],
                'total_attempts': 0
            }

        # 正答率の計算
        accuracy = recent_answers.aggregate(
            accuracy=Avg('is_correct')
        )['accuracy'] or 0

        # 弱点トピックの分析（正答率が低い問題のキーワード）
        weak_problems = recent_answers.filter(is_correct=False)
        weak_topics = []

        # 簡易的な弱点分析（実際にはより詳細な分析が必要）
        weak_difficulties = weak_problems.values('problem__difficulty').annotate(
            count=Count('id')
        ).order_by('-count')

        for item in weak_difficulties[:3]:
            weak_topics.append(item['problem__difficulty'])

        return {
            'accuracy': float(accuracy),
            'weak_topics': weak_topics,
            'total_attempts': recent_answers.count(),
            'recent_performance': recent_answers.count()
        }

    @action(
        detail=True,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
        url_path='images/upload'
    )
    def upload_image(self, request, pk=None):
        """
        画像アップロードエンドポイント (Phase 1)

        POST /api/problems/{problem_id}/images/upload/

        Request (multipart/form-data):
            - file: 画像ファイル (必須)
            - usage_kind: 'problem' | 'explanation' (必須)

        Response:
            - MediaAsset情報
        """
        problem = self.get_object()

        # 権限チェック: 自分の組織の問題のみ
        if problem.organization_id != request.user.organization_id:
            return Response(
                {'error': '権限がありません'},
                status=status.HTTP_403_FORBIDDEN
            )

        # リクエストデータの検証
        file_data = request.FILES.get('file')
        usage_kind = request.data.get('usage_kind')

        if not file_data:
            return Response(
                {'error': 'ファイルが必要です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if usage_kind not in ['problem', 'explanation']:
            return Response(
                {'error': 'usage_kindは "problem" または "explanation" を指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # ファイルバリデーション
            StorageService.validate_file(file_data)

            # アセットID生成
            asset_id = uuid.uuid4()

            # ファイル拡張子取得
            original_filename = file_data.name
            extension = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else 'png'

            # ストレージキー生成
            storage_key = StorageService.generate_storage_key(
                org_slug=problem.organization.slug,
                subject_slug=problem.subject.slug,
                usage_kind=usage_kind,
                asset_id=asset_id,
                extension=extension
            )

            # ファイル保存
            StorageService.save_file(storage_key, file_data)

            # SHA256チェックサム計算
            file_data.seek(0)
            checksum = hashlib.sha256(file_data.read()).hexdigest()

            # MediaAsset作成
            media_asset = MediaAsset.objects.create(
                id=asset_id,
                organization_id=problem.organization_id,
                subject=problem.subject,
                usage_kind=usage_kind,
                storage_key=storage_key,
                original_filename=original_filename,
                mime_type=file_data.content_type,
                file_size_bytes=file_data.size,
                checksum_sha256=checksum
            )

            # 既存の紐づけを取得して次のpositionを決定
            existing_links = ProblemMediaAsset.objects.filter(
                problem=problem,
                usage_kind=usage_kind
            ).order_by('-position')

            next_position = 1
            if existing_links.exists():
                next_position = existing_links.first().position + 1

            # ProblemMediaAsset作成（問題と画像の紐づけ）
            ProblemMediaAsset.objects.create(
                problem=problem,
                asset=media_asset,
                usage_kind=usage_kind,
                position=next_position,
                organization_id=problem.organization_id
            )

            # キャッシュ無効化
            cache_service.invalidate_problems_cache(problem.subject_id)

            return Response(
                MediaAssetSerializer(media_asset).data,
                status=status.HTTP_201_CREATED
            )

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'画像アップロードに失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=True,
        methods=['delete'],
        url_path='images/delete/(?P<asset_id>[^/.]+)'
    )
    def delete_image(self, request, pk=None, asset_id=None):
        """
        画像削除エンドポイント (Phase 1)

        DELETE /api/problems/{problem_id}/images/delete/{asset_id}/

        Response:
            - 成功メッセージ
        """
        problem = self.get_object()

        # 権限チェック
        if problem.organization_id != request.user.organization_id:
            return Response(
                {'error': '権限がありません'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # MediaAsset取得
            media_asset = MediaAsset.objects.get(
                id=asset_id,
                organization_id=request.user.organization_id
            )

            # ProblemMediaAsset削除（紐づけ解除）
            problem_link = ProblemMediaAsset.objects.filter(
                problem=problem,
                asset=media_asset
            ).first()

            if not problem_link:
                return Response(
                    {'error': 'この問題に紐づけられていない画像です'},
                    status=status.HTTP_404_NOT_FOUND
                )

            problem_link.delete()

            # 他の問題でも使用されていない場合は、MediaAssetも論理削除
            other_links = ProblemMediaAsset.objects.filter(asset=media_asset).exists()
            if not other_links:
                media_asset.is_deleted = True
                media_asset.save()

                # 物理ファイルも削除
                StorageService.delete_file(media_asset.storage_key)

            # キャッシュ無効化
            cache_service.invalidate_problems_cache(problem.subject_id)

            return Response(
                {'message': '画像を削除しました'},
                status=status.HTTP_200_OK
            )

        except MediaAsset.DoesNotExist:
            return Response(
                {'error': '画像が見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'画像削除に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QuizSessionViewSet(viewsets.ModelViewSet):
    serializer_class = QuizSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return QuizSession.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return QuizSessionDetailSerializer
        return QuizSessionSerializer

    def create(self, request):
        # End any active sessions first
        QuizSession.objects.filter(
            user=request.user,
            is_active=True
        ).update(is_active=False, ended_at=timezone.now())

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = serializer.save(user=request.user)

        # Get total problem count for the subject (no limit)
        problems_queryset = Problem.objects.filter(is_deleted=False)
        if session.subject:
            problems_queryset = problems_queryset.filter(subject=session.subject)

        # Set total_problems to the actual count in the subject
        # 無制限クイズのため、problem_countパラメータは無視
        session.total_problems = problems_queryset.count()
        session.save()

        return Response(
            QuizSessionSerializer(session).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def next_problem(self, request, pk=None):
        """次の問題を取得"""
        session = self.get_object()

        if not session.is_active:
            return Response(
                {'error': 'Session is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # サービス層を使用してビジネスロジックを実行
        next_problem, is_review_mode, total_problems_in_subject = QuizService.get_next_problem(session)

        if not next_problem:
            return Response(
                {'error': 'No problems available in this subject'},
                status=status.HTTP_404_NOT_FOUND
            )

        # レスポンス作成
        serializer = ProblemDisplaySerializer(next_problem)
        response_data = serializer.data
        response_data['total_problems_in_subject'] = total_problems_in_subject
        response_data['is_review_mode'] = is_review_mode

        return Response(response_data)

    @action(detail=True, methods=['post'])
    def submit_answer(self, request, pk=None):
        session = self.get_object()

        if not session.is_active:
            return Response(
                {'error': 'Session is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SubmitAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        problem_id = serializer.validated_data['problem_id']
        selected_choice_ids = serializer.validated_data.get('selected_choice_ids', [])
        text_answer = serializer.validated_data.get('text_answer', '')
        time_taken = serializer.validated_data.get('time_taken', 0)

        try:
            problem = Problem.objects.get(id=problem_id, is_deleted=False)
        except Problem.DoesNotExist:
            return Response(
                {'error': 'Problem not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if already answered
        if session.answers.filter(problem=problem).exists():
            return Response(
                {'error': 'Problem already answered'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create answer
        answer = QuizAnswer.objects.create(
            session=session,
            problem=problem,
            text_answer=text_answer,
            time_taken=time_taken
        )

        # Add selected choices
        if selected_choice_ids:
            choices = Choice.objects.filter(id__in=selected_choice_ids, problem=problem)
            answer.selected_choices.set(choices)

        # Check if answer is correct
        is_correct = False
        if problem.problem_type == 'text':
            # For text answers, this would need more sophisticated checking
            # For now, just mark as needs review
            is_correct = False
        else:
            correct_choices = set(problem.choices.filter(is_correct=True).values_list('id', flat=True))
            selected_choices = set(selected_choice_ids)
            is_correct = correct_choices == selected_choices

        answer.is_correct = is_correct
        answer.save()

        # Update session statistics
        session.completed_problems += 1
        if is_correct:
            session.correct_answers += 1

        # 無制限クイズのため、セッション完了チェックを削除
        # ユーザーが中断するまで問題を出し続ける
        session.save()

        # Return result with explanation and updated session
        return Response({
            'is_correct': is_correct,
            'explanation': problem.explanation,
            'explanation_image': problem.explanation_image.url if problem.explanation_image else None,
            'correct_choices': list(problem.choices.filter(is_correct=True).values('id', 'text')),
            'session_complete': not session.is_active,
            'session': QuizSessionSerializer(session).data,  # 追加: 更新されたセッション情報
            'session_stats': {  # 後方互換性のため残す
                'completed': session.completed_problems,
                'total': session.total_problems,
                'correct': session.correct_answers
            }
        })

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        session = self.get_object()

        if not session.is_active:
            return Response(
                {'error': 'Session is already ended'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.is_active = False
        session.ended_at = timezone.now()
        session.save()

        serializer = QuizSessionDetailSerializer(session)
        return Response(serializer.data)
