"""Paso 1: copia los archivos oficiales a data/raw/ y anota fecha y huella (SHA-256).

    uv run python -m scripts.copiar_datos [carpeta_origen]    # por defecto ~/Downloads

data/raw/ no se sube a git; el manifiesto (data/manifiesto_raw.csv) sí, para saber
de qué versión de cada archivo salió cada número.
"""

from __future__ import annotations

import csv
import hashlib
import shutil
import sys
from datetime import date
from pathlib import Path

from scripts import ARCHIVO_DENUE, ARCHIVO_OBSERVATORIO, ARCHIVOS_INAH, MANIFIESTO, PDF_OBSERVATORIO, RAW

ARCHIVOS = [ARCHIVO_OBSERVATORIO, PDF_OBSERVATORIO, *ARCHIVOS_INAH, ARCHIVO_DENUE]


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def main(origen: Path) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    faltan = [a for a in ARCHIVOS if not (origen / a).exists()]
    if faltan:
        sys.exit(f"Faltan en {origen}: {', '.join(faltan)}")
    filas = []
    for nombre in ARCHIVOS:
        destino = RAW / nombre
        huella = sha256(origen / nombre)
        if not destino.exists() or sha256(destino) != huella:
            shutil.copy2(origen / nombre, destino)
        filas.append({
            "archivo": nombre,
            "fecha_copia": date.today().isoformat(),
            "bytes": destino.stat().st_size,
            "sha256": huella,
        })
        print(f"  {nombre}  {huella[:12]}")
    with MANIFIESTO.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print(f"{len(filas)} archivos en {RAW}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads")
