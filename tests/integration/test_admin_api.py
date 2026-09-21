"""HTTP integration coverage for /api/v1/admin (auth account provisioning)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from helpers import (
    API_PREFIX,
    INTEGRATION_TEST_PASSWORD,
    SEED_ADMIN_EMAIL,
    SEED_ENLACE_EMAIL,
    bearer,
    login,
    persona_id_for,
)

API = API_PREFIX


async def _create_authenticable_persona(client: AsyncClient, admin_token: str) -> str:
    """Fresh COORDINADOR_GENERAL persona with no auth_users row yet."""
    response = await client.post(
        f"{API}/personas",
        json={
            "rol": "COORDINADOR_GENERAL",
            "parent_persona_id": None,
            "nombre": "Integracion",
            "apellido_paterno": "Admin",
            "apellido_materno": uuid4().hex[:8],
            "telefono": f"555{uuid4().int % 10_000_000:07d}",
        },
        headers=bearer(admin_token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_amigo_persona(client: AsyncClient, enlace_token: str, parent_id: str) -> str:
    response = await client.post(
        f"{API}/personas",
        json={
            "rol": "AMIGO",
            "parent_persona_id": parent_id,
            "nombre": "Amigo",
            "apellido_paterno": "Admin",
            "apellido_materno": uuid4().hex[:8],
            "telefono": f"555{uuid4().int % 10_000_000:07d}",
        },
        headers=bearer(enlace_token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_user_as_admin(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    persona_id = await _create_authenticable_persona(integration_client, admin_token)
    email = f"admin-created-{uuid4().hex[:8]}@example.com"

    response = await integration_client.post(
        f"{API}/admin/users",
        json={
            "email": email,
            "password": INTEGRATION_TEST_PASSWORD,
            "persona_id": persona_id,
        },
        headers=bearer(admin_token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == email
    assert body["persona_id"] == persona_id
    assert body["rol"] == "COORDINADOR_GENERAL"

    login_response = await integration_client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": INTEGRATION_TEST_PASSWORD},
    )
    assert login_response.status_code == 200, login_response.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_user_requires_authentication(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    persona_id = await _create_authenticable_persona(integration_client, admin_token)

    response = await integration_client.post(
        f"{API}/admin/users",
        json={
            "email": f"anon-{uuid4().hex[:8]}@example.com",
            "password": INTEGRATION_TEST_PASSWORD,
            "persona_id": persona_id,
        },
    )
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_user_forbidden_for_non_admin(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    persona_id = await _create_authenticable_persona(integration_client, admin_token)

    response = await integration_client.post(
        f"{API}/admin/users",
        json={
            "email": f"forbidden-{uuid4().hex[:8]}@example.com",
            "password": INTEGRATION_TEST_PASSWORD,
            "persona_id": persona_id,
        },
        headers=bearer(enlace_token),
    )
    assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_user_duplicate_email_conflicts(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    email = f"dup-{uuid4().hex[:8]}@example.com"
    first_persona_id = await _create_authenticable_persona(integration_client, admin_token)
    second_persona_id = await _create_authenticable_persona(integration_client, admin_token)

    first = await integration_client.post(
        f"{API}/admin/users",
        json={
            "email": email,
            "password": INTEGRATION_TEST_PASSWORD,
            "persona_id": first_persona_id,
        },
        headers=bearer(admin_token),
    )
    assert first.status_code == 201, first.text

    second = await integration_client.post(
        f"{API}/admin/users",
        json={
            "email": email,
            "password": INTEGRATION_TEST_PASSWORD,
            "persona_id": second_persona_id,
        },
        headers=bearer(admin_token),
    )
    assert second.status_code == 409


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_user_rejects_amigo_persona(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    enlace_id = await persona_id_for(SEED_ENLACE_EMAIL)
    amigo_id = await _create_amigo_persona(integration_client, enlace_token, str(enlace_id))

    response = await integration_client.post(
        f"{API}/admin/users",
        json={
            "email": f"amigo-{uuid4().hex[:8]}@example.com",
            "password": INTEGRATION_TEST_PASSWORD,
            "persona_id": amigo_id,
        },
        headers=bearer(admin_token),
    )
    assert response.status_code == 422
