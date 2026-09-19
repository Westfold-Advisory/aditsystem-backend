from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import Base, TimestampedModel, UUIDPrimaryKey


class AuthUser(UUIDPrimaryKey, TimestampedModel, Base):
    __tablename__ = "auth_users"

    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    persona = relationship("Persona", back_populates="auth_user")
