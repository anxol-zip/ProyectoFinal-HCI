"""Sesión, "mejor ve a…" y "¿Cómo está?" (CU_01, CU_04, CU_05)."""

from __future__ import annotations

from fastapi import APIRouter

from app.deps import Ahora, Con, EsDemo
from app.schemas import (RecomendacionOut, RecomendarIn, ReporteIn, ReporteOut, RespuestaBusquedaIn,
                         RespuestaBusquedaOut, SesionIn, SesionOut)
from turismo_core import servicio

router = APIRouter(tags=["turista"])


@router.post("/sesiones", response_model=SesionOut)
def crear_sesion(s: SesionIn, con: Con, ahora: Ahora, demo: EsDemo):
    """Al abrir la app. El servidor genera el ``sesion_id``; sin cuenta ni datos personales (RN_07)."""
    return servicio.crear_sesion(con, ahora, s.intereses, s.horas, s.origen_id, es_demo=demo)


@router.post("/recomendar", response_model=RecomendacionOut)
def recomendar(r: RecomendarIn, con: Con, ahora: Ahora):
    """"Mejor ve a…": si el punto está en rojo, cerrado o con lluvia fuerte al aire libre, propone otro
    (nunca en rojo, parecido y a menos de 1 h, RN_02) y otra hora. Sin ``punto_id``: el mejor lugar ahora."""
    return servicio.recomendar(con, ahora, r.sesion_id, r.punto_id, r.origen_id, r.intereses, r.horas)


@router.post("/busquedas/{busqueda_id}/aceptar", response_model=RespuestaBusquedaOut)
def aceptar(busqueda_id: int, con: Con, r: RespuestaBusquedaIn | None = None):
    """El turista eligió la alternativa ("Vamos") o no ("Prefiero mi plan", con ``aceptada: false``)."""
    return servicio.responder_busqueda(con, busqueda_id, True if r is None else r.aceptada)


@router.post("/reportes", response_model=ReporteOut)
def reportar(r: ReporteIn, con: Con, ahora: Ahora):
    """Botón "¿Cómo está?". Filtros antispam (RN_04 a RN_06) y el estado nuevo del punto."""
    return servicio.registrar_reporte(con, ahora, r.sesion_id, r.punto_id, r.nivel, r.espera_min, r.distancia_m)
