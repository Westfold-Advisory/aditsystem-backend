# E2E jerárquico local (TRA-91)

Flujo reproducible sobre Docker Compose local. No ejecuta reset remoto ni toca AWS.

## Requisitos

- `.env.compose` derivado de `.env.compose.example` con `APP_ENV=local`
- Claves JWT locales en `keys/` según README
- `BOOTSTRAP_PASSWORD` no versionada (el script usa un valor de ejemplo si no se exporta)

## Ejecución

```bash
chmod +x scripts/e2e-hierarchy-local.sh
BOOTSTRAP_PASSWORD='cambie-esta-clave' ./scripts/e2e-hierarchy-local.sh
```

### Datos masivos opcionales (TRA-120)

Tras el seed mínimo del script E2E (o en un entorno local ya migrado):

```bash
BOOTSTRAP_PASSWORD='cambie-esta-clave' docker compose --env-file .env.compose run --rm api \
  aditsystem-seed-faker --export-json faker-seed-accounts.json --export-accounts
```

Use el JSON generado para escenarios con listas, filtros y paginación. Véase
`docs/runbook-development.md` para modos `--append` y `--fresh-subtree`.

## Qué valida

1. Reset local deliberado (`reset-local-db.sh --confirm-local-reset`)
2. Migraciones Alembic y seed de development
3. Login encadenado ADMIN → Coordinador General → Coordinador → Enlace
4. Métricas y mapa scoped (`GET /personas/{id}/metricas`, `GET /personas/{id}/mapa`)
5. Registro de documento (metadata de foto) bajo Enlace
6. Rechazo 403 al consultar una rama hermana
7. AMIGO sin credenciales (login rechazado)

El reset de AWS development permanece en `docs/runbook-development.md` y sólo se dispara manualmente con el workflow `Development database reset` (`workflow_dispatch`), confirmación literal y environment protegido.
