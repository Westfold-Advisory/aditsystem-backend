"""HTTP integration coverage for /api/v1/personas and nested resources."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from helpers import (
    API_PREFIX,
    SEED_ADMIN_EMAIL,
    SEED_COORDINADOR_EMAIL,
    SEED_ENLACE_EMAIL,
    SEED_GENERAL_EMAIL,
    bearer,
    create_integration_geocerca,
    login,
    persona_id_for,
)

API = API_PREFIX


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_persona_as_admin(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)

    payload = {
        "rol": "COORDINADOR_GENERAL",
        "parent_persona_id": None,
        "nombre": "Integracion",
        "apellido_paterno": "Nueva",
        "apellido_materno": "General",
        "telefono": "5550199901",
        "email": "qa.tra138.cg.integracion@example.com",
        "password": "12345678",
    }
    response = await integration_client.post(
        f"{API}/personas",
        json=payload,
        headers=bearer(admin_token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["rol"] == "COORDINADOR_GENERAL"
    assert body["nombre"] == payload["nombre"]

    get_response = await integration_client.get(
        f"{API}/personas/{body['id']}",
        headers=bearer(admin_token),
    )
    assert get_response.status_code == 200
    assert get_response.json()["id"] == body["id"]

    await integration_client.delete(
        f"{API}/personas/{body['id']}",
        headers=bearer(admin_token),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_persona_forbidden_for_wrong_role(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    response = await integration_client.post(
        f"{API}/personas",
        json={
            "rol": "COORDINADOR_GENERAL",
            "parent_persona_id": None,
            "nombre": "No",
            "apellido_paterno": "Permitido",
            "apellido_materno": "Rama",
            "telefono": "5550199902",
            "email": "no.permitido@example.com",
            "password": "12345678",
        },
        headers=bearer(enlace_token),
    )
    assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_persona_validation_error(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    response = await integration_client.post(
        f"{API}/personas",
        json={
            "rol": "AMIGO",
            "nombre": "",
            "apellido_paterno": "X",
            "apellido_materno": "Y",
            "telefono": "1",
        },
        headers=bearer(admin_token),
    )
    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_persona_forbidden_on_sibling_branch(
    integration_client: AsyncClient,
) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    coordinador_token = await login(integration_client, SEED_COORDINADOR_EMAIL)

    general_id = await persona_id_for(SEED_GENERAL_EMAIL)

    denied = await integration_client.get(
        f"{API}/personas/{general_id}",
        headers=bearer(coordinador_token),
    )
    assert denied.status_code == 403

    allowed = await integration_client.get(
        f"{API}/personas/{general_id}",
        headers=bearer(admin_token),
    )
    assert allowed.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_persona_not_found(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    missing_id = str(uuid4())
    response = await integration_client.get(
        f"{API}/personas/{missing_id}",
        headers=bearer(admin_token),
    )
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_patch_and_soft_delete_persona(integration_client: AsyncClient) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    enlace_id = await persona_id_for(SEED_ENLACE_EMAIL)

    create = await integration_client.post(
        f"{API}/personas",
        json={
            "rol": "AMIGO",
            "parent_persona_id": str(enlace_id),
            "nombre": "Amigo",
            "apellido_paterno": "Integracion",
            "apellido_materno": "Baja",
            "telefono": "5550199903",
        },
        headers=bearer(enlace_token),
    )
    assert create.status_code == 201, create.text
    amigo_id = create.json()["id"]

    patch = await integration_client.patch(
        f"{API}/personas/{amigo_id}",
        json={"telefono": "5550199904"},
        headers=bearer(enlace_token),
    )
    assert patch.status_code == 200
    assert patch.json()["telefono"] == "5550199904"

    delete = await integration_client.delete(
        f"{API}/personas/{amigo_id}",
        headers=bearer(enlace_token),
    )
    assert delete.status_code == 204


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_descendants_and_metrics(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    general_id = await persona_id_for(SEED_GENERAL_EMAIL)

    descendants = await integration_client.get(
        f"{API}/personas/{general_id}/descendientes",
        headers=bearer(admin_token),
    )
    assert descendants.status_code == 200
    assert isinstance(descendants.json(), list)
    assert len(descendants.json()) >= 1

    metrics = await integration_client.get(
        f"{API}/personas/{general_id}/metricas",
        headers=bearer(admin_token),
    )
    assert metrics.status_code == 200
    data = metrics.json()
    assert "descendientes" in data
    assert data["descendientes"] >= len(descendants.json())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scoped_map_payload(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    general_id = await persona_id_for(SEED_GENERAL_EMAIL)

    response = await integration_client.get(
        f"{API}/personas/{general_id}/mapa",
        headers=bearer(admin_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["root_persona_id"] == str(general_id)
    assert isinstance(body["personas"], list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_persona_documentos_register_and_list(
    integration_client: AsyncClient,
) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    admin_id = await persona_id_for(SEED_ADMIN_EMAIL)

    register = await integration_client.post(
        f"{API}/personas/{admin_id}/documentos",
        json={
            "tipo": "OTRO",
            "titulo": "Documento integracion",
            "descripcion": "Metadatos de prueba",
            "s3_key": "integration/personas/doc-prueba.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 1024,
        },
        headers=bearer(admin_token),
    )
    assert register.status_code == 201, register.text

    listed = await integration_client.get(
        f"{API}/personas/{admin_id}/documentos",
        headers=bearer(admin_token),
    )
    assert listed.status_code == 200
    titles = [item["titulo"] for item in listed.json()]
    assert "Documento integracion" in titles

    document_id = register.json()["id"]
    download = await integration_client.get(
        f"{API}/personas/{admin_id}/documentos/{document_id}/descarga",
        headers=bearer(admin_token),
    )
    assert download.status_code == 503, download.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_persona_geocercas_assign_and_unassign(
    integration_client: AsyncClient,
) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    admin_id = await persona_id_for(SEED_ADMIN_EMAIL)

    geocerca_id = await create_integration_geocerca(f"INT-{uuid4().hex[:8]}")

    assign = await integration_client.post(
        f"{API}/personas/{admin_id}/geocercas",
        json={"geocerca_id": geocerca_id},
        headers=bearer(admin_token),
    )
    assert assign.status_code == 201, assign.text

    listed = await integration_client.get(
        f"{API}/personas/{admin_id}/geocercas",
        headers=bearer(admin_token),
    )
    assert listed.status_code == 200
    assert any(item["id"] == geocerca_id for item in listed.json())

    unassign = await integration_client.delete(
        f"{API}/personas/{admin_id}/geocercas/{geocerca_id}",
        headers=bearer(admin_token),
    )
    assert unassign.status_code == 204

    empty = await integration_client.get(
        f"{API}/personas/{admin_id}/geocercas",
        headers=bearer(admin_token),
    )
    assert all(item["id"] != geocerca_id for item in empty.json())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_patch_persona_forbidden_for_sibling(
    integration_client: AsyncClient,
) -> None:
    coordinador_token = await login(integration_client, SEED_COORDINADOR_EMAIL)
    general_id = await persona_id_for(SEED_GENERAL_EMAIL)

    response = await integration_client.patch(
        f"{API}/personas/{general_id}",
        json={"telefono": "5550000000"},
        headers=bearer(coordinador_token),
    )
    assert response.status_code == 403
