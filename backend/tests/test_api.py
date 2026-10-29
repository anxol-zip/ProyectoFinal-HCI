"""Endpoints de la API contra una BD sintética (no depende de puebla.db, que no está en git)."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import deps
from app.main import app
from turismo_core.bd import conectar, crear_esquema

T = datetime(2026, 10, 16, 13, 0)
HORA = T.strftime("%Y-%m-%d %H:00")


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("PUEBLA_TAREAS", "0")
    ruta = tmp_path / "prueba.db"
    con = conectar(ruta)
    crear_esquema(con)
    con.execute("INSERT INTO destino (id, nombre) VALUES (1, 'Cd. Puebla')")
    # 1 museo tranquilo · 2 museo lleno · 3 mirador cerrado
    for pid, clave, interior in ((1, "museo_a", 1), (2, "museo_b", 1), (3, "mirador", 0)):
        con.execute("INSERT INTO punto (id, clave, nombre, destino_id, tipo, categorias, interior, lat, lon, verificado) "
                    "VALUES (?, ?, ?, 1, 'museo', 'historia,arte', ?, 19.04, -98.2, 1)",
                    (pid, clave, f"Punto {pid}", interior))
        con.execute("INSERT INTO umbral_punto VALUES (?, 1.0, 1.4, 'percentil', 100, ?)", (pid, T.isoformat()))
    con.executemany("INSERT INTO afluencia_estimada (punto_id, para_hora, estimacion, valor_final, semaforo, confianza) "
                    "VALUES (?, ?, ?, ?, ?, 'estimado')",
                    [(1, HORA, 0.8, 0.8, "verde"), (2, HORA, 2.0, 2.0, "rojo"), (3, HORA, None, None, "cerrado")])
    con.executemany("INSERT INTO matriz_traslado (origen_id, destino_id, minutos_base, km, minutos_pie, km_pie) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    [(a, b, 20.0, 9.0, 120.0, 8.0) for a in (1, 2, 3) for b in (1, 2, 3) if a != b])
    con.commit()
    con.close()

    def conexion():
        c = conectar(ruta, check_same_thread=False)
        try:
            yield c
        finally:
            c.close()

    reloj = {"t": T, "demo": False, "ruta": ruta}
    app.dependency_overrides[deps.conexion] = conexion
    app.dependency_overrides[deps.ahora] = lambda: reloj["t"]
    app.dependency_overrides[deps.es_demo] = lambda: reloj["demo"]
    yield TestClient(app), reloj
    app.dependency_overrides.clear()


def sesion(c, **perfil):
    return c.post("/api/sesiones", json=perfil).json()["sesion_id"]


def test_semaforo_ordenado_y_cerrados_al_final(cliente):
    c, _ = cliente
    r = c.get("/api/semaforo?origen_id=1").json()
    assert [p["color"] for p in r["puntos"]] == ["verde", "rojo", "cerrado"]
    assert r["puntos"][0]["traslado"] == {"minutos": 0, "modo": "a pie"}
    assert r["datos"]["afluencia_cubre_esta_hora"] is True
    assert c.get("/api/puntos/99/estado").status_code == 404


def test_estado_punto_trae_ficha_y_enlace(cliente):
    c, _ = cliente
    e = c.get("/api/puntos/2/estado?origen_id=1").json()
    assert e["color"] == "rojo" and e["verificado"] is True
    assert e["traslado"] == {"desde": 1, "minutos": 20, "modo": "en coche"}
    assert e["como_llegar_url"].endswith("destination=19.04,-98.2")


def test_recomendar_guarda_la_busqueda_y_se_acepta(cliente):
    c, _ = cliente
    sid = sesion(c, intereses=["historia"], origen_id=2)
    r = c.post("/api/recomendar", json={"sesion_id": sid, "punto_id": 2}).json()
    assert r["motivo"] == "afluencia" and r["alternativa"]["id"] == 1
    assert "Mejor ve a Punto 1" in r["razon"]
    assert c.post(f"/api/busquedas/{r['busqueda_id']}/aceptar", json={"aceptada": True}).json()["aceptada"] is True
    assert c.post("/api/recomendar", json={"sesion_id": "no-existe"}).status_code == 404


def test_tres_reportes_llenos_confirman_y_cambian_el_color(cliente):
    c, reloj = cliente
    for i in range(3):
        reloj["t"] = T + timedelta(minutes=i)
        r = c.post("/api/reportes", json={"sesion_id": sesion(c), "punto_id": 1, "nivel": 3, "distancia_m": 50}).json()
    assert r["reporte"]["estado"] == "valido"
    assert (r["punto"]["color"], r["punto"]["confianza"]) == ("rojo", "confirmado por turistas")
    assert r["punto"]["normalmente"] == "verde"


def test_reporte_repetido_y_punto_cerrado(cliente):
    c, _ = cliente
    sid = sesion(c)
    assert c.post("/api/reportes", json={"sesion_id": sid, "punto_id": 1, "nivel": 2}).json()["reporte"]["peso"] == 0.5
    rep = c.post("/api/reportes", json={"sesion_id": sid, "punto_id": 1, "nivel": 2}).json()["reporte"]
    assert rep["estado"] == "descartado" and "13:30" in rep["mensaje"]
    assert c.post("/api/reportes", json={"sesion_id": sid, "punto_id": 3, "nivel": 1}).json()["reporte"]["estado"] == "descartado"
    assert c.post("/api/reportes", json={"sesion_id": sid, "punto_id": 1, "nivel": 5}).status_code == 422


def test_velocidad_imposible_descarta_la_sesion_salvo_en_demo(cliente):
    c, reloj = cliente
    sid = sesion(c)
    c.post("/api/reportes", json={"sesion_id": sid, "punto_id": 1, "nivel": 2})
    reloj["t"] = T + timedelta(minutes=2)            # 2 min para un traslado de 20 min en coche
    r = c.post("/api/reportes", json={"sesion_id": sid, "punto_id": 2, "nivel": 3}).json()
    assert r["reporte"]["motivo"].startswith("velocidad imposible")
    assert c.get("/api/panel/afluencia").json()["hoy"]["reportes_por_estado"]["descartado"] == 2

    reloj["demo"] = True
    demo = sesion(c)
    reloj["t"] = T + timedelta(minutes=3)
    c.post("/api/reportes", json={"sesion_id": demo, "punto_id": 1, "nivel": 2})
    reloj["t"] = T + timedelta(minutes=4)
    assert c.post("/api/reportes", json={"sesion_id": demo, "punto_id": 2, "nivel": 3}).json()["reporte"]["estado"] == "valido"


def test_panel_separa_la_demo(cliente):
    c, reloj = cliente
    reloj["demo"] = True
    sid = sesion(c, origen_id=2)
    b = c.post("/api/recomendar", json={"sesion_id": sid, "punto_id": 2}).json()["busqueda_id"]
    c.post(f"/api/busquedas/{b}/aceptar")
    assert c.get("/api/panel/redirecciones").json()["total_aceptadas"] == 0
    con_demo = c.get("/api/panel/redirecciones?incluir_demo=true").json()
    assert con_demo["total_aceptadas"] == 1 and con_demo["filas"][0]["hacia_id"] == 1


def test_ajuste_manual_gana_y_se_quita(cliente):
    c, _ = cliente
    a = c.post("/api/panel/ajustes", json={"punto_id": 1, "color": "rojo", "motivo": "Obra en la entrada", "horas": 2}).json()
    assert a["punto"]["color"] == "rojo" and a["punto"]["ajuste_manual"] == "Obra en la entrada"
    assert len(c.get("/api/panel/ajustes").json()) == 1
    assert c.delete(f"/api/panel/ajustes/{a['ajuste_id']}").json()["punto"]["color"] == "verde"


def _observatorio(ruta, valores: dict[str, float], derrama_por_visitante: float = 1000.0):
    con = conectar(ruta)
    for p, v in valores.items():
        con.execute("INSERT INTO hecho_observatorio (destino_id, periodo, indicador, valor) VALUES (1, ?, 'afluencia', ?)", (p, v))
        con.execute("INSERT INTO hecho_observatorio (destino_id, periodo, indicador, valor) VALUES (1, ?, 'derrama_mxn', ?)",
                    (p, v * derrama_por_visitante))
    con.commit()
    con.close()


def _meses(desde: str, hasta: str) -> list[str]:
    a, m = map(int, desde.split("-"))
    salida = []
    while f"{a}-{m:02d}" <= hasta:
        salida.append(f"{a}-{m:02d}")
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return salida


def test_derrama_redistribuida_y_nueva_sin_contar_dos_veces(cliente):
    c, reloj = cliente
    _observatorio(reloj["ruta"], {p: 100.0 for p in _meses("2025-07", "2026-06")})     # $1,000 por visitante
    for volvio in (False, True):
        sid = sesion(c, origen_id=2)
        b = c.post("/api/recomendar", json={"sesion_id": sid, "punto_id": 2}).json()["busqueda_id"]
        c.post(f"/api/busquedas/{b}/aceptar")
        if volvio:          # después reporta desde el lugar que había pedido: la parada se sumó a su plan
            reloj["t"] = T + timedelta(minutes=40)
            c.post("/api/reportes", json={"sesion_id": sid, "punto_id": 2, "nivel": 3})
    d = c.get("/api/panel/derrama").json()
    assert d["redirecciones_aceptadas"] == 2
    assert (d["redistribuida_mxn"], d["nueva_estimada_mxn"]) == (1000.0, 1000.0)
    assert d["redistribuida_entre_destinos_mxn"] == 0       # mismo destino: no sale dinero de Cd. Puebla
    assert "1 visitante" in d["supuesto"]


def test_semaforo_estatal_dato_y_estimado(cliente):
    c, reloj = cliente
    valores = {p: 100.0 for p in _meses("2022-01", "2026-06")}
    valores["2025-10"] = 200.0
    _observatorio(reloj["ruta"], valores)
    publicado = c.get("/api/panel/semaforo-estatal?mes=10&anio=2025").json()["destinos"][0]
    assert (publicado["tipo"], publicado["color"], publicado["nivel"]) == ("dato", "rojo", 2.0)
    estimado = c.get("/api/panel/semaforo-estatal?mes=10&anio=2026").json()["destinos"][0]
    assert estimado["tipo"] == "estimado" and estimado["periodos_usados"] == ["2023-10", "2024-10", "2025-10"]
    assert estimado["visitantes"] == 133 and estimado["color"] == "rojo"
    assert c.get("/api/panel/semaforo-estatal?mes=13").status_code == 422


def test_semana_hoy_espera_y_vs_normal(cliente):
    c, reloj = cliente
    s = c.get("/api/puntos/1/semana").json()
    assert s["dias"][0]["fecha"] == "2026-10-16" and s["dias"][0]["horas"][0]["color"] == "verde"
    assert c.get("/api/puntos/3/semana").json()["dias"][0]["abierto"] is False       # el mirador está cerrado
    assert c.get("/api/puntos/99/semana").status_code == 404
    e = c.get("/api/puntos/1/estado").json()
    assert e["espera_reportada"] is None and e["vs_normal"] == "igual"
    for i, espera in enumerate((10, 30, 20)):                                        # 3 turistas, mediana 20
        reloj["t"] = T + timedelta(minutes=i)
        c.post("/api/reportes", json={"sesion_id": sesion(c), "punto_id": 1, "nivel": 3, "espera_min": espera, "distancia_m": 50})
    e = c.get("/api/puntos/1/estado").json()
    assert e["espera_reportada"] == {"minutos": 20, "n_reportes": 3, "ultima_hace_min": 0}
    assert (e["color"], e["normalmente"], e["vs_normal"]) == ("rojo", "verde", "mas_lleno")
