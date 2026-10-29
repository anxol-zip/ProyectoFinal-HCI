"""Base de datos de desarrollo: corre el backend sin `data/raw/` ni `.env`.

Usa el mismo pipeline del backend con los datos ya procesados que vienen en git
(`backend/data/processed/`, el catálogo y los eventos) y calcula la afluencia estimada
de los próximos días. Lo único inventado son los **traslados**: OpenRouteService necesita
una clave, así que se aproximan con la distancia en línea recta. El clima y el tráfico
quedan vacíos (sin lluvia ni tráfico) y el asistente responde 503 si no hay Ollama.

Sirve para trabajar en la interfaz en cualquier compu. La demo y las pruebas con
usuarios se hacen con la base real (`puebla.db`) en la laptop que tiene los datos.

    cd backend
    uv run python ../herramientas/bd_desarrollo.py            # crea data/desarrollo.db (14 días)
    uv run python ../herramientas/bd_desarrollo.py --dias 7
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
os.environ.setdefault("DATABASE_URL", "sqlite:///data/desarrollo.db")
sys.path.insert(0, str(BACKEND))

from scripts import calcular_afluencia, cargar_bd  # noqa: E402
from turismo_core.bd import conectar, ruta_bd  # noqa: E402

FUENTE = "Traslados aproximados para desarrollo (no oficiales)"
FACTOR_CALLE = 1.35        # la ruta en coche es más larga que la línea recta
FACTOR_PIE = 1.25
KMH_COCHE = 24             # velocidad promedio en ciudad, sin tráfico
KMH_PIE = 4.5
MINUTOS_ESTACIONAR = 4


def km_linea_recta(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def traslados_aproximados(con):
    puntos = [(r["id"], (r["lat"], r["lon"])) for r in con.execute("SELECT id, lat, lon FROM punto ORDER BY id")]
    con.execute(
        "INSERT INTO fuente (nombre, url, licencia, frecuencia, fecha_descarga) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(nombre) DO UPDATE SET fecha_descarga = excluded.fecha_descarga",
        (FUENTE, "herramientas/bd_desarrollo.py", "Cálculo propio", "única", date.today().isoformat()),
    )
    fuente_id = con.execute("SELECT id FROM fuente WHERE nombre = ?", (FUENTE,)).fetchone()[0]
    filas = []
    for o, a in puntos:
        for d, b in puntos:
            km = km_linea_recta(a, b)
            km_coche, km_pie = km * FACTOR_CALLE, km * FACTOR_PIE
            min_coche = 0 if o == d else km_coche / KMH_COCHE * 60 + MINUTOS_ESTACIONAR
            filas.append((o, d, round(min_coche, 1), round(km_coche, 2),
                          round(km_pie / KMH_PIE * 60, 1), round(km_pie, 2), fuente_id))
    con.execute("DELETE FROM matriz_traslado")
    con.executemany(
        "INSERT INTO matriz_traslado (origen_id, destino_id, minutos_base, km, minutos_pie, km_pie, fuente_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)", filas)
    con.commit()
    return len(filas)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dias", type=int, default=14, help="días de afluencia estimada a partir de hoy")
    args = p.parse_args()

    ruta = ruta_bd()
    if ruta.name == "puebla.db":
        sys.exit("Esta herramienta no escribe en puebla.db (la base real). Usa otra DATABASE_URL.")
    print(f"== Base de desarrollo: {ruta}")
    cargar_bd.main()
    with conectar() as con:
        print(f"== Traslados aproximados: {traslados_aproximados(con)} pares")
    calcular_afluencia.main(dias=args.dias)
    print("\nListo. Levanta el backend con esta base:\n"
          "  DATABASE_URL=sqlite:///data/desarrollo.db PUEBLA_TAREAS=0 uv run uvicorn app.main:app --reload --port 8000")


if __name__ == "__main__":
    main()
