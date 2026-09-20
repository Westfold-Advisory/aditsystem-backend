# TRA-127 — Persona: dirección, coordenadas y necesidades

## Campos en `PersonaCreate` / `PersonaUpdate` / `PersonaRead`

| Campo | Tipo | Notas |
| --- | --- | --- |
| `calle` | string, opcional | Máx. 200 |
| `numero_exterior` | string, opcional | Máx. 30 |
| `numero_interior` | string, opcional | Máx. 30 |
| `colonia` | string, opcional | Máx. 120 |
| `codigo_postal` | string, opcional | Máx. 10 |
| `entre_calles` | string, opcional | Máx. 255 |
| `latitud` / `longitud` | decimal, opcional | Deben enviarse juntas; rango estándar |
| `necesidades_comunidad` | enum[], opcional | Máx. 3 valores únicos; catálogo `NecesidadComunidad` |

## Geocodificación (Nominatim / OpenStreetMap)

En **alta** o **actualización** de persona:

1. Si el cliente envía `latitud` y `longitud`, se respetan.
2. Si no, pero hay `calle` (y colonia o CP), el backend llama a **Nominatim** (`countrycodes=mx`) y persiste el resultado.
3. Si Nominatim no devuelve resultados → **422** con mensaje accionable.

Variables de entorno:

| Variable | Default | Uso |
| --- | --- | --- |
| `GEOCODING_ENABLED` | `true` | Desactivar en tests locales sin red |
| `NOMINATIM_BASE_URL` | `https://nominatim.openstreetmap.org` | Instancia self-hosted futura |
| `NOMINATIM_USER_AGENT` | placeholder | **Obligatorio** identificar la app (política OSM) |
| `NOMINATIM_COUNTRY_CODES` | `mx` | Acotar búsqueda |

El servicio público impone ~**1 solicitud/segundo**; el cliente backend serializa las llamadas. Para producción con muchos altas, planear instancia Nominatim propia o caché.

## Mapa de cobertura

`GET /api/v1/personas/{persona_id}/mapa/cobertura`

Parámetros:

- `grid_precision` (2–5, default 3): redondeo de lat/lng para celdas del heatmap (~111 m con 3 decimales).
- `necesidad` (opcional): filtra celdas del heatmap a un valor del catálogo.

Respuesta:

- `pines`: personas en el alcance jerárquico con coordenadas (para marcadores).
- `heatmap`: celdas agregadas `{ latitud, longitud, necesidad, intensidad }` — no lista cruda persona×necesidad.

El endpoint existente `GET .../mapa` incluye ahora `latitud`/`longitud` en cada entrada cuando existen.
