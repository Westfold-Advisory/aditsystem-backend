from fastapi import APIRouter

from aditsystem_backend.api.v1.endpoints import admin, auth, events, public_events
from aditsystem_backend.api.v1.endpoints.documentos import router as documentos_router
from aditsystem_backend.api.v1.endpoints.invitados import router as invitados_router
from aditsystem_backend.api.v1.endpoints.lideres import router as lideres_router
from aditsystem_backend.api.v1.endpoints.politicos import router as politicos_router

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(events.router)
api_router.include_router(public_events.router)
api_router.include_router(admin.router)
api_router.include_router(politicos_router)
api_router.include_router(lideres_router)
api_router.include_router(invitados_router)
api_router.include_router(documentos_router)
