# Prueba técnica full stack: backoffice + API cliente

Starter repo para evaluar criterio full stack con foco principal en Django.

## Stack

- Django 5.2
- Django templates para backoffice
- Django Ninja para API cliente
- Pydantic v2 para contratos y errores del API
- pytest + factory_boy

## Dominio

El dominio es ficticio y está basado en reservas:

- `Customer`
- `Room`
- `Reservation`

## Flujo de la prueba

El assessment tiene dos partes:

1. Extender el backoffice Django con una transición nueva de reservas.
2. Construir una mini app cliente en `client-app/` para consumir el API.
3. Dockerizar la solución completa.

La consigna completa está en [ASSESSMENT.md](./ASSESSMENT.md).
El contrato base del API está en [API_CONTRACT.md](./API_CONTRACT.md).

## Docker

```bash
cp .env.example .env   # y completar DJANGO_SECRET_KEY
docker compose up --build
```

- Mini app cliente: [http://localhost:8080](http://localhost:8080)
- Backoffice: [http://localhost:8000/backoffice/reservations/](http://localhost:8000/backoffice/reservations/)

Detalle de imágenes, variables de entorno y decisiones en [DOCKER.md](./DOCKER.md).
La mini app también se puede correr sin Docker: ver
[client-app/README.md](./client-app/README.md).

## Setup

```bash
uv sync
uv run python src/manage.py migrate
uv run python src/manage.py seed_assessment_data
uv run python src/manage.py runserver
```

## URLs útiles

- Backoffice login: [http://127.0.0.1:8000/accounts/login/](http://127.0.0.1:8000/accounts/login/)
- Backoffice reservas: [http://127.0.0.1:8000/backoffice/reservations/](http://127.0.0.1:8000/backoffice/reservations/)
- API base: [http://127.0.0.1:8000/api/v1/](http://127.0.0.1:8000/api/v1/)

## Checks mínimos

```bash
PYTHONPATH=src uv run pytest
uv run ruff check .
```

## Credenciales semilla

Se crean con `seed_assessment_data`:

- Staff manager
  - username: `manager`
  - password: `demo1234`
- Staff operator
  - username: `operator`
  - password: `demo1234`
- Cliente Alice
  - email: `alice@example.com`
  - password: `demo1234`
- Cliente Bob
  - email: `bob@example.com`
  - password: `demo1234`
