import pytest
from httpx import ASGITransport, AsyncClient

from aditsystem_backend.core.config import Settings
from aditsystem_backend.main import build_app


@pytest.mark.asyncio
@pytest.mark.parametrize("environment", ["local", "development"])
async def test_docs_are_exposed_in_standard_non_production_environments(
    environment: str,
) -> None:
    app = build_app(Settings(app_env=environment))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for path in ("/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json"):
            response = await client.get(path)
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_docs_can_be_enabled_in_an_explicit_non_production_environment() -> None:
    app = build_app(Settings(app_env="qa", enable_api_docs=True))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/openapi.json")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_docs_are_not_exposed_in_production_even_if_explicitly_enabled() -> None:
    app = build_app(Settings(app_env="production", enable_api_docs=True))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for path in ("/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json"):
            response = await client.get(path)
            assert response.status_code == 404

        health = await client.get("/health")

    assert health.status_code == 200


@pytest.mark.asyncio
async def test_openapi_declares_http_bearer_jwt_for_protected_routes() -> None:
    app = build_app(Settings(app_env="local"))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/openapi.json")

    document = response.json()
    assert document["components"]["securitySchemes"]["BearerAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT emitido por POST /api/v1/auth/login.",
    }
    assert document["paths"]["/api/v1/personas/{persona_id}"]["get"]["security"] == [
        {"BearerAuth": []}
    ]
    assert "/api/v1/auth/register" not in document["paths"]
    assert document["paths"]["/api/v1/events"]["post"]["security"] == [{"BearerAuth": []}]


@pytest.mark.asyncio
async def test_protected_route_still_rejects_missing_or_invalid_bearer_tokens() -> None:
    app = build_app(Settings(app_env="local"))
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        missing = await client.get("/api/v1/auth/me")
        invalid = await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"}
        )

    assert missing.status_code == 401
    assert invalid.status_code == 401
