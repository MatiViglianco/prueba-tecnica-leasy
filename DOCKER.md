# Docker

La solución corre con dos contenedores:

| Servicio | Imagen | Puerto | Qué hace |
|---|---|---|---|
| `backend` | `Dockerfile` (raíz) | `8000` | Django con gunicorn: backoffice, admin y API `/api/v1`. |
| `client` | `client-app/Dockerfile` | `8080` | nginx sirve la SPA y hace proxy de `/api/` a `backend`. |

## Levantar todo

Requisitos: Docker con Compose v2.

```bash
cp .env.example .env
docker compose up --build
```

`.env` necesita un `DJANGO_SECRET_KEY` propio. Para generarlo:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Cuando los dos servicios están `healthy`:

- Mini app cliente: [http://localhost:8080](http://localhost:8080) (`alice@example.com` / `demo1234`)
- Backoffice: [http://localhost:8000/backoffice/reservations/](http://localhost:8000/backoffice/reservations/) (`manager` / `demo1234`)
- API: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)

Para apagar: `docker compose down`. Para borrar también la base de datos:
`docker compose down -v`.

## Variables de entorno

Se leen de `.env` (ver `.env.example`). Compose falla al arrancar si falta
`DJANGO_SECRET_KEY`.

| Variable | Default | Uso |
|---|---|---|
| `DJANGO_SECRET_KEY` | — (obligatoria) | Clave de Django. Con `DJANGO_DEBUG=0` la app no arranca con la clave insegura del starter. |
| `API_JWT_SECRET` | `DJANGO_SECRET_KEY` | Clave para firmar los JWT del API cliente. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,backend` | Hosts que acepta Django. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `http://localhost:8000,http://127.0.0.1:8000` | Orígenes válidos para los formularios del backoffice. |
| `DJANGO_SEED_DEMO_DATA` | `1` | Crea usuarios y reservas de demo al arrancar. |
| `DJANGO_LOG_LEVEL` | `INFO` | Nivel de logs (a stdout). |
| `BACKEND_PORT` / `CLIENT_PORT` | `8000` / `8080` | Puertos publicados en el host. |

La imagen del backend fija `DJANGO_DEBUG=0`, `DJANGO_DB_PATH=/app/data/db.sqlite3`
y `DJANGO_STATIC_ROOT=/app/staticfiles`.

## Imagen del backend

- **Multi-stage.** La etapa `builder` instala las dependencias con
  `uv sync --frozen --no-dev` a partir de `uv.lock`: mismas versiones que en
  desarrollo y sin herramientas de build en la imagen final.
- **Cache de capas.** Primero se copian `pyproject.toml` y `uv.lock` y se
  instalan las dependencias; el código va después. Cambiar código no reinstala
  dependencias.
- **Sin root.** Corre como el usuario `app` (uid 10001).
- **gunicorn**, no `runserver`, con 3 workers y access log a stdout.
- **Estáticos.** `collectstatic` corre en el build y WhiteNoise los sirve (solo
  los usa el admin; los templates del backoffice tienen el CSS inline).
- **Arranque.** `docker/backend-entrypoint.sh` aplica migraciones y, si
  `DJANGO_SEED_DEMO_DATA=1`, carga los datos de demo. Después ejecuta gunicorn
  con `exec`, así gunicorn recibe las señales de `docker stop`.
- **Healthcheck** contra `/accounts/login/`. El cliente espera a que el backend
  esté `healthy` antes de arrancar.

## Imagen del cliente

- Etapa `node:22-alpine` con `npm ci` (respeta `package-lock.json`) y
  `npm run build`, que también corre el chequeo de tipos.
- Etapa final `nginxinc/nginx-unprivileged` (no corre como root, escucha en
  8080) con solo los archivos de `dist/`.
- nginx hace proxy de `/api/` a `API_UPSTREAM` (`http://backend:8000`). El
  navegador ve un solo origen, así que Django no necesita CORS ni dependencias
  extra.
- Los assets con hash se cachean un año y `index.html` se revalida siempre.

## Base de datos

Se usa **SQLite** en el volumen `backend-data` (`/app/data/db.sqlite3`), que
sobrevive a `docker compose down` y `up`. Alcanza para la prueba, pero tiene
límites:

- Las escrituras se serializan; con muchos workers o tráfico real conviene
  PostgreSQL.
- `select_for_update` no bloquea filas en SQLite; la protección contra
  cancelaciones concurrentes funciona de verdad con PostgreSQL.
- No escala a más de una réplica del backend.

Pasar a PostgreSQL implicaría agregar un servicio `db` al compose, el driver
`psycopg` y leer la conexión desde una variable de entorno.

## En un despliegue real

- Las migraciones irían en un paso de release separado y no en el arranque de
  cada contenedor.
- `DJANGO_SEED_DEMO_DATA=0`.
- HTTPS en un proxy delante, con `SECURE_PROXY_SSL_HEADER` y cookies `Secure`.
