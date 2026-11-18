from __future__ import annotations

from http import HTTPStatus
from uuid import UUID

from ninja import NinjaAPI, Router
from ninja.errors import AuthenticationError, HttpError, ValidationError
from ninja.responses import Status

from client_portal.schemas import (
    CancelReservationRequest,
    ClientProfileSchema,
    LoginRequest,
    ProblemDetailSchema,
    ReservationListItem,
    TokenResponse,
)
from client_portal.security import ClientJWTAuth, ClientTokenService
from client_portal.services import (
    ClientPortalAuthService,
    ClientReservationCancelService,
    ClientReservationQueryService,
)
from reservations.exceptions import (
    ReservationCancelReasonRequiredError,
    ReservationNotFoundError,
    ReservationStatusTransitionError,
)
from reservations.models import Reservation
from shared.errors import AppError

api = NinjaAPI(title="Assessment Client API", version="1.0.0")
client_auth = ClientJWTAuth()

auth_router = Router(tags=["auth"])
reservation_router = Router(tags=["reservations"])

FAMILY_HTTP = {
    "auth": (401, "Authentication Failed"),
    "domain": (400, "Application Error"),
}

# Specific domain errors that deserve a more precise HTTP status than the
# family default. Checked in order with isinstance, so subclasses inherit it.
ERROR_HTTP = (
    (ReservationNotFoundError, 404, "Resource Not Found"),
    (ReservationStatusTransitionError, 409, "Conflict"),
    (ReservationCancelReasonRequiredError, 422, "Validation Error"),
)


def _http_status_for(exc: AppError) -> tuple[int, str]:
    for error_class, status, title in ERROR_HTTP:
        if isinstance(exc, error_class):
            return status, title
    return FAMILY_HTTP.get(exc.family, FAMILY_HTTP["domain"])


def _problem_response(
    request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    errors: list[dict] | None = None,
):
    problem = ProblemDetailSchema.make(
        request=request,
        status=status,
        code=code,
        title=title,
        detail=detail,
        errors=errors,
    )
    return api.create_response(request, problem.model_dump(), status=status)


@api.exception_handler(AppError)
def handle_app_error(request, exc: AppError):
    status, title = _http_status_for(exc)
    return _problem_response(
        request,
        status=status,
        code=exc.code,
        title=title,
        detail=exc.detail,
        errors=exc.errors,
    )


@api.exception_handler(ValidationError)
def handle_validation_error(request, exc: ValidationError):
    errors = [
        {
            "loc": [str(part) for part in error.get("loc", ())],
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
        }
        for error in exc.errors
    ]
    return _problem_response(
        request,
        status=422,
        code="validation_error",
        title="Validation Error",
        detail="The request payload is invalid.",
        errors=errors,
    )


@api.exception_handler(AuthenticationError)
def handle_authentication_error(request, exc: AuthenticationError):
    return _problem_response(
        request,
        status=401,
        code="auth_not_authenticated",
        title="Authentication Failed",
        detail="Authentication credentials were not provided.",
    )


@api.exception_handler(HttpError)
def handle_http_error(request, exc: HttpError):
    status = exc.status_code
    return _problem_response(
        request,
        status=status,
        code=f"http_{status}",
        title=HTTPStatus(status).phrase,
        detail=str(exc),
    )


@auth_router.post(
    "/login",
    response={200: TokenResponse, 401: ProblemDetailSchema},
    auth=None,
)
def login(request, payload: LoginRequest):
    customer = ClientPortalAuthService().authenticate_client(
        email=payload.email,
        password=payload.password,
    )
    token = ClientTokenService.issue_access_token(customer=customer)
    return Status(200, TokenResponse(access_token=token))


@auth_router.get("/me", response=ClientProfileSchema, auth=client_auth)
def me(request):
    customer = request.auth
    return ClientProfileSchema(
        id=customer.id,
        email=customer.user.email,
        display_name=customer.display_name,
    )


def _to_list_item(reservation: Reservation) -> ReservationListItem:
    return ReservationListItem(
        id=reservation.id,
        room_name=reservation.room.name,
        status=reservation.status,
        starts_at=reservation.starts_at,
        ends_at=reservation.ends_at,
        cancel_reason=reservation.cancel_reason or None,
    )


@reservation_router.get("/", response=list[ReservationListItem], auth=client_auth)
def list_reservations(request):
    reservations = ClientReservationQueryService().get_customer_reservations(
        customer_id=request.auth.id
    )
    return [_to_list_item(reservation) for reservation in reservations]


@reservation_router.post(
    "/{reservation_id}/cancel",
    response={
        200: ReservationListItem,
        401: ProblemDetailSchema,
        404: ProblemDetailSchema,
        409: ProblemDetailSchema,
        422: ProblemDetailSchema,
    },
    auth=client_auth,
)
def cancel_reservation(request, reservation_id: UUID, payload: CancelReservationRequest):
    reservation = ClientReservationCancelService().cancel_reservation(
        customer_id=request.auth.id,
        reservation_id=reservation_id,
        reason=payload.reason,
    )
    return Status(200, _to_list_item(reservation))


api.add_router("/auth/", auth_router)
api.add_router("/reservations/", reservation_router)
