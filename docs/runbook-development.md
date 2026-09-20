# Runbook de desarrollo: migración, seed y reset local

Este procedimiento aplica únicamente a una base local de Docker Compose. No
contiene comandos de borrado remoto y rechaza `APP_ENV=production`.

## Preparación y migración desde vacío

1. Copie `.env.compose.example` a `.env.compose`. Use sólo credenciales locales.
2. Genere las claves JWT locales descritas en el README.
3. Inicie la base y aplique el esquema: `docker compose --env-file .env.compose up --build -d db migrations`.
4. Confirme el resultado: `docker compose --env-file .env.compose run --rm migrations alembic current` debe informar la revisión `20260920_000007`.
5. Ejecute el seed con una contraseña no versionada: `BOOTSTRAP_PASSWORD='cambie-esta-clave' docker compose --env-file .env.compose run --rm api aditsystem-seed-development`.

El seed usa nombres, teléfonos y dominios reservados ficticios. Crea ADMIN,
COORDINADOR_GENERAL, COORDINADOR y ENLACE autenticables, más un AMIGO sin fila
en `auth_users`. Es idempotente y aborta ante un email existente incompatible.

## Reset local explícito

Operación destructiva local:

```bash
./scripts/reset-local-db.sh --confirm-local-reset
docker compose --env-file .env.compose up --build
```

El script exige confirmación literal, `.env.compose` con `APP_ENV=local`, y
rechaza una `DATABASE_URL` externa. Sólo elimina los volúmenes administrados
por el Compose de este repositorio. No lo ejecute fuera del directorio raíz.

## Prohibición de reset remoto/producción

No hay script ni pipeline de reset para development remoto o producción. Toda
operación remota requiere una solicitud de cambio aprobada, snapshot verificable,
MFA/break-glass, validación de cuenta y tags de development, y ejecución por
SSM dentro de la VPC. Producción queda expresamente fuera de alcance.

## Verificación de seguridad y contrato

Antes de entregar un cambio ejecute:

```bash
ruff check --ignore E501,S104,S105,S106,I001,F401,ASYNC250 .
pytest
alembic upgrade head
```

En `local`/`development`, revise `/api/v1/openapi.json`: debe declarar Bearer
JWT y no debe contener `/auth/register`. En producción, `/api/v1/docs`,
`/api/v1/redoc` y `/api/v1/openapi.json` deben responder 404.
