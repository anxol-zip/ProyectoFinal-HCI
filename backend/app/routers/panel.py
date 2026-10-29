"""Panel de gobierno (CU_07): solo agregados (RN_12); la demo del stand se separa (RN_11)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from app.deps import Ahora, Con
from app.schemas import AjusteIn
from turismo_core import panel

router = APIRouter(prefix="/panel", tags=["panel"])


@router.get("/afluencia")
def afluencia(con: Con, ahora: Ahora, incluir_demo: bool = False):
    """Mapa de calor: estado de cada punto ahora y totales del día (reportes y redirecciones)."""
    return panel.afluencia(con, ahora, incluir_demo)


@router.get("/redirecciones")
def redirecciones(con: Con, ahora: Ahora, desde: date | None = None, hasta: date | None = None,
                  incluir_demo: bool = False):
    """De dónde → a dónde → por qué. Por defecto, hoy."""
    return panel.redirecciones(con, desde or ahora.date(), hasta or ahora.date(), incluir_demo)


@router.get("/derrama")
def derrama(con: Con, ahora: Ahora, desde: date | None = None, hasta: date | None = None,
            incluir_demo: bool = False):
    """Derrama **redistribuida** y **nueva estimada** (RN_14), con el gasto por visitante de cada destino
    (Observatorio) y el supuesto escrito. Por defecto, hoy."""
    return panel.derrama(con, desde or ahora.date(), hasta or ahora.date(), incluir_demo)


@router.get("/semaforo-estatal")
def semaforo_estatal(con: Con, ahora: Ahora, mes: int | None = Query(default=None, ge=1, le=12),
                     anio: int | None = Query(default=None, ge=2017, le=2100)):
    """Los destinos del Observatorio en un mes contra su propia historia. Por defecto, el mes actual
    (si no está publicado, sale estimado con el promedio del mismo mes de los últimos 3 años)."""
    return panel.semaforo_estatal(con, mes or ahora.month, anio or ahora.year)


@router.get("/umbrales")
def umbrales(con: Con):
    """Umbrales ``bajo``/``alto`` de cada punto y su método (explica el color)."""
    return panel.umbrales(con)


@router.get("/ajustes")
def ajustes(con: Con, ahora: Ahora):
    """Ajustes manuales vigentes."""
    return panel.ajustes_vigentes(con, ahora)


@router.post("/ajustes")
def fijar_ajuste(a: AjusteIn, con: Con, ahora: Ahora):
    """"Fijar color" (RN_16): gana sobre el cálculo hasta que vence; el turista ve el motivo."""
    return panel.fijar_ajuste(con, ahora, a.punto_id, a.color, a.motivo, a.horas)


@router.delete("/ajustes/{ajuste_id}")
def quitar_ajuste(ajuste_id: int, con: Con, ahora: Ahora):
    """Termina un ajuste antes de su hora de fin."""
    return panel.quitar_ajuste(con, ahora, ajuste_id)
