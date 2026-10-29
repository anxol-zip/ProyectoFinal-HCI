"""Paso 3: los 4 reportes del INAH (HTML con extensión .xls) -> data/processed/inah.csv."""

from __future__ import annotations

import csv
from collections import Counter

from scripts import ARCHIVOS_INAH, PROCESSED, RAW
from turismo_core.ingesta import decodificar, leer_inah


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    visitas: Counter[tuple] = Counter()
    recintos: dict[str, tuple[str, str]] = {}
    for nombre in ARCHIVOS_INAH:
        texto = decodificar((RAW / nombre).read_bytes())
        n = 0
        for f in leer_inah(texto):
            recintos[f.clave_siinah] = (f.recinto, f.siglas)
            visitas[(f.clave_siinah, f"{f.anio}-{f.mes:02d}", f.tipo_visitante, f.nacionalidad)] += f.visitas
            n += 1
        print(f"  {nombre}: {n} filas")

    with (PROCESSED / "inah.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["clave_siinah", "periodo", "tipo_visitante", "nacionalidad", "visitas"])
        for clave, v in sorted(visitas.items()):
            w.writerow([*clave, v])
    with (PROCESSED / "recintos_inah.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["clave_siinah", "nombre", "siglas"])
        for clave, (nombre, siglas) in sorted(recintos.items()):
            w.writerow([clave, nombre, siglas])

    periodos = sorted({k[1] for k in visitas})
    print(f"{len(recintos)} recintos, {len(visitas)} combinaciones, {periodos[0]} a {periodos[-1]}")


if __name__ == "__main__":
    main()
