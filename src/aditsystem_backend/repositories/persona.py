from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from aditsystem_backend.models.persona import Persona


class PersonaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, persona_id: str) -> Persona | None:
        result = await self.session.execute(
            select(Persona).options(selectinload(Persona.auth_user)).where(Persona.id == persona_id)
        )
        return result.scalar_one_or_none()

    async def list_children(self, parent_persona_id: str) -> list[Persona]:
        result = await self.session.execute(
            select(Persona)
            .where(Persona.parent_persona_id == parent_persona_id, Persona.deleted_at.is_(None))
            .order_by(Persona.nombre, Persona.apellido_paterno)
        )
        return list(result.scalars().all())

    async def list_descendants(self, persona_id: str) -> list[Persona]:
        tree = select(Persona.id).where(Persona.parent_persona_id == persona_id).cte("tree", recursive=True)
        child = Persona.__table__.alias("child")
        tree = tree.union_all(select(child.c.id).join(tree, child.c.parent_persona_id == tree.c.id))
        result = await self.session.execute(
            select(Persona).join(tree, Persona.id == tree.c.id).where(Persona.deleted_at.is_(None))
        )
        return list(result.scalars().all())

    async def create(self, persona: Persona) -> Persona:
        self.session.add(persona)
        await self.session.flush()
        await self.session.refresh(persona)
        return persona
