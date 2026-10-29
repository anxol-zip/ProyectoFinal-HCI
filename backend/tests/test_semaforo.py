import pytest

from turismo_core import semaforo
from turismo_core.semaforo import (
    UMBRALES_GENERALES,
    Umbrales,
    calcular_umbrales,
    color,
    serie_relativa,
    umbrales_manuales,
)


def test_serie_relativa_divide_entre_la_mediana_e_ignora_ceros():
    assert serie_relativa([100, 200, 300, 0, None]) == [0.5, 1.0, 1.5]


def test_serie_relativa_vacia():
    assert serie_relativa([0, None]) == []


def test_poca_historia_usa_cortes_generales():
    u = calcular_umbrales([1.0] * 5)
    assert (u.bajo, u.alto, u.metodo, u.n_muestras) == (0.9, 1.3, "general", 5)


def test_punto_estable_y_punto_estacional_tienen_umbrales_distintos():
    estable = calcular_umbrales([0.95, 1.0, 1.05] * 8)
    estacional = calcular_umbrales([0.6, 0.8, 1.0, 1.2, 1.5, 1.7] * 4)
    assert estable.metodo == estacional.metodo == "percentil"
    assert estacional.alto > estable.alto
    # El mismo valor es rojo en el punto estable y amarillo en el estacional
    assert color(1.4, estable) == "rojo"
    assert color(1.4, estacional) == "amarillo"


def test_umbrales_quedan_acotados_y_separados():
    u = calcular_umbrales([1.0] * 24)  # historia plana: todos los percentiles = 1.0
    assert semaforo.BAJO_MIN <= u.bajo <= semaforo.BAJO_MAX
    assert u.alto - u.bajo >= semaforo.SEPARACION_MIN - 1e-9


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(None, "sin_dato"), (0.5, "verde"), (0.9, "amarillo"), (1.3, "amarillo"), (1.31, "rojo")],
)
def test_color_con_cortes_generales(valor, esperado):
    assert color(valor, UMBRALES_GENERALES) == esperado


def test_umbrales_manuales():
    u = umbrales_manuales(0.7, 1.0)
    assert u.metodo == "manual"
    assert color(1.1, u) == "rojo"


def test_umbrales_invalidos():
    with pytest.raises(ValueError):
        Umbrales(1.2, 1.0, "manual")
