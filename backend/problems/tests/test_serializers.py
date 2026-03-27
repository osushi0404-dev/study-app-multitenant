"""
シリアライザーのテストコード
イシュー#026: クイズ機能バグ修正のためのテスト
"""
import pytest
from django.contrib.auth import get_user_model
from problems.models import Subject, Problem, Choice, QuizSession
from problems.serializers import (
    ProblemDisplaySerializer,
    QuizSessionSerializer,
    ProblemFieldConversionMixin
)
from accounts.models import Organization, OrganizationCategory

User = get_user_model()


@pytest.mark.django_db
class TestProblemDisplaySerializer:
    """ProblemDisplaySerializerのテスト"""

    @pytest.fixture
    def setup_data(self):
        """テストデータのセットアップ"""
        # 組織とユーザーの作成
        category = OrganizationCategory.objects.create(name="テスト", slug="test")
        org = Organization.objects.create(name="Test Org", slug="test-org", category=category)
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            user_id="testuser",
            organization=org
        )

        # 科目と問題の作成
        subject = Subject.objects.create(name="テスト科目", organization=org)
        problem = Problem.objects.create(
            subject=subject,
            created_by=user,
            question="テスト問題文",
            problem_type="single",
            difficulty=1,
            points=10
        )

        # 選択肢の作成
        Choice.objects.create(problem=problem, text="選択肢1", is_correct=True, order=1)
        Choice.objects.create(problem=problem, text="選択肢2", is_correct=False, order=2)

        return {"problem": problem, "user": user}

    def test_question_text_field_exists(self, setup_data):
        """question_textフィールドが存在することを確認（バグ修正）"""
        problem = setup_data["problem"]
        serializer = ProblemDisplaySerializer(problem)
        data = serializer.data

        assert "question_text" in data, "question_textフィールドが存在しません"
        assert data["question_text"] == "テスト問題文", "question_textの値が正しくありません"

    def test_difficulty_conversion(self, setup_data):
        """difficultyが文字列に変換されることを確認"""
        problem = setup_data["problem"]
        serializer = ProblemDisplaySerializer(problem)
        data = serializer.data

        assert data["difficulty"] == "easy", f"difficultyの変換が正しくありません: {data['difficulty']}"

    def test_problem_type_conversion(self, setup_data):
        """problem_typeが正しく変換されることを確認"""
        problem = setup_data["problem"]
        serializer = ProblemDisplaySerializer(problem)
        data = serializer.data

        assert data["problem_type"] == "single_choice", f"problem_typeの変換が正しくありません: {data['problem_type']}"

    def test_choices_included(self, setup_data):
        """選択肢が含まれることを確認"""
        problem = setup_data["problem"]
        serializer = ProblemDisplaySerializer(problem)
        data = serializer.data

        assert "choices" in data, "choicesフィールドが存在しません"
        assert len(data["choices"]) == 2, f"選択肢の数が正しくありません: {len(data['choices'])}"


@pytest.mark.django_db
class TestQuizSessionSerializer:
    """QuizSessionSerializerのテスト"""

    @pytest.fixture
    def setup_data(self):
        """テストデータのセットアップ"""
        category = OrganizationCategory.objects.create(name="テスト", slug="test")
        org = Organization.objects.create(name="Test Org", slug="test-org", category=category)
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            user_id="testuser",
            organization=org
        )

        subject = Subject.objects.create(name="テスト科目", organization=org)
        session = QuizSession.objects.create(
            user=user,
            subject=subject,
            total_problems=10,
            completed_problems=5,
            correct_answers=3
        )

        return {"session": session, "user": user}

    def test_answered_problems_field_exists(self, setup_data):
        """answered_problemsフィールドが存在することを確認（バグ修正）"""
        session = setup_data["session"]
        serializer = QuizSessionSerializer(session)
        data = serializer.data

        assert "answered_problems" in data, "answered_problemsフィールドが存在しません"
        assert data["answered_problems"] == 5, f"answered_problemsの値が正しくありません: {data['answered_problems']}"

    def test_completed_problems_field_exists(self, setup_data):
        """completed_problemsフィールドも存在することを確認（後方互換性）"""
        session = setup_data["session"]
        serializer = QuizSessionSerializer(session)
        data = serializer.data

        assert "completed_problems" in data, "completed_problemsフィールドが存在しません"

    def test_accuracy_calculation(self, setup_data):
        """正答率の計算が正しいことを確認"""
        session = setup_data["session"]
        serializer = QuizSessionSerializer(session)
        data = serializer.data

        expected_accuracy = round((3 / 5) * 100, 2)
        assert data["accuracy"] == expected_accuracy, f"正答率の計算が正しくありません: {data['accuracy']}"


@pytest.mark.django_db
class TestProblemFieldConversionMixin:
    """ProblemFieldConversionMixinのテスト（DRY原則の検証）"""

    def test_mixin_is_used_by_both_serializers(self):
        """MixinがProblemSerializerとProblemDisplaySerializerで使用されていることを確認"""
        from problems.serializers import ProblemSerializer, ProblemDisplaySerializer

        assert issubclass(ProblemSerializer, ProblemFieldConversionMixin), \
            "ProblemSerializerがProblemFieldConversionMixinを継承していません"
        assert issubclass(ProblemDisplaySerializer, ProblemFieldConversionMixin), \
            "ProblemDisplaySerializerがProblemFieldConversionMixinを継承していません"
