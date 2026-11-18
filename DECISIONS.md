# Decisiones técnicas

## 1. Las transiciones de estado viven en un servicio de dominio

`ON_HOLD` y la cancelación son métodos de `ReservationLifecycleService`, igual
que la confirmación que ya traía el starter. Cada transición sigue los mismos
pasos:

1. Valida el motivo (`strip()`; vacío o solo espacios no cuenta).
2. Bloquea la fila con `select_for_update` dentro de `transaction.atomic`.
3. Compara el estado actual con un conjunto de estados permitidos definido en
   `reservations/constants.py` (`RESERVATION_HOLDABLE_STATUSES`,
   `RESERVATION_CANCELLABLE_STATUSES`).
4. Si algo falla, lanza un error de dominio (`ReservationStatusTransitionError`,
   `ReservationHoldReasonRequiredError`, `ReservationCancelReasonRequiredError`).

Las vistas del backoffice y los endpoints del API solo validan la entrada,
llaman al servicio y traducen los errores a su canal: mensaje y redirect en el
backoffice, problem+json en el API. La regla de negocio está en un solo lugar,
y se prueba directamente con tests de servicio, sin HTTP.

El permiso `reservations.hold_reservation` se exige en la vista
(`permission_required`), no solo ocultando el botón. Un `operator` que arma el
POST a mano recibe `403`.

Para la cancelación desde el API, `ClientReservationCancelService` primero
verifica que la reserva sea del cliente autenticado y después delega en el
servicio de dominio. La propiedad de la reserva es una regla del portal cliente;
el ciclo de vida de la reserva no depende de quién la pide.

## 2. Todos los errores del API usan el mismo formato y un status HTTP preciso

El contrato exige errores en formato problem. El starter solo lo cumplía para
los errores de dominio: un body inválido o un request sin token devolvían el
formato por defecto de Ninja (`{"detail": ...}`). Agregué handlers para
`ValidationError` y `HttpError`/`AuthenticationError` de Ninja, así **todo**
error del API respeta el contrato, incluido el `422` con el detalle por campo
en `errors`.

También agregué un mapeo de clase de error a status HTTP en la capa del API
(`ERROR_HTTP` en `client_portal/api.py`):

| Error | Status |
|---|---|
| `ReservationNotFoundError` | `404` |
| `ReservationStatusTransitionError` | `409` |
| `ReservationCancelReasonRequiredError` | `422` |
| resto de errores de dominio | `400` (comportamiento del starter) |

Los errores de dominio no saben nada de HTTP: el mapeo vive en el API y el
backoffice reutiliza los mismos errores sin cambios.

Una reserva de **otro cliente** responde `404` y no `403`. Así el API no
revela qué ids de reserva existen.

En el cliente, `apiRequest` convierte cualquier fallo (error del API, respuesta
que no es JSON o servidor caído) en un `ApiError` con un `Problem`. La UI decide
qué mostrar según el `code`, nunca según el texto del mensaje.

## 3. Un solo origen para el navegador: nginx hace de proxy del API

La SPA y el API se ven desde el navegador como un solo origen. En Docker, el
nginx que sirve el build de la SPA reenvía `/api/` al contenedor de Django. En
desarrollo, el dev server de Vite hace lo mismo con `server.proxy`.

- No hace falta CORS ni agregar `django-cors-headers`.
- El cliente usa rutas relativas (`/api/v1`) y la misma build sirve para
  cualquier entorno.
- El backend no necesita exponerse al navegador para que funcione la app
  cliente; en este compose se publica en `:8000` solo por el backoffice.

El resto del empaquetado sigue la misma idea de una imagen pensada para
producción: build multi-stage con `uv sync --frozen --no-dev`, usuario no-root,
gunicorn en lugar de `runserver`, estáticos con WhiteNoise, healthchecks, y una
configuración por variables de entorno que falla al arrancar si falta
`DJANGO_SECRET_KEY` con `DEBUG` apagado. El detalle está en
[DOCKER.md](./DOCKER.md).

## Alternativa descartada: Next.js para la mini app

Next.js resuelve problemas que esta app no tiene: SSR, server components,
routing por archivos. A cambio suma costos concretos:

- La imagen necesita un runtime de Node en producción (`output: "standalone"`),
  en lugar de archivos estáticos detrás de nginx.
- Hay que decidir dónde vive el token (servidor, cookie o cliente) y
  mezclar componentes de servidor y de cliente para dos pantallas y un modal.
- Si se usa `output: "export"` para evitar el servidor, queda React con una
  capa extra que no se usa.

Vite + React + TypeScript genera una SPA estática que nginx sirve directamente.
El estado se maneja con `useState` y `fetch` nativo, sin librerías extra.

Otras alternativas que también descarté:

- **`django-cors-headers`.** Funciona, pero es una dependencia más y una
  configuración de orígenes que el proxy evita.
- **Poner el status HTTP en cada excepción de dominio.** Mezcla capas: el
  backoffice usa los mismos errores y no habla HTTP.
- **Migrar a PostgreSQL.** La consigna permite SQLite. Las limitaciones están en
  [DOCKER.md](./DOCKER.md#base-de-datos).

## Supuestos

- **ON_HOLD** se aplica desde `requested` o `confirmed`. No implementé una
  transición para salir de `ON_HOLD` porque la consigna no la pide; sería otro
  método del mismo servicio con su permiso.
- **Cancelación** permitida desde `requested`, `confirmed` y `on_hold`. No se
  valida si la reserva ya empezó, porque la consigna solo habla de estados.
- Al cancelar una reserva en espera se conserva `hold_reason`, para no perder
  historia.
- Los textos de los errores de dominio siguen en inglés, como los del starter.
  El cliente muestra mensajes en español según el `code`.
- El cliente muestra las fechas en la zona horaria del navegador; el backoffice,
  en la de Django (`America/Lima`). Es el mismo instante con distinta zona.
- El token del cliente se guarda en `sessionStorage`: sobrevive a un refresh y
  se borra al cerrar la pestaña. Es accesible desde JavaScript; una cookie
  `HttpOnly` sería más segura, pero obligaría a cambiar la autenticación del API
  y agregar protección CSRF.
- Con SQLite, `select_for_update` no bloquea filas. El código queda correcto para
  cuando se use una base que sí lo soporte.
- En Docker, las migraciones y los datos de demo se cargan al arrancar el
  contenedor para que `docker compose up` alcance para probar. En un despliegue
  real irían en un paso de release y sin datos de demo.

## Fuera del alcance pedido

- La vista de **confirmar** del starter devolvía `500` si la reserva ya no
  estaba en `requested`. La corregí para que muestre el error de dominio, con su
  test, porque la nueva vista de hold usa el mismo manejo de errores.
- El botón rojo del backoffice perdía el texto al pasar el mouse. Agregué el
  estilo `:hover`.

## Uso de IA

Usé Claude (Anthropic) como asistente durante la prueba: para analizar el
starter, discutir alternativas de diseño, generar código y tests, y probar los
flujos en el navegador. Revisé cada cambio y puedo explicar y modificar
cualquier parte de la solución.
