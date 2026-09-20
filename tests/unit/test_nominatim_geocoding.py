from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from aditsystem_backend.core.config import Settings
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.services.nominatim_geocoding import (
    NominatimGeocodingService,
    format_persona_address,
)


def test_format_persona_address_builds_mexico_query() -> None:
    line = format_persona_address(
        calle="Av. Juárez",
        numero_exterior="100",
        colonia="Centro",
        codigo_postal="72000",
    )
    assert line is not None
    assert "Av. Juárez 100" in line
    assert "México" in line


@pytest.mark.asyncio
async def test_geocode_returns_first_result() -> None:
    settings = Settings(
        geocoding_enabled=True,
        nominatim_user_agent="ADITSYSTEM-test/1.0 (test@example.com)",
    )
    service = NominatimGeocodingService(settings=settings)
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: [{"lat": "19.0433", "lon": "-98.2019"}]

    with patch(
        "aditsystem_backend.services.nominatim_geocoding.httpx.AsyncClient.get",
        new=AsyncMock(return_value=mock_response),
    ):
        lat, lon = await service.geocode("Av. Juárez, Puebla, México")

    assert lat == Decimal("19.0433")
    assert lon == Decimal("-98.2019")


@pytest.mark.asyncio
async def test_geocode_empty_results_422() -> None:
    settings = Settings(
        geocoding_enabled=True,
        nominatim_user_agent="ADITSYSTEM-test/1.0 (test@example.com)",
    )
    service = NominatimGeocodingService(settings=settings)
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: []

    with patch(
        "aditsystem_backend.services.nominatim_geocoding.httpx.AsyncClient.get",
        new=AsyncMock(return_value=mock_response),
    ):
        with pytest.raises(DomainError, match="no encontramos coordenadas"):
            await service.geocode("dirección inexistente xyz")
