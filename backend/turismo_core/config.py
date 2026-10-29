"""Lee ``backend/.env`` (claves de las APIs) sin dependencias extra.

Lo que ya esté en el entorno gana sobre el archivo. El archivo nunca se sube a git (.gitignore).
"""

from __future__ import annotations

import os
from pathlib import Path

from turismo_core.bd import BACKEND

ENV = BACKEND / ".env"


def leer_env(ruta: Path = ENV) -> dict[str, str]:
    valores = {}
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            valores[clave.strip()] = valor.split(" #")[0].strip()
    return valores


def clave(nombre: str) -> str | None:
    return os.environ.get(nombre) or leer_env().get(nombre) or None
