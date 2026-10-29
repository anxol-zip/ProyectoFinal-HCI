"""Catálogo, semáforo y estado de un punto (CU_02, CU_03)."""

from __future__ import annotations

from fastapi import APIRouter

from app.deps import Ahora, Con
from app.schemas import PuntoCatalogo, PuntoDetalle, SemaforoOut, SemanaOut
from turismo_core import servicio

router = APIRouter(tags=["puntos"])


@router.get("/puntos", response_model=list[PuntoCatalogo])
def puntos(con: Con, destino: str | None = None, tipo: str | None = None):
    """Catálogo de la zona piloto, con la fuente de cada dato."""
    return servicio.catalogo(con, destino, tipo)


@router.get("/semaforo", response_model=SemaforoOut)
def semaforo(con: Con, ahora: Ahora, origen_id: int | None = None):
    """Todos los puntos con su color **ahora**, ordenados por conveniencia. Con ``origen_id`` trae el traslado."""
    return servicio.semaforo(con, ahora, origen_id)


@router.get("/puntos/{punto_id}/estado", response_model=PuntoDetalle)
def estado(punto_id: int, con: Con, ahora: Ahora, origen_id: int | None = None):
    """Tarjeta del punto: semáforo con su razón, próximas horas, clima, traslado, horario, eventos y fuente."""
    return servicio.estado_punto(con, punto_id, ahora, origen_id)


@router.get("/puntos/{punto_id}/semana", response_model=SemanaOut)
def semana(punto_id: int, con: Con, ahora: Ahora):
    """"¿Cuándo me conviene ir?": tabla día × hora de hoy y los días siguientes (estimado, sin reportes), con
    la hora más tranquila y la más llena de cada día."""
    return servicio.semana_punto(con, punto_id, ahora)
