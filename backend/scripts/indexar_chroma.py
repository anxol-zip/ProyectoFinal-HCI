"""Paso 8: llena ChromaDB con los textos de ``turismo_core.conocimiento`` (docs/05b §7).

    uv run python -m scripts.indexar_chroma            # todo
    uv run python -m scripts.indexar_chroma --ver      # solo imprime los textos, sin Ollama ni ChromaDB

IDs fijos + ``upsert``: correrlo otra vez actualiza los mismos documentos. Los documentos que ya no
existen (p. ej. un evento que dejó de estar verificado) se borran. Necesita Ollama con ``bge-m3``.
"""

from __future__ import annotations

import sys
import time
from datetime import date, timedelta

from turismo_core import conocimiento as cn
from turismo_core.bd import conectar


def documentos(con) -> dict[str, list[cn.Doc]]:
    return {
        "puntos": cn.docs_puntos(con),
        "eventos": cn.docs_eventos(con),
        "conocimiento": cn.docs_observatorio(con) + cn.docs_inah(con) + cn.docs_metodologia() + [cn.doc_fuentes(con)],
        "bitacora": cn.docs_bitacora(con, date.today() - timedelta(days=60)),
        "establecimientos": cn.docs_establecimientos(con),
    }


LOTE = 64


def indexar(docs: dict[str, list[cn.Doc]]) -> None:
    from turismo_core import llm, vector

    for nombre, lista in docs.items():
        col = vector.coleccion(nombre)
        t = time.perf_counter()
        for i in range(0, len(lista), LOTE):          # en lotes: el DENUE son miles de textos
            parte = lista[i:i + LOTE]
            col.upsert(ids=[d.id for d in parte], documents=[d.texto for d in parte],
                       embeddings=llm.embeber([d.texto for d in parte]), metadatas=[d.metadatos for d in parte])
        sobran = set(col.get(include=[])["ids"]) - {d.id for d in lista}
        if sobran:
            col.delete(ids=sorted(sobran))
        print(f"  {nombre:<13} {len(lista):>3} documentos ({len(sobran)} borrados) en {time.perf_counter() - t:.1f} s")


def main(ver: bool = False) -> None:
    with conectar() as con:
        docs = documentos(con)
    if ver:
        for nombre, lista in docs.items():
            print(f"\n===== {nombre} ({len(lista)})")
            for d in lista:
                print(f"[{d.id}] {d.texto}\n    {d.metadatos}")
        return
    indexar(docs)


if __name__ == "__main__":
    main("--ver" in sys.argv)
