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

# Install the application before copying runtime sources so dependency layers are
# reusable when only application code changes.
COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY alembic ./alembic
RUN pip install --no-cache-dir . \
    && addgroup --system app \
    && adduser --system --ingroup app --home /app app \
    && chown -R app:app /app

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=2).read()" || exit 1

CMD ["uvicorn", "aditsystem_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
