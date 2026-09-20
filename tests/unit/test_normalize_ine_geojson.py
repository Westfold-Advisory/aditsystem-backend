import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "normalize_ine_geojson.py"
_spec = importlib.util.spec_from_file_location("normalize_ine_geojson", _SCRIPT)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
normalize_feature = _mod.normalize_feature


def test_normalize_entidad_feature() -> None:
    feature = {"properties": {"entidad": 21, "nombre": "PUEBLA"}}
    normalize_feature("ENTIDAD", feature)
    assert feature["properties"]["nombre"] == "PUEBLA"
    assert feature["properties"]["codigo"] == "21"
    assert feature["properties"]["state_code"] == 21


def test_normalize_municipio_feature() -> None:
    feature = {"properties": {"entidad": 21, "municipio": 2, "nombre": "ACATENO"}}
    normalize_feature("MUNICIPIO", feature)
    assert feature["properties"]["codigo"] == "2"
    assert feature["properties"]["codigo_padre"] == "21"
    assert feature["properties"]["state_name"] == "ACATENO"
