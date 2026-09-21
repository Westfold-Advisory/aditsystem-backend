from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.enums import PersonRole
from aditsystem_backend.models.persona import Persona


class PersonaPolicy:
    """RBAC plus real-tree ownership.  Non-admins never cross sibling branches."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def is_admin(actor: AuthUser) -> bool:
        return actor.persona.rol is PersonRole.ADMIN

    @staticmethod
    def can_create_role(actor_role: PersonRole, new_role: PersonRole) -> bool:
        if actor_role is PersonRole.ADMIN:
            return True
        if actor_role is PersonRole.COORDINADOR_GENERAL:
            return new_role not in (PersonRole.ADMIN, PersonRole.COORDINADOR_GENERAL)
        if actor_role is PersonRole.COORDINADOR:
            return new_role in (PersonRole.ENLACE, PersonRole.AMIGO)
        if actor_role is PersonRole.ENLACE:
            return new_role is PersonRole.AMIGO
        return False

    async def assert_manage(self, actor: AuthUser, target: Persona) -> None:
        if self.is_admin(actor) or target.id == actor.persona_id:
            return
        if await self._is_descendant(target.id, actor.persona_id):
            return
        raise DomainError("acceso denegado", status_code=403)

    async def assert_create(self, actor: AuthUser, role: PersonRole, parent: Persona | None) -> None:
        if not self.can_create_role(actor.persona.rol, role):
            raise DomainError("acceso denegado", status_code=403)
        if role is PersonRole.ADMIN and parent is not None:
            raise DomainError("acceso denegado", status_code=403)
        if self.is_admin(actor):
            return
        if parent is None:
            raise DomainError("acceso denegado", status_code=403)
        await self.assert_manage(actor, parent)

    async def _is_descendant(self, candidate_id: str, ancestor_id: str) -> bool:
        lineage = select(Persona.id, Persona.parent_persona_id).where(Persona.id == candidate_id).cte(
            "lineage", recursive=True
        )
        parent = Persona.__table__.alias("parent")
        lineage = lineage.union_all(
            select(parent.c.id, parent.c.parent_persona_id).join(
                lineage, parent.c.id == lineage.c.parent_persona_id
            )
        )
        result = await self.session.execute(select(lineage.c.id).where(lineage.c.id == ancestor_id))
        return result.scalar_one_or_none() is not None
