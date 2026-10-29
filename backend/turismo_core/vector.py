"""ChromaDB: la base de conocimiento (texto) del asistente, junto a SQLite (números). docs/05b.

Una sola conexión por proceso. Por defecto, ``PersistentClient`` en ``backend/data/chroma``
(ignorada por git; se reconstruye con ``scripts.indexar_chroma``). Con ``CHROMA_HOST`` se usa un
servidor local (``chroma run``), por si FastAPI y el servidor MCP necesitan compartirla (paso 9).

Los embeddings los calcula ``llm.embeber`` (bge-m3 en Ollama) y se le pasan a Chroma ya hechos;
las colecciones usan distancia coseno.
"""

from __future__ import annotations

import chromadb
from chromadb.config import Settings

from turismo_core.bd import DATA
from turismo_core.config import clave

RUTA = DATA / "chroma"
COLECCIONES = ("puntos", "eventos", "conocimiento", "bitacora", "establecimientos")

_cliente = None


def cliente():
    global _cliente
    if _cliente is None:
        ajustes = Settings(anonymized_telemetry=False)      # nada sale a internet
        host = clave("CHROMA_HOST")
        _cliente = (chromadb.HttpClient(host=host, port=int(clave("CHROMA_PORT") or 8001), settings=ajustes)
                    if host else chromadb.PersistentClient(path=str(RUTA), settings=ajustes))
    return _cliente


def coleccion(nombre: str):
    return cliente().get_or_create_collection(name=nombre, embedding_function=None,
                                              configuration={"hnsw": {"space": "cosine"}})


def conteos() -> dict[str, int]:
    return {n: coleccion(n).count() for n in COLECCIONES}
