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

## Admins de equipo (correos reales, development)

Provisiona cuentas ADMIN adicionales para el equipo operativo. Los correos se
configuran por entorno (no en código). Copie `.env.team-admins.example` a un
archivo local no versionado y exporte las variables antes de ejecutar:

```bash
export TEAM_ADMIN_EMAILS='brandon.roldan.br2@gmail.com,ramirezmarco935@gmail.com,ascenddavid@gmail.com'
export BOOTSTRAP_PASSWORD='cambie-esta-clave'
docker compose --env-file .env.compose run --rm api aditsystem-seed-team-admins
```

El comando es idempotente: cuentas ADMIN activas existentes se omiten.

### Admins de equipo en EC2 (development, AWS)

**No** forman parte del deploy automático (`scripts/deploy-ec2.sh` ni secrets de
GitHub Actions). El pipeline no lee `TEAM_ADMIN_EMAILS`; hay que ejecutar el seed
**una vez por SSM** después de un deploy saludable (`GET /health` = 200).

Hay dos formas de suministrar la lista de correos:

1. **Variable en la sesión SSM** (rápido): exporte `TEAM_ADMIN_EMAILS` en el
   comando, sin persistirla en la instancia.
2. **Secreto en Secrets Manager** (recomendado para repetir la operación): cree
   el contenedor del secreto (Terraform o consola) y guarde **solo** un JSON
   como valor, por ejemplo `aditsystem-dev/team-admin-emails`:

   ```json
   {"emails":"brandon.roldan.br2@gmail.com,ramirezmarco935@gmail.com,ascenddavid@gmail.com"}
   ```

   Conceda al instance profile de la EC2 `secretsmanager:GetSecretValue` sobre
   ese ARN. No suba este JSON a Git ni a variables del workflow.

La contraseña inicial reutiliza la misma política que el bootstrap:
`BOOTSTRAP_PASSWORD_SECRET_ID` (p. ej. el secreto existente `bootstrap-admin`, si
el JSON incluye `password`) o `BOOTSTRAP_PASSWORD` solo en la sesión SSM.

En **Session Manager** (o SSM Run Command) sobre la instancia backend, con la
imagen ya desplegada:

```bash
set -euo pipefail
export IMAGE_URI="$(docker inspect --format '{{.Config.Image}}' aditsystem-backend)"
export AWS_REGION="$(printf '%s' "$IMAGE_URI" | sed -E 's|^[^.]+\.dkr\.ecr\.([^.]+)\.amazonaws.com/.*|\1|')"
export AWS_DEFAULT_REGION="$AWS_REGION"

# Opción A — correos en la sesión (no los persista en disco):
export TEAM_ADMIN_EMAILS='brandon.roldan.br2@gmail.com,ramirezmarco935@gmail.com,ascenddavid@gmail.com'

# Opción B — leer lista desde Secrets Manager (recomendado):
# export TEAM_ADMIN_EMAILS_SECRET_ID='aditsystem-dev/team-admin-emails'

export BOOTSTRAP_PASSWORD_SECRET_ID='aditsystem-dev/bootstrap-admin'
bash /opt/aditsystem/seed-team-admins-development-ec2.sh
```

Copie `scripts/seed-team-admins-development-ec2.sh` del repositorio a
`/opt/aditsystem/` en la instancia (una vez) si prefiere el wrapper frente al
`docker run` directo. Equivalente mínimo (sin archivo extra en la EC2):

```bash
docker run --rm --env-file /opt/aditsystem/runtime.env \
  -e "AWS_REGION=$AWS_REGION" -e "AWS_DEFAULT_REGION=$AWS_REGION" \
  -e TEAM_ADMIN_EMAILS='brandon.roldan.br2@gmail.com,ramirezmarco935@gmail.com,ascenddavid@gmail.com' \
  -e BOOTSTRAP_PASSWORD_SECRET_ID='aditsystem-dev/bootstrap-admin' \
  -v /opt/aditsystem/keys:/run/aditsystem/keys:ro \
  "$IMAGE_URI" aditsystem-seed-team-admins
```

Crear el valor del secreto de correos (una vez, consola o CLI autorizada):

```bash
aws secretsmanager create-secret \
  --region mx-central-1 \
  --name aditsystem-dev/team-admin-emails \
  --secret-string '{"emails":"brandon.roldan.br2@gmail.com,ramirezmarco935@gmail.com,ascenddavid@gmail.com"}'
```

