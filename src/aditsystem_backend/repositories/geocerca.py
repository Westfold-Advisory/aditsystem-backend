from typing import Any

from geoalchemy2.functions import ST_AsGeoJSON, ST_Contains, ST_GeomFromText, ST_Simplify
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.models.enums import TipoGeocerca
from aditsystem_backend.models.geocerca import Geocerca


class GeocercaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, geocerca: Geocerca) -> Geocerca:
        self.session.add(geocerca)
        await self.session.flush()
        await self.session.refresh(geocerca)
        return geocerca

    async def get(self, geocerca_id: str) -> Geocerca | None:
        return await self.session.get(Geocerca, geocerca_id)

    async def get_by_hash(self, hash_geometria: str, tipo: TipoGeocerca) -> Geocerca | None:
        stmt = select(Geocerca).where(
            Geocerca.hash_geometria == hash_geometria,
            Geocerca.tipo == tipo,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        tipo: TipoGeocerca | None = None,
        codigo: str | None = None,
        codigo_padre: str | None = None,
        vigente: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> list[Geocerca]:
        filters = [Geocerca.vigente == vigente]
        if tipo is not None:
            filters.append(Geocerca.tipo == tipo)
        if codigo is not None:
            filters.append(Geocerca.codigo == codigo)
        if codigo_padre is not None:
            filters.append(Geocerca.codigo_padre == codigo_padre)

        stmt = (
            select(Geocerca)
            .where(and_(*filters))
            .order_by(Geocerca.tipo, Geocerca.nombre)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(
        self,
        tipo: TipoGeocerca | None = None,
        vigente: bool = True,
    ) -> int:
        from sqlalchemy import func

        filters = [Geocerca.vigente == vigente]
        if tipo is not None:
            filters.append(Geocerca.tipo == tipo)

        stmt = select(func.count()).select_from(Geocerca).where(and_(*filters))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def contains_point(
        self,
        latitud: float,
        longitud: float,
        tipo: TipoGeocerca | None = None,
    ) -> list[Geocerca]:
        """Return all active geocercas whose geometry contains the given point."""
        point_wkt = f"POINT({longitud} {latitud})"
        point_geom = ST_GeomFromText(point_wkt, 4326)

        filters = [
            Geocerca.vigente == True,  # noqa: E712
            ST_Contains(Geocerca.geometria, point_geom),
        ]
        if tipo is not None:
            filters.append(Geocerca.tipo == tipo)

        stmt = select(Geocerca).where(and_(*filters))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_geometry_geojson(self, geocerca_id: str) -> dict[str, Any] | None:
        """Return the full GeoJSON geometry for a geocerca."""
        import json

        stmt = select(ST_AsGeoJSON(Geocerca.geometria).label("geojson")).where(
            Geocerca.id == geocerca_id
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        return json.loads(row.geojson)

    async def get_simplified_geometry_geojson(
        self, geocerca_id: str, tolerance: float = 0.001
    ) -> dict[str, Any] | None:
        """Return a simplified GeoJSON geometry for map rendering."""
        import json

        stmt = select(
            ST_AsGeoJSON(ST_Simplify(Geocerca.geometria, tolerance)).label("geojson")
        ).where(Geocerca.id == geocerca_id)
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        return json.loads(row.geojson)

    async def deactivate_previous_versions(
        self, tipo: TipoGeocerca, codigo: str | None
    ) -> None:
        """Mark all current versions of a geocerca as no longer vigente."""
        filters = [Geocerca.tipo == tipo, Geocerca.vigente == True]  # noqa: E712
        if codigo is not None:
            filters.append(Geocerca.codigo == codigo)
        stmt = (
            select(Geocerca).where(and_(*filters))
        )
        result = await self.session.execute(stmt)
        for geocerca in result.scalars().all():
            geocerca.vigente = False
        await self.session.flush()

    async def save(self, geocerca: Geocerca) -> Geocerca:
        await self.session.flush()
        await self.session.refresh(geocerca)
        return geocerca
