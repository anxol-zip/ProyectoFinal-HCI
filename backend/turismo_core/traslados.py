"""Matriz de traslados entre los puntos con OpenRouteService (docs/04 §2, docs/05).

Se consulta **una sola vez** (una matriz en coche y otra a pie) y se guarda en ``matriz_traslado``.
En vivo, el tiempo en coche solo se multiplica por el factor de tráfico (paso 10); a pie no cambia.

Datos de ruteo © colaboradores de OpenStreetMap (ODbL), calculados por openrouteservice.org.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass

URL = "https://api.openrouteservice.org/v2/matrix/{perfil}"
PERFILES = {"coche": "driving-car", "pie": "foot-walking"}


@dataclass(frozen=True)
class Traslado:
    origen_id: int
    destino_id: int
    minutos: float | None     # None: ORS no encontró ruta
    km: float | None


def cuerpo(coordenadas: Sequence[tuple[float, float]]) -> dict:
    """ORS pide [lon, lat]; nosotros guardamos (lat, lon)."""
    return {"locations": [[lon, lat] for lat, lon in coordenadas], "metrics": ["duration", "distance"], "units": "km"}


def consultar(coordenadas: Sequence[tuple[float, float]], modo: str, api_key: str, timeout: float = 60) -> dict:
    req = urllib.request.Request(
        URL.format(perfil=PERFILES[modo]), data=json.dumps(cuerpo(coordenadas)).encode(),
        headers={"Authorization": api_key, "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": "PueblaAhora-hackathon-puebla-turistica-360/0.1"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def leer_matriz(datos: dict, punto_ids: Sequence[int]) -> list[Traslado]:
    """``durations`` en segundos y ``distances`` en km, en el orden de ``punto_ids``."""
    dur, dist = datos["durations"], datos["distances"]
    if len(dur) != len(punto_ids) or any(len(fila) != len(punto_ids) for fila in dur):
        raise ValueError(f"Matriz de {len(dur)} filas para {len(punto_ids)} puntos")
    salida = []
    for i, o in enumerate(punto_ids):
        for j, d in enumerate(punto_ids):
            s, km = dur[i][j], dist[i][j]
            salida.append(Traslado(o, d, None if s is None else round(s / 60, 1), None if km is None else round(km, 2)))
    return salida
