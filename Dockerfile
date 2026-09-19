# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Upgrade OS packages so fixed CVEs (including libpcre2) are not shipped downstream.
RUN apt-get update \
    && apt-get upgrade --no-install-recommends -y \
    && rm -rf /var/lib/apt/lists/*

# Install runtime dependencies before copying application source so this expensive
# layer is reused whenever only source files change (cache invalidated by pyproject.toml).
COPY pyproject.toml README.md alembic.ini ./
RUN pip install --no-cache-dir \
      $(python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(' '.join(d['project']['dependencies']))")

# Copy source after dependencies so changes to src/ skip the dep-download layer.
COPY src ./src
COPY alembic ./alembic

# Install the package itself without re-downloading its dependencies.
RUN pip install --no-cache-dir --no-deps . \
    && addgroup --system --gid 10001 app \
    && adduser --system --uid 10001 --ingroup app --home /app app \
    && chown -R app:app /app

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=2).read()" || exit 1

CMD ["uvicorn", "aditsystem_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
