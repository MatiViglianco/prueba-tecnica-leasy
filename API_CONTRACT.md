# Contrato base del API cliente

Base URL local:

- `http://127.0.0.1:8000/api/v1`

## Auth

### `POST /auth/login`

Request:

```json
{
  "email": "alice@example.com",
  "password": "demo1234"
}
```

Response `200`:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

### `GET /auth/me`

Header:

```text
Authorization: Bearer <token>
```

Response `200`:

```json
{
  "id": "uuid",
  "email": "alice@example.com",
  "display_name": "Alice Stone"
}
```

## Reservations

### `GET /reservations/`

Header:

```text
Authorization: Bearer <token>
```

Response `200`:

```json
[
  {
    "id": "uuid",
    "room_name": "Room A",
    "status": "requested",
    "starts_at": "2026-04-20T15:00:00-05:00",
    "ends_at": "2026-04-20T17:00:00-05:00",
    "cancel_reason": null
  }
]
```

### `POST /reservations/{reservation_id}/cancel`

Cancela una reserva del cliente autenticado.

Header:

```text
Authorization: Bearer <token>
```

Request:

```json
{
  "reason": "Cambio de planes"
}
```

`reason` es obligatorio, se recortan los espacios y debe tener entre 1 y 500
caracteres.

Response `200` (la reserva actualizada, mismo esquema que el listado):

```json
{
  "id": "uuid",
  "room_name": "Room A",
  "status": "cancelled",
  "starts_at": "2026-04-20T15:00:00-05:00",
  "ends_at": "2026-04-20T17:00:00-05:00",
  "cancel_reason": "Cambio de planes"
}
```

Estados que se pueden cancelar: `requested`, `confirmed`, `on_hold`.

Errores:

| Status | `code` | Cuándo |
|---|---|---|
| 401 | `auth_not_authenticated` | Falta el header `Authorization`. |
| 401 | `auth_invalid_token` | Token inválido o expirado. |
| 404 | `reservation_not_found` | La reserva no existe o pertenece a otro cliente. |
| 409 | `reservation_invalid_transition` | La reserva ya está en un estado que no se puede cancelar. |
| 422 | `validation_error` | Falta `reason`, está vacío o el body es inválido. `errors` detalla los campos. |

## Error format

Los errores de dominio y auth deben mantenerse en este formato:

```json
{
  "type": "urn:assessment:problem:auth_invalid_credentials",
  "title": "Authentication Failed",
  "status": 401,
  "detail": "Invalid email or password.",
  "code": "auth_invalid_credentials",
  "instance": "/api/v1/auth/login",
  "errors": null
}
```

El endpoint de cancelación que debe construir el candidato debe seguir este
mismo contrato.

Los errores de validación del payload (`422`, `code: validation_error`) usan el
mismo formato e incluyen el detalle por campo en `errors`:

```json
{
  "type": "urn:assessment:problem:validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "The request payload is invalid.",
  "code": "validation_error",
  "instance": "/api/v1/reservations/<id>/cancel",
  "errors": [
    {"loc": ["body", "payload", "reason"], "msg": "Field required", "type": "missing"}
  ]
}
```
