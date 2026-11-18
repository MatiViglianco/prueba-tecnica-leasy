from __future__ import annotations

from http import HTTPStatus

from ninja import NinjaAPI, Router
from ninja.errors import AuthenticationError, HttpError, ValidationError
from ninja.responses import Status

from client_portal.schemas import (
    ClientProfileSchema,
    LoginRequest,
    ProblemDetailSchema,
    ReservationListItem,
    TokenResponse,
)
from client_portal.security import ClientJWTAuth, ClientTokenService
from client_portal.services import ClientPortalAuthService, ClientReservationQueryService
from shared.errors import AppError

api = NinjaAPI(title="Assessment Client API", version="1.0.0")
client_auth = ClientJWTAuth()

auth_router = Router(tags=["auth"])
reservation_router = Router(tags=["reservations"])

FAMILY_HTTP = {
    "auth": (401, "Authentication Failed"),
    "domain": (400, "Application Error"),
}


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
    status, title = FAMILY_HTTP.get(exc.family, FAMILY_HTTP["domain"])
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


@reservation_router.get("/", response=list[ReservationListItem], auth=client_auth)
def list_reservations(request):
    reservations = ClientReservationQueryService().get_customer_reservations(
        customer_id=request.auth.id
    )
    return [
        ReservationListItem(
            id=reservation.id,
            room_name=reservation.room.name,
            status=reservation.status,
            starts_at=reservation.starts_at,
            ends_at=reservation.ends_at,
            cancel_reason=reservation.cancel_reason or None,
        )
        for reservation in reservations
    ]


api.add_router("/auth/", auth_router)
api.add_router("/reservations/", reservation_router)
