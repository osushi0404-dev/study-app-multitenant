"""
I158: クイズ開始時のセッション二重作成の是正（開始の冪等性と「1 ユーザー 1 有効セッション」）。

- 開始は同一ユーザー内で直列化し、有効セッションは常に高々 1 件
- Idempotency-Key（UUID）が同じ再送は作成済みセッションを 200 で返す
- PUT/PATCH/DELETE は 405・is_active は読み取り専用
- 回答送信・終了は開始処理が終了させた is_active を書き戻さない

TC-01〜TC-19（docs/tests/open/I158_auto_test.md）に対応。
"""
import importlib
import inspect
import threading
import uuid
from unittest import mock

import pytest
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Organization, OrganizationCategory
from problems.models import Problem, QuizSession, Subject
from problems.services.quiz_service import QuizService
from problems.views import QuizSessionViewSet

User = get_user_model()

QUIZ_URL = "/api/quiz/"
KEY = "6f1c2a7e-3b9d-4c55-8a10-2f4e6d8b9c01"

BODY_400_KEY = {"error": {"main_message": "入力内容にエラーがあります",
                          "sub_message": "Idempotency-Key は UUID 形式で指定してください", "details": {}}}
BODY_409 = {"error": {"main_message": "クイズの開始が競合しました",
                      "sub_message": "しばらくしてから再度お試しください", "details": {}}}
BODY_422 = {"error": {"main_message": "Idempotency-Key が別の内容で使用されています",
                      "sub_message": "新しいキーで再度お試しください", "details": {}}}


def _build():
    cat = OrganizationCategory.objects.create(name="テストI158", slug="test-cat-i158")
    org = Organization.objects.create(
        name="組織I158", slug="org-i158", type="school", category=cat, is_active=True)
    user = User.objects.create_user(
        email="user_i158@example.com", user_id="user_i158", password="pass",
        organization=org, role="user",
    )
    other = User.objects.create_user(
        email="other_i158@example.com", user_id="other_i158", password="pass",
        organization=org, role="user",
    )
    subject_a = Subject.objects.create(name="科目I158A", slug="subj-i158-a", organization=org)
    subject_b = Subject.objects.create(name="科目I158B", slug="subj-i158-b", organization=org)
    # total_problems の検証用: subject_a に未削除 2 件＋削除済み 1 件、subject_b に 1 件
    for subject, question, is_deleted in [
        (subject_a, "A1", False), (subject_a, "A2", False),
        (subject_a, "A3", True), (subject_b, "B1", False),
    ]:
        Problem.objects.create(
            subject=subject, organization=org, created_by=user, question=question,
            problem_type="single", difficulty=1, explanation="解説", is_deleted=is_deleted,
        )
    return {"user": user, "other": other, "subject_a": subject_a, "subject_b": subject_b}


@pytest.fixture
def setup(db):
    return _build()


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _active_count(user):
    return QuizSession.objects.filter(user=user, is_active=True).count()


def _post_concurrently(user, payload, headers):
    """Barrier で揃えた 2 スレッドから同時に開始する。結果は (status, id) のリスト。"""
    barrier = threading.Barrier(2)
    results = []
    errors = []

    def worker():
        try:
            client = _client(user)
            barrier.wait(timeout=10)
            response = client.post(QUIZ_URL, payload, format="json", **headers)
            results.append((response.status_code, response.data.get("id")))
        except Exception as exc:  # スレッド内の例外を握りつぶさず集める
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
        assert not thread.is_alive()
    assert errors == []
    return results


