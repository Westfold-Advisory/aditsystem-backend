"""CLI: import GeoJSON/KML into geocercas (used on EC2 via Docker entrypoint)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any


async def run_import(
    file_content: str | dict[str, Any],
    fuente: str,
    tipo_str: str,
    *,
    is_kml: bool,
    replace: bool,
    batch_id: str | None,
) -> dict[str, int]:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from aditsystem_backend.core.config import get_settings
    from aditsystem_backend.models.enums import TipoGeocerca
    from aditsystem_backend.services.geocerca import GeocercaService

    settings = get_settings()
    tipo = TipoGeocerca(tipo_str.upper())

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        svc = GeocercaService(session)
        if is_kml:
            result = await svc.import_kml(
                file_content,  # type: ignore[arg-type]
                tipo=tipo,
                fuente=fuente,
                importado_por=batch_id,
                replace_existing=replace,
            )
        else:
            result = await svc.import_geojson(
                file_content,  # type: ignore[arg-type]
                tipo=tipo,
                fuente=fuente,
                importado_por=batch_id,
                replace_existing=replace,
            )

    await engine.dispose()
    return result


def main_cli() -> None:
    parser = argparse.ArgumentParser(description="Importar geocercas desde GeoJSON o KML")
    parser.add_argument("--file", required=True, help="Ruta al archivo GeoJSON o KML")
    parser.add_argument(
        "--tipo",
        required=True,
        choices=[
            "ESTADO",
            "MUNICIPIO",
            "SECCION",
            "DISTRITO_LOCAL",
            "DISTRITO_FEDERAL",
        ],
    )
    parser.add_argument("--kml", action="store_true")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--batch-id", default=None)
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: archivo no encontrado: {args.file}", file=sys.stderr)
        raise SystemExit(1)

    if args.kml:
        file_content: str | dict[str, Any] = file_path.read_text(encoding="utf-8")
    else:
        with file_path.open(encoding="utf-8") as handle:
            file_content = json.load(handle)

    result = asyncio.run(
        run_import(
            file_content=file_content,
            fuente=file_path.name,
            tipo_str=args.tipo,
            is_kml=args.kml,
            replace=args.replace,
            batch_id=args.batch_id,
        )
    )

    print(
        f"Importación completa — creadas: {result['created']}, "
        f"omitidas (duplicadas): {result['skipped']}, "
        f"errores: {result['errors']}"
    )
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main_cli()
