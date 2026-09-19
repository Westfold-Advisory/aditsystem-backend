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
import sys
from pathlib import Path

# Allow running from the project root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def run(
    file_path: str,
    tipo_str: str,
    is_kml: bool,
    replace: bool,
    batch_id: str | None,
) -> None:
    import json

    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from aditsystem_backend.core.config import get_settings
    from aditsystem_backend.models.enums import TipoGeocerca
    from aditsystem_backend.services.geocerca import GeocercaService

    settings = get_settings()
    tipo = TipoGeocerca(tipo_str.upper())
    fuente = Path(file_path).name

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        svc = GeocercaService(session)

        if is_kml:
            content = Path(file_path).read_text(encoding="utf-8")
            result = await svc.import_kml(
                content,
                tipo=tipo,
                fuente=fuente,
                importado_por=batch_id,
                replace_existing=replace,
            )
        else:
            with open(file_path, encoding="utf-8") as f:
                feature_collection = json.load(f)
            result = await svc.import_geojson(
                feature_collection,
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

    if not Path(args.file).exists():
        print(f"Error: archivo no encontrado: {args.file}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(
        run(
            file_path=args.file,
            tipo_str=args.tipo,
            is_kml=args.kml,
            replace=args.replace,
            batch_id=args.batch_id,
        )
    )


if __name__ == "__main__":
    main()
