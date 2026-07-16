import json
import logging
from typing import Any, Dict, List

from rest_framework import serializers
from .models import Subject, Problem, Choice, QuizSession, QuizAnswer, MediaAsset, ProblemMediaAsset

logger = logging.getLogger(__name__)


class SubjectSerializer(serializers.ModelSerializer):
    problem_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subject
        fields = ['id', 'name', 'description', 'problem_count', 'created_at', 'updated_at']


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct', 'order']
        extra_kwargs = {
            'is_correct': {'write_only': True}
        }


class ChoiceDisplaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'order']


class MediaAssetSerializer(serializers.ModelSerializer):
    """画像アセットのシリアライザー"""
    url = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = [
            'id', 'url', 'usage_kind', 'original_filename',
            'mime_type', 'file_size_bytes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_url(self, obj):
        """画像URLを取得"""
        return obj.get_url()


class ProblemMediaAssetSerializer(serializers.ModelSerializer):
    """問題画像紐づけのシリアライザー"""
    asset = MediaAssetSerializer(read_only=True)

    class Meta:
        model = ProblemMediaAsset
        fields = ['id', 'asset', 'usage_kind', 'position']
        read_only_fields = ['id']


class ProblemFieldConversionMixin:
    """Problem型変換の共通ロジック（DRY原則）"""

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # difficulty を文字列に変換
        difficulty_map = {1: 'easy', 2: 'medium', 3: 'hard'}
        data['difficulty'] = difficulty_map.get(instance.difficulty, 'medium')

        # problem_type を変換
        type_map = {
            'single': 'single_choice',
            'multiple': 'multiple_choice',
            'text': 'text'
        }
        data['problem_type'] = type_map.get(instance.problem_type, instance.problem_type)

        return data


class ProblemSerializer(ProblemFieldConversionMixin, serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    question_text = serializers.CharField(source='question', required=False)  # フロントエンド用のフィールド名
    question_image = serializers.SerializerMethodField()
    explanation_image = serializers.SerializerMethodField()
    # 新方式: MediaAsset配列
    question_images = serializers.SerializerMethodField()
    explanation_images = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = [
            'id', 'subject', 'subject_name', 'question', 'question_text', 'problem_type',
            'difficulty', 'explanation', 'is_deleted',
            'is_ai_generated', 'choices', 'created_by', 'created_by_username',
            'created_at', 'updated_at',
            'question_image', 'explanation_image',  # 旧形式（後方互換性）
            'question_images', 'explanation_images'  # 新形式
        ]
        read_only_fields = ['created_by', 'is_ai_generated']

    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        フロントエンドからのデータを内部形式に変換

        Note:
            QueryDict→dict変換はMultipartFormDataMixinで実施済み
            本メソッドはビジネスロジック変換のみを担当
        """
        # dataをコピー（元データを変更しないため）
        data = dict(data)

        # question_text → question への変換
        if 'question_text' in data:
            data['question'] = data.pop('question_text')

        # difficulty の変換
        if 'difficulty' in data:
            difficulty_map = {'easy': 1, 'medium': 2, 'hard': 3}
            if isinstance(data['difficulty'], str):
                data['difficulty'] = difficulty_map.get(data['difficulty'], 2)

        # problem_type の変換
        if 'problem_type' in data:
            type_map = {
                'single_choice': 'single',
                'multiple_choice': 'multiple',
                'text': 'text'
            }
            data['problem_type'] = type_map.get(data['problem_type'], data['problem_type'])

        # choices が文字列のリストで送られてきた場合、JSONパースして辞書型に変換
        if 'choices' in data and isinstance(data['choices'], list):
            logger.debug(f"Processing {len(data['choices'])} choices for problem")
            parsed_choices: List[Dict[str, Any]] = []

            for idx, choice in enumerate(data['choices']):
                if isinstance(choice, str):
                    try:
                        parsed_choice = json.loads(choice)
                        parsed_choices.append(parsed_choice)
                        logger.debug(f"Successfully parsed choice {idx}: {parsed_choice.get('text', 'N/A')}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse choice {idx}: {e}")
                        parsed_choices.append(choice)
                else:
                    parsed_choices.append(choice)

            data['choices'] = parsed_choices

        return super().to_internal_value(data)

    def validate_choices(self, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        選択肢のバリデーション
        """
        if not value:
            raise serializers.ValidationError("選択肢は少なくとも1つ必要です")

        if len(value) > 10:
            raise serializers.ValidationError("選択肢は最大10個までです")

        # 正解が少なくとも1つ存在するか確認
        correct_count = sum(1 for choice in value if choice.get('is_correct'))
        if correct_count == 0:
            raise serializers.ValidationError("正解の選択肢を少なくとも1つ選択してください")

        # XSS対策: テキストの長さ制限と空白チェック
        for idx, choice in enumerate(value):
            choice_text = choice.get('text', '')
            if len(choice_text) > 500:
                raise serializers.ValidationError(
                    f"選択肢{idx + 1}のテキストが長すぎます（最大500文字）"
                )
            if not choice_text.strip():
                raise serializers.ValidationError(
                    f"選択肢{idx + 1}のテキストが空です"
                )

        logger.info(f"Validated {len(value)} choices, {correct_count} correct answer(s)")
        return value

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        problem = Problem.objects.create(**validated_data)

        for choice_data in choices_data:
            Choice.objects.create(problem=problem, **choice_data)

        return problem

    def update(self, instance, validated_data):
        choices_data = validated_data.pop('choices', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if choices_data is not None:
            instance.choices.all().delete()
            for choice_data in choices_data:
                Choice.objects.create(problem=instance, **choice_data)

        return instance

    def get_question_image(self, obj):
        """問題画像のURLを取得（旧形式、後方互換性のため保持）"""
        return obj.get_question_image_url()

    def get_explanation_image(self, obj):
        """解説画像のURLを取得（旧形式、後方互換性のため保持）"""
        return obj.get_explanation_image_url()

    def get_question_images(self, obj):
        """問題用画像の配列を取得（新方式）"""
        media_links = obj.get_media_assets(usage_kind='problem')
        return MediaAssetSerializer([link.asset for link in media_links], many=True).data

    def get_explanation_images(self, obj):
        """解説用画像の配列を取得（新方式）"""
        media_links = obj.get_media_assets(usage_kind='explanation')
        return MediaAssetSerializer([link.asset for link in media_links], many=True).data


class ChoiceAdminSerializer(serializers.ModelSerializer):
    """管理画面専用: is_correct を読み書き両可で露出する（I078）。

    ProblemViewSet（I102 で admin 限定）以外で使用しないこと。
    出題・結果・AI 応答は ChoiceSerializer / ChoiceDisplaySerializer（非露出）を維持する。
    ChoiceSerializer の fields を変更する場合は本クラスも合わせて更新すること
    （意図的な非継承＝既存クラス不変更方針のため）。
    """
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct', 'order']


class ProblemAdminSerializer(ProblemSerializer):
    """管理画面専用: choices のみ is_correct 露出版に差し替える（I078）"""
    choices = ChoiceAdminSerializer(many=True, required=False)


class ProblemDisplaySerializer(ProblemFieldConversionMixin, serializers.ModelSerializer):
    choices = ChoiceDisplaySerializer(many=True, read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    question_text = serializers.CharField(source='question', read_only=True)  # フロントエンド用のフィールド名
    question_image = serializers.SerializerMethodField()
    explanation_image = serializers.SerializerMethodField()
    # 新方式: MediaAsset配列
    question_images = serializers.SerializerMethodField()
    explanation_images = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = [
            'id', 'subject_name', 'question', 'question_text', 'problem_type',
            'difficulty', 'choices',
            'question_image', 'explanation_image',  # 旧形式（後方互換性）
            'question_images', 'explanation_images'  # 新形式
        ]

    def get_question_image(self, obj):
        """問題画像のURLを取得（旧形式、後方互換性のため保持）"""
        return obj.get_question_image_url()

    def get_explanation_image(self, obj):
        """解説画像のURLを取得（旧形式、後方互換性のため保持）"""
        return obj.get_explanation_image_url()

    def get_question_images(self, obj):
        """問題用画像の配列を取得（新方式）"""
        media_links = obj.get_media_assets(usage_kind='problem')
        return MediaAssetSerializer([link.asset for link in media_links], many=True).data

    def get_explanation_images(self, obj):
        """解説用画像の配列を取得（新方式）"""
        media_links = obj.get_media_assets(usage_kind='explanation')
        return MediaAssetSerializer([link.asset for link in media_links], many=True).data


class QuizAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAnswer
        fields = [
            'id', 'problem', 'selected_choices', 'text_answer',
            'is_correct', 'time_taken'
        ]
        read_only_fields = ['is_correct']


class QuizAnswerDetailSerializer(serializers.ModelSerializer):
    problem = ProblemSerializer(read_only=True)
    selected_choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = QuizAnswer
        fields = [
            'id', 'problem', 'selected_choices', 'text_answer',
            'is_correct', 'answered_at', 'time_taken'
        ]


class QuizSessionSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    # フロントエンド用のフィールド名（completed_problems のエイリアス）
    answered_problems = serializers.IntegerField(source='completed_problems', read_only=True)
    duration = serializers.SerializerMethodField()
    accuracy = serializers.SerializerMethodField()

    class Meta:
        model = QuizSession
        fields = [
            'id', 'subject', 'subject_name', 'total_problems',
            'completed_problems', 'answered_problems', 'correct_answers',
            'started_at', 'ended_at', 'is_active', 'duration', 'accuracy'
        ]
        read_only_fields = [
            'total_problems', 'completed_problems', 'correct_answers',
            'ended_at'
        ]

    def get_duration(self, obj):
        if obj.ended_at and obj.started_at:
            delta = obj.ended_at - obj.started_at
            return int(delta.total_seconds())
        return None

    def get_accuracy(self, obj):
        if obj.completed_problems > 0:
            return round((obj.correct_answers / obj.completed_problems) * 100, 2)
        return 0


class QuizSessionDetailSerializer(QuizSessionSerializer):
    answers = QuizAnswerDetailSerializer(many=True, read_only=True)

    class Meta(QuizSessionSerializer.Meta):
        fields = QuizSessionSerializer.Meta.fields + ['answers']


class SubmitAnswerSerializer(serializers.Serializer):
    problem_id = serializers.IntegerField()
    selected_choice_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
    text_answer = serializers.CharField(required=False, allow_blank=True)
    time_taken = serializers.IntegerField(min_value=0, default=0)
