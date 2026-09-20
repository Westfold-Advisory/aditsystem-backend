from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from geoalchemy2.shape import from_shape
from shapely.geometry import shape
from shapely.validation import make_valid
from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import TipoGeocerca
from aditsystem_backend.models.geocerca import Geocerca
from aditsystem_backend.repositories.geocerca import GeocercaRepository
from aditsystem_backend.schemas.geocerca import (
    ContainsPointRequest,
    GeocercaCreate,
    GeocercaListParams,
    GeocercaRead,
    GeocercaSimplified,
    GeocercaWithGeometry,
)


def _hash_geometry(geojson_geometry: dict[str, Any]) -> str:
    canonical = json.dumps(geojson_geometry, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _geojson_to_wkb(geojson_geometry: dict[str, Any]) -> Any:
    geom = shape(geojson_geometry)
    if not geom.is_valid:
        geom = make_valid(geom)
    if geom.is_empty:
        raise DomainError("la geometría está vacía después de la validación")
    return from_shape(geom, srid=4326)


class GeocercaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = GeocercaRepository(session)

    async def create(self, payload: GeocercaCreate) -> GeocercaRead:
        hash_geom = _hash_geometry(payload.geojson_geometry)
        existing = await self.repo.get_by_hash(hash_geom, payload.tipo)
        if existing:
            raise DomainError(
                "ya existe una geocerca con la misma geometría y tipo",
                status_code=409,
            )

        wkb = _geojson_to_wkb(payload.geojson_geometry)

        geocerca = Geocerca(
            tipo=payload.tipo,
            nombre=payload.nombre,
            codigo=payload.codigo,
            codigo_padre=payload.codigo_padre,
            fuente=payload.fuente,
            hash_geometria=hash_geom,
            geometria=wkb,
            vigente=True,
            importado_en=datetime.now(UTC),
            importado_por=payload.importado_por,
        )
        await self.repo.create(geocerca)
        await self.session.commit()
        await self.session.refresh(geocerca)
        return GeocercaRead.model_validate(geocerca)

    async def get_or_404(self, geocerca_id: str) -> Geocerca:
        geocerca = await self.repo.get(geocerca_id)
        if geocerca is None:
            raise DomainError("geocerca no encontrada", status_code=404)
        return geocerca

    async def get_detail(self, geocerca_id: str) -> GeocercaWithGeometry:
        geocerca = await self.get_or_404(geocerca_id)
        geometry = await self.repo.get_geometry_geojson(geocerca_id)
        data = GeocercaRead.model_validate(geocerca).model_dump()
        return GeocercaWithGeometry(**data, geometry=geometry)

    async def list(self, params: GeocercaListParams) -> list[GeocercaSimplified]:
        items = await self.repo.list(
            tipo=params.tipo,
            codigo=params.codigo,
            codigo_padre=params.codigo_padre,
            vigente=params.vigente,
            page=params.page,
            page_size=params.page_size,
        )
        result = []
        for item in items:
            geom = await self.repo.get_simplified_geometry_geojson(item.id)
            base = GeocercaRead.model_validate(item).model_dump()
            result.append(GeocercaSimplified(**base, geometry_simplified=geom))
        return result

    async def contains_point(
        self, req: ContainsPointRequest
    ) -> list[GeocercaWithGeometry]:
        items = await self.repo.contains_point(req.latitud, req.longitud, req.tipo)
        result = []
        for item in items:
            geometry = await self.repo.get_geometry_geojson(item.id)
            base = GeocercaRead.model_validate(item).model_dump()
            result.append(GeocercaWithGeometry(**base, geometry=geometry))
        return result

    async def deactivate(self, geocerca_id: str) -> GeocercaRead:
        geocerca = await self.get_or_404(geocerca_id)
        if not geocerca.vigente:
            raise DomainError("la geocerca ya está inactiva")
        geocerca.vigente = False
        await self.repo.save(geocerca)
        await self.session.commit()
        await self.session.refresh(geocerca)
        return GeocercaRead.model_validate(geocerca)

    async def import_geojson(
        self,
        feature_collection: dict[str, Any],
        tipo: TipoGeocerca,
        fuente: str,
        importado_por: str | None = None,
        replace_existing: bool = False,
    ) -> dict[str, int]:
        """Import a GeoJSON FeatureCollection into geocercas."""
        if feature_collection.get("type") != "FeatureCollection":
            raise DomainError("se esperaba un FeatureCollection GeoJSON")

        crs = feature_collection.get("crs", {})
        crs_name = crs.get("properties", {}).get("name", "")
        if crs_name and "4326" not in crs_name and "CRS84" not in crs_name:
            raise DomainError(
                f"CRS no soportado: '{crs_name}'. Solo se acepta EPSG:4326 / CRS84"
            )

        created = 0
        skipped = 0
        errors = 0

        for feature in feature_collection.get("features", []):
            props = feature.get("properties") or {}
            geom_json = feature.get("geometry")
            if not geom_json:
                errors += 1
                continue

            gtype = geom_json.get("type", "")
            if gtype not in ("Polygon", "MultiPolygon"):
                errors += 1
                continue

            nombre = (
                props.get("state_name")
                or props.get("nombre")
                or props.get("name")
                or "Sin nombre"
            )
            codigo = None
            for key in ("state_code", "codigo", "seccion", "distrito_l", "distrito_f"):
                if props.get(key) is not None:
                    codigo = str(props[key])
                    break
            codigo_padre = (
                str(props["codigo_padre"]) if props.get("codigo_padre") is not None else None
            )

            hash_geom = _hash_geometry(geom_json)
            existing = await self.repo.get_by_hash(hash_geom, tipo)
            if existing:
                skipped += 1
                continue

            try:
                wkb = _geojson_to_wkb(geom_json)
            except (DomainError, Exception):
                errors += 1
                continue

            if replace_existing:
                await self.repo.deactivate_previous_versions(tipo, codigo)

            geocerca = Geocerca(
                tipo=tipo,
                nombre=str(nombre),
                codigo=codigo,
                codigo_padre=codigo_padre,
                fuente=fuente,
                hash_geometria=hash_geom,
                geometria=wkb,
                vigente=True,
                importado_en=datetime.now(UTC),
                importado_por=importado_por,
            )
            self.session.add(geocerca)
            created += 1

        await self.session.commit()
        return {"created": created, "skipped": skipped, "errors": errors}

    async def import_kml(
        self,
        kml_content: str,
        tipo: TipoGeocerca,
        fuente: str,
        importado_por: str | None = None,
        replace_existing: bool = False,
    ) -> dict[str, int]:
        """Parse a KML string and import geometries as geocercas."""
        try:
            import defusedxml.ElementTree as ET

            NS = {
                "kml": "http://www.opengis.net/kml/2.2",
                "gx": "http://www.google.com/kml/ext/2.2",
            }
        except ImportError as exc:
            raise DomainError("defusedxml no disponible; instalar con pip install defusedxml") from exc

        root = ET.fromstring(kml_content)
        placemarks = root.findall(".//kml:Placemark", NS)

        created = 0
        skipped = 0
        errors = 0

        def _coords_text_to_list(coords_text: str) -> list[list[float]]:
            coords = []
            for token in coords_text.strip().split():
                parts = token.split(",")
                if len(parts) >= 2:
                    coords.append([float(parts[0]), float(parts[1])])
            return coords

        def _polygon_element_to_geojson(
            poly_el: Any,
        ) -> dict[str, Any] | None:
            outer = poly_el.find("kml:outerBoundaryIs/kml:LinearRing/kml:coordinates", NS)
            if outer is None or not outer.text:
                return None
            rings = [_coords_text_to_list(outer.text)]
            for inner in poly_el.findall(
                "kml:innerBoundaryIs/kml:LinearRing/kml:coordinates", NS
            ):
                if inner.text:
                    rings.append(_coords_text_to_list(inner.text))
            return {"type": "Polygon", "coordinates": rings}

        for pm in placemarks:
            # Extract properties from ExtendedData
            props: dict[str, Any] = {}
            for sd in pm.findall(".//kml:SimpleData", NS):
                name = sd.get("name", "")
                props[name] = sd.text or ""

            nombre = (
                props.get("nombre")
                or props.get("name")
                or f"Distrito {props.get('distrito_l', '')}"
            ).strip() or "Sin nombre"
            codigo = props.get("distrito_l") or props.get("id")
            codigo_padre = props.get("entidad")

            # Collect polygons (handles MultiGeometry)
            polygons = []
            for poly in pm.findall(".//kml:Polygon", NS):
                geom = _polygon_element_to_geojson(poly)
                if geom:
                    polygons.append(geom)

            if not polygons:
                errors += 1
                continue

            if len(polygons) == 1:
                geom_json = polygons[0]
            else:
                geom_json = {
                    "type": "MultiPolygon",
                    "coordinates": [p["coordinates"] for p in polygons],
                }

            hash_geom = _hash_geometry(geom_json)
            existing = await self.repo.get_by_hash(hash_geom, tipo)
            if existing:
                skipped += 1
                continue

            try:
                wkb = _geojson_to_wkb(geom_json)
            except Exception:
                errors += 1
                continue

            if replace_existing:
                await self.repo.deactivate_previous_versions(tipo, codigo)

            geocerca = Geocerca(
                tipo=tipo,
                nombre=str(nombre),
                codigo=str(codigo) if codigo else None,
                codigo_padre=str(codigo_padre) if codigo_padre else None,
                fuente=fuente,
                hash_geometria=hash_geom,
                geometria=wkb,
                vigente=True,
                importado_en=datetime.now(UTC),
                importado_por=importado_por,
            )
            self.session.add(geocerca)
            created += 1

        await self.session.commit()
        return {"created": created, "skipped": skipped, "errors": errors}
