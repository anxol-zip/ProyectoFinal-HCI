"""Asistente con RAG (CU_06, RN_10): responde solo con nuestros datos y cita sus fuentes."""

from __future__ import annotations

import json

from fastapi import APIRouter

from app.deps import Ahora, Con
from app.schemas import ChatIn, ChatOut
from turismo_core import rag
from turismo_core.servicio import NoEncontrado

router = APIRouter(tags=["asistente"])


@router.post("/chat", response_model=ChatOut)
def chat(c: ChatIn, con: Con, ahora: Ahora):
    """Pregunta abierta ("tengo 4 horas y llueve, ¿qué hago?"). Qwen3 en Ollama, local; sin internet.
    Si Ollama no está, responde 503."""
    origen, intereses = c.origen_id, []
    if c.sesion_id:
        s = con.execute("SELECT perfil FROM sesion WHERE id = ?", (c.sesion_id,)).fetchone()
        if s is None:
            raise NoEncontrado("Sesión no encontrada: pide una nueva con POST /api/sesiones")
        perfil = json.loads(s["perfil"] or "{}")
        origen = origen if origen is not None else perfil.get("origen_id")
        intereses = perfil.get("intereses", [])
    if origen is not None and con.execute("SELECT 1 FROM punto WHERE id = ?", (origen,)).fetchone() is None:
        raise NoEncontrado(f"No existe el punto {origen}")
    return rag.preguntar(con, ahora, c.pregunta, origen, intereses)
