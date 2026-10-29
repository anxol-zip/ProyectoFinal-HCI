import pytest

from turismo_core import traslados
from turismo_core.config import leer_env


def test_cuerpo_manda_lon_lat():
    c = traslados.cuerpo([(19.04, -98.19), (19.05, -98.30)])
    assert c["locations"] == [[-98.19, 19.04], [-98.30, 19.05]]
    assert c["metrics"] == ["duration", "distance"] and c["units"] == "km"


def test_leer_matriz_convierte_a_minutos():
    datos = {"durations": [[0.0, 1274.0], [1175.55, None]], "distances": [[0.0, 12.50007], [12.28619, None]]}
    t = {(x.origen_id, x.destino_id): x for x in traslados.leer_matriz(datos, [5, 8])}
    assert (t[(5, 8)].minutos, t[(5, 8)].km) == (21.2, 12.5)
    assert t[(8, 5)].minutos == 19.6
    assert t[(8, 8)].minutos is None              # ORS sin ruta
    with pytest.raises(ValueError):
        traslados.leer_matriz(datos, [5])


def test_leer_env(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comentario\nORS_API_KEY=abc=\nTOMTOM_API_KEY = xyz  # nota\n\nVACIA\n", encoding="utf-8")
    assert leer_env(env) == {"ORS_API_KEY": "abc=", "TOMTOM_API_KEY": "xyz"}
    assert leer_env(tmp_path / "no_existe") == {}