(Si el nombre ya existe, use `put-secret-value` en lugar de `create-secret`.)

Verifique login: `POST /api/v1/auth/login` con cada correo.

## Reset local explícito

Operación destructiva local:

```bash
./scripts/reset-local-db.sh --confirm-local-reset
docker compose --env-file .env.compose up --build
```

El script exige confirmación literal, `.env.compose` con `APP_ENV=local`, y
rechaza una `DATABASE_URL` externa. Sólo elimina los volúmenes administrados
por el Compose de este repositorio. No lo ejecute fuera del directorio raíz.

## Límites del reset remoto

El reset remoto sólo existe para **development** y nunca forma parte del
pipeline normal. Requiere solicitud de cambio aprobada, snapshot verificable,
MFA/break-glass, validación de cuenta/tags de development y ejecución por SSM
dentro de la VPC. Producción queda expresamente fuera de alcance.

En GitHub Actions el workflow **Development database reset** sólo admite
`workflow_dispatch`, exige el environment protegido `development`, la
confirmación literal `RESET_DEVELOPMENT_DATA` y un `change_id`. No se ejecuta
en merges ni en pushes a `main`.

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

### Reset de esquema en SSM

Este bloque borra todo el esquema `public` de la base configurada en la EC2 y
lo reconstruye con Alembic. No lo ejecute hasta que el snapshot anterior esté
disponible. Requiere una imagen desplegada que incluya
`aditsystem-reset-development`.

En Systems Manager use `AWS-RunShellScript`, seleccione sólo
`aditsystem-dev-backend-instance`, sustituya únicamente `CHG-XXXX` por el ID
de cambio y pegue el bloque completo:

```bash
set -euo pipefail

APP_DIR=/opt/aditsystem
CONTAINER=aditsystem-backend
RESET_CHANGE_ID='CHG-XXXX'

test -f "$APP_DIR/runtime.env"
grep -qx 'APP_ENV=development' "$APP_DIR/runtime.env"
docker inspect "$CONTAINER" >/dev/null

# Muestra sólo el hostname RDS, nunca el DATABASE_URL ni sus credenciales.
RESET_DATABASE_HOST="$(python3 - "$APP_DIR/runtime.env" <<'PY'
from pathlib import Path
from urllib.parse import urlsplit

for line in Path(__import__('sys').argv[1]).read_text().splitlines():
    if line.startswith('DATABASE_URL='):
        print(urlsplit(line.split('=', 1)[1]).hostname)
        break
else:
    raise SystemExit('DATABASE_URL is missing from runtime.env')
PY
)"

case "$RESET_DATABASE_HOST" in
  *.rds.amazonaws.com) ;;
  *) echo 'Reset rejected: expected an RDS hostname.' >&2; exit 2 ;;
esac
case "$RESET_DATABASE_HOST" in
  *prod*) echo 'Reset rejected: production-like hostname.' >&2; exit 2 ;;
esac

IMAGE_URI="$(docker inspect --format '{{.Config.Image}}' "$CONTAINER")"
docker stop "$CONTAINER"

if ! docker run --rm --env-file "$APP_DIR/runtime.env" \
  -e RESET_CONFIRMATION=RESET_DEVELOPMENT_DATA \
  -e "RESET_DATABASE_HOST=$RESET_DATABASE_HOST" \
  -e "RESET_CHANGE_ID=$RESET_CHANGE_ID" \
  "$IMAGE_URI" aditsystem-reset-development; then
  echo 'Reset or guards failed; API remains stopped. Restore the verified snapshot if needed.' >&2
  exit 1
fi

docker run --rm --env-file "$APP_DIR/runtime.env" \
  -v "$APP_DIR/keys:/run/aditsystem/keys:ro" \
  "$IMAGE_URI" alembic upgrade head
docker start "$CONTAINER"
curl --fail --silent http://127.0.0.1:8000/health
echo
echo 'Development reset, migrations and API health check completed.'
```

Las guardas deben abortar si el runtime no es development, el host no es RDS,
el host parece producción, el host no coincide exactamente con `DATABASE_URL`,
falta el Change ID o la confirmación literal. Si falla el reset o Alembic, la
API queda detenida; restaure el snapshot verificado antes de reiniciarla. No
use este bloque para otra instancia, otro entorno ni producción.

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
