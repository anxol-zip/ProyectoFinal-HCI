"""Conexión a SQLite (puebla.db) y creación del esquema (sql/esquema.sql)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
DATA = BACKEND / "data"
ESQUEMA = BACKEND / "sql" / "esquema.sql"


def ruta_bd() -> Path:
    """Ruta de la BD según ``DATABASE_URL`` (docs/05: ``sqlite:///data/puebla.db``).

    Una ruta relativa se toma desde ``backend/``, que es donde se corre todo.
    """
    url = os.environ.get("DATABASE_URL", "sqlite:///data/puebla.db")
    if not url.startswith("sqlite:///"):
        raise ValueError(f"Solo se soporta SQLite por ahora: {url}")
    ruta = Path(url.removeprefix("sqlite:///"))
    return ruta if ruta.is_absolute() else BACKEND / ruta


def conectar(ruta: Path | str | None = None, check_same_thread: bool = True) -> sqlite3.Connection:
    """``check_same_thread=False`` para la API: FastAPI puede abrir la conexión en un hilo y usarla en otro."""
    con = sqlite3.connect(ruta or ruta_bd(), check_same_thread=check_same_thread)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


# Columnas agregadas al esquema después de crear la BD. ``CREATE TABLE IF NOT EXISTS`` no las
# agrega a una tabla que ya existe, así que se agregan aquí sin tocar los datos.
COLUMNAS_NUEVAS = [
    ("evento", "nota", "TEXT"),
    ("matriz_traslado", "minutos_pie", "REAL"),
    ("matriz_traslado", "km_pie", "REAL"),
    ("obs_trafico", "minutos_actual", "REAL"),      # paso 10: TomTom Routing por corredor
    ("obs_trafico", "minutos_libre", "REAL"),
    ("obs_trafico", "minutos_historico", "REAL"),
    ("obs_trafico", "km", "REAL"),
]


def crear_esquema(con: sqlite3.Connection) -> None:
    con.executescript(ESQUEMA.read_text(encoding="utf-8"))
    for tabla, columna, tipo in COLUMNAS_NUEVAS:
        existentes = {r[1] for r in con.execute(f"PRAGMA table_info({tabla})")}
        if columna not in existentes:
            con.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")
