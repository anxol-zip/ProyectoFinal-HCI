"""Paso 10: tráfico en vivo con TomTom Routing (docs/04 §2 y docs/05 "Cómo se actualiza la capa en vivo").

En lugar de muestrear tramos sueltos (Flow Segment Data) se pide la **ruta completa** entre 6 anclas de la
zona piloto con ``traffic=true&computeTravelTimeFor=all``: TomTom devuelve el tiempo con el tráfico actual y
sin tráfico de toda la ruta real, sin tener que elegir coordenadas sobre la carretera.

    factor del corredor = tiempo con tráfico ÷ tiempo sin tráfico   (acotado a 1–4)

Los minutos en coche de OpenRouteService (sin tráfico) se multiplican por el factor del corredor que une
las anclas de origen y destino. Cada punto usa el ancla más cercana en línea recta (calculado, no a mano).

Supuestos, documentados:
- Un viaje toma el factor del corredor entre sus anclas (Catedral → Atlixco usa Zócalo → Atlixco).
- Dentro de la misma ancla no hay dato de tráfico: factor 1 y se dice "sin tráfico en vivo".
- Un factor vale ``VIGENCIA`` (90 min); si no hay uno vigente (de noche, sin internet, sin clave), factor 1.

Consumo: 30 corredores por consulta, cada 30 min de 8:00 a 20:00 ≈ 720 consultas al día (plan gratuito:
2,500 consultas no-tile al día según docs/04).
"""

from __future__ import annotations

import json
import sqlite3
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import permutations

from turismo_core.conocimiento import distancia_m

# Zócalo de Puebla · Gran Pirámide de Cholula · Centro de Atlixco · Exconvento de Huejotzingo ·
# Museo del Barroco (Angelópolis) · Africam Safari
ANCLAS = (21, 12, 18, 17, 10, 20)
VIGENCIA = timedelta(minutes=90)
FACTOR_MIN, FACTOR_MAX = 1.0, 4.0
URL = ("https://api.tomtom.com/routing/1/calculateRoute/{a_lat},{a_lon}:{b_lat},{b_lon}/json"
       "?traffic=true&computeTravelTimeFor=all&routeType=fastest&travelMode=car&key={clave}")


@dataclass(frozen=True)
class Corredor:
    tramo: str                  # "21-12"
    km: float
    minutos_actual: float
    minutos_libre: float
    minutos_historico: float | None

    @property
    def factor(self) -> float:
        return round(min(FACTOR_MAX, max(FACTOR_MIN, self.minutos_actual / self.minutos_libre)), 3)


def tramo(a: int, b: int) -> str:
    return f"{a}-{b}"


def corredores(anclas: Iterable[int] = ANCLAS) -> list[tuple[int, int]]:
    return list(permutations(anclas, 2))


def ancla_de(puntos: dict[int, tuple[float, float]], anclas: Iterable[int] = ANCLAS) -> dict[int, int]:
    """Para cada punto, el ancla más cercana en línea recta (vacío si el catálogo no tiene las anclas)."""
    anclas = [a for a in anclas if a in puntos]
    if not anclas:
        return {}
    return {pid: min(anclas, key=lambda a: distancia_m(lat, lon, *puntos[a])) for pid, (lat, lon) in puntos.items()}


def leer_ruta(a: int, b: int, datos: dict) -> Corredor:
    s = datos["routes"][0]["summary"]
    historico = s.get("historicTrafficTravelTimeInSeconds")
    return Corredor(tramo(a, b), round(s["lengthInMeters"] / 1000, 2), round(s["travelTimeInSeconds"] / 60, 1),
                    round(s["noTrafficTravelTimeInSeconds"] / 60, 1), None if historico is None else round(historico / 60, 1))


def consultar(puntos: dict[int, tuple[float, float]], clave: str, timeout: float = 20) -> list[Corredor]:
    salida = []
    for a, b in corredores():
        url = URL.format(a_lat=puntos[a][0], a_lon=puntos[a][1], b_lat=puntos[b][0], b_lon=puntos[b][1], clave=clave)
        with urllib.request.urlopen(url, timeout=timeout) as r:
            salida.append(leer_ruta(a, b, json.load(r)))
    return salida


def guardar(con: sqlite3.Connection, corredores_: Iterable[Corredor], consultado_en: datetime) -> int:
    filas = [(c.tramo, consultado_en.isoformat(timespec="seconds"), round(c.km / (c.minutos_actual / 60), 1),
              round(c.km / (c.minutos_libre / 60), 1), c.factor, c.minutos_actual, c.minutos_libre,
              c.minutos_historico, c.km) for c in corredores_]
    con.executemany("INSERT OR REPLACE INTO obs_trafico (tramo, consultado_en, vel_actual, vel_libre, factor, "
                    "minutos_actual, minutos_libre, minutos_historico, km) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", filas)
    return len(filas)


@dataclass(frozen=True)
class Factores:
    """Factores vigentes a una hora y el ancla de cada punto. ``de(a, b)`` es lo que usan los traslados."""
    por_tramo: dict[str, float]
    anclas: dict[int, int]
    consultado_en: datetime | None

    def de(self, a: int, b: int) -> float | None:
        """Factor del viaje a → b; ``None`` si no hay dato vigente (misma ancla o sin consulta reciente)."""
        za, zb = self.anclas.get(a), self.anclas.get(b)
        if za is None or zb is None or za == zb:
            return None
        return self.por_tramo.get(tramo(za, zb))


def factores_vigentes(con: sqlite3.Connection, ahora: datetime) -> Factores:
    puntos = {r["id"]: (r["lat"], r["lon"]) for r in con.execute("SELECT id, lat, lon FROM punto")}
    desde = (ahora - VIGENCIA).isoformat(timespec="seconds")
    filas = con.execute(
        """SELECT o.tramo, o.factor, o.consultado_en FROM obs_trafico o
           JOIN (SELECT tramo, MAX(consultado_en) AS ultima FROM obs_trafico
                 WHERE consultado_en BETWEEN ? AND ? GROUP BY tramo) u
             ON u.tramo = o.tramo AND u.ultima = o.consultado_en""",
        (desde, ahora.isoformat(timespec="seconds"))).fetchall()
    ultima = max((datetime.fromisoformat(r["consultado_en"]) for r in filas), default=None)
    return Factores({r["tramo"]: r["factor"] for r in filas}, ancla_de(puntos) if puntos else {}, ultima)
