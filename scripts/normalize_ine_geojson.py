#!/usr/bin/env python3
"""Map INE Marco Geográfico Electoral properties for import_geocercas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def normalize_feature(layer: str, feature: dict[str, Any]) -> None:
    props = feature.setdefault("properties", {})
    layer_key = layer.upper()

    if layer_key == "DISTRITO_LOCAL" and props.get("distrito_l") is not None:
        dl = int(props["distrito_l"])
        props["state_name"] = f"DL{dl}"
        props["state_code"] = dl
        props["nombre"] = props["state_name"]
        if props.get("entidad") is not None:
            props["codigo_padre"] = str(int(props["entidad"]))
        return

    if layer_key == "DISTRITO_FEDERAL" and props.get("distrito_f") is not None:
        df = int(props["distrito_f"])
        props["state_name"] = f"DF{df}"
        props["state_code"] = df
        props["nombre"] = props["state_name"]
        if props.get("entidad") is not None:
            props["codigo_padre"] = str(int(props["entidad"]))
        return

    if layer_key == "SECCION" and props.get("seccion") is not None:
        seccion = int(props["seccion"])
        props["state_name"] = f"Sección {seccion}"
        props["state_code"] = seccion
        props["nombre"] = props["state_name"]
        if props.get("municipio") is not None:
            props["codigo_padre"] = str(int(props["municipio"]))
        return


def normalize_collection(layer: str, data: dict[str, Any]) -> dict[str, Any]:
    if data.get("type") != "FeatureCollection":
        raise ValueError("se esperaba FeatureCollection")
    for feature in data.get("features", []):
        normalize_feature(layer, feature)
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalizar propiedades INE en GeoJSON")
    parser.add_argument("--layer", required=True, help="DISTRITO_LOCAL, DISTRITO_FEDERAL o SECCION")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    normalized = normalize_collection(args.layer, data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(normalized, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(normalized.get('features', []))} features to {args.output}")


if __name__ == "__main__":
    main()
