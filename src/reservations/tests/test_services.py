import uuid

import pytest

from reservations.constants import (
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_CONFIRMED,
    RESERVATION_STATUS_ON_HOLD,
    RESERVATION_STATUS_REQUESTED,
)
from reservations.exceptions import (
    ReservationCancelReasonRequiredError,
    ReservationHoldReasonRequiredError,
    ReservationNotFoundError,
    ReservationStatusTransitionError,
)
from reservations.services import ReservationLifecycleService
from reservations.tests.factories import ReservationFactory


@pytest.mark.django_db
def test_confirm_reservation_moves_requested_to_confirmed():
    reservation = ReservationFactory(status="requested")

    ReservationLifecycleService().confirm_reservation(reservation_id=reservation.id)

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_CONFIRMED


@pytest.mark.django_db
def test_confirm_reservation_rejects_invalid_transition():
    reservation = ReservationFactory(status=RESERVATION_STATUS_CANCELLED)

    with pytest.raises(ReservationStatusTransitionError):
        ReservationLifecycleService().confirm_reservation(reservation_id=reservation.id)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "initial_status",
    [RESERVATION_STATUS_REQUESTED, RESERVATION_STATUS_CONFIRMED],
)
def test_hold_reservation_moves_holdable_status_to_on_hold(initial_status):
    reservation = ReservationFactory(status=initial_status)

    ReservationLifecycleService().hold_reservation(
        reservation_id=reservation.id,
        reason="  Payment pending  ",
    )

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_ON_HOLD
    assert reservation.hold_reason == "Payment pending"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "initial_status",
    [RESERVATION_STATUS_ON_HOLD, RESERVATION_STATUS_CANCELLED],
)
def test_hold_reservation_rejects_invalid_transition(initial_status):
    reservation = ReservationFactory(status=initial_status, hold_reason="")

    with pytest.raises(ReservationStatusTransitionError):
        ReservationLifecycleService().hold_reservation(
            reservation_id=reservation.id,
            reason="Payment pending",
        )

    reservation.refresh_from_db()
    assert reservation.status == initial_status
    assert reservation.hold_reason == ""


@pytest.mark.django_db
@pytest.mark.parametrize("reason", ["", "   ", None])
def test_hold_reservation_requires_reason(reason):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)

    with pytest.raises(ReservationHoldReasonRequiredError):
        ReservationLifecycleService().hold_reservation(
            reservation_id=reservation.id,
            reason=reason,
        )

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED


@pytest.mark.django_db
def test_hold_reservation_raises_not_found_for_unknown_id():
    with pytest.raises(ReservationNotFoundError):
        ReservationLifecycleService().hold_reservation(
            reservation_id=uuid.uuid4(),
            reason="Payment pending",
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "initial_status",
    [
        RESERVATION_STATUS_REQUESTED,
        RESERVATION_STATUS_CONFIRMED,
        RESERVATION_STATUS_ON_HOLD,
    ],
)
def test_cancel_reservation_moves_cancellable_status_to_cancelled(initial_status):
    reservation = ReservationFactory(status=initial_status)

    ReservationLifecycleService().cancel_reservation(
        reservation_id=reservation.id,
        reason="  Plans changed  ",
    )

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_CANCELLED
    assert reservation.cancel_reason == "Plans changed"


@pytest.mark.django_db
def test_cancel_reservation_rejects_already_cancelled():
    reservation = ReservationFactory(
        status=RESERVATION_STATUS_CANCELLED,
        cancel_reason="Original reason",
    )

    with pytest.raises(ReservationStatusTransitionError):
        ReservationLifecycleService().cancel_reservation(
            reservation_id=reservation.id,
            reason="Second attempt",
        )

    reservation.refresh_from_db()
    assert reservation.cancel_reason == "Original reason"


@pytest.mark.django_db
@pytest.mark.parametrize("reason", ["", "   ", None])
def test_cancel_reservation_requires_reason(reason):
    reservation = ReservationFactory(status=RESERVATION_STATUS_REQUESTED)

    with pytest.raises(ReservationCancelReasonRequiredError):
        ReservationLifecycleService().cancel_reservation(
            reservation_id=reservation.id,
            reason=reason,
        )

    reservation.refresh_from_db()
    assert reservation.status == RESERVATION_STATUS_REQUESTED
