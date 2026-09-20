from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

import httpx

from aditsystem_backend.core.config import Settings, get_settings
from aditsystem_backend.core.exceptions import DomainError

_MIN_REQUEST_INTERVAL_SECONDS = 1.1
_rate_lock = asyncio.Lock()
_last_request_at = 0.0


def format_persona_address(
    *,
    calle: str | None,
    numero_exterior: str | None,
    colonia: str | None,
    codigo_postal: str | None,
    entre_calles: str | None = None,
) -> str | None:
    if not calle or not calle.strip():
        return None
    street = calle.strip()
    if numero_exterior and numero_exterior.strip():
        street = f"{street} {numero_exterior.strip()}"
    segments = [street]
    if colonia and colonia.strip():
        segments.append(colonia.strip())
    if codigo_postal and codigo_postal.strip():
        segments.append(codigo_postal.strip())
    if entre_calles and entre_calles.strip():
        segments.append(f"Entre {entre_calles.strip()}")
    segments.append("México")
    return ", ".join(segments)


class NominatimGeocodingService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return self.settings.geocoding_enabled

    async def geocode(self, address: str) -> tuple[Decimal, Decimal]:
        if not self.enabled:
            raise DomainError("geocodificación deshabilitada", status_code=503)
        if not self.settings.nominatim_user_agent.strip():
            raise DomainError(
                "falta NOMINATIM_USER_AGENT para geocodificar (política de uso de OSM)",
                status_code=500,
            )

        await self._respect_rate_limit()
        url = urljoin(self.settings.nominatim_base_url.rstrip("/") + "/", "search")
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "countrycodes": self.settings.nominatim_country_codes,
        }
        headers = {"User-Agent": self.settings.nominatim_user_agent}

        try:
            async with httpx.AsyncClient(timeout=self.settings.nominatim_timeout_seconds) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                payload: list[dict[str, Any]] = response.json()
        except httpx.HTTPError as exc:
            raise DomainError(
                "no pudimos contactar el servicio de geocodificación",
                status_code=502,
            ) from exc

        if not payload:
            raise DomainError(
                "no encontramos coordenadas para la dirección capturada; revisa calle, colonia y CP",
                status_code=422,
            )

        first = payload[0]
        return Decimal(str(first["lat"])), Decimal(str(first["lon"]))

    async def _respect_rate_limit(self) -> None:
        global _last_request_at
        async with _rate_lock:
            now = time.monotonic()
            wait = _MIN_REQUEST_INTERVAL_SECONDS - (now - _last_request_at)
            if wait > 0:
                await asyncio.sleep(wait)
            _last_request_at = time.monotonic()
