import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_integration(integration_client) -> None:
    response = await integration_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_public_events_list_empty_database(integration_client) -> None:
    response = await integration_client.get("/api/v1/public/events")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
