"""Paso 4: DENUE (zip de 37 MB) -> establecimientos turísticos de la zona piloto.

Salidas en data/processed/: ``denue_zona_piloto.csv`` y ``municipios_denue.csv``
(nombre -> clave INEGI de todos los municipios del estado).
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections import Counter

from scripts import ARCHIVO_DENUE, CATALOGO, CSV_DENUE, PROCESSED, RAW
from turismo_core.ingesta import leer_denue


def municipios_catalogo() -> set[str]:
    with CATALOGO.open(encoding="utf-8") as f:
        return {fila["municipio"].strip() for fila in csv.DictReader(f)}


def _codificacion(z: zipfile.ZipFile) -> str:
    with z.open(CSV_DENUE) as f:
        muestra = f.read(4 << 20)
    try:
        muestra.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError as e:
        # El corte de la muestra puede partir un carácter al final; eso no cuenta.
        return "utf-8" if e.start >= len(muestra) - 3 else "cp1252"


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    municipios = municipios_catalogo()
    with zipfile.ZipFile(RAW / ARCHIVO_DENUE) as z:
        cod = _codificacion(z)
        with z.open(CSV_DENUE) as b:
            filas, claves = leer_denue(io.TextIOWrapper(b, encoding=cod, newline=""), municipios)

    faltan = municipios - claves.keys()
    if faltan:
        raise SystemExit(f"Municipios del catálogo que no aparecen en el DENUE: {sorted(faltan)}")

    with (PROCESSED / "denue_zona_piloto.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    with (PROCESSED / "municipios_denue.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["municipio", "cve_mun"])
        w.writerows(sorted(claves.items()))

    print(f"Codificación {cod}; {len(claves)} municipios en el estado")
    for (mun, giro), n in sorted(Counter((e["municipio"], e["giro"]) for e in filas).items()):
        print(f"  {mun:<22} {giro:<12} {n:>6}")
    print(f"{len(filas)} establecimientos en la zona piloto")


if __name__ == "__main__":
    main()
