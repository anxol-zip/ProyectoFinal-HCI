"""Paso 10: factor de tráfico por corredor, anclas, vigencia y su efecto en los traslados (sin llamar a TomTom)."""

from datetime import datetime, timedelta

from turismo_core import trafico
from turismo_core.bd import conectar, crear_esquema
from turismo_core.situacion import traslados

T = datetime(2026, 10, 16, 13, 0)


def test_factor_de_la_ruta_y_sus_limites():
    ruta = {"routes": [{"summary": {"lengthInMeters": 12516, "travelTimeInSeconds": 1800,
                                    "noTrafficTravelTimeInSeconds": 1200, "historicTrafficTravelTimeInSeconds": 1500}}]}
    c = trafico.leer_ruta(21, 12, ruta)
    assert (c.tramo, c.km, c.minutos_actual, c.minutos_libre, c.factor) == ("21-12", 12.52, 30.0, 20.0, 1.5)
    assert trafico.Corredor("x", 1, 9.0, 10.0, None).factor == 1.0      # nunca "más rápido que sin tráfico"
    assert trafico.Corredor("x", 1, 90.0, 10.0, None).factor == 4.0     # tope


def test_anclas_por_cercania():
    puntos = {21: (19.0434, -98.1981), 12: (19.0576, -98.3017), 1: (19.0430, -98.1985), 15: (19.0395, -98.2970)}
    assert trafico.ancla_de(puntos, anclas=(21, 12)) == {21: 21, 12: 12, 1: 21, 15: 12}
    assert trafico.ancla_de(puntos, anclas=(99,)) == {}


def _bd(tmp_path):
    con = conectar(tmp_path / "t.db")
    crear_esquema(con)
    con.execute("INSERT INTO destino (id, nombre) VALUES (1, 'D')")
    for pid, lat, lon in ((21, 19.0434, -98.1981), (12, 19.0576, -98.3017), (1, 19.0430, -98.1985)):
        con.execute("INSERT INTO punto (id, clave, nombre, destino_id, lat, lon) VALUES (?, ?, ?, 1, ?, ?)",
                    (pid, f"p{pid}", f"P{pid}", lat, lon))
    con.executemany("INSERT INTO matriz_traslado (origen_id, destino_id, minutos_base, km, minutos_pie, km_pie) "
                    "VALUES (?, ?, 20, 12, 160, 13)", [(1, 12), (12, 1), (1, 21), (21, 1), (21, 12), (12, 21)])
    return con


def test_traslados_con_trafico_vigente(tmp_path):
    con = _bd(tmp_path)
    trafico.guardar(con, [trafico.Corredor("21-12", 12, 30.0, 20.0, None)], T - timedelta(minutes=20))
    f = trafico.factores_vigentes(con, T)
    assert f.de(1, 12) == 1.5                 # la Catedral usa el corredor de su ancla (Zócalo → Pirámide)
    assert f.de(12, 1) is None                # sin consulta en ese sentido
    assert f.de(1, 21) is None                # misma ancla: sin tráfico en vivo
    con_trafico, sin = traslados(con, T), traslados(con)
    assert con_trafico[(1, 12)] == (30.0, 160) and sin[(1, 12)] == (20, 160)


def test_un_factor_viejo_no_se_usa(tmp_path):
    con = _bd(tmp_path)
    trafico.guardar(con, [trafico.Corredor("21-12", 12, 30.0, 20.0, None)], T - timedelta(hours=3))
    assert trafico.factores_vigentes(con, T).de(1, 12) is None
    assert traslados(con, T)[(1, 12)] == (20, 160)
