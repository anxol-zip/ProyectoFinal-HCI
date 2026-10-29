"""Estado del semáforo de un punto: junta umbrales, reportes y ajuste manual.

Devuelve las columnas derivadas de ``afluencia_estimada`` (docs/05) más lo que
la app necesita para explicar el color (umbrales y si hubo ajuste manual).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from turismo_core.reportes import Confianza, Reporte, fusionar
from turismo_core.semaforo import AjusteManual, Color, Umbrales, color, color_final


@dataclass(frozen=True)
class EstadoSemaforo:
    estimacion: float | None
    valor_final: float | None
    n_reportes: int
    semaforo: Color
    confianza: Confianza
    umbrales: Umbrales
    ajuste_manual: str | None      # motivo, si el color lo fijó la Secretaría


def evaluar(
    estimacion: float | None,
    umbrales: Umbrales,
    reportes: Iterable[Reporte],
    ahora: datetime,
    ajuste: AjusteManual | None = None,
) -> EstadoSemaforo:
    if estimacion is None:
        valor, n, confianza = None, 0, "estimado"
    else:
        f = fusionar(estimacion, reportes, umbrales, ahora)
        valor, n, confianza = f.valor_final, f.n_reportes, f.confianza

    mostrado, es_manual = color_final(color(valor, umbrales), ajuste, ahora)
    return EstadoSemaforo(
        estimacion=estimacion,
        valor_final=valor,
        n_reportes=n,
        semaforo=mostrado,
        confianza=confianza,
        umbrales=umbrales,
        ajuste_manual=ajuste.motivo if es_manual and ajuste else None,
    )
