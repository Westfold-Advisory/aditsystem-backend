"""HTTP integration coverage for /api/v1/auth (login + current user).

Seed accounts (``login()`` in ``helpers.py``) mint JWTs directly because their
``@aditsystem.test`` emails are rejected by pydantic's ``EmailStr`` as a
reserved TLD on a real request body. These tests exercise the actual
``POST /login`` contract with accounts created via
``helpers.create_direct_login_account`` instead.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import DBAPIError

from aditsystem_backend.models.enums import PersonRole
from helpers import (
    API_PREFIX,
    INTEGRATION_TEST_PASSWORD,
    SEED_ADMIN_EMAIL,
    SEED_ENLACE_EMAIL,
    bearer,
    create_direct_login_account,
    login,
    persona_id_for,
)

API = f"{API_PREFIX}/auth"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_returns_token_for_valid_credentials(
    integration_client: AsyncClient,
) -> None:
    email = f"login-ok-{uuid4().hex[:8]}@example.com"
    await create_direct_login_account(email, INTEGRATION_TEST_PASSWORD, PersonRole.ADMIN)

    response = await integration_client.post(
        f"{API}/login",
        json={"email": email, "password": INTEGRATION_TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == email
    assert body["user"]["rol"] == "ADMIN"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_rejects_invalid_password(integration_client: AsyncClient) -> None:
    email = f"login-badpw-{uuid4().hex[:8]}@example.com"
    await create_direct_login_account(email, INTEGRATION_TEST_PASSWORD, PersonRole.ADMIN)

    response = await integration_client.post(
        f"{API}/login",
        json={"email": email, "password": "wrong-password"},
    )
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_rejects_unknown_email(integration_client: AsyncClient) -> None:
    response = await integration_client.post(
        f"{API}/login",
        json={
            "email": f"missing-{uuid4().hex[:8]}@example.com",
            "password": "whatever123",
        },
    )
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_amigo_persona_cannot_receive_auth_user_row(
    integration_client: AsyncClient,
) -> None:
    """AMIGO is deliberately excluded from AUTHENTICABLE_PERSON_ROLES.

    Enforcement is defense in depth: the admin API's 422 guard
    (test_admin_api.py::test_create_user_rejects_amigo_persona) is backed by
    a DB trigger (``reject_amigo_auth_user``, migration TRA-88) that refuses
    an ``auth_users`` row for any AMIGO persona at the schema level. That
    makes "AMIGO rechazado" on login structurally true — an AMIGO can never
    hold credentials to submit to POST /login in the first place.
    """
    enlace_id = await persona_id_for(SEED_ENLACE_EMAIL)

    with pytest.raises(DBAPIError, match="AMIGO no puede tener cuenta autenticable"):
        await create_direct_login_account(
            f"login-amigo-{uuid4().hex[:8]}@example.com",
            INTEGRATION_TEST_PASSWORD,
            PersonRole.AMIGO,
            parent_persona_id=str(enlace_id),
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_me_returns_current_user_for_valid_token(
    integration_client: AsyncClient,
) -> None:
    token = await login(integration_client, SEED_ADMIN_EMAIL)

    response = await integration_client.get(f"{API}/me", headers=bearer(token))
    assert response.status_code == 200, response.text
    assert response.json()["email"] == SEED_ADMIN_EMAIL
    assert response.json()["rol"] == "ADMIN"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_me_requires_authentication(integration_client: AsyncClient) -> None:
    response = await integration_client.get(f"{API}/me")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_me_rejects_invalid_token(integration_client: AsyncClient) -> None:
    response = await integration_client.get(
        f"{API}/me", headers=bearer("not-a-real-jwt")
    )
    assert response.status_code == 401
