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
    gestor_id: Mapped[str | None] = mapped_column(ForeignKey("gestores.id"), unique=True)
    invitado_id: Mapped[str | None] = mapped_column(ForeignKey("invitados.id"), unique=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.INVITADO, nullable=False
    )

    created_events = relationship(
        "Event", back_populates="creator", foreign_keys="Event.created_by"
    )
    politico = relationship("Politico")
    gestor = relationship("Gestor")
    invitado = relationship("Invitado")
