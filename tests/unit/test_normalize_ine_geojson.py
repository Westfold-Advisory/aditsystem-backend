from scripts.normalize_ine_geojson import normalize_feature


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
