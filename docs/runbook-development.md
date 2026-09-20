# Runbook de desarrollo: migración, seed y reset local

Este procedimiento aplica únicamente a una base local de Docker Compose. No
contiene comandos de borrado remoto y rechaza `APP_ENV=production`.

## Preparación y migración desde vacío

1. Copie `.env.compose.example` a `.env.compose`. Use sólo credenciales locales.
2. Genere las claves JWT locales descritas en el README.
3. Inicie la base y aplique el esquema: `docker compose --env-file .env.compose up --build -d db migrations`.
4. Confirme el resultado: `docker compose --env-file .env.compose run --rm migrations alembic current` debe informar la revisión `20260920_000008`.
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

## AWS development: plantillas SSM

Estas plantillas son para la EC2 del entorno **development**. En Systems
Manager use el documento `AWS-RunShellScript`, seleccione sólo la instancia
`aditsystem-dev-backend-instance` y guarde el resultado en CloudWatch. Nunca
pegue contraseñas, JSON de secretos ni valores de `runtime.env` en SSM.

### Preflight y snapshot (antes de un reset)

La operación debe tener un Change ID y un snapshot RDS disponible antes de
detener la API. Desde una sesión AWS con MFA y el perfil de development:

```bash
aws sts get-caller-identity
aws rds list-tags-for-resource --resource-name '<ARN_RDS_DEVELOPMENT>'
aws rds create-db-snapshot \
  --db-instance-identifier '<RDS_DEVELOPMENT_ID>' \
  --db-snapshot-identifier 'aditsystem-dev-pre-reset-YYYYMMDDHHMM'
aws rds wait db-snapshot-available \
  --db-snapshot-identifier 'aditsystem-dev-pre-reset-YYYYMMDDHHMM'
```

Confirme `Environment=dev`, que el identificador no contiene `prod` y que el
snapshot terminó antes de continuar. No use estas plantillas con otra cuenta,
otro identificador o producción.

### Detener escritor y verificar runtime en SSM

Pegar como comando SSM; no borra datos:

```bash
set -euo pipefail
test "${CONFIRM_ENVIRONMENT:-}" = development
test "${CONFIRM_RESET:-}" = RESET_DEVELOPMENT_DATA
test -f /opt/aditsystem/runtime.env
grep -qx 'APP_ENV=development' /opt/aditsystem/runtime.env
docker stop aditsystem-backend
```

Configure las variables SSM exactamente como `CONFIRM_ENVIRONMENT=development`
y `CONFIRM_RESET=RESET_DEVELOPMENT_DATA`. Si una guarda falla, el reset debe
abortarse. El borrado de RDS/esquema se ejecuta únicamente mediante una
automatización aprobada y versionada; no sustituya ese paso por `DROP SCHEMA`
manual.

### Recrear API y bootstrap ADMIN después del reset aprobado

1. Reejecute el pipeline de backend en `main` para que SSM aplique
   `alembic upgrade head` y arranque la imagen SHA.
2. Espere `GET /health` = 200.
3. Ejecute por SSM el bootstrap sin entregar la contraseña. Sustituya sólo el
   ARN/ID de Secrets Manager que termina en `/bootstrap-admin`:

```bash
set -euo pipefail
APP_DIR=/opt/aditsystem
IMAGE_URI="$(docker inspect --format '{{.Config.Image}}' aditsystem-backend)"
AWS_REGION="$(printf '%s' "$IMAGE_URI" | sed -E 's|^[^.]+\.dkr\.ecr\.([^.]+)\.amazonaws\.com/.*|\1|')"
grep -qx 'APP_ENV=development' "$APP_DIR/runtime.env"
docker run --rm --env-file "$APP_DIR/runtime.env" \
  -e "AWS_REGION=$AWS_REGION" -e "AWS_DEFAULT_REGION=$AWS_REGION" \
  -e BOOTSTRAP_EMAIL=eperez@ervic.pro \
  -e BOOTSTRAP_PASSWORD_SECRET_ID='<ARN_O_ID_BOOTSTRAP_ADMIN>' \
  -v "$APP_DIR/keys:/run/aditsystem/keys:ro" \
  "$IMAGE_URI" aditsystem-bootstrap-admin
curl --fail --silent http://127.0.0.1:8000/health
```

Si aparece `AccessDenied`, agregue al instance profile solamente
`secretsmanager:GetSecretValue` sobre el secreto bootstrap. Si aparece
`NoRegionError`, confirme que ambas variables de región están presentes.

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
