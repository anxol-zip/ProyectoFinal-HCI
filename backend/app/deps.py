"""Dependencias de FastAPI: conexión a SQLite por petición, la hora y el modo demo.

En las pruebas se reemplazan con ``app.dependency_overrides`` (BD temporal y hora fija).
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

from fastapi import Depends

from turismo_core.bd import conectar


def conexion() -> Iterator[sqlite3.Connection]:
    con = conectar(check_same_thread=False)
    try:
        yield con
    finally:
        con.close()


def ahora() -> datetime:
    """Siempre la hora real: no hay modo escenario (decisión del 2026-10-15)."""
    return datetime.now().replace(microsecond=0)


def es_demo() -> bool:
    """``PUEBLA_DEMO=1`` al levantar la API en el stand: las sesiones nuevas se marcan ``es_demo`` (RN_11)."""
    return os.environ.get("PUEBLA_DEMO", "0") == "1"


Con = Annotated[sqlite3.Connection, Depends(conexion)]
Ahora = Annotated[datetime, Depends(ahora)]
EsDemo = Annotated[bool, Depends(es_demo)]
