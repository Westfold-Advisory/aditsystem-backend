# ADITSYSTEM Backend

Backend de ADITSYSTEM implementado con:

- Python 3.12+
- FastAPI
- PostgreSQL + PostGIS
- SQLAlchemy 2 async
- Alembic
- Pydantic v2
- JWT propio con RS256

## Objetivo del módulo actual

El repositorio incluye un módulo backend para:

- gestión de roles `POLITICO`, `GESTOR`, `INVITADO` y `ADMIN`
- gestión de eventos
- invitaciones a eventos
- confirmación/rechazo de asistencia
- check-in por QR
- check-in por geolocalización
- check-in manual por organizador o administrador

## Requisitos locales

- Python 3.12+
- PostgreSQL 16+ con PostGIS
- claves RSA para JWT

## Configuración rápida

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Levanta PostgreSQL con PostGIS local. Un ejemplo rápido con Docker:

```bash
docker run --name aditsystem-postgis \
  -e POSTGRES_DB=aditsystem \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -d postgis/postgis:16-3.4
```

Genera un par RSA para JWT:

```bash
mkdir -p keys
openssl genrsa -out keys/jwt-private.pem 2048
openssl rsa -in keys/jwt-private.pem -pubout -out keys/jwt-public.pem
```

## Migraciones

```bash
alembic upgrade head
```

## Ejecución local

```bash
uvicorn aditsystem_backend.main:app --reload
```

Documentación:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Tests

```bash
pytest
```

Pruebas mínimas de calidad:

```bash
python3 -m compileall src tests
ruff check .
```

## Documentación técnica

- [Arquitectura](docs/architecture.md)
- [Base de datos](docs/database.md)

## Estructura del proyecto

```text
src/aditsystem_backend/
  api/
  core/
  db/
  models/
  repositories/
  schemas/
  services/
  main.py
alembic/
docs/
tests/
```
