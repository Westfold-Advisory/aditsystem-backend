import pytest
from httpx import ASGITransport, AsyncClient

from aditsystem_backend.core.config import Settings
from aditsystem_backend.main import build_app


def _app_with_origins(*origins: str):
    settings = Settings(cors_allowed_origins=list(origins), cors_allow_credentials=True)
    return build_app(settings)


def test_cors_csv_environment_values_are_parsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001"
    )
    monkeypatch.setenv("CORS_ALLOW_METHODS", "GET,POST,OPTIONS")
    monkeypatch.setenv("CORS_ALLOW_HEADERS", "Authorization,Content-Type")

    settings = Settings()

    assert settings.cors_allowed_origins == ["http://localhost:3000", "http://localhost:3001"]
    assert settings.cors_allow_methods == ["GET", "POST", "OPTIONS"]
    assert settings.cors_allow_headers == ["Authorization", "Content-Type"]


@pytest.mark.asyncio
async def test_allowed_origin_returns_acao_header() -> None:
    app = _app_with_origins("http://localhost:3000")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_disallowed_origin_omits_acao_header() -> None:
    app = _app_with_origins("http://localhost:3000")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/health", headers={"Origin": "http://evil.example.com"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_preflight_allowed_origin_returns_200() -> None:
    app = _app_with_origins("http://localhost:3000")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_no_wildcard_when_credentials_enabled() -> None:
    app = _app_with_origins("http://localhost:3000")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/health", headers={"Origin": "http://localhost:3000"})

    acao = response.headers.get("access-control-allow-origin", "")
    assert acao != "*", "Wildcard origin must not be used when credentials are enabled"


@pytest.mark.asyncio
async def test_multiple_allowed_origins() -> None:
    s3_origin = "http://my-bucket.s3-website-us-east-1.amazonaws.com"
    app = _app_with_origins("http://localhost:3000", s3_origin)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        r1 = await client.get("/health", headers={"Origin": "http://localhost:3000"})
        r2 = await client.get("/health", headers={"Origin": s3_origin})

    assert r1.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert r2.headers.get("access-control-allow-origin") == s3_origin
