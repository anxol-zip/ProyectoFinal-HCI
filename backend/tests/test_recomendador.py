from datetime import datetime

import pytest

from turismo_core import conveniencia as cv
from turismo_core.estado import EstadoSemaforo
from turismo_core.recomendador import mejor_hora, motivo_de_cambio, recomendar, similitud, traslado
from turismo_core.semaforo import Umbrales
from turismo_core.situacion import PuntoAhora

U = Umbrales(1.0, 1.4, "percentil", 100)
AHORA = datetime(2026, 10, 18, 13)


def punto(pid, nivel, cats="historia", interior=True, lluvia="sin", abierto=True, color=None, manual=None):
    if not abierto:
        estado = None
    else:
        c = color or ("verde" if nivel < U.bajo else "amarillo" if nivel <= U.alto else "rojo")
        estado = EstadoSemaforo(nivel, nivel, 0, c, "estimado", U, manual)
    return PuntoAhora(pid, f"p{pid}", f"Punto {pid}", "D", "museo", frozenset(cats.split(",")), interior,
                      19.0, -98.2, abierto, estado, lluvia)


# (origen, destino) -> (coche, pie)
MATRIZ = {(1, 2): (7.0, 58.0), (1, 3): (25.0, 160.0), (1, 4): (80.0, 400.0), (1, 5): (5.0, 12.0)}


def test_similitud_coseno_de_categorias():
    assert similitud({"historia"}, {"historia"}) == 1.0
    assert similitud({"historia", "arte"}, {"historia"}) == pytest.approx(0.707, abs=1e-3)
    assert similitud({"historia"}, {"naturaleza"}) == 0.0
    assert similitud(set(), {"historia"}) == 0.0


def test_traslado_a_pie_si_es_cerca():
    assert traslado(1, 5, MATRIZ) == (12.0, "a pie")
    assert traslado(1, 2, MATRIZ) == (7.0, "en coche")
    assert traslado(1, 1, MATRIZ) == (0.0, "a pie")
    assert traslado(None, 2, MATRIZ) == (None, None)


def test_motivo_de_cambio():
    assert motivo_de_cambio(punto(1, 2.0)) == "afluencia"
    assert motivo_de_cambio(punto(1, 0.5, abierto=False)) == "cerrado"
    assert motivo_de_cambio(punto(1, 0.5, interior=False, lluvia="fuerte")) == "lluvia"
    assert motivo_de_cambio(punto(1, 0.5, interior=True, lluvia="fuerte")) is None
    assert motivo_de_cambio(punto(1, 1.2)) is None


def test_conveniencia_por_partes():
    assert cv.parte_afluencia(punto(1, 0.8)) == 1.0
    assert cv.parte_afluencia(punto(1, 1.4)) == pytest.approx(0.4)
    assert cv.parte_afluencia(punto(1, 2.8)) == pytest.approx(0.2)
    assert cv.parte_afluencia(punto(1, 0.5, color="rojo", manual="Obra")) == cv.POR_COLOR_MANUAL["rojo"]
    assert cv.parte_clima(punto(1, 1, interior=False, lluvia="fuerte")) == 0.2
    assert cv.parte_traslado(30) == 0.5 and cv.parte_traslado(90) == 0.0
    sin_origen = cv.conveniencia(punto(1, 0.8), None)
    assert sin_origen.traslado is None and sin_origen.total == 1.0


def test_alternativa_nunca_roja_ni_cerrada_ni_lejos_y_parecida():
    puntos = {
        1: punto(1, 3.0, "historia,cultura"),          # pedido, en rojo
        2: punto(2, 0.7, "historia"),                  # verde, 7 min: la buena
        3: punto(3, 2.0, "historia"),                  # rojo
        4: punto(4, 0.5, "historia"),                  # verde pero a 80 min
        5: punto(5, 0.5, "naturaleza"),                # verde y cerca pero no se parece
    }
    r = recomendar(puntos, MATRIZ, AHORA, pedido_id=1)
    assert r.motivo == "afluencia" and r.alternativa.punto.id == 2
    assert {c.punto.id for c in r.otras} == set()
    assert "en rojo" in r.razon and "Punto 2" in r.razon and "7 min en coche" in r.razon


def test_propone_otra_hora():
    puntos = {1: punto(1, 3.0), 2: punto(2, 0.7)}
    pron = [(datetime(2026, 10, 18, 14), "rojo", 2.0), (datetime(2026, 10, 18, 15), "amarillo", 1.2),
            (datetime(2026, 10, 18, 16), "verde", 0.8)]
    r = recomendar(puntos, MATRIZ, AHORA, pedido_id=1, pronostico_pedido=pron)
    assert r.otra_hora.hora == datetime(2026, 10, 18, 16) and r.otra_hora.color == "verde"
    assert "regresa a las 16:00" in r.razon


def test_mejor_hora_al_dia_siguiente():
    pron = [(datetime(2026, 10, 18, 14), "rojo", 2.0), (datetime(2026, 10, 19, 10), "amarillo", 1.1)]
    assert mejor_hora(pron).hora == datetime(2026, 10, 19, 10)
    assert mejor_hora([(datetime(2026, 10, 18, 14), "cerrado", None)]) is None


def test_si_llueve_al_aire_libre_prefiere_techado():
    puntos = {
        1: punto(1, 0.8, "historia", interior=False, lluvia="fuerte"),
        2: punto(2, 0.7, "historia", interior=False, lluvia="fuerte"),
        3: punto(3, 0.9, "historia", interior=True, lluvia="fuerte"),
    }
    r = recomendar(puntos, MATRIZ, AHORA, pedido_id=1)
    assert r.motivo == "lluvia" and r.alternativa.punto.id == 3 and "(techado)" in r.razon


def test_si_esta_bien_no_cambia():
    r = recomendar({1: punto(1, 0.8), 2: punto(2, 0.5)}, MATRIZ, AHORA, pedido_id=1)
    assert r.motivo is None and r.alternativa is None and "buen momento" in r.razon


def test_sin_pedido_usa_intereses_y_poco_tiempo_limita_el_traslado():
    puntos = {1: punto(1, 0.5, "historia"), 2: punto(2, 0.5, "naturaleza"), 3: punto(3, 0.5, "naturaleza")}
    r = recomendar(puntos, MATRIZ, AHORA, intereses=["naturaleza"])
    assert r.alternativa.punto.id in (2, 3) and "naturaleza" in r.razon
    # Con 1 h, el traslado máximo es de 20 min: el punto 3 (25 min) queda fuera.
    r = recomendar(puntos, MATRIZ, AHORA, origen_id=1, intereses=["naturaleza"], horas=1)
    assert r.alternativa.punto.id == 2 and not r.otras
