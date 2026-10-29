from datetime import date, datetime

import pytest

from turismo_core import afluencia as af
from turismo_core.afluencia import Contexto, EventoActivo, Perfil

CTX = Contexto()


def _perfil(tipo="museo", horario='{"mar": "10:00-17:00", "mie": "10:00-17:00", "jue": "10:00-17:00", '
            '"vie": "10:00-17:00", "sab": "10:00-17:00", "dom": "10:00-17:00"}', mensual=None, **kw) -> Perfil:
    h, confirmado = af.leer_horario(horario, tipo)
    # 100 visitas por día abierto en todos los meses de la historia, salvo julio (doble).
    if mensual is None:
        mensual = {}
        for a in af.AÑOS_HISTORIA:
            for m in range(1, 13):
                n = len(af.dias_abiertos(h, a, m))
                mensual[(a, m)] = 100.0 * n * (2 if m == 7 else 1)
    return Perfil(1, "x", tipo, True, "inah", mensual, h, confirmado, **kw)


def test_leer_horario_oficial_y_supuesto():
    h, ok = af.leer_horario('{"jue": "10:00-17:00", "dom": "09:00-14:00"}', "museo")
    assert ok and h == {3: [(10, 17)], 6: [(9, 14)]}
    h, ok = af.leer_horario(None, "museo")
    assert not ok and 0 not in h and h[1] == [(10, 18)]        # museo supuesto: cierra en lunes
    assert af.horas_abiertas({3: [(10, 17)]}, 3) == [10, 11, 12, 13, 14, 15, 16]
    assert af.horas_abiertas({3: [(10, 17)]}, 4) == []


def test_horario_con_dos_turnos_y_medias_horas():
    # Capilla del Rosario: 9:00–13:30 y 15:30–18:00 (Ayuntamiento de Puebla).
    h, _ = af.leer_horario('{"mar": "09:00-13:30,15:30-18:00"}', "templo")
    assert h == {1: [(9, 14), (15, 18)]}
    assert af.horas_abiertas(h, 1) == [9, 10, 11, 12, 13, 15, 16, 17]   # cerrado de 14 a 15


def test_base_mes_es_relativa_a_la_mediana_del_punto():
    p = _perfil()
    assert p.base_mes(2026, 3) == pytest.approx(1.0)
    assert p.base_mes(2026, 7) == pytest.approx(2.0)


def test_factores_de_dia_y_hora_promedian_uno():
    p = _perfil()
    abiertos = af.dias_abiertos(p.horario, 2026, 10)
    assert sum(af.f_dia(p, d, CTX) for d in abiertos) / len(abiertos) == pytest.approx(1.0)
    horas = af.horas_abiertas(p.horario, 2)
    assert sum(af.f_hora(p, datetime(2026, 10, 21, h)) for h in horas) / len(horas) == pytest.approx(1.0)


def test_domingo_pesa_mas_y_mediodia_mas_que_la_manana():
    p = _perfil()
    dom, mie = date(2026, 10, 18), date(2026, 10, 21)
    assert af.f_dia(p, dom, CTX) > af.f_dia(p, mie, CTX)
    assert af.f_hora(p, datetime(2026, 10, 21, 13)) > af.f_hora(p, datetime(2026, 10, 21, 10))


def test_cerrado_no_tiene_estimacion():
    p = _perfil()
    lunes = af.estimar(p, 1, datetime(2026, 10, 19, 12), CTX)
    noche = af.estimar(p, 1, datetime(2026, 10, 21, 20), CTX)
    abierto = af.estimar(p, 1, datetime(2026, 10, 21, 12, 40), CTX)
    assert not lunes.abierto and lunes.estimacion is None
    assert not noche.abierto and noche.estimacion is None
    assert abierto.abierto and abierto.estimacion > 0
    assert abierto.para_hora == datetime(2026, 10, 21, 12)    # se redondea a la hora


def test_festivo_cuenta_como_domingo_salvo_en_el_inah():
    festivo = date(2026, 11, 16)                                  # lunes, Revolución
    ctx = Contexto(festivos=frozenset({festivo}))
    otro = _perfil(horario=None, tipo="templo")
    inah = _perfil(horario=None, tipo="templo", peso_domingo=3.0, domingo_es_dato=True)
    assert af.peso_dia(otro, festivo, ctx) == af.PESOS_DIA[af.DOMINGO]
    assert af.peso_dia(inah, festivo, ctx) == af.PESOS_DIA[af.SABADO]


def test_puente_sube_el_fin_de_semana():
    sabado = date(2026, 11, 14)
    p = _perfil()
    assert af.peso_dia(p, sabado, Contexto(puentes=frozenset({sabado}))) == pytest.approx(
        af.PESOS_DIA[af.SABADO] * af.F_PUENTE)


def test_evento_verificado_del_punto_o_del_destino():
    p = _perfil()
    momento = datetime(2026, 10, 21, 12)
    del_punto = EventoActivo("A", "alto", 1, None, datetime(2026, 10, 1), datetime(2026, 11, 1))
    otro_destino = EventoActivo("B", "medio", None, 9, datetime(2026, 10, 1), datetime(2026, 11, 1))
    pasado = EventoActivo("C", "alto", 1, None, datetime(2026, 9, 1), datetime(2026, 9, 30))
    f, nombres = af.f_evento(p, 5, momento, [del_punto, otro_destino, pasado])
    assert f == af.F_EVENTO["alto"] and nombres == ("A",)
    assert af.estimar(p, 5, momento, CTX, [del_punto]).estimacion == pytest.approx(
        af.estimar(p, 5, momento, CTX).estimacion * af.F_EVENTO["alto"], rel=1e-2)


def test_peso_domingo_inah_desde_entrada_dominical():
    h, _ = af.leer_horario(None, "zona_arqueologica")        # todos los días
    # Octubre 2026: 31 días abiertos, 4 domingos. 3,100 visitas pagadas (100/día) + 800 dominicales (200/domingo).
    assert af.peso_domingo_inah([("2026-10", 800, 3100)], h) == pytest.approx(3.0)
    assert af.peso_domingo_inah([("2026-10", 0, 3100)], h) is None
    assert af.peso_domingo_inah([("2026-10", 80000, 3100)], h) == af.DOMINGO_INAH_MAX


def test_umbrales_desde_historia_en_la_misma_escala():
    p = _perfil()
    u = af.umbrales_desde_historia(p, CTX)
    assert u.metodo == "percentil" and u.n_muestras > 1000
    assert 0 < u.bajo < u.alto
    # El pico de un domingo de julio sale en rojo; una mañana de miércoles de marzo, en verde.
    from turismo_core.semaforo import color
    assert color(af.estimar(p, 1, datetime(2026, 7, 19, 13), CTX).estimacion, u) == "rojo"
    assert color(af.estimar(p, 1, datetime(2026, 3, 18, 10), CTX).estimacion, u) == "verde"


def test_sin_historia_no_hay_base():
    p = _perfil(mensual={})
    assert p.base_mes(2026, 10) is None
    assert af.estimar(p, 1, datetime(2026, 10, 21, 12), CTX).estimacion is None
    assert af.umbrales_desde_historia(p, CTX).metodo == "general"
