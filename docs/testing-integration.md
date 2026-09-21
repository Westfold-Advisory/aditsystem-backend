# Tests de integración (API + Postgres)

Los tests marcados con `@pytest.mark.integration` ejercitan la aplicación FastAPI
contra una base **Postgres/PostGIS** real (mismo motor que Docker Compose).

La suite incluye humo (`test_smoke_api.py`) y cobertura HTTP por recurso:
**Personas** (`test_personas_api.py`: CRUD, descendientes, métricas, mapa,
documentos y geocercas anidadas), **Eventos** (`test_events_api.py`: CRUD,
ciclo de vida, invitaciones y check-in), **Auth** (`test_auth_api.py`:
`POST /login`, `GET /me`), **Admin** (`test_admin_api.py`:
`POST /admin/users`) y **Geocercas** (`test_geocercas_api.py`: list/get/
contains/create/delete). El fixture de sesión (`conftest.py` + `helpers.py`,
compartido por toda la suite) aplica migraciones, genera claves JWT locales
si faltan y ejecuta `seed_development` con contraseña de prueba fija (sólo en
entornos `local`/`development`).

**Nota — `login()` vs. `POST /login` real:** las cuentas de seed usan el
dominio `@aditsystem.test`, que `pydantic.EmailStr` rechaza como TLD
reservado (IANA/RFC 2606) en un body de request real. La mayoría de la suite
usa `helpers.login()`, que emite el JWT directamente (sin pasar por el
endpoint) para poder probar los recursos protegidos. `test_auth_api.py`
ejercita el contrato real de `POST /login` con cuentas creadas vía
`helpers.create_direct_login_account()` usando un dominio no reservado
(`@example.com`).

## Local

1. Levante la base y migraciones:

   ```bash
   docker compose --env-file .env.compose up --build -d db migrations
   ```

2. Genere claves JWT en `keys/` (ver README).

3. Ejecute integración:

   ```bash
   export RUN_INTEGRATION_TESTS=1
   export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/aditsystem
   pytest -m integration
   ```

Los tests unitarios siguen siendo la vía por defecto:

```bash
pytest -m "not integration"
```

## CI

El workflow `Backend CI` incluye el job **Integration tests (Postgres)** cuando
`RUN_INTEGRATION_TESTS=1` y el servicio PostGIS están configurados en
`.github/workflows/ci.yml`.

## Admins de equipo (development)

Tras migrar, puede provisionar cuentas ADMIN del equipo:

```bash
export TEAM_ADMIN_EMAILS='brandon.roldan.br2@gmail.com,ramirezmarco935@gmail.com,ascenddavid@gmail.com'
export BOOTSTRAP_PASSWORD='contraseña-no-versionada'
aditsystem-seed-team-admins
```

Vea `.env.team-admins.example`. Los correos **no** deben versionarse en código.
