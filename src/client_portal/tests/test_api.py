import uuid

import pytest

from client_portal.security import ClientTokenService
from reservations.constants import (
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_CONFIRMED,
    RESERVATION_STATUS_REQUESTED,
)
from reservations.tests.factories import CustomerFactory, ReservationFactory, UserFactory


@pytest.mark.django_db
def test_login_returns_access_token(client):
    user = UserFactory(email="alice@example.com", username="alice", password="demo1234")
    customer = CustomerFactory(user=user)

    response = client.post(
        "/api/v1/auth/login",
        data={"email": customer.user.email, "password": "demo1234"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.django_db
def test_me_returns_customer_profile(client):
    customer = CustomerFactory()
    token = ClientTokenService.issue_access_token(customer=customer)

    response = client.get(
        "/api/v1/auth/me",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(customer.id)


@pytest.mark.django_db
def test_reservation_list_is_scoped_to_customer(client):
    customer = CustomerFactory()
    other_customer = CustomerFactory()
    own_reservation = ReservationFactory(customer=customer)
    ReservationFactory(customer=other_customer)
    token = ClientTokenService.issue_access_token(customer=customer)

    response = client.get(
        "/api/v1/reservations/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(own_reservation.id)


PROBLEM_KEYS = {"type", "title", "status", "detail", "code", "instance", "errors"}


def _assert_problem(response, *, status: int, code: str) -> dict:
    assert response.status_code == status
    payload = response.json()
    assert set(payload) == PROBLEM_KEYS
    assert payload["status"] == status
    assert payload["code"] == code
    assert payload["type"] == f"urn:assessment:problem:{code}"
    assert payload["instance"] == response.wsgi_request.path
    return payload


@pytest.mark.django_db
def test_login_with_wrong_password_returns_problem(client):
    user = UserFactory(email="alice@example.com", username="alice", password="demo1234")
    CustomerFactory(user=user)

    response = client.post(
        "/api/v1/auth/login",
        data={"email": "alice@example.com", "password": "wrong-password"},
        content_type="application/json",
    )

    _assert_problem(response, status=401, code="auth_invalid_credentials")


@pytest.mark.django_db
def test_login_with_invalid_payload_returns_validation_problem(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"email": "alice@example.com"},
        content_type="application/json",
    )

    payload = _assert_problem(response, status=422, code="validation_error")
    assert payload["errors"][0]["loc"][-1] == "password"


@pytest.mark.django_db
def test_me_without_token_returns_problem(client):
    response = client.get("/api/v1/auth/me")

    _assert_problem(response, status=401, code="auth_not_authenticated")


@pytest.mark.django_db
def test_me_with_invalid_token_returns_problem(client):
    response = client.get(
        "/api/v1/auth/me",
        HTTP_AUTHORIZATION="Bearer not-a-valid-token",
    )

    _assert_problem(response, status=401, code="auth_invalid_token")


def _auth_header(customer) -> dict:
    token = ClientTokenService.issue_access_token(customer=customer)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def _cancel(client, reservation_id, *, payload=None, headers=None):
    return client.post(
        f"/api/v1/reservations/{reservation_id}/cancel",
        data=payload if payload is not None else {"reason": "Plans changed"},
        content_type="application/json",
        **(headers or {}),
    )


@pytest.mark.django_db
def test_cancel_reservation_returns_updated_reservation(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_CONFIRMED)

    response = _cancel(
        client,
        reservation.id,
        payload={"reason": "  Plans changed  "},
        headers=_auth_header(reservation.customer),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(reservation.id)
    assert payload["status"] == RESERVATION_STATUS_CANCELLED
    assert payload["cancel_reason"] == "Plans changed"
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_CANCELLED


@pytest.mark.django_db
def test_cancel_reservation_of_another_customer_returns_not_found(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    intruder = CustomerFactory()

    response = _cancel(client, reservation.id, headers=_auth_header(intruder))

    _assert_problem(response, status=404, code="reservation_not_found")
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED


@pytest.mark.django_db
def test_cancel_unknown_reservation_returns_not_found(client):
    customer = CustomerFactory()

    response = _cancel(client, uuid.uuid4(), headers=_auth_header(customer))

    _assert_problem(response, status=404, code="reservation_not_found")


@pytest.mark.django_db
def test_cancel_already_cancelled_reservation_returns_conflict(client):
    reservation = ReservationFactory(
        status=RESERVATION_STATUS_CANCELLED,
        cancel_reason="Original reason",
    )

    response = _cancel(client, reservation.id, headers=_auth_header(reservation.customer))

    _assert_problem(response, status=409, code="reservation_invalid_transition")
    reservation.refresh_from_db()
    assert reservation.cancel_reason == "Original reason"


@pytest.mark.django_db
@pytest.mark.parametrize("payload", [{}, {"reason": ""}, {"reason": "   "}])
def test_cancel_without_reason_returns_validation_problem(client, payload):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)

    response = _cancel(
        client,
        reservation.id,
        payload=payload,
        headers=_auth_header(reservation.customer),
    )

    problem = _assert_problem(response, status=422, code="validation_error")
    assert problem["errors"][0]["loc"][-1] == "reason"
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED


@pytest.mark.django_db
def test_cancel_without_token_returns_problem(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)

    response = _cancel(client, reservation.id)

    _assert_problem(response, status=401, code="auth_not_authenticated")
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED
