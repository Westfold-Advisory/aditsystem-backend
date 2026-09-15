# Arquitectura del Proyecto

## Stack

- Python 3.12+
- FastAPI
- SQLAlchemy 2 async
- PostgreSQL + PostGIS
- Alembic
- Pydantic v2
- JWT propio con RS256
- Pytest + HTTPX

## Estructura

```text
aditsystem-backend/
  alembic/                    # Migraciones de base de datos
  docs/                       # Documentación funcional y técnica
  src/aditsystem_backend/
    api/                      # Ruteo y dependencias FastAPI
    core/                     # Configuración, seguridad, excepciones
    db/                       # Base declarativa y sesión async
    models/                   # Modelos SQLAlchemy
    repositories/             # Acceso a datos
    schemas/                  # DTOs Pydantic
    services/                 # Reglas de negocio
    main.py                   # Aplicación FastAPI
  tests/                      # Tests unitarios
```

## Modelo de negocio

- `POLITICO` administra su estructura política.
- `LIDER` depende de un `POLITICO` (antes llamado `GESTOR`).
- `INVITADO` depende de un `LIDER`.
- `ADMIN` es un rol transversal de plataforma.

La autenticación se resuelve en `users`, pero la información detallada vive en `politicos`, `lideres` e `invitados`.

## Módulo de eventos

1. Un `POLITICO`, `LIDER` o `ADMIN` crea un evento.
2. El responsable genera invitaciones para entidades `INVITADO`.
3. El invitado responde la invitación desde su cuenta enlazada.
4. Si la invitación queda `ACEPTADA`, se habilita el check-in.
5. El check-in puede hacerse por QR, geolocalización o manualmente.
6. Cada check-in actualiza `event_attendances` y evita duplicados.

## Flujo por capas

1. `api/` recibe requests y serializa responses.
2. `schemas/` valida payloads de entrada y salida.
3. `services/` ejecuta reglas de negocio y transacciones.
4. `repositories/` encapsula consultas SQLAlchemy.
5. `models/` define persistencia y relaciones.

## Seguridad

- Acceso con JWT de sesión firmado con RS256.
- Tokens QR temporales independientes de la sesión.
- La identidad se resuelve desde `users`.
- La autorización se evalúa en servicios.
- Las invitaciones y asistencias operan sobre `invitados`, no sobre usuarios genéricos.

## Reglas críticas

- Solo `POLITICO`, `LIDER` o `ADMIN` crean eventos e invitaciones.
- Un `INVITADO` necesita una cuenta ligada mediante `users.invitado_id`.
- Solo un invitado con invitación `ACEPTADA` puede hacer check-in.
- El evento debe estar `PUBLICADO` o `EN_CURSO`.
- El check-in se valida dentro de la ventana permitida.
- No se permiten check-ins duplicados.
- La distancia se calcula en backend con PostGIS.

## OpenAPI

FastAPI expone:

- `/docs`
- `/redoc`
- `${API_V1_PREFIX}/openapi.json`
