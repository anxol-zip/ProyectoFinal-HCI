"""Paso 10: tráfico de TomTom en los 30 corredores entre anclas -> obs_trafico.

    uv run python -m scripts.actualizar_trafico

Lo corre la API cada 30 min de 8:00 a 20:00. Sin clave o sin internet, avisa y no falla: los traslados
quedan sin tráfico (factor 1) y la app lo dice.
"""

from __future__ import annotations

import urllib.error
from datetime import datetime

from turismo_core import trafico
from turismo_core.bd import conectar, crear_esquema
from turismo_core.config import clave


def main() -> bool:
    k = clave("TOMTOM_API_KEY")
    if not k:
        print("  AVISO sin TOMTOM_API_KEY en backend/.env: los traslados quedan sin tráfico")
        return False
    with conectar() as con:
        crear_esquema(con)
        puntos = {r["id"]: (r["lat"], r["lon"]) for r in con.execute("SELECT id, lat, lon FROM punto")}
        ahora = datetime.now().replace(microsecond=0)
        try:
            datos = trafico.consultar(puntos, k)
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e:
            mensaje = str(e).replace(k, "***")
            print(f"  AVISO TomTom no respondió ({mensaje}); se usa el último dato vigente si lo hay")
            return False
        n = trafico.guardar(con, datos, ahora)
        lentos = sorted(datos, key=lambda c: -c.factor)[:3]
        print(f"  {n} corredores ({ahora:%Y-%m-%d %H:%M}); más lentos: " +
              ", ".join(f"{c.tramo} ×{c.factor} ({c.minutos_actual:.0f} vs {c.minutos_libre:.0f} min)" for c in lentos))
        return True


if __name__ == "__main__":
    main()
