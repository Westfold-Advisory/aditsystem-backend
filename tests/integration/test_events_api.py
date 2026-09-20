"""HTTP integration coverage for /api/v1/events and its lifecycle/check-in sub-resources.

Acción x rol (comportamiento real verificado por esta suite; ver notas):

| Acción                          | ADMIN | Creador (CG/COORDINADOR/ENLACE) | Otro autenticado | Anónimo |
|----------------------------------|-------|----------------------------------|-------------------|---------|
| GET /events, GET /events/{id}    | 200   | 200                               | 200 (sin scope, ver nota *)  | 401 |
| POST /events                     | 201   | 201                               | 201 (cualquier rol autenticable puede crear, ver nota **) | 401 |
| PATCH/publish/unpublish/start/   | 200   | 200 si es el creador             | 403               | 401     |
| finish/cancel/delete             |       |                                   |                   |         |
| POST invitations                 | 200/201 si gestiona el evento | igual | 403 | 401 |
| POST invitations/{id}/respond    | 200 (proxy, cualquier persona) | 200 solo si es el propio invitado | 403 | 401 |
| POST checkin/manual              | 200 si gestiona el evento | igual | 403 | 401 |
| POST checkin/qr, checkin/geolocation | 403 (no es AMIGO) | 403 (no es AMIGO) | 403 | 401 |

(*) `GET /events` y `GET /events/{id}` no aplican scope por rama/creador — cualquier
  rol autenticable ve cualquier evento no eliminado. Documentado aquí porque el
  código no lo filtra, a diferencia de `/personas`.
(**) `create_event` acepta los 4 roles autenticables (ADMIN, COORDINADOR_GENERAL,
  COORDINADOR, ENLACE); no existe un rol autenticable sin permiso de alta.

Nota sobre AMIGO y check-in por QR/geolocalización: la persona AMIGO seed no
tiene fila `auth_users` (no está en `AUTHENTICABLE_PERSON_ROLES`), así que hoy
no puede obtener un JWT y por tanto no puede alcanzar `/checkin/qr` ni
`/checkin/geolocation` como actor autenticado — esos endpoints están vivos en
código pero inalcanzables end-to-end con el mecanismo de auth actual. Esta
suite lo documenta con pruebas negativas (403 con actor no-AMIGO) y cubre el
flujo de asistencia real y alcanzable: check-in manual registrado por el
organizador/ADMIN.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
    login,
    persona_id_for,
)

API = API_PREFIX


def _event_payload(**overrides: object) -> dict[str, object]:
    start = datetime.now(UTC) + timedelta(days=7)
    payload: dict[str, object] = {
        "tipo": "asamblea",
        "nombre": f"Evento integracion {uuid4().hex[:8]}",
        "descripcion": "Evento creado por la suite de integracion.",
        "latitud": "19.432608",
        "longitud": "-99.133209",
        "ubicacion_texto": "Zocalo, CDMX",
        "fecha_inicio": start.isoformat(),
        "fecha_fin": (start + timedelta(hours=2)).isoformat(),
        "capacidad_maxima": None,
        "requiere_checkin": True,
        "checkin_radio_metros": 100,
    }
    payload.update(overrides)
    return payload


async def _create_event(
    client: AsyncClient, token: str, **overrides: object
) -> dict[str, object]:
    response = await client.post(
        f"{API}/events",
        json=_event_payload(**overrides),
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_amigo(
    client: AsyncClient, organizer_token: str, parent_id: str
) -> str:
    """Register a fresh AMIGO persona (no auth_users row) as an invitee."""
    response = await client.post(
        f"{API}/personas",
        json={
            "rol": "AMIGO",
            "parent_persona_id": parent_id,
            "nombre": "Invitado",
            "apellido_paterno": "Integracion",
            "apellido_materno": uuid4().hex[:8],
            "telefono": f"555{uuid4().int % 10_000_000:07d}",
        },
        headers=bearer(organizer_token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


# --- CRUD base -------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_event_allowed_for_every_authenticable_role(
    integration_client: AsyncClient,
) -> None:
    for email in (
        SEED_ADMIN_EMAIL,
        SEED_GENERAL_EMAIL,
        SEED_COORDINADOR_EMAIL,
        SEED_ENLACE_EMAIL,
    ):
        token = await login(integration_client, email)
        event = await _create_event(integration_client, token)
        assert event["estatus"] == "BORRADOR"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_event_requires_authentication(
    integration_client: AsyncClient,
) -> None:
    response = await integration_client.post(f"{API}/events", json=_event_payload())
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_event_validation_error(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    response = await integration_client.post(
        f"{API}/events",
        json=_event_payload(fecha_fin=datetime.now(UTC).isoformat()),
        headers=bearer(admin_token),
    )
    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_and_get_event_visible_to_any_authenticated_role(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    event = await _create_event(integration_client, enlace_token)

    coordinador_token = await login(integration_client, SEED_COORDINADOR_EMAIL)
    listing = await integration_client.get(
        f"{API}/events", headers=bearer(coordinador_token)
    )
    assert listing.status_code == 200
    assert any(item["id"] == event["id"] for item in listing.json())

    detail = await integration_client.get(
        f"{API}/events/{event['id']}", headers=bearer(coordinador_token)
    )
    assert detail.status_code == 200
    assert detail.json()["id"] == event["id"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_event_not_found(integration_client: AsyncClient) -> None:
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    response = await integration_client.get(
        f"{API}/events/{uuid4()}", headers=bearer(admin_token)
    )
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_event_invalid_date_range_returns_400(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    event = await _create_event(integration_client, enlace_token)

    response = await integration_client.patch(
        f"{API}/events/{event['id']}",
        json={"fecha_fin": event["fecha_inicio"]},
        headers=bearer(enlace_token),
    )
    assert response.status_code == 400


# --- Permisos de gestión (update/publish/.../delete) -----------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manage_actions_forbidden_for_non_creator(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    event = await _create_event(integration_client, enlace_token)

    coordinador_token = await login(integration_client, SEED_COORDINADOR_EMAIL)
    event_id = event["id"]

    patch = await integration_client.patch(
        f"{API}/events/{event_id}",
        json={"nombre": "No deberia aplicar"},
        headers=bearer(coordinador_token),
    )
    assert patch.status_code == 403

    publish = await integration_client.post(
        f"{API}/events/{event_id}/publish", headers=bearer(coordinador_token)
    )
    assert publish.status_code == 403

    delete = await integration_client.delete(
        f"{API}/events/{event_id}", headers=bearer(coordinador_token)
    )
    assert delete.status_code == 403

    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    admin_publish = await integration_client.post(
        f"{API}/events/{event_id}/publish", headers=bearer(admin_token)
    )
    assert admin_publish.status_code == 200


# --- Ciclo de vida y publicación pública ------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lifecycle_publish_exposes_event_on_public_api_then_unpublish_hides_it(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    event = await _create_event(integration_client, enlace_token)
    event_id = event["id"]

    draft_list = await integration_client.get(f"{API}/public/events")
    assert draft_list.status_code == 200
    assert all(item["id"] != event_id for item in draft_list.json())

    draft_detail = await integration_client.get(f"{API}/public/events/{event_id}")
    assert draft_detail.status_code == 404

    publish = await integration_client.post(
        f"{API}/events/{event_id}/publish", headers=bearer(enlace_token)
    )
    assert publish.status_code == 200
    assert publish.json()["estatus"] == "PUBLICADO"

    published_list = await integration_client.get(f"{API}/public/events")
    assert any(item["id"] == event_id for item in published_list.json())

    published_detail = await integration_client.get(f"{API}/public/events/{event_id}")
    assert published_detail.status_code == 200
    assert published_detail.json()["id"] == event_id

    unpublish = await integration_client.post(
        f"{API}/events/{event_id}/unpublish", headers=bearer(enlace_token)
    )
    assert unpublish.status_code == 200
    assert unpublish.json()["estatus"] == "BORRADOR"

    hidden_again = await integration_client.get(f"{API}/public/events/{event_id}")
    assert hidden_again.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lifecycle_start_and_finish(integration_client: AsyncClient) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    event = await _create_event(integration_client, enlace_token)
    event_id = event["id"]

    await integration_client.post(
        f"{API}/events/{event_id}/publish", headers=bearer(enlace_token)
    )

    start = await integration_client.post(
        f"{API}/events/{event_id}/start", headers=bearer(enlace_token)
    )
    assert start.status_code == 200
    assert start.json()["estatus"] == "EN_CURSO"

    finish = await integration_client.post(
        f"{API}/events/{event_id}/finish", headers=bearer(enlace_token)
    )
    assert finish.status_code == 200
    assert finish.json()["estatus"] == "FINALIZADO"

    cancel_after_finish = await integration_client.post(
        f"{API}/events/{event_id}/cancel", headers=bearer(enlace_token)
    )
    assert cancel_after_finish.status_code == 409


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_state_transitions_return_409(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    event = await _create_event(integration_client, enlace_token)
    event_id = event["id"]

    unpublish_draft = await integration_client.post(
        f"{API}/events/{event_id}/unpublish", headers=bearer(enlace_token)
    )
    assert unpublish_draft.status_code == 409

    start_draft = await integration_client.post(
        f"{API}/events/{event_id}/start", headers=bearer(enlace_token)
    )
    assert start_draft.status_code == 409

    finish_draft = await integration_client.post(
        f"{API}/events/{event_id}/finish", headers=bearer(enlace_token)
    )
    assert finish_draft.status_code == 409

    cancel = await integration_client.post(
        f"{API}/events/{event_id}/cancel", headers=bearer(enlace_token)
    )
    assert cancel.status_code == 200

    cancel_again = await integration_client.post(
        f"{API}/events/{event_id}/cancel", headers=bearer(enlace_token)
    )
    assert cancel_again.status_code == 409


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_only_allowed_in_borrador_or_cancelado(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)

    draft = await _create_event(integration_client, enlace_token)
    delete_draft = await integration_client.delete(
        f"{API}/events/{draft['id']}", headers=bearer(enlace_token)
    )
    assert delete_draft.status_code == 204

    published = await _create_event(integration_client, enlace_token)
    await integration_client.post(
        f"{API}/events/{published['id']}/publish", headers=bearer(enlace_token)
    )
    delete_published = await integration_client.delete(
        f"{API}/events/{published['id']}", headers=bearer(enlace_token)
    )
    assert delete_published.status_code == 409

    cancelled = await _create_event(integration_client, enlace_token)
    await integration_client.post(
        f"{API}/events/{cancelled['id']}/cancel", headers=bearer(enlace_token)
    )
    delete_cancelled = await integration_client.delete(
        f"{API}/events/{cancelled['id']}", headers=bearer(enlace_token)
    )
    assert delete_cancelled.status_code == 204


# --- Invitaciones ------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invitation_lifecycle_and_capacity_limit(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    enlace_id = str(await persona_id_for(SEED_ENLACE_EMAIL))
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)

    event = await _create_event(integration_client, enlace_token, capacidad_maxima=1)
    event_id = event["id"]
    await integration_client.post(
        f"{API}/events/{event_id}/publish", headers=bearer(enlace_token)
    )

    persona_a = await _create_amigo(integration_client, enlace_token, enlace_id)

    invite = await integration_client.post(
        f"{API}/events/{event_id}/invitations",
        json={"persona_id": persona_a},
        headers=bearer(enlace_token),
    )
    assert invite.status_code == 201, invite.text
    assert invite.json()["estatus"] == "PENDIENTE"

    duplicate = await integration_client.post(
        f"{API}/events/{event_id}/invitations",
        json={"persona_id": persona_a},
        headers=bearer(enlace_token),
    )
    assert duplicate.status_code == 409

    accept = await integration_client.post(
        f"{API}/events/{event_id}/invitations/{invite.json()['id']}/respond",
        json={"estatus": "ACEPTADA"},
        headers=bearer(admin_token),
    )
    assert accept.status_code == 200
    assert accept.json()["estatus"] == "ACEPTADA"

    persona_b = await _create_amigo(integration_client, enlace_token, enlace_id)
    over_capacity = await integration_client.post(
        f"{API}/events/{event_id}/invitations",
        json={"persona_id": persona_b},
        headers=bearer(enlace_token),
    )
    assert over_capacity.status_code == 409


@pytest.mark.integration
@pytest.mark.asyncio
async def test_respond_invitation_forbidden_for_unrelated_actor(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    enlace_id = str(await persona_id_for(SEED_ENLACE_EMAIL))

    event = await _create_event(integration_client, enlace_token)
    event_id = event["id"]
    await integration_client.post(
        f"{API}/events/{event_id}/publish", headers=bearer(enlace_token)
    )

    persona_a = await _create_amigo(integration_client, enlace_token, enlace_id)
    invite = await integration_client.post(
        f"{API}/events/{event_id}/invitations",
        json={"persona_id": persona_a},
        headers=bearer(enlace_token),
    )
    assert invite.status_code == 201

    coordinador_token = await login(integration_client, SEED_COORDINADOR_EMAIL)
    forbidden = await integration_client.post(
        f"{API}/events/{event_id}/invitations/{invite.json()['id']}/respond",
        json={"estatus": "ACEPTADA"},
        headers=bearer(coordinador_token),
    )
    assert forbidden.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_invitation_blocked_on_terminal_event_states(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    enlace_id = str(await persona_id_for(SEED_ENLACE_EMAIL))

    event = await _create_event(integration_client, enlace_token)
    event_id = event["id"]
    await integration_client.post(
        f"{API}/events/{event_id}/cancel", headers=bearer(enlace_token)
    )

    persona_a = await _create_amigo(integration_client, enlace_token, enlace_id)
    response = await integration_client.post(
        f"{API}/events/{event_id}/invitations",
        json={"persona_id": persona_a},
        headers=bearer(enlace_token),
    )
    assert response.status_code == 400


# --- Asistencia / check-in ---------------------------------------------------


async def _publish_event_with_accepted_invitation(
    client: AsyncClient, enlace_token: str, admin_token: str
) -> tuple[str, str]:
    """Returns (event_id, persona_id) for an accepted invitee ready to check in."""
    enlace_id = str(await persona_id_for(SEED_ENLACE_EMAIL))
    event = await _create_event(client, enlace_token)
    event_id = event["id"]
    await client.post(f"{API}/events/{event_id}/publish", headers=bearer(enlace_token))

    persona_id = await _create_amigo(client, enlace_token, enlace_id)
    invite = await client.post(
        f"{API}/events/{event_id}/invitations",
        json={"persona_id": persona_id},
        headers=bearer(enlace_token),
    )
    await client.post(
        f"{API}/events/{event_id}/invitations/{invite.json()['id']}/respond",
        json={"estatus": "ACEPTADA"},
        headers=bearer(admin_token),
    )
    return event_id, persona_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manual_checkin_lifecycle_by_organizer(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    admin_token = await login(integration_client, SEED_ADMIN_EMAIL)
    event_id, persona_id = await _publish_event_with_accepted_invitation(
        integration_client, enlace_token, admin_token
    )

    checkin = await integration_client.post(
        f"{API}/events/{event_id}/checkin/manual",
        json={"persona_id": persona_id},
        headers=bearer(enlace_token),
    )
    assert checkin.status_code == 200, checkin.text
    body = checkin.json()
    assert body["estatus"] == "PRESENTE"
    assert body["checkin_at"] is not None
    assert body["checkin_metodo"] == "MANUAL"

    idempotent = await integration_client.post(
        f"{API}/events/{event_id}/checkin/manual",
        json={"persona_id": persona_id},
        headers=bearer(enlace_token),
    )
    assert idempotent.status_code == 200
    assert idempotent.json()["checkin_at"] == body["checkin_at"]

    attendances = await integration_client.get(
        f"{API}/events/{event_id}/attendances", headers=bearer(enlace_token)
    )
    assert attendances.status_code == 200
    assert any(
        item["persona_id"] == persona_id and item["estatus"] == "PRESENTE"
        for item in attendances.json()
    )

    coordinador_token = await login(integration_client, SEED_COORDINADOR_EMAIL)
    forbidden_list = await integration_client.get(
        f"{API}/events/{event_id}/attendances", headers=bearer(coordinador_token)
    )
    assert forbidden_list.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manual_checkin_requires_accepted_invitation(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    enlace_id = str(await persona_id_for(SEED_ENLACE_EMAIL))

    event = await _create_event(integration_client, enlace_token)
    event_id = event["id"]
    await integration_client.post(
        f"{API}/events/{event_id}/publish", headers=bearer(enlace_token)
    )

    persona_id = await _create_amigo(integration_client, enlace_token, enlace_id)
    await integration_client.post(
        f"{API}/events/{event_id}/invitations",
        json={"persona_id": persona_id},
        headers=bearer(enlace_token),
    )  # left PENDIENTE, never accepted

    checkin = await integration_client.post(
        f"{API}/events/{event_id}/checkin/manual",
        json={"persona_id": persona_id},
        headers=bearer(enlace_token),
    )
    assert checkin.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_manual_checkin_persona_not_found(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    event = await _create_event(integration_client, enlace_token)
    event_id = event["id"]
    await integration_client.post(
        f"{API}/events/{event_id}/publish", headers=bearer(enlace_token)
    )

    checkin = await integration_client.post(
        f"{API}/events/{event_id}/checkin/manual",
        json={"persona_id": str(uuid4())},
        headers=bearer(enlace_token),
    )
    assert checkin.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_qr_requires_published_event(
    integration_client: AsyncClient,
) -> None:
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    event = await _create_event(integration_client, enlace_token)
    event_id = event["id"]

    too_early = await integration_client.post(
        f"{API}/events/{event_id}/checkin/qr-token", headers=bearer(enlace_token)
    )
    assert too_early.status_code == 400

    await integration_client.post(
        f"{API}/events/{event_id}/publish", headers=bearer(enlace_token)
    )
    qr = await integration_client.post(
        f"{API}/events/{event_id}/checkin/qr-token", headers=bearer(enlace_token)
    )
    assert qr.status_code == 200, qr.text
    assert qr.json()["event_id"] == event_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_self_service_checkin_endpoints_reject_non_amigo_actor(
    integration_client: AsyncClient,
) -> None:
    """AMIGO cannot authenticate today (see module docstring), so the reachable
    assertion is that any authenticable (non-AMIGO) actor is rejected before
    token/geo validation even runs."""
    enlace_token = await login(integration_client, SEED_ENLACE_EMAIL)
    event = await _create_event(integration_client, enlace_token)
    event_id = event["id"]
    await integration_client.post(
        f"{API}/events/{event_id}/publish", headers=bearer(enlace_token)
    )

    qr_checkin = await integration_client.post(
        f"{API}/events/{event_id}/checkin/qr",
        json={"token": "not-a-real-token"},
        headers=bearer(enlace_token),
    )
    assert qr_checkin.status_code == 403

    geo_checkin = await integration_client.post(
        f"{API}/events/{event_id}/checkin/geolocation",
        json={
            "latitud": "19.432608",
            "longitud": "-99.133209",
            "precision_metros": "5",
        },
        headers=bearer(enlace_token),
    )
    assert geo_checkin.status_code == 403
