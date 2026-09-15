from fastapi import APIRouter, status

from aditsystem_backend.api.deps import CurrentUser, DBSession
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.exceptions import to_http_exception as to_http
from aditsystem_backend.schemas.auth import AdminUserCreate, UserRead
from aditsystem_backend.services.auth import AuthService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminUserCreate,
    session: DBSession,
    current_user: CurrentUser,
) -> UserRead:
    try:
        user = await AuthService(session).create_user(payload, current_user)
        return UserRead.model_validate(user)
    except DomainError as exc:
        raise to_http(exc) from exc
