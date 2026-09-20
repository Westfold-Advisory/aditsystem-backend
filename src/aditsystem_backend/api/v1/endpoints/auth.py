from fastapi import APIRouter

from aditsystem_backend.api.deps import CurrentUser, DBSession
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.exceptions import to_http_exception as to_http
from aditsystem_backend.schemas.auth import AuthUserRead, TokenResponse, UserLogin
from aditsystem_backend.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, session: DBSession) -> TokenResponse:
    try:
        return await AuthService(session).login(payload.email, payload.password)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.get("/me", response_model=AuthUserRead)
async def read_me(current_user: CurrentUser) -> AuthUserRead:
    return AuthUserRead(
        id=current_user.id,
        email=current_user.email,
        persona_id=current_user.persona_id,
        rol=current_user.persona.rol,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )
