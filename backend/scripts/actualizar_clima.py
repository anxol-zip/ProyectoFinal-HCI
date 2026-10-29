"""Paso 7a: pronóstico por hora de Open-Meteo para todos los puntos -> obs_clima.

    uv run python -m scripts.actualizar_clima

Se corre cada hora (docs/05, "Cómo se actualiza la capa en vivo"). Si no hay internet,
avisa y no falla: la afluencia usa el último pronóstico guardado.
"""

from __future__ import annotations

import urllib.error
from datetime import datetime

from turismo_core import clima
from turismo_core.bd import conectar


def main() -> bool:
    with conectar() as con:
        puntos = [(r["id"], r["lat"], r["lon"]) for r in con.execute("SELECT id, lat, lon FROM punto ORDER BY id")]
        ahora = datetime.now().replace(second=0, microsecond=0)
        try:
            pronosticos = clima.consultar(puntos)
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            ultima = con.execute("SELECT MAX(consultado_en) FROM obs_clima").fetchone()[0]
            print(f"  AVISO Open-Meteo no respondió ({e}); se usa la última consulta guardada: {ultima or 'ninguna'}")
            return False
        n = clima.guardar(con, pronosticos, ahora)
        lluvia = sum(clima.nivel_lluvia(p.prob_lluvia_pct, p.lluvia_mm) != "sin" for p in pronosticos)
        print(f"  {n} horas de pronóstico para {len(puntos)} puntos (consulta {ahora:%Y-%m-%d %H:%M}); "
              f"{lluvia} con lluvia moderada o fuerte")
        return True


if __name__ == "__main__":
    main()
