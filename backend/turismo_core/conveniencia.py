"""Índice de conveniencia: qué tan buena idea es ir a un punto **ahora** (docs/05, Capa 1).

    conveniencia = 0.40 · afluencia + 0.25 · clima + 0.35 · traslado      (cada parte de 0 a 1)

Si no se sabe desde dónde sale el turista, el traslado no cuenta y los otros dos pesos se reparten.

Pesos definidos por el equipo y documentados (supuesto):

- **Afluencia**: 1 hasta el umbral ``bajo`` del punto; baja en línea recta a 0.4 en el umbral
  ``alto``; arriba del rojo sigue bajando (0.4 · alto / nivel). Si la Secretaría fijó el color a mano
  (RN_16), se usa el color: verde 1, amarillo 0.6, rojo 0.1.
- **Clima**: techado 1; al aire libre 1 sin lluvia, 0.6 con lluvia moderada y 0.2 con lluvia fuerte.
- **Traslado**: 1 a 0 minutos, 0 a 60 minutos o más (RN_02: una alternativa está a menos de 1 h).
"""

from __future__ import annotations

from dataclasses import dataclass

from turismo_core.situacion import PuntoAhora

PESOS = {"afluencia": 0.40, "clima": 0.25, "traslado": 0.35}
MAX_MINUTOS = 60.0
POR_COLOR_MANUAL = {"verde": 1.0, "amarillo": 0.6, "rojo": 0.1}
CLIMA_AIRE_LIBRE = {"sin": 1.0, "moderada": 0.6, "fuerte": 0.2}


@dataclass(frozen=True)
class Conveniencia:
    total: float
    afluencia: float
    clima: float
    traslado: float | None      # None: no se sabe el origen


def parte_afluencia(p: PuntoAhora) -> float:
    if p.estado is None or p.estado.valor_final is None:
        return 0.0
    if p.estado.ajuste_manual:
        return POR_COLOR_MANUAL.get(p.estado.semaforo, 0.0)
    v, u = p.estado.valor_final, p.estado.umbrales
    if v <= u.bajo:
        return 1.0
    if v <= u.alto:
        return 1.0 - 0.6 * (v - u.bajo) / (u.alto - u.bajo)
    return 0.4 * u.alto / v


def parte_clima(p: PuntoAhora) -> float:
    return 1.0 if p.interior else CLIMA_AIRE_LIBRE[p.lluvia]


def parte_traslado(minutos: float) -> float:
    return max(0.0, 1.0 - minutos / MAX_MINUTOS)


def conveniencia(p: PuntoAhora, minutos: float | None) -> Conveniencia:
    """``minutos=None``: no se conoce el origen; el traslado no cuenta."""
    a, c = parte_afluencia(p), parte_clima(p)
    if minutos is None:
        total = (PESOS["afluencia"] * a + PESOS["clima"] * c) / (PESOS["afluencia"] + PESOS["clima"])
        return Conveniencia(round(total, 3), round(a, 3), round(c, 3), None)
    t = parte_traslado(minutos)
    total = PESOS["afluencia"] * a + PESOS["clima"] * c + PESOS["traslado"] * t
    return Conveniencia(round(total, 3), round(a, 3), round(c, 3), round(t, 3))
