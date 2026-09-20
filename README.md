# ADITSYSTEM Backend

API FastAPI de ADITSYSTEM. Requiere Python 3.12 y PostgreSQL/PostGIS para los flujos que acceden a datos.

## Desarrollo local

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn aditsystem_backend.main:app --reload
```

La aplicación escucha en `http://localhost:8000`; la comprobación de vida está en `GET /health`.

## Documentación OpenAPI

En `local` y `development` se publica la documentación interactiva en
`/api/v1/docs`, ReDoc en `/api/v1/redoc` y el contrato en
`/api/v1/openapi.json`. Swagger incluye el esquema HTTP Bearer/JWT: obtenga un
token con `POST /api/v1/auth/login` y péguelo en **Authorize** (sin añadir el
prefijo `Bearer`). Sólo ADMIN, COORDINADOR_GENERAL, COORDINADOR y ENLACE pueden
tener cuenta; AMIGO no tiene contraseña, registro ni inicio de sesión.

En `production` estas tres rutas no se exponen, incluso si
`ENABLE_API_DOCS=true`; el endpoint de salud y la API continúan disponibles.
Para habilitar documentación en un entorno no productivo distinto de `local` o
`development`, establezca explícitamente `ENABLE_API_DOCS=true`. Nunca use esa
variable para producción.

La configuración se lee desde variables de entorno (o un `.env` local que nunca se versiona). Para autenticación, proporcione rutas a claves privadas/públicas mediante `JWT_PRIVATE_KEY_PATH` y `JWT_PUBLIC_KEY_PATH`; las claves no se incorporan en la imagen.

## Contenedor

La imagen se construye para `linux/amd64` y se ejecuta sin privilegios como el usuario `app`:

```bash
docker build --platform linux/amd64 -t aditsystem-backend:local .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL='postgresql+asyncpg://USER:PASSWORD@HOST:5432/aditsystem' \
  aditsystem-backend:local
curl http://localhost:8000/health
```

Monte o inyecte las claves JWT de forma segura en tiempo de ejecución. No use `--build-arg`, imágenes ni repositorios para secretos.

## Docker Compose local

El entorno local inicia PostgreSQL 16 con PostGIS en un volumen nombrado,
aplica las migraciones Alembic y, sólo si éstas terminan correctamente, inicia la
API. Requiere Docker Compose v2.

```bash
cp .env.compose.example .env.compose
mkdir -p keys
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out keys/jwt-private.pem
openssl rsa -pubout -in keys/jwt-private.pem -out keys/jwt-public.pem
docker compose --env-file .env.compose up --build
```

Compruebe la API en otra terminal:

```bash
curl http://localhost:8000/health
```

Las claves se montan de sólo lectura desde `keys/`, que está ignorado por Git y
por el contexto de construcción. `.env.compose` también está ignorado: use sólo
valores locales y nunca copie secretos de otros entornos. El servicio `migrations`
puede finalizar con éxito; la API continúa ejecutándose.

Para detener el entorno, use `docker compose down`. Para detenerlo y reiniciar
la base local (operación destructiva), use:

```bash
./scripts/reset-local-db.sh --confirm-local-reset
```

El script sólo permite `APP_ENV=local`, exige la confirmación literal y rechaza
una URL de base de datos externa. El procedimiento completo de migración, seed
ficticio y controles de operación está en `docs/runbook-development.md`.

Si `migrations` falla, consulte `docker compose logs migrations`; normalmente
indica que PostgreSQL aún no está listo o que existe un volumen creado con un
esquema incompatible. Si la API no arranca, confirme que ambos PEM existen en
`keys/` y que el puerto configurado en `API_PORT` está libre.

## CI y publicación

En cada PR hacia `main`, GitHub Actions ejecuta Ruff, Pytest, build para x86_64 y Trivy. Después de un merge a `main`, el workflow de publicación usa GitHub OIDC y el environment `development` para publicar en ECR. Configure en ese environment las variables no secretas `AWS_DEPLOY_ROLE_ARN`, `AWS_REGION` y `AWS_ECR_REPOSITORY`, y proteja el environment con aprobación según la política del equipo. Mientras falte alguna, el job de publicación se omite de forma segura; Terraform debe crear el rol y ECR antes de habilitarlo.

Las imágenes se etiquetan de forma inmutable como `sha-<commit completo>` y trazable como `main-<commit corto>`.

Cuando también estén configuradas `AWS_EC2_INSTANCE_ID`, `AWS_RUNTIME_SECRET_ARN` y `AWS_DB_SECRET_ARN`, el mismo workflow despliega la etiqueta SHA por SSM en la EC2 creada por Terraform. Ejecuta migraciones antes de reemplazar el contenedor y verifica `/health`; no usa SSH ni entrega secretos a GitHub.

El bootstrap de ADMIN es una operación SSM posterior y explícita, nunca parte
del deploy ni del seed. Consulte `docs/bootstrap_admin.md`; requiere el ARN/ID
del secreto Terraform existente `bootstrap-admin` y permisos mínimos del
instance profile para leerlo.

El secret de runtime de Secrets Manager debe ser JSON y contener `jwt_private_key`, `jwt_public_key`, `database_name` y `cors_allowed_origins`. La contraseña RDS se lee del secret administrado por RDS. Ambos secretos sólo se consultan desde el instance profile de la EC2.