# ---- TC-01: キー無しの新規開始 ----
def test_start_without_key_creates_session(setup):
    response = _client(setup["user"]).post(
        QUIZ_URL, {"subject": setup["subject_a"].id}, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert _active_count(setup["user"]) == 1
    session = QuizSession.objects.get(pk=response.data["id"])
    assert session.client_request_id is None
    assert response.data["total_problems"] == 2
    assert "client_request_id" not in response.data


# ---- TC-02: キー無しの開始は後勝ち ----
def test_start_without_key_ends_previous_active(setup):
    previous = QuizSession.objects.create(user=setup["user"], subject=setup["subject_a"])

    response = _client(setup["user"]).post(
        QUIZ_URL, {"subject": setup["subject_a"].id}, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    previous.refresh_from_db()
    assert previous.is_active is False
    assert previous.ended_at is not None
    assert _active_count(setup["user"]) == 1
    assert response.data["id"] != previous.id


# ---- TC-03: 同じキーの再送は既存を返す ----
def test_same_key_returns_existing_session(setup):
    client = _client(setup["user"])
    payload = {"subject": setup["subject_a"].id}

    first = client.post(QUIZ_URL, payload, format="json", HTTP_IDEMPOTENCY_KEY=KEY)
    second = client.post(QUIZ_URL, payload, format="json", HTTP_IDEMPOTENCY_KEY=KEY)

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_200_OK
    assert first.data["id"] == second.data["id"]
    assert QuizSession.objects.filter(user=setup["user"]).count() == 1


# ---- TC-04: 異なるキーは後勝ち ----
def test_different_key_ends_previous_session(setup):
    client = _client(setup["user"])
    payload = {"subject": setup["subject_a"].id}

    first = client.post(QUIZ_URL, payload, format="json", HTTP_IDEMPOTENCY_KEY=KEY)
    second = client.post(QUIZ_URL, payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_201_CREATED
    assert first.data["id"] != second.data["id"]
    assert QuizSession.objects.get(pk=first.data["id"]).is_active is False
    assert _active_count(setup["user"]) == 1


# ---- TC-05: UUID でないキーは 400 ----
@pytest.mark.parametrize("raw_key", ["not-a-uuid", ""])
def test_invalid_key_returns_400(setup, raw_key):
    response = _client(setup["user"]).post(
        QUIZ_URL, {"subject": setup["subject_a"].id}, format="json",
        HTTP_IDEMPOTENCY_KEY=raw_key)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == BODY_400_KEY
    assert QuizSession.objects.count() == 0


# ---- TC-06: 同じキーで科目が違う再送は 422 ----
def test_same_key_with_different_subject_returns_422(setup):
    client = _client(setup["user"])

    first = client.post(
        QUIZ_URL, {"subject": setup["subject_a"].id}, format="json", HTTP_IDEMPOTENCY_KEY=KEY)
    second = client.post(
        QUIZ_URL, {"subject": setup["subject_b"].id}, format="json", HTTP_IDEMPOTENCY_KEY=KEY)

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert second.json() == BODY_422
    assert QuizSession.objects.filter(user=setup["user"]).count() == 1
    assert QuizSession.objects.get(pk=first.data["id"]).is_active is True


# ---- TC-07: 同時 2 回（キー無し）でも有効は 1 件 ----
@pytest.mark.django_db(transaction=True)
def test_concurrent_start_without_key_keeps_single_active():
    world = _build()

    results = _post_concurrently(world["user"], {"subject": world["subject_a"].id}, {})

    assert [code for code, _ in results] == [status.HTTP_201_CREATED] * 2
    assert _active_count(world["user"]) == 1
    assert QuizSession.objects.filter(user=world["user"]).count() == 2


# ---- TC-08: 同時 2 回（同じキー）は 1 件だけ作成 ----
@pytest.mark.django_db(transaction=True)
def test_concurrent_start_with_same_key_creates_once():
    world = _build()

    results = _post_concurrently(
        world["user"], {"subject": world["subject_a"].id}, {"HTTP_IDEMPOTENCY_KEY": KEY})

    assert sorted(code for code, _ in results) == [status.HTTP_200_OK, status.HTTP_201_CREATED]
    assert results[0][1] == results[1][1]
    assert QuizSession.objects.filter(user=world["user"]).count() == 1


# ---- TC-09: DB 制約で有効 2 件目を拒否 ----
def test_db_constraint_rejects_second_active_session(setup):
    QuizSession.objects.create(user=setup["user"], is_active=True)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            QuizSession.objects.create(user=setup["user"], is_active=True)


# ---- TC-10: 制約違反は 409・途中の更新は取り消される ----
def test_integrity_error_returns_409_and_rolls_back(setup):
    previous = QuizSession.objects.create(user=setup["user"], subject=setup["subject_a"])

    with mock.patch.object(QuizSession.objects, "create", side_effect=IntegrityError):
        response = _client(setup["user"]).post(
            QUIZ_URL, {"subject": setup["subject_a"].id}, format="json")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == BODY_409
    previous.refresh_from_db()
    assert previous.is_active is True
    assert previous.ended_at is None
    assert QuizSession.objects.filter(user=setup["user"]).count() == 1


# ---- TC-11: 書き換え・削除は 405 ----
def test_update_and_delete_are_not_allowed(setup):
    session = QuizSession.objects.create(user=setup["user"], subject=setup["subject_a"])
    client = _client(setup["user"])
    url = f"{QUIZ_URL}{session.id}/"

    responses = [
        client.put(url, {"is_active": False}, format="json"),
        client.patch(url, {"is_active": False}, format="json"),
        client.delete(url),
    ]

    assert [r.status_code for r in responses] == [status.HTTP_405_METHOD_NOT_ALLOWED] * 3
    session.refresh_from_db()
    assert session.is_active is True


# ---- TC-12: 作成時に is_active を送っても無視される ----
def test_is_active_is_read_only_on_create(setup):
    response = _client(setup["user"]).post(
        QUIZ_URL, {"subject": setup["subject_a"].id, "is_active": False}, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["is_active"] is True
    assert QuizSession.objects.get(pk=response.data["id"]).is_active is True


# ---- TC-13: CORS preflight で idempotency-key が許可される ----
def test_cors_preflight_allows_idempotency_key(db):
    response = APIClient().options(
        QUIZ_URL,
        HTTP_ORIGIN="http://localhost:3000",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type,idempotency-key",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "idempotency-key" in response["Access-Control-Allow-Headers"].lower()


# ---- TC-14: データマイグレーション関数が最新以外だけを終了する ----
def test_data_migration_deactivates_all_but_latest(setup):
    migration = importlib.import_module(
        "problems.migrations.0020_deactivate_duplicate_active_quizsessions")
    constraint = next(
        c for c in QuizSession._meta.constraints if c.name == "uniq_active_quizsession_per_user")
    with connection.schema_editor() as editor:
        editor.remove_constraint(QuizSession, constraint)

    user, other = setup["user"], setup["other"]
    now = timezone.now()
    oldest, middle, latest = [QuizSession.objects.create(user=user) for _ in range(3)]
    for offset, session in [(3, oldest), (2, middle), (1, latest)]:
        QuizSession.objects.filter(pk=session.pk).update(
            started_at=now - timezone.timedelta(hours=offset))
    ended_at = now - timezone.timedelta(days=1)
    finished = QuizSession.objects.create(user=user, is_active=False, ended_at=ended_at)
    other_active = QuizSession.objects.create(user=other)

    migration.deactivate_duplicate_active_sessions(django_apps, None)

    # 制約はテストのロールバックで元に戻る（更新直後に同じトランザクションで付け直すと
    # PostgreSQL の pending trigger events になるため、本番のマイグレーションも 0020/0021 を分けている）
    assert _active_count(user) == 1
    for session in (oldest, middle, latest, finished, other_active):
        session.refresh_from_db()
    assert latest.is_active is True
    assert oldest.is_active is False and oldest.ended_at is not None
    assert middle.is_active is False and middle.ended_at is not None
    assert finished.is_active is False and finished.ended_at == ended_at
    assert other_active.is_active is True


# ---- TC-15: 同じキーのセッションが終了済みでもそのまま返す ----
def test_same_key_returns_ended_session_as_is(setup):
    client = _client(setup["user"])
    payload = {"subject": setup["subject_a"].id}

    first = client.post(QUIZ_URL, payload, format="json", HTTP_IDEMPOTENCY_KEY=KEY)
    client.post(f"{QUIZ_URL}{first.data['id']}/end/")
    third = client.post(QUIZ_URL, payload, format="json", HTTP_IDEMPOTENCY_KEY=KEY)

    assert third.status_code == status.HTTP_200_OK
    assert third.data["id"] == first.data["id"]
    assert third.data["is_active"] is False
    assert QuizSession.objects.filter(user=setup["user"]).count() == 1


# ---- TC-16: キーはユーザーごと ----
def test_key_is_scoped_per_user(setup):
    payload = {"subject": setup["subject_a"].id}

    mine = _client(setup["user"]).post(QUIZ_URL, payload, format="json", HTTP_IDEMPOTENCY_KEY=KEY)
    theirs = _client(setup["other"]).post(QUIZ_URL, payload, format="json", HTTP_IDEMPOTENCY_KEY=KEY)

    assert theirs.status_code == status.HTTP_201_CREATED
    assert theirs.data["id"] != mine.data["id"]
    assert QuizSession.objects.get(pk=theirs.data["id"]).user == setup["other"]
    assert QuizSession.objects.get(pk=mine.data["id"]).is_active is True


# ---- TC-17: 未認証は 401 ----
def test_unauthenticated_start_returns_401(setup):
    response = APIClient().post(QUIZ_URL, {"subject": setup["subject_a"].id}, format="json")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert QuizSession.objects.count() == 0


# ---- TC-18: 回答送信は開始処理が終了させた状態を書き戻さない ----
def test_submit_answer_does_not_reactivate_session_ended_by_start(setup):
    session = QuizSession.objects.create(user=setup["user"], subject=setup["subject_a"])
    problem = Problem.objects.filter(subject=setup["subject_a"], is_deleted=False).first()
    # submit_answer が get_object で読んだ直後に、別タブの開始が割り込んだ状態を再現する
    stale = QuizSession.objects.get(pk=session.pk)
    QuizService.start_session(
        user=setup["user"], subject=setup["subject_a"], client_request_id=None)

    with mock.patch.object(QuizSessionViewSet, "get_object", return_value=stale):
        response = _client(setup["user"]).post(
            f"{QUIZ_URL}{session.id}/submit_answer/",
            {"problem_id": problem.id, "selected_choice_ids": []}, format="json")

    assert response.status_code == status.HTTP_200_OK
    session.refresh_from_db()
    assert session.is_active is False
    assert session.completed_problems == 1
    assert _active_count(setup["user"]) == 1


# ---- TC-19: QuizSessionViewSet に全列保存の session.save() が残っていない ----
def test_quiz_session_viewset_saves_only_needed_columns():
    source = inspect.getsource(QuizSessionViewSet)

    assert "session.save()" not in source
