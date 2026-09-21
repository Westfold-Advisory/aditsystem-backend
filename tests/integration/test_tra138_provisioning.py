"""TRA-138: RBAC provisioning, atomic credentials, password change."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from helpers import (
    API_PREFIX,
    SEED_ADMIN_EMAIL,
    SEED_COORDINADOR_EMAIL,
    SEED_ENLACE_EMAIL,
    SEED_GENERAL_EMAIL,
    bearer,
    login,
    persona_id_for,
)

API = API_PREFIX


async def login_with_password(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_authenticable_requires_min_password_length(
    integration_client: AsyncClient,
) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    response = await integration_client.post(
        f"{API}/personas",
        json={
            "rol": "ENLACE",
            "parent_persona_id": str(await persona_id_for(SEED_COORDINADOR_EMAIL)),
            "nombre": "Enlace",
            "apellido_paterno": "Pwd",
            "apellido_materno": "Corta",
            "telefono": "5550100101",
            "email": "qa.tra138.pwd7@example.com",
            "password": "1234567",
        },
        headers=bearer(admin_token),
    )
    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_atomic_provision_and_login(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    email = "qa.tra138.enlace.atomic@example.com"
    password = "12345678"
    coordinador_id = await persona_id_for(SEED_COORDINADOR_EMAIL)

    create = await integration_client.post(
        f"{API}/personas",
        json={
            "rol": "ENLACE",
            "parent_persona_id": str(coordinador_id),
            "nombre": "Enlace",
            "apellido_paterno": "Atomic",
            "apellido_materno": "Provision",
            "telefono": "5550100102",
            "email": email,
            "password": password,
        },
        headers=bearer(admin_token),
    )
    assert create.status_code == 201, create.text
    persona_id = create.json()["id"]

    token = await login_with_password(integration_client, email, password)
    assert token

    await integration_client.delete(f"{API}/personas/{persona_id}", headers=bearer(admin_token))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_general_coordinator_creates_enlace_under_coordinador(
    integration_client: AsyncClient,
) -> None:
    general_token = await login(integration_client, SEED_GENERAL_EMAIL)
    coordinador_id = await persona_id_for(SEED_COORDINADOR_EMAIL)
    email = "qa.tra138.enlace.cg@example.com"

    create = await integration_client.post(
        f"{API}/personas",
        json={
            "rol": "ENLACE",
            "parent_persona_id": str(coordinador_id),
            "nombre": "Enlace",
            "apellido_paterno": "Bajo",
            "apellido_materno": "Coord",
            "telefono": "5550100103",
            "email": email,
            "password": "12345678",
        },
        headers=bearer(general_token),
    )
    assert create.status_code == 201, create.text
    persona_id = create.json()["id"]
    await integration_client.delete(f"{API}/personas/{persona_id}", headers=bearer(general_token))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_password_rejects_short_password(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    enlace_id = await persona_id_for(SEED_ENLACE_EMAIL)

    response = await integration_client.put(
        f"{API}/personas/{enlace_id}/credenciales/contrasena",
        json={"new_password": "1234567"},
        headers=bearer(admin_token),
    )
    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_password_and_login(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    email = "qa.tra138.chpwd@example.com"
    coordinador_id = await persona_id_for(SEED_COORDINADOR_EMAIL)

    create = await integration_client.post(
        f"{API}/personas",
        json={
            "rol": "ENLACE",
            "parent_persona_id": str(coordinador_id),
            "nombre": "Enlace",
            "apellido_paterno": "Change",
            "apellido_materno": "Pwd",
            "telefono": "5550100104",
            "email": email,
            "password": "12345678",
        },
        headers=bearer(admin_token),
    )
    assert create.status_code == 201, create.text
    persona_id = create.json()["id"]

    update = await integration_client.put(
        f"{API}/personas/{persona_id}/credenciales/contrasena",
        json={"new_password": "87654321"},
        headers=bearer(admin_token),
    )
    assert update.status_code == 204

    assert await login_with_password(integration_client, email, "87654321")

    await integration_client.delete(f"{API}/personas/{persona_id}", headers=bearer(admin_token))
