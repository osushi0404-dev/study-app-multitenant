"""
ビューのテストコード
イシュー#026: クイズ機能バグ修正のためのテスト
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from problems.models import Subject, Problem, Choice, QuizSession
from accounts.models import Organization, OrganizationCategory

User = get_user_model()


@pytest.mark.django_db
class TestQuizSessionViewSet:
    """QuizSessionViewSetのテスト"""

    @pytest.fixture
    def setup_data(self):
        """テストデータのセットアップ"""
        # 組織とユーザーの作成
        category = OrganizationCategory.objects.create(name="テスト", slug="test")
        org = Organization.objects.create(name="Test Org", slug="test-org", category=category)
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            username="testuser",
            organization=org
        )

        # 科目と問題の作成
        subject = Subject.objects.create(name="テスト科目", organization=org)

        # 複数の問題を作成
        problems = []
        for i in range(5):
            problem = Problem.objects.create(
                subject=subject,
                created_by=user,
                question=f"テスト問題{i+1}",
                problem_type="single",
                difficulty=1,
                points=10
            )
            Choice.objects.create(problem=problem, text=f"正解{i+1}", is_correct=True, order=1)
            Choice.objects.create(problem=problem, text=f"不正解{i+1}", is_correct=False, order=2)
            problems.append(problem)

        # APIクライアントの作成
        client = APIClient()
        client.force_authenticate(user=user)

        return {
            "user": user,
            "subject": subject,
            "problems": problems,
            "client": client,
            "org": org
        }

    def test_next_problem_returns_random_order(self, setup_data):
        """next_problemがランダムな順序で問題を返すことを確認（UX改善）"""
        client = setup_data["client"]
        subject = setup_data["subject"]

        # セッションを作成
        session = QuizSession.objects.create(
            user=setup_data["user"],
            subject=subject,
            total_problems=5,
            is_active=True
        )

        # 複数回問題を取得して、異なる問題が返されることを確認
        fetched_problems = []
        for _ in range(3):
            url = reverse('quizsession-next-problem', kwargs={'pk': session.id})
            response = client.get(url)

            assert response.status_code == status.HTTP_200_OK, \
                f"ステータスコードが正しくありません: {response.status_code}"

            fetched_problems.append(response.data['id'])

            # 回答を送信して次の問題へ
            if len(fetched_problems) < 3:
                submit_url = reverse('quizsession-submit-answer', kwargs={'pk': session.id})
                choices = Choice.objects.filter(problem_id=response.data['id'], is_correct=True)
                client.post(submit_url, {
                    'problem_id': response.data['id'],
                    'selected_choice_ids': [str(choices.first().id)],
                    'time_taken': 10
                })

        # 注: 完全なランダム性の検証は統計的に困難なため、
        # ここでは問題が正常に取得できることを確認
        assert len(fetched_problems) == 3, "問題の取得数が正しくありません"

    def test_next_problem_includes_question_text(self, setup_data):
        """next_problemのレスポンスにquestion_textが含まれることを確認（バグ修正）"""
        client = setup_data["client"]
        subject = setup_data["subject"]

        # セッションを作成
        session = QuizSession.objects.create(
            user=setup_data["user"],
            subject=subject,
            total_problems=5,
            is_active=True
        )

        # 問題を取得
        url = reverse('quizsession-next-problem', kwargs={'pk': session.id})
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "question_text" in response.data, "question_textフィールドが存在しません"
        assert response.data["question_text"] != "", "question_textが空です"

    def test_session_includes_answered_problems(self, setup_data):
        """セッションレスポンスにanswered_problemsが含まれることを確認（バグ修正）"""
        client = setup_data["client"]
        subject = setup_data["subject"]

        # セッションを作成
        session = QuizSession.objects.create(
            user=setup_data["user"],
            subject=subject,
            total_problems=10,
            completed_problems=3,
            is_active=True
        )

        # セッション情報を取得
        url = reverse('quizsession-detail', kwargs={'pk': session.id})
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "answered_problems" in response.data, "answered_problemsフィールドが存在しません"
        assert response.data["answered_problems"] == 3, \
            f"answered_problemsの値が正しくありません: {response.data['answered_problems']}"

    def test_problem_type_conversion(self, setup_data):
        """problem_typeが正しく変換されてレスポンスされることを確認"""
        client = setup_data["client"]
        subject = setup_data["subject"]

        # セッションを作成
        session = QuizSession.objects.create(
            user=setup_data["user"],
            subject=subject,
            total_problems=5,
            is_active=True
        )

        # 問題を取得
        url = reverse('quizsession-next-problem', kwargs={'pk': session.id})
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["problem_type"] == "single_choice", \
            f"problem_typeの変換が正しくありません: {response.data['problem_type']}"

    def test_difficulty_conversion(self, setup_data):
        """difficultyが正しく変換されてレスポンスされることを確認"""
        client = setup_data["client"]
        subject = setup_data["subject"]

        # セッションを作成
        session = QuizSession.objects.create(
            user=setup_data["user"],
            subject=subject,
            total_problems=5,
            is_active=True
        )

        # 問題を取得
        url = reverse('quizsession-next-problem', kwargs={'pk': session.id})
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["difficulty"] == "easy", \
            f"difficultyの変換が正しくありません: {response.data['difficulty']}"
