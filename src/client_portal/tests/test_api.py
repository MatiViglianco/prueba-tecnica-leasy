import pytest

from client_portal.security import ClientTokenService
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
