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
docker compose down --volumes
```

Si `migrations` falla, consulte `docker compose logs migrations`; normalmente
indica que PostgreSQL aún no está listo o que existe un volumen creado con un
esquema incompatible. Si la API no arranca, confirme que ambos PEM existen en
`keys/` y que el puerto configurado en `API_PORT` está libre.

## CI y publicación

En cada PR hacia `main`, GitHub Actions ejecuta Ruff, Pytest, build para x86_64 y Trivy. Después de un merge a `main`, el workflow de publicación usa GitHub OIDC y el environment `development` para publicar en ECR. Configure en ese environment las variables no secretas `AWS_DEPLOY_ROLE_ARN`, `AWS_REGION` y `AWS_ECR_REPOSITORY`, y proteja el environment con aprobación según la política del equipo.

Las imágenes se etiquetan de forma inmutable como `sha-<commit completo>` y trazable como `main-<commit corto>`.
