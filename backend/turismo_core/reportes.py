"""Fusión de la afluencia estimada con los reportes de turistas.

Fórmula de docs/05 ("Cómo se combinan con la estimación") y RN_08/RN_09 de docs/10:

    afluencia = (w_m · estimación + Σ w_i · r_i) / (w_m + Σ w_i)
    w_i = peso_i · exp(−Δt_i / 45 min)

- ``w_m`` vale lo mismo que ~2 reportes recientes.
- Un reporte de hace 30 min pesa ~la mitad; a las 3 h ya casi no cuenta.
- Con 3 o más reportes ``valido`` en la última hora: "confirmado por turistas".

Los reportes vienen en niveles 1 vacío · 2 normal · 3 lleno. Para mezclarlos con la
estimación (escala relativa del punto) se traducen con **los umbrales de ese punto**:
vacío = bajo × 0.5, normal = punto medio, lleno = alto × 1.5. Así "lleno" siempre
cae en rojo y "vacío" en verde, sea el punto estable o estacional, y bastan ~3
reportes recientes para voltear el color que dio el modelo.

Los filtros antispam (RN_04 a RN_06, docs/05 "Filtros antes de aceptar un reporte")
deciden ``estado`` y ``peso`` al recibir el reporte (``filtrar``):

- Punto cerrado: ``descartado``.
- Misma sesión y mismo punto hace menos de 30 min: ``descartado`` (RN_05).
- Velocidad imposible: el reporte anterior de la sesión fue en otro punto y no da tiempo de
  llegar ni en coche sin tráfico (menos de la mitad del tiempo de OpenRouteService; el 0.5 es
  **supuesto**, sacado del ejemplo de docs/05: 20 km en 5 min). Se descarta la sesión completa.
  No se aplica a las sesiones de demo: en el stand un evaluador reporta varios puntos seguidos.
- Sin GPS (``distancia_m`` desconocida): ``valido`` con peso 0.5 (docs/05).
- A más de 500 m del punto: ``dudoso`` con peso 0.5 (el peso es **supuesto**; docs/05 no lo fija).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from turismo_core.semaforo import Umbrales

Estado = Literal["valido", "dudoso", "descartado"]
Confianza = Literal["estimado", "confirmado por turistas"]

TAU_MIN = 45.0                     # caducidad exponencial (docs/05)
PESO_MODELO = 2.0                  # la estimación vale ~2 reportes
VENTANA_CONFIRMADO = timedelta(hours=1)
MIN_CONFIRMADO = 3
VIDA_MAX = timedelta(hours=3)      # después de esto el reporte ni se lee


@dataclass(frozen=True)
class Reporte:
    nivel: Literal[1, 2, 3]        # 1 vacío · 2 normal · 3 lleno
    creado_en: datetime
    peso: float = 1.0              # confianza de los filtros antispam (0 a 1)
    estado: Estado = "valido"


@dataclass(frozen=True)
class Fusion:
    valor_final: float
    n_reportes: int                # reportes que sí pesaron
    confianza: Confianza


def valor_de_nivel(nivel: int, umbrales: Umbrales) -> float:
    """Traduce el nivel reportado a la escala relativa del punto."""
    if nivel == 1:
        return umbrales.bajo * 0.5
    if nivel == 2:
        return (umbrales.bajo + umbrales.alto) / 2
    if nivel == 3:
        return umbrales.alto * 1.5
    raise ValueError(f"Nivel inválido: {nivel}")


def peso_temporal(reporte: Reporte, ahora: datetime) -> float:
    """Peso del reporte después de la caducidad; 0 si está descartado, es viejo o futuro."""
    if reporte.estado == "descartado":
        return 0.0
    edad = ahora - reporte.creado_en
    if edad < timedelta(0) or edad > VIDA_MAX:
        return 0.0
    return max(0.0, reporte.peso) * math.exp(-edad.total_seconds() / 60 / TAU_MIN)


def fusionar(
    estimacion: float,
    reportes: Iterable[Reporte],
    umbrales: Umbrales,
    ahora: datetime,
) -> Fusion:
    """Afluencia final del punto: estimación corregida con los reportes."""
    num = PESO_MODELO * estimacion
    den = PESO_MODELO
    n_pesan = 0
    n_validos_hora = 0
    for r in reportes:
        w = peso_temporal(r, ahora)
        if w <= 0:
            continue
        num += w * valor_de_nivel(r.nivel, umbrales)
        den += w
        n_pesan += 1
        if r.estado == "valido" and ahora - r.creado_en <= VENTANA_CONFIRMADO:
            n_validos_hora += 1

    confianza: Confianza = (
        "confirmado por turistas" if n_validos_hora >= MIN_CONFIRMADO else "estimado"
    )
    return Fusion(round(num / den, 3), n_pesan, confianza)


# ───────────── Filtros antispam (RN_04 a RN_06) ─────────────

RADIO_M = 500.0
PESO_SIN_GPS = 0.5
PESO_DUDOSO = 0.5                  # supuesto
ESPERA_REPETIDO = timedelta(minutes=30)
FACTOR_VELOCIDAD = 0.5             # supuesto


@dataclass(frozen=True)
class ReportePrevio:
    """Un reporte anterior de la misma sesión (no descartado)."""
    punto_id: int
    creado_en: datetime


@dataclass(frozen=True)
class Filtro:
    estado: Estado
    peso: float
    motivo: str | None             # por qué no es un reporte normal (se guarda y se muestra)
    descartar_sesion: bool = False


def filtrar(
    punto_id: int,
    ahora: datetime,
    abierto: bool,
    distancia_m: float | None,
    previos: Sequence[ReportePrevio],
    minutos_coche: Callable[[int, int], float | None],
    es_demo: bool = False,
) -> Filtro:
    """Decide el estado y el peso de un reporte nuevo. ``minutos_coche(a, b)`` sale de la matriz de ORS."""
    if not abierto:
        return Filtro("descartado", 0.0, "punto cerrado")

    mismo = [r for r in previos if r.punto_id == punto_id and ahora - r.creado_en < ESPERA_REPETIDO]
    if mismo:
        otra_vez = max(r.creado_en for r in mismo) + ESPERA_REPETIDO
        return Filtro("descartado", 0.0, f"repetido: de nuevo a las {otra_vez:%H:%M}")

    if not es_demo:
        otros = [r for r in previos if r.punto_id != punto_id and r.creado_en <= ahora]
        if otros:
            ultimo = max(otros, key=lambda r: r.creado_en)
            minutos = minutos_coche(ultimo.punto_id, punto_id)
            transcurrido = (ahora - ultimo.creado_en).total_seconds() / 60
            if minutos is not None and transcurrido < FACTOR_VELOCIDAD * minutos:
                return Filtro("descartado", 0.0,
                              f"velocidad imposible: {transcurrido:.0f} min desde otro punto a {minutos:.0f} min en coche",
                              descartar_sesion=True)

    if distancia_m is None:
        return Filtro("valido", PESO_SIN_GPS, "sin GPS")
    if distancia_m > RADIO_M:
        return Filtro("dudoso", PESO_DUDOSO, f"a {distancia_m:.0f} m del punto")
    return Filtro("valido", 1.0, None)
