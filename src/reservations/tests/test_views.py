import uuid

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from reservations.constants import (
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_ON_HOLD,
    RESERVATION_STATUS_REQUESTED,
)
from reservations.tests.factories import ReservationFactory, UserFactory, grant_permission


def _staff_user(*codenames):
    user = UserFactory(is_staff=True)
    for codename in codenames:
        grant_permission(user=user, codename=codename)
    return user


@pytest.mark.django_db
def test_reservation_list_requires_login(client):
    response = client.get(reverse("reservation_list"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_reservation_list_renders_for_user_with_permission(client):
    reservation = ReservationFactory()
    user = UserFactory()
    grant_permission(user=user, codename="view_reservation")
    client.force_login(user)

    response = client.get(reverse("reservation_list"))

    assert response.status_code == 200
    assert reservation.customer.display_name in response.content.decode()


@pytest.mark.django_db
def test_reservation_confirm_requires_permission(client):
    reservation = ReservationFactory()
    user = UserFactory()
    client.force_login(user)

    response = client.post(reverse("reservation_confirm", args=[reservation.id]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_hold_requires_login(client):
    reservation = ReservationFactory()

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"hold_reason": "Payment pending"},
    )

    assert response.status_code == 302
    assert reverse("login") in response["Location"]


@pytest.mark.django_db
def test_hold_is_forbidden_without_hold_permission(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    client.force_login(_staff_user("view_reservation", "change_reservation"))

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"hold_reason": "Payment pending"},
    )

    assert response.status_code == 403
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED
    assert reservation.hold_reason == ""


@pytest.mark.django_db
def test_hold_puts_reservation_on_hold_with_reason(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    client.force_login(_staff_user("view_reservation", "hold_reservation"))

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"hold_reason": "Payment pending"},
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("reservation_detail", args=[reservation.id])
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_ON_HOLD
    assert reservation.hold_reason == "Payment pending"


@pytest.mark.django_db
def test_hold_without_reason_returns_422_and_keeps_status(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    client.force_login(_staff_user("view_reservation", "hold_reservation"))

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"hold_reason": "   "},
    )

    assert response.status_code == 422
    assert "hold_reason" in response.context["hold_form"].errors
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED


@pytest.mark.django_db
def test_hold_invalid_transition_shows_error_and_keeps_status(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_CANCELLED)
    client.force_login(_staff_user("view_reservation", "hold_reservation"))

    response = client.post(
        reverse("reservation_hold", args=[reservation.id]),
        {"hold_reason": "Payment pending"},
    )

    assert response.status_code == 302
    messages = [str(message) for message in get_messages(response.wsgi_request)]
    assert messages == ["Reservation cannot transition from its current status."]
    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_CANCELLED
    assert reservation.hold_reason == ""


@pytest.mark.django_db
def test_hold_unknown_reservation_returns_404(client):
    client.force_login(_staff_user("view_reservation", "hold_reservation"))

    response = client.post(
        reverse("reservation_hold", args=[uuid.uuid4()]),
        {"hold_reason": "Payment pending"},
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_hold_rejects_get(client):
    reservation = ReservationFactory()
    client.force_login(_staff_user("view_reservation", "hold_reservation"))

    response = client.get(reverse("reservation_hold", args=[reservation.id]))

    assert response.status_code == 405


@pytest.mark.django_db
def test_detail_shows_hold_form_only_with_permission(client):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)
    hold_url = reverse("reservation_hold", args=[reservation.id])

    client.force_login(_staff_user("view_reservation"))
    response = client.get(reverse("reservation_detail", args=[reservation.id]))
    assert hold_url not in response.content.decode()

    client.force_login(_staff_user("view_reservation", "hold_reservation"))
    response = client.get(reverse("reservation_detail", args=[reservation.id]))
    assert hold_url in response.content.decode()


@pytest.mark.django_db
def test_detail_shows_hold_reason_and_hides_form_when_on_hold(client):
    reservation = ReservationFactory(
        status=RESERVATION_STATUS_ON_HOLD,
        hold_reason="Payment pending",
    )
    client.force_login(_staff_user("view_reservation", "hold_reservation"))

    response = client.get(reverse("reservation_detail", args=[reservation.id]))

    content = response.content.decode()
    assert "Payment pending" in content
    assert reverse("reservation_hold", args=[reservation.id]) not in content


@pytest.mark.django_db
def test_list_reflects_on_hold_status(client):
    ReservationFactory(status=RESERVATION_STATUS_ON_HOLD, hold_reason="Payment pending")
    client.force_login(_staff_user("view_reservation"))

    response = client.get(reverse("reservation_list"))

    assert "On hold" in response.content.decode()
