from __future__ import annotations

from uuid import UUID

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import QuerySet

from client_portal.exceptions import InvalidCredentialsError
from reservations.exceptions import ReservationNotFoundError
from reservations.models import Customer, Reservation
from reservations.services import ReservationLifecycleService


class ClientPortalAuthService:
    def authenticate_client(self, *, email: str, password: str) -> Customer:
        user = User.objects.filter(email=email).select_related("customer_profile").first()
        if user is None or user.is_staff or not hasattr(user, "customer_profile"):
            raise InvalidCredentialsError()

        authenticated = authenticate(username=user.username, password=password)
        if authenticated is None or not authenticated.is_active:
            raise InvalidCredentialsError()

        return authenticated.customer_profile


class ClientReservationQueryService:
    def get_customer_reservations(self, *, customer_id) -> QuerySet[Reservation]:
        return Reservation.objects.filter(customer_id=customer_id).select_related("room")


class ClientReservationCancelService:
    def cancel_reservation(
        self,
        *,
        customer_id: UUID,
        reservation_id: UUID,
        reason: str,
    ) -> Reservation:
        # Another customer's reservation is reported as not found so the API
        # does not reveal which reservation ids exist.
        is_owner = Reservation.objects.filter(
            pk=reservation_id,
            customer_id=customer_id,
        ).exists()
        if not is_owner:
            raise ReservationNotFoundError()

        return ReservationLifecycleService().cancel_reservation(
            reservation_id=reservation_id,
            reason=reason,
        )
