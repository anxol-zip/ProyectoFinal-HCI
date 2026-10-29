from datetime import datetime, timedelta

import pytest

from turismo_core.estado import evaluar
from turismo_core.reportes import Reporte, ReportePrevio, filtrar, fusionar, peso_temporal, valor_de_nivel
from turismo_core.semaforo import UMBRALES_GENERALES, AjusteManual, color

AHORA = datetime(2026, 10, 16, 13, 0)
U = UMBRALES_GENERALES


def hace(minutos: float) -> datetime:
    return AHORA - timedelta(minutes=minutos)


def test_niveles_caen_en_su_color():
    assert color(valor_de_nivel(1, U), U) == "verde"
    assert color(valor_de_nivel(2, U), U) == "amarillo"
    assert color(valor_de_nivel(3, U), U) == "rojo"


def test_peso_cae_a_la_mitad_en_unos_30_minutos():
    w = peso_temporal(Reporte(3, hace(30)), AHORA)
    assert w == pytest.approx(0.51, abs=0.02)


@pytest.mark.parametrize(
    "r",
    [
        Reporte(3, hace(5), estado="descartado"),
        Reporte(3, hace(200)),            # más de 3 h
        Reporte(3, AHORA + timedelta(minutes=5)),  # reloj adelantado
    ],
)
def test_reportes_que_no_pesan(r):
    assert peso_temporal(r, AHORA) == 0


def test_sin_reportes_manda_la_estimacion():
    f = fusionar(0.8, [], U, AHORA)
    assert (f.valor_final, f.n_reportes, f.confianza) == (0.8, 0, "estimado")


def test_un_reporte_no_voltea_el_color():
    # El modelo dice verde; un solo "lleno" no debe pasarlo a rojo (docs/05)
    f = fusionar(0.7, [Reporte(3, hace(1))], U, AHORA)
    assert color(f.valor_final, U) != "rojo"


def test_tres_reportes_recientes_confirman_y_mandan():
    reportes = [Reporte(3, hace(m)) for m in (2, 5, 10)]
    f = fusionar(0.7, reportes, U, AHORA)
    assert f.confianza == "confirmado por turistas"
    assert color(f.valor_final, U) == "rojo"


def test_dudosos_pesan_pero_no_confirman():
    reportes = [Reporte(3, hace(m), peso=0.5, estado="dudoso") for m in (2, 5, 10)]
    f = fusionar(0.7, reportes, U, AHORA)
    assert f.n_reportes == 3
    assert f.confianza == "estimado"


def test_evaluar_con_ajuste_manual_vigente_y_vencido():
    ajuste = AjusteManual("rojo", "Cerrado por evento privado", hasta=AHORA + timedelta(hours=2))
    e = evaluar(0.7, U, [], AHORA, ajuste)
    assert (e.semaforo, e.ajuste_manual) == ("rojo", "Cerrado por evento privado")

    vencido = AjusteManual("rojo", "Obra", hasta=hace(1))
    e = evaluar(0.7, U, [], AHORA, vencido)
    assert (e.semaforo, e.ajuste_manual) == ("verde", None)


def test_evaluar_sin_estimacion():
    e = evaluar(None, U, [Reporte(3, hace(1))], AHORA)
    assert (e.semaforo, e.valor_final, e.confianza) == ("sin_dato", None, "estimado")


# ───────────── Filtros antispam (RN_04 a RN_06) ─────────────

COCHE = {(1, 2): 20.0, (2, 1): 20.0}


def minutos_coche(a, b):
    return COCHE.get((a, b))


def test_filtro_gps_y_geocerca():
    sin_gps = filtrar(1, AHORA, True, None, [], minutos_coche)
    assert (sin_gps.estado, sin_gps.peso) == ("valido", 0.5)
    cerca = filtrar(1, AHORA, True, 120, [], minutos_coche)
    assert (cerca.estado, cerca.peso, cerca.motivo) == ("valido", 1.0, None)
    lejos = filtrar(1, AHORA, True, 900, [], minutos_coche)
    assert (lejos.estado, lejos.peso) == ("dudoso", 0.5)


def test_filtro_cerrado_y_repetido():
    assert filtrar(1, AHORA, False, None, [], minutos_coche).estado == "descartado"
    rep = filtrar(1, AHORA, True, None, [ReportePrevio(1, hace(10))], minutos_coche)
    assert rep.estado == "descartado" and rep.motivo.endswith("13:20")
    assert filtrar(1, AHORA, True, None, [ReportePrevio(1, hace(31))], minutos_coche).estado == "valido"


def test_filtro_velocidad_imposible_salvo_en_demo():
    previo = [ReportePrevio(2, hace(5))]               # 5 min desde un punto a 20 min en coche
    f = filtrar(1, AHORA, True, None, previo, minutos_coche)
    assert f.estado == "descartado" and f.descartar_sesion
    assert filtrar(1, AHORA, True, None, previo, minutos_coche, es_demo=True).estado == "valido"
    assert filtrar(1, AHORA, True, None, [ReportePrevio(2, hace(15))], minutos_coche).estado == "valido"
