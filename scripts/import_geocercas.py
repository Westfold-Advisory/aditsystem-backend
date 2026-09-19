#!/usr/bin/env python3
"""Import GeoJSON or KML files into the geocercas table.

Usage:
    python scripts/import_geocercas.py --file path/to/states.geojson --tipo ESTADO
    python scripts/import_geocercas.py --file path/to/distritos.json --tipo DISTRITO
    python scripts/import_geocercas.py --file path/to/distritos.kml --tipo DISTRITO --kml
    python scripts/import_geocercas.py --file path/to/states.geojson --tipo ESTADO --replace
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Allow running from the project root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def run(
    file_content: str | dict[str, Any],
    fuente: str,
    tipo_str: str,
    is_kml: bool,
    replace: bool,
    batch_id: str | None,
) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from aditsystem_backend.core.config import get_settings
    from aditsystem_backend.models.enums import TipoGeocerca
    from aditsystem_backend.services.geocerca import GeocercaService

    settings = get_settings()
    tipo = TipoGeocerca(tipo_str.upper())

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
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

    print(
        f"Importación completa — creadas: {result['created']}, "
        f"omitidas (duplicadas): {result['skipped']}, "
        f"errores: {result['errors']}"
    )
    if result["errors"]:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Importar geocercas desde GeoJSON o KML")
    parser.add_argument("--file", required=True, help="Ruta al archivo GeoJSON o KML")
    parser.add_argument(
        "--tipo",
        required=True,
        choices=["ESTADO", "MUNICIPIO", "DISTRITO"],
        help="Tipo de geocerca",
    )
    parser.add_argument("--kml", action="store_true", help="El archivo es KML")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Desactivar versiones anteriores antes de importar",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Identificador del lote de importación (max 100 chars)",
    )
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: archivo no encontrado: {args.file}", file=sys.stderr)
        sys.exit(1)

    # Read the file synchronously here (outside the async context) to avoid
    # blocking I/O inside an async function (ruff ASYNC230/ASYNC240).
    if args.kml:
        file_content: str | dict[str, Any] = file_path.read_text(encoding="utf-8")
    else:
        with file_path.open(encoding="utf-8") as f:
            file_content = json.load(f)

    asyncio.run(
        run(
            file_content=file_content,
            fuente=file_path.name,
            tipo_str=args.tipo,
            is_kml=args.kml,
            replace=args.replace,
            batch_id=args.batch_id,
        )
    )


if __name__ == "__main__":
    main()
