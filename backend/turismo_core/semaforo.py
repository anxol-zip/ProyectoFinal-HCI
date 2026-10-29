"""Semáforo con umbrales por lugar.

Cada punto se compara contra **su propia historia** (escala relativa: 1.0 = un día
normal para ese lugar, ver docs/05 "Cómo se calcula la afluencia estimada").
En lugar de usar el mismo corte para todos, cada punto tiene dos umbrales,
``bajo`` y ``alto``, como en Druktebeeld de Ámsterdam (docs/10 - Referencias):

    valor <  bajo          -> verde
    bajo <= valor <= alto  -> amarillo
    valor >  alto          -> rojo

Los umbrales salen de percentiles de la serie histórica relativa del punto
(INAH u Observatorio). Si el punto tiene poca historia, se usan los cortes
generales de docs/05 (0.9 y 1.3). La Secretaría puede fijarlos a mano desde
el panel, y eso siempre gana.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from statistics import median, quantiles
from typing import Literal

Color = Literal["verde", "amarillo", "rojo", "sin_dato"]
Metodo = Literal["percentil", "general", "manual"]

# Cortes generales de docs/05; se usan cuando el punto no tiene historia suficiente.
BAJO_GENERAL = 0.9
ALTO_GENERAL = 1.3

# Percentiles de la historia del propio punto. "Rojo" = más lleno que el 85 % de sus meses.
PERCENTIL_BAJO = 60
PERCENTIL_ALTO = 85

# Con menos de un año de meses no se confía en los percentiles.
MIN_MUESTRAS = 12

# Límites para que un punto con historia rara no quede con cortes absurdos.
BAJO_MIN, BAJO_MAX = 0.8, 1.1
ALTO_MIN, ALTO_MAX = 1.15, 1.8
SEPARACION_MIN = 0.15


@dataclass(frozen=True)
class Umbrales:
    bajo: float
    alto: float
    metodo: Metodo
    n_muestras: int = 0

    def __post_init__(self) -> None:
        if not 0 < self.bajo < self.alto:
            raise ValueError(f"Umbrales inválidos: bajo={self.bajo}, alto={self.alto}")


UMBRALES_GENERALES = Umbrales(BAJO_GENERAL, ALTO_GENERAL, "general")


def serie_relativa(visitas: Sequence[float]) -> list[float]:
    """Convierte visitas absolutas en escala relativa: valor ÷ mediana del punto.

    Se ignoran meses sin dato (``None``) o en cero, como los cierres de 2020–2021.
    """
    validas = [float(v) for v in visitas if v is not None and v > 0]
    if not validas:
        return []
    m = median(validas)
    return [v / m for v in validas]


def calcular_umbrales(
    historia_relativa: Sequence[float],
    p_bajo: int = PERCENTIL_BAJO,
    p_alto: int = PERCENTIL_ALTO,
) -> Umbrales:
    """Umbrales de un punto a partir de su historia en escala relativa."""
    datos = [v for v in historia_relativa if v is not None and v > 0]
    if len(datos) < MIN_MUESTRAS:
        return Umbrales(BAJO_GENERAL, ALTO_GENERAL, "general", len(datos))

    cortes = quantiles(datos, n=100, method="inclusive")  # cortes[k-1] = percentil k
    bajo = _acotar(cortes[p_bajo - 1], BAJO_MIN, BAJO_MAX)
    alto = _acotar(cortes[p_alto - 1], ALTO_MIN, ALTO_MAX)
    alto = max(alto, bajo + SEPARACION_MIN)
    return Umbrales(round(bajo, 3), round(alto, 3), "percentil", len(datos))


def umbrales_manuales(bajo: float, alto: float) -> Umbrales:
    """Umbrales fijados por la Secretaría desde el panel (ganan sobre los calculados)."""
    return Umbrales(bajo, alto, "manual")


def color(valor: float | None, umbrales: Umbrales = UMBRALES_GENERALES) -> Color:
    """Color del semáforo para un valor de afluencia relativa."""
    if valor is None:
        return "sin_dato"
    if valor < umbrales.bajo:
        return "verde"
    if valor <= umbrales.alto:
        return "amarillo"
    return "rojo"


@dataclass(frozen=True)
class AjusteManual:
    """Color fijado a mano desde el panel (como el personal de East Lothian).

    Sirve para lo que el modelo no ve: un cierre, una fila de dos horas, una obra.
    Caduca en ``hasta`` para que nadie olvide quitarlo.
    """

    color: Color
    motivo: str
    hasta: datetime

    def vigente(self, ahora: datetime) -> bool:
        return ahora < self.hasta


def color_final(
    calculado: Color, ajuste: AjusteManual | None, ahora: datetime
) -> tuple[Color, bool]:
    """Color que se muestra y si viene de un ajuste manual vigente."""
    if ajuste is not None and ajuste.vigente(ahora):
        return ajuste.color, True
    return calculado, False


def _acotar(x: float, minimo: float, maximo: float) -> float:
    return min(max(x, minimo), maximo)
