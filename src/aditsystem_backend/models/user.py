from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import Base, TimestampedModel, UUIDPrimaryKey
from aditsystem_backend.models.enums import UserRole


class User(UUIDPrimaryKey, TimestampedModel, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    politico_id: Mapped[str | None] = mapped_column(ForeignKey("politicos.id"), unique=True)
    lider_id: Mapped[str | None] = mapped_column(ForeignKey("lideres.id"), unique=True)
    invitado_id: Mapped[str | None] = mapped_column(ForeignKey("invitados.id"), unique=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.INVITADO, nullable=False
    )

    created_events = relationship(
        "Event", back_populates="creator", foreign_keys="Event.created_by"
    )
    politico = relationship("Politico")
    lider = relationship("Lider")
    invitado = relationship("Invitado")
