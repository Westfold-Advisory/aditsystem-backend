from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ADITSYSTEM Backend"
    app_env: str = "local"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/aditsystem"
    )

    jwt_private_key_path: Path = Path("./keys/jwt-private.pem")
    jwt_public_key_path: Path = Path("./keys/jwt-public.pem")
    jwt_algorithm: str = "RS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_issuer: str = "aditsystem-backend"
    jwt_audience: str = "aditsystem-clients"

    event_qr_issuer: str = "aditsystem-event-qr"
    event_qr_audience: str = "aditsystem-event-scanner"
    event_qr_ttl_seconds: int = 120

    default_checkin_radius_meters: int = 100
    max_allowed_geo_precision_meters: int = 100

    # CORS — set via comma-separated env var, e.g.:
    # CORS_ALLOWED_ORIGINS=http://localhost:3000,https://aditsystem.ervic.pro
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    cors_allow_credentials: bool = True
    cors_allow_methods: Annotated[list[str], NoDecode] = Field(
        default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )
    cors_allow_headers: Annotated[list[str], NoDecode] = Field(
        default=["Authorization", "Content-Type"]
    )

    @field_validator(
        "cors_allowed_origins",
        "cors_allow_methods",
        "cors_allow_headers",
        mode="before",
    )
    @classmethod
    def _parse_comma_list(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def jwt_private_key(self) -> str:
        return self.jwt_private_key_path.read_text(encoding="utf-8")

    @property
    def jwt_public_key(self) -> str:
        return self.jwt_public_key_path.read_text(encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
