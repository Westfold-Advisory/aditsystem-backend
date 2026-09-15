from fastapi import APIRouter, status

from aditsystem_backend.api.deps import CurrentUser, DBSession
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.exceptions import to_http_exception as to_http
from aditsystem_backend.schemas.auth import TokenResponse, UserCreate, UserLogin, UserRead
from aditsystem_backend.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate, session: DBSession) -> UserRead:
    try:
        user = await AuthService(session).register(payload)
        return UserRead.model_validate(user)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, session: DBSession) -> TokenResponse:
    try:
        return await AuthService(session).login(payload.email, payload.password)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.get("/me", response_model=UserRead)
async def read_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
