# Tests de integración (API + Postgres)

Los tests marcados con `@pytest.mark.integration` ejercitan la aplicación FastAPI
contra una base **Postgres/PostGIS** real (mismo motor que Docker Compose).

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
