"""Situación de todos los puntos a una hora: lo que ve el turista en el mapa.

Junta, para cada punto (docs/05 y docs/10):
- la afluencia estimada de esa hora (``afluencia_estimada``, ya con día, hora, evento y clima),
- los reportes de turistas de las últimas 3 h (``reportes.fusionar``, RN_08 y RN_09),
- el ajuste manual vigente del panel (RN_16),
- y la lluvia pronosticada (``obs_clima``).

La usan el recomendador, la API y el servidor MCP, para que los tres digan lo mismo.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

from turismo_core import clima
from turismo_core.estado import EstadoSemaforo, evaluar
from turismo_core.reportes import VIDA_MAX, Reporte
from turismo_core.semaforo import AjusteManual, Umbrales, UMBRALES_GENERALES


@dataclass(frozen=True)
class PuntoAhora:
    id: int
    clave: str
    nombre: str
    destino: str
    tipo: str
    categorias: frozenset[str]
    interior: bool
    lat: float
    lon: float
    abierto: bool
    estado: EstadoSemaforo | None      # None si está cerrado
    lluvia: str                        # 'sin' · 'moderada' · 'fuerte'
    eventos: tuple[str, ...] = ()

    @property
    def color(self) -> str:
        return "cerrado" if not self.abierto or self.estado is None else self.estado.semaforo

    @property
    def nivel(self) -> float | None:
        """Afluencia final en escala relativa (1.0 = una hora normal en ese lugar)."""
        return None if self.estado is None else self.estado.valor_final

    @property
    def exceso(self) -> float | None:
        """Cuánto rebasa el umbral rojo del lugar (> 1 = rojo). Sirve para ordenar qué tan lleno está."""
        if self.estado is None or self.estado.valor_final is None:
            return None
        return round(self.estado.valor_final / self.estado.umbrales.alto, 2)


# Horas en que tiene sentido recomendar una visita (supuesto, 2026-10-16): un lugar abierto las 24 h
# (calles, barrios, plazas) sale "más tranquilo" de madrugada, y eso no es un consejo útil.
HORAS_VISITA = range(8, 22)      # de 8:00 a 21:00, para "la hora más tranquila / más llena"
HORAS_TABLA = range(6, 24)       # de 6:00 a 23:00 en la tabla semanal (como el pronóstico de Kioto)


def _hora(momento: datetime) -> datetime:
    return momento.replace(minute=0, second=0, microsecond=0)


def cargar_umbrales(con: sqlite3.Connection) -> dict[int, Umbrales]:
    return {r["punto_id"]: Umbrales(r["bajo"], r["alto"], r["metodo"], r["n_muestras"] or 0)
            for r in con.execute("SELECT * FROM umbral_punto")}


def cargar_reportes(con: sqlite3.Connection, momento: datetime) -> dict[int, list[Reporte]]:
    desde = (momento - VIDA_MAX).isoformat(timespec="seconds")
    salida: dict[int, list[Reporte]] = {}
    for r in con.execute(
        "SELECT punto_id, nivel, creado_en, peso, estado FROM reporte WHERE creado_en BETWEEN ? AND ?",
        (desde, momento.isoformat(timespec="seconds")),
    ):
        salida.setdefault(r["punto_id"], []).append(
            Reporte(r["nivel"], datetime.fromisoformat(r["creado_en"]), r["peso"] if r["peso"] is not None else 1.0,
                    r["estado"] or "valido"))
    return salida


def cargar_ajustes(con: sqlite3.Connection, momento: datetime) -> dict[int, AjusteManual]:
    """El ajuste vigente más reciente de cada punto."""
    salida: dict[int, AjusteManual] = {}
    for r in con.execute(
        "SELECT punto_id, color, motivo, hasta FROM ajuste_manual WHERE creado_en <= ? AND hasta > ? ORDER BY creado_en",
        (momento.isoformat(timespec="seconds"), momento.isoformat(timespec="seconds")),
    ):
        salida[r["punto_id"]] = AjusteManual(r["color"], r["motivo"], datetime.fromisoformat(r["hasta"]))
    return salida


def situacion(con: sqlite3.Connection, momento: datetime) -> dict[int, PuntoAhora]:
    """Estado de todos los puntos en la hora de ``momento`` (los reportes cuentan hasta ``momento``)."""
    hora = _hora(momento)
    umbrales = cargar_umbrales(con)
    reportes = cargar_reportes(con, momento)
    ajustes = cargar_ajustes(con, momento)
    pronostico = clima.ultimo_pronostico(con, hora, hora)
    estimadas = {r["punto_id"]: r for r in con.execute(
        "SELECT punto_id, estimacion, semaforo FROM afluencia_estimada WHERE para_hora = ?",
        (hora.strftime("%Y-%m-%d %H:00"),))}
    eventos = _eventos_por_punto(con, hora)

    salida = {}
    for p in con.execute(
        "SELECT p.*, d.nombre AS destino FROM punto p JOIN destino d ON d.id = p.destino_id ORDER BY p.id"
    ):
        est = estimadas.get(p["id"])
        abierto = est is not None and est["semaforo"] != "cerrado"
        estado = None
        if abierto:
            estado = evaluar(est["estimacion"], umbrales.get(p["id"], UMBRALES_GENERALES),
                             reportes.get(p["id"], []), momento, ajustes.get(p["id"]))
        pr = pronostico.get((p["id"], hora))
        salida[p["id"]] = PuntoAhora(
            id=p["id"], clave=p["clave"], nombre=p["nombre"], destino=p["destino"], tipo=p["tipo"],
            categorias=frozenset(c.strip() for c in (p["categorias"] or "").split(",") if c.strip()),
            interior=bool(p["interior"]), lat=p["lat"], lon=p["lon"], abierto=abierto, estado=estado,
            lluvia=clima.nivel_lluvia(pr.prob_lluvia_pct, pr.lluvia_mm) if pr else "sin",
            eventos=eventos.get(p["id"], ()),
        )
    return salida


def _eventos_por_punto(con: sqlite3.Connection, hora: datetime) -> dict[int, tuple[str, ...]]:
    t = hora.strftime("%Y-%m-%d %H:%M")
    salida: dict[int, list[str]] = {}
    for e in con.execute(
        "SELECT e.nombre, e.punto_id, e.destino_id FROM evento e WHERE e.verificado = 1 AND e.inicio <= ? AND e.fin >= ?",
        (t, t),
    ):
        ids = [e["punto_id"]] if e["punto_id"] else [
            r[0] for r in con.execute("SELECT id FROM punto WHERE destino_id = ?", (e["destino_id"],))]
        for pid in ids:
            salida.setdefault(pid, []).append(e["nombre"])
    return {k: tuple(v) for k, v in salida.items()}


def traslados(con: sqlite3.Connection, ahora: datetime | None = None) -> dict[tuple[int, int], tuple[float, float]]:
    """(origen, destino) -> (minutos en coche, minutos a pie).

    Sin ``ahora``: en coche sin tráfico (ORS), como lo necesita el filtro de velocidad imposible.
    Con ``ahora``: en coche × el factor de tráfico vigente del corredor (paso 10, ``trafico.py``).
    """
    from turismo_core import trafico   # import local: trafico importa conocimiento

    base = {(r["origen_id"], r["destino_id"]): (r["minutos_base"], r["minutos_pie"])
            for r in con.execute("SELECT origen_id, destino_id, minutos_base, minutos_pie FROM matriz_traslado")}
    if ahora is None:
        return base
    f = trafico.factores_vigentes(con, ahora)
    return {(a, b): (coche * (f.de(a, b) or 1.0), pie) for (a, b), (coche, pie) in base.items()}


def pronostico_punto(con: sqlite3.Connection, punto_id: int, momento: datetime, horas: int = 48
                     ) -> list[tuple[datetime, str, float | None]]:
    """Las horas siguientes de un punto (hora, color, nivel) según la afluencia estimada, sin reportes:
    sirve para proponer "regresa a las 10:00"."""
    desde = _hora(momento) + timedelta(hours=1)
    hasta = desde + timedelta(hours=horas - 1)
    return [(datetime.strptime(r["para_hora"], "%Y-%m-%d %H:%M"), r["semaforo"], r["valor_final"])
            for r in con.execute(
                "SELECT para_hora, semaforo, valor_final FROM afluencia_estimada "
                "WHERE punto_id = ? AND para_hora BETWEEN ? AND ? ORDER BY para_hora",
                (punto_id, desde.strftime("%Y-%m-%d %H:00"), hasta.strftime("%Y-%m-%d %H:00")))]
