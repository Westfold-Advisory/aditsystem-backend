from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.exceptions import DomainError, to_http_exception
from aditsystem_backend.core.security import decode_access_token
from aditsystem_backend.db.session import get_db_session
from aditsystem_backend.models.user import User
from aditsystem_backend.repositories.user import UserRepository

bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    bearerFormat="JWT",
    description="JWT emitido por POST /api/v1/auth/login.",
    auto_error=False,
)

DBSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    session: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token requerido")

    try:
        payload = decode_access_token(credentials.credentials)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token inválido") from exc

    user = await UserRepository(session).get_by_id(str(payload.sub))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="usuario no encontrado")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_request_ip(x_forwarded_for: Annotated[str | None, Header()] = None) -> str | None:
    if not x_forwarded_for:
        return None
    return x_forwarded_for.split(",")[0].strip()


def raise_domain_error(error: DomainError) -> None:
    raise to_http_exception(error)
