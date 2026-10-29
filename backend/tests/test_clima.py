import sqlite3
from datetime import datetime

import pytest

from turismo_core import clima
from turismo_core.bd import crear_esquema
from turismo_core.clima import Pronostico


def _lugar(prob, mm):
    return {"hourly": {
        "time": ["2026-10-18T12:00", "2026-10-18T13:00"],
        "temperature_2m": [21.5, 22.0],
        "precipitation_probability": prob,
        "precipitation": mm,
        "weather_code": [3, 61],
    }}


@pytest.mark.parametrize("prob,mm,nivel", [
    (0, 0, "sin"), (29, 0.1, "sin"), (30, 0, "moderada"), (10, 0.2, "moderada"),
    (60, 0, "fuerte"), (5, 1.0, "fuerte"), (None, None, "sin"),
])
def test_nivel_lluvia(prob, mm, nivel):
    assert clima.nivel_lluvia(prob, mm) == nivel


def test_f_clima_baja_al_aire_libre_y_sube_techado():
    lluvia = Pronostico(1, datetime(2026, 10, 18, 13), 18, 80, 2.0, 61)
    assert clima.f_clima(False, lluvia) == clima.F_AIRE_LIBRE["fuerte"] < 1
    assert clima.f_clima(True, lluvia) == clima.F_TECHADO["fuerte"] > 1
    assert clima.f_clima(False, None) == 1.0


def test_url_pide_todas_las_coordenadas_en_una_consulta():
    url = clima.url_consulta([(19.05796, -98.30223), (18.90972, -98.43421)])
    assert "latitude=19.05796%2C18.90972" in url and "longitude=-98.30223%2C-98.43421" in url
    assert "timezone=America%2FMexico_City" in url and "precipitation_probability" in url


def test_leer_respuesta_en_el_orden_de_los_puntos():
    datos = [_lugar([0, 10], [0, 0]), _lugar([70, 90], [0.5, 2.1])]
    p = clima.leer_respuesta(datos, [7, 9])
    assert len(p) == 4
    assert (p[0].punto_id, p[0].valido_para, p[0].temp_c) == (7, datetime(2026, 10, 18, 12), 21.5)
    assert (p[3].punto_id, p[3].prob_lluvia_pct, p[3].lluvia_mm, p[3].weather_code) == (9, 90, 2.1, 61)
    # Una sola coordenada: Open-Meteo regresa un objeto, no una lista.
    assert len(clima.leer_respuesta(_lugar([0, 0], [0, 0]), [1])) == 2
    with pytest.raises(ValueError):
        clima.leer_respuesta(datos, [7])


def test_ultimo_pronostico_usa_la_consulta_mas_reciente():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    crear_esquema(con)
    con.execute("INSERT INTO destino (id, nombre) VALUES (1, 'X')")
    con.execute("INSERT INTO punto (id, clave, nombre, destino_id, lat, lon) VALUES (1, 'x', 'X', 1, 19, -98)")
    hora = datetime(2026, 10, 18, 13)
    clima.guardar(con, [Pronostico(1, hora, 20, 10, 0, 1)], datetime(2026, 10, 18, 8))
    clima.guardar(con, [Pronostico(1, hora, 19, 85, 3.0, 63)], datetime(2026, 10, 18, 11))
    ult = clima.ultimo_pronostico(con, datetime(2026, 10, 18), datetime(2026, 10, 19))
    p = ult[(1, hora)]
    assert p.prob_lluvia_pct == 85 and p.consultado_en == datetime(2026, 10, 18, 11)
