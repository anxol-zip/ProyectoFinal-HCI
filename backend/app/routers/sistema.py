"""Revisión antes de la demo (``/api/salud``)."""

from __future__ import annotations

import json
import urllib.request

from fastapi import APIRouter, Request

from app.deps import Ahora, Con, EsDemo
from turismo_core import llm, trafico, vector
from turismo_core.config import clave
from turismo_core.servicio import frescura

router = APIRouter(tags=["sistema"])
OLLAMA = llm.URL + "/api/tags"


def _ollama() -> dict:
    try:
        with urllib.request.urlopen(OLLAMA, timeout=1) as r:
            return {"disponible": True, "modelos": [m["name"] for m in json.load(r).get("models", [])]}
    except (OSError, ValueError):
        return {"disponible": False, "modelos": []}


def _chroma() -> dict:
    try:
        return vector.conteos()
    except Exception as e:  # sin índice o carpeta dañada: se dice, no se cae /salud
        return {"error": repr(e)}


@router.get("/salud")
def salud(con: Con, ahora: Ahora, demo: EsDemo, request: Request):
    """SQLite, frescura del clima y la afluencia, claves presentes (sin mostrarlas), Ollama y la última actualización."""
    cuenta = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    programador = getattr(request.app.state, "programador", None)
    return {
        "modo_demo": demo,
        "bd": {
            "puntos": cuenta("SELECT COUNT(*) FROM punto"),
            "puntos_verificados": cuenta("SELECT COUNT(*) FROM punto WHERE verificado = 1"),
            "eventos_verificados": cuenta("SELECT COUNT(*) FROM evento WHERE verificado = 1"),
            "pares_traslado": cuenta("SELECT COUNT(*) FROM matriz_traslado"),
            "sesiones": cuenta("SELECT COUNT(*) FROM sesion"),
            "reportes": cuenta("SELECT COUNT(*) FROM reporte"),
        },
        "datos": frescura(con, ahora),
        "claves": {"ORS_API_KEY": clave("ORS_API_KEY") is not None, "TOMTOM_API_KEY": clave("TOMTOM_API_KEY") is not None},
        "ollama": _ollama() | {"modelo": llm.MODELO, "embeddings": llm.EMBED},
        "chroma": _chroma(),
        "actualizacion": None if programador is None else programador.ultima,
        "trafico": {"corredores_vigentes": len(trafico.factores_vigentes(con, ahora).por_tramo),
                    "ultima_tarea": None if programador is None else programador.trafico},
    }
