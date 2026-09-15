from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from aditsystem_backend.api.v1.router import api_router
from aditsystem_backend.core.config import Settings, get_settings
from aditsystem_backend.core.exceptions import DomainError, to_http_exception


def build_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield

    _app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    @_app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        error = to_http_exception(exc)
        return JSONResponse(status_code=error.status_code, content={"detail": error.detail})

    @_app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    _app.include_router(api_router, prefix=settings.api_v1_prefix)

    return _app


app = build_app()


def run() -> None:
    uvicorn.run("aditsystem_backend.main:app", host="0.0.0.0", port=8000, reload=True)
