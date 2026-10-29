"""Paso 2: tabla del Observatorio (Markdown) -> data/processed/observatorio.csv en formato largo."""

from __future__ import annotations

import csv

from pypdf import PdfReader

from scripts import ARCHIVO_OBSERVATORIO, PDF_OBSERVATORIO, PROCESSED, RAW
from turismo_core.ingesta import (
    AÑOS_PANDEMIA,
    complementar_con_pdf,
    leer_observatorio,
    quitar_meses_sin_publicar,
    revisar_acumulado,
)


def lineas_pdf() -> list[str]:
    lector = PdfReader(RAW / PDF_OBSERVATORIO)
    return [linea for pagina in lector.pages for linea in (pagina.extract_text() or "").splitlines()]


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    with (RAW / ARCHIVO_OBSERVATORIO).open(encoding="utf-8") as f:
        filas = quitar_meses_sin_publicar(list(leer_observatorio(f)))
    filas, rellenas = complementar_con_pdf(filas, lineas_pdf())
    print(f"{rellenas} filas vacías en el Markdown se rellenaron con el PDF")

    avisos = [a for a in map(revisar_acumulado, filas) if a]
    vistos: set[tuple] = set()
    n = 0
    with (PROCESSED / "observatorio.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["destino", "periodo", "indicador", "valor", "es_pandemia"])
        for fila in filas:
            clave = (fila.destino, fila.indicador, fila.anio)
            if clave in vistos:
                avisos.append(f"Fila repetida: {clave}")
                continue
            vistos.add(clave)
            for mes, valor in enumerate(fila.meses, start=1):
                if valor is None:
                    continue
                w.writerow([fila.destino, f"{fila.anio}-{mes:02d}", fila.indicador, valor,
                            int(fila.anio in AÑOS_PANDEMIA)])
                n += 1

    destinos = sorted({f.destino for f in filas})
    con_datos = {f.destino for f in filas if any(v is not None for v in f.meses)}
    print(f"{len(filas)} filas de la tabla -> {n} valores; {len(con_datos)} destinos con datos")
    print("  " + ", ".join(sorted(con_datos)))
    for d in sorted(set(destinos) - con_datos):
        años = sorted({f.anio for f in filas if f.destino == d})
        avisos.append(f"{d}: todas sus celdas están vacías (años en la tabla: {años[0]}–{años[-1]})")
    for a in avisos:
        print(f"  AVISO {a}")


if __name__ == "__main__":
    main()
