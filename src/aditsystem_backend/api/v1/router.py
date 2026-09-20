from fastapi import APIRouter

from aditsystem_backend.api.v1.endpoints import admin, auth, events, public_events
from aditsystem_backend.api.v1.endpoints.personas import router as personas_router

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(public_events.router)
api_router.include_router(events.router)
api_router.include_router(admin.router)
api_router.include_router(personas_router)
