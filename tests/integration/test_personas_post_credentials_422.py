"""POST /personas — 422 matrix for credentials (TRA-138 / AC-PWD-02)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from helpers import (
    API_PREFIX,
    SEED_ADMIN_EMAIL,
    SEED_COORDINADOR_EMAIL,
    SEED_ENLACE_EMAIL,
    bearer,
    login,
    persona_id_for,
)

API = API_PREFIX

ENLACE_BASE = {
    "rol": "ENLACE",
    "nombre": "QA",
    "apellido_paterno": "Post",
    "apellido_materno": "Personas",
    "telefono": "5550100199",
}

AMIGO_BASE = {
    "rol": "AMIGO",
    "nombre": "QA",
    "apellido_paterno": "Amigo",
    "apellido_materno": "SinCuenta",
    "telefono": "5550100198",
}


@pytest.fixture
async def admin_headers(integration_client: AsyncClient) -> dict[str, str]:
    token = await login(integration_client, SEED_ADMIN_EMAIL)
    return bearer(token)


@pytest.fixture
async def enlace_parent_id() -> str:
    return str(await persona_id_for(SEED_COORDINADOR_EMAIL))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_enlace_missing_email_and_password_422(
    integration_client: AsyncClient, admin_headers: dict[str, str], enlace_parent_id: str
) -> None:
    response = await integration_client.post(
        f"{API}/personas",
        json={**ENLACE_BASE, "parent_persona_id": enlace_parent_id},
        headers=admin_headers,
    )
    assert response.status_code == 422, response.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_enlace_email_without_password_422(
    integration_client: AsyncClient, admin_headers: dict[str, str], enlace_parent_id: str
) -> None:
    response = await integration_client.post(
        f"{API}/personas",
        json={
            **ENLACE_BASE,
            "parent_persona_id": enlace_parent_id,
            "email": "qa.missing.pwd@example.com",
        },
        headers=admin_headers,
    )
    assert response.status_code == 422, response.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_enlace_password_too_short_422(
    integration_client: AsyncClient, admin_headers: dict[str, str], enlace_parent_id: str
) -> None:
    response = await integration_client.post(
        f"{API}/personas",
        json={
            **ENLACE_BASE,
            "parent_persona_id": enlace_parent_id,
            "email": "qa.pwd7@example.com",
            "password": "1234567",
        },
        headers=admin_headers,
    )
    assert response.status_code == 422, response.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_enlace_valid_credentials_201(
    integration_client: AsyncClient, admin_headers: dict[str, str], enlace_parent_id: str
) -> None:
    response = await integration_client.post(
        f"{API}/personas",
        json={
            **ENLACE_BASE,
            "parent_persona_id": enlace_parent_id,
            "email": "qa.enlace.valid@example.com",
            "password": "12345678",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    persona_id = response.json()["id"]
    await integration_client.delete(f"{API}/personas/{persona_id}", headers=admin_headers)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_amigo_with_credentials_422(
    integration_client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    enlace_id = str(await persona_id_for(SEED_ENLACE_EMAIL))
    response = await integration_client.post(
        f"{API}/personas",
        json={
            **AMIGO_BASE,
            "parent_persona_id": enlace_id,
            "email": "qa.amigo.bad@example.com",
            "password": "12345678",
        },
        headers=admin_headers,
    )
    assert response.status_code == 422, response.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_amigo_without_credentials_201(
    integration_client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    enlace_id = str(await persona_id_for(SEED_ENLACE_EMAIL))
    response = await integration_client.post(
        f"{API}/personas",
        json={**AMIGO_BASE, "parent_persona_id": enlace_id},
        headers=bearer(enlace_token),
    )
    assert response.status_code == 201, response.text
    persona_id = response.json()["id"]
    await integration_client.delete(
        f"{API}/personas/{persona_id}", headers=bearer(enlace_token)
    )
