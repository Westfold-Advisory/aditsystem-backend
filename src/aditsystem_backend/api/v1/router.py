from fastapi import APIRouter

from aditsystem_backend.api.v1.endpoints import admin, auth, events, public_events

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(events.router)
api_router.include_router(public_events.router)
api_router.include_router(admin.router)
