from fastapi import APIRouter, status

from aditsystem_backend.api.deps import CurrentUser, DBSession
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.exceptions import to_http_exception as to_http
from aditsystem_backend.schemas.auth import AuthUserCreate, AuthUserRead
from aditsystem_backend.services.auth import AuthService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users", response_model=AuthUserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AuthUserCreate,
    session: DBSession,
    current_user: CurrentUser,
) -> AuthUserRead:
    try:
        user = await AuthService(session).create_user(payload, current_user)
        return AuthUserRead(
            id=user.id, email=user.email, persona_id=user.persona_id,
            rol=user.persona.rol, is_active=user.is_active,
            created_at=user.created_at, updated_at=user.updated_at,
        )
    except DomainError as exc:
        raise to_http(exc) from exc
