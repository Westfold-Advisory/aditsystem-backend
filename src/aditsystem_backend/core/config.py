from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def jwt_private_key(self) -> str:
        return self.jwt_private_key_path.read_text(encoding="utf-8")

    @property
    def jwt_public_key(self) -> str:
        return self.jwt_public_key_path.read_text(encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
