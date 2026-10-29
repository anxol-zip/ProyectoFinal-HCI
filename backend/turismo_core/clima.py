"""Clima en vivo con Open-Meteo y su efecto en la afluencia (docs/04 §2, docs/05).

- **Una sola consulta** con las coordenadas de todos los puntos, cada hora, con
  ``timezone=America/Mexico_City``. Sin clave; datos con licencia CC BY 4.0 (se da crédito
  en "Acerca de", RN_13).
- Cada pronóstico se **guarda** en ``obs_clima`` (no se tira): con unas semanas da historia propia
  para calibrar el efecto de la lluvia (docs/05, "¿Por qué guardar el clima?").
- Si la consulta falla, se usa el último pronóstico guardado y se dice de cuándo es
  (``ultimo_pronostico`` devuelve ``consultado_en``).

Efecto en la afluencia (``f_clima``), **supuesto documentado**:

| Lluvia en esa hora | Punto al aire libre | Punto techado |
|---|---|---|
| Fuerte (prob ≥ 60 % o ≥ 1 mm) | × 0.70 | × 1.10 |
| Moderada (prob ≥ 30 % o ≥ 0.2 mm) | × 0.85 | × 1.05 |
| Sin lluvia | × 1.00 | × 1.00 |

Que la lluvia baje la visita al aire libre y suba la de museos sigue lo reportado para museos
(p. ej. Cuffe, Victoria University of Wellington: los días lluviosos suben las visitas a museos).
Los números exactos son nuestros y se calibran con ``obs_clima`` y los reportes.
"""

from __future__ import annotations

import json
import sqlite3
import urllib.parse
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

URL = "https://api.open-meteo.com/v1/forecast"
VARIABLES = ["temperature_2m", "precipitation_probability", "precipitation", "weather_code"]
DIAS_PRONOSTICO = 8          # hoy + 7, lo mismo que calcula la afluencia
ZONA = "America/Mexico_City"

LLUVIA_FUERTE = (60.0, 1.0)      # (probabilidad %, mm en la hora)
LLUVIA_MODERADA = (30.0, 0.2)
F_AIRE_LIBRE = {"fuerte": 0.70, "moderada": 0.85, "sin": 1.0}
F_TECHADO = {"fuerte": 1.10, "moderada": 1.05, "sin": 1.0}


@dataclass(frozen=True)
class Pronostico:
    punto_id: int
    valido_para: datetime
    temp_c: float | None
    prob_lluvia_pct: float | None
    lluvia_mm: float | None
    weather_code: int | None
    consultado_en: datetime | None = None


def nivel_lluvia(prob: float | None, mm: float | None) -> str:
    prob, mm = prob or 0.0, mm or 0.0
    if prob >= LLUVIA_FUERTE[0] or mm >= LLUVIA_FUERTE[1]:
        return "fuerte"
    if prob >= LLUVIA_MODERADA[0] or mm >= LLUVIA_MODERADA[1]:
        return "moderada"
    return "sin"


def f_clima(interior: bool, p: Pronostico | None) -> float:
    """Sin pronóstico, el clima no mueve la estimación (1.0)."""
    if p is None:
        return 1.0
    return (F_TECHADO if interior else F_AIRE_LIBRE)[nivel_lluvia(p.prob_lluvia_pct, p.lluvia_mm)]


# ───────────── Open-Meteo ─────────────

def url_consulta(coordenadas: Sequence[tuple[float, float]], dias: int = DIAS_PRONOSTICO) -> str:
    return URL + "?" + urllib.parse.urlencode({
        "latitude": ",".join(f"{lat:.5f}" for lat, _ in coordenadas),
        "longitude": ",".join(f"{lon:.5f}" for _, lon in coordenadas),
        "hourly": ",".join(VARIABLES),
        "timezone": ZONA,
        "forecast_days": dias,
    })


def leer_respuesta(datos: list | dict, punto_ids: Sequence[int]) -> list[Pronostico]:
    """Open-Meteo regresa una lista (varias coordenadas) en el mismo orden en que se pidieron;
    con una sola coordenada regresa un objeto."""
    lugares = datos if isinstance(datos, list) else [datos]
    if len(lugares) != len(punto_ids):
        raise ValueError(f"Open-Meteo devolvió {len(lugares)} lugares para {len(punto_ids)} puntos")
    salida = []
    for pid, lugar in zip(punto_ids, lugares):
        h = lugar["hourly"]
        for i, t in enumerate(h["time"]):
            salida.append(Pronostico(
                pid, datetime.fromisoformat(t), h["temperature_2m"][i], h["precipitation_probability"][i],
                h["precipitation"][i], h["weather_code"][i],
            ))
    return salida


def consultar(puntos: Sequence[tuple[int, float, float]], timeout: float = 30) -> list[Pronostico]:
    """``puntos`` = [(punto_id, lat, lon)]. Una sola llamada para todos."""
    url = url_consulta([(lat, lon) for _, lat, lon in puntos])
    req = urllib.request.Request(url, headers={"User-Agent": "PueblaAhora-hackathon-puebla-turistica-360/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return leer_respuesta(json.load(r), [pid for pid, _, _ in puntos])


# ───────────── obs_clima ─────────────

def guardar(con: sqlite3.Connection, pronosticos: Iterable[Pronostico], consultado_en: datetime) -> int:
    filas = [(p.punto_id, consultado_en.isoformat(timespec="minutes"), p.valido_para.isoformat(timespec="minutes"),
              p.temp_c, p.prob_lluvia_pct, p.lluvia_mm, p.weather_code) for p in pronosticos]
    con.executemany("INSERT OR REPLACE INTO obs_clima VALUES (?, ?, ?, ?, ?, ?, ?)", filas)
    return len(filas)


def ultimo_pronostico(con: sqlite3.Connection, desde: datetime, hasta: datetime) -> dict[tuple[int, datetime], Pronostico]:
    """Para cada punto y hora, el pronóstico de la consulta más reciente que la cubre."""
    filas = con.execute(
        """SELECT o.* FROM obs_clima o
           JOIN (SELECT punto_id, valido_para, MAX(consultado_en) AS ultima FROM obs_clima
                 WHERE valido_para BETWEEN ? AND ? GROUP BY punto_id, valido_para) u
             ON u.punto_id = o.punto_id AND u.valido_para = o.valido_para AND u.ultima = o.consultado_en""",
        (desde.isoformat(timespec="minutes"), hasta.isoformat(timespec="minutes")),
    )
    return {
        (r["punto_id"], datetime.fromisoformat(r["valido_para"])): Pronostico(
            r["punto_id"], datetime.fromisoformat(r["valido_para"]), r["temp_c"], r["prob_lluvia_pct"],
            r["lluvia_mm"], r["weather_code"], datetime.fromisoformat(r["consultado_en"]))
        for r in filas
    }
