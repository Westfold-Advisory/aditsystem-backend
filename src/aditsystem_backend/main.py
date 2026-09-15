from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from aditsystem_backend.api.v1.router import api_router
from aditsystem_backend.core.config import get_settings
from aditsystem_backend.core.exceptions import DomainError, to_http_exception

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.exception_handler(DomainError)
async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
    error = to_http_exception(exc)
    return JSONResponse(status_code=error.status_code, content={"detail": error.detail})


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_v1_prefix)


def run() -> None:
    uvicorn.run("aditsystem_backend.main:app", host="0.0.0.0", port=8000, reload=True)
