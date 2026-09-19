from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from aditsystem_backend.models.enums import TipoGeocerca


class GeocercaBase(BaseModel):
    tipo: TipoGeocerca
    nombre: str = Field(min_length=1, max_length=255)
    codigo: str | None = Field(default=None, max_length=50)
    codigo_padre: str | None = Field(default=None, max_length=50)
    fuente: str = Field(min_length=1, max_length=255)


class GeocercaCreate(GeocercaBase):
    geojson_geometry: dict[str, Any] = Field(
        description="GeoJSON geometry object (Polygon or MultiPolygon)"
    )
    importado_por: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_geometry_type(self) -> "GeocercaCreate":
        allowed = {"Polygon", "MultiPolygon"}
        gtype = self.geojson_geometry.get("type")
        if gtype not in allowed:
            raise ValueError(f"geometry type must be one of {allowed}, got '{gtype}'")
        return self


class GeocercaRead(GeocercaBase):
    id: str
    hash_geometria: str
    version: int
    vigente: bool
    importado_en: datetime
    importado_por: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GeocercaWithGeometry(GeocercaRead):
    """Full response including the geometry as GeoJSON."""

    geometry: dict[str, Any] | None = Field(
        default=None,
        description="GeoJSON geometry object",
    )


class GeocercaSimplified(GeocercaRead):
    """List response with simplified geometry for map rendering."""

    geometry_simplified: dict[str, Any] | None = Field(
        default=None,
        description="Simplified GeoJSON geometry for map rendering",
    )


class ContainsPointRequest(BaseModel):
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    tipo: TipoGeocerca | None = None


class GeocercaListParams(BaseModel):
    tipo: TipoGeocerca | None = None
    codigo: str | None = None
    codigo_padre: str | None = None
    vigente: bool = True
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
