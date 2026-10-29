"""Afluencia estimada por punto y hora (docs/05, "Cómo se calcula la afluencia estimada").

    estimación = base del mes × f_día × f_hora × f_evento × f_clima

Todo en **escala relativa del punto**: 1.0 = una hora normal de un día normal en ese lugar.
No sabemos la capacidad de cada lugar, así que cada punto se compara contra su propia historia.

Qué sale de datos oficiales y qué es supuesto (ficha del modelo):

| Pieza | Fuente | Tipo |
|---|---|---|
| Base del mes | INAH (visitas del recinto) o Observatorio (afluencia del destino), mismo mes de 2023–2026 | **Dato** |
| Domingo en recintos INAH | Visitas "Entrada dominical" del INAH ÷ domingos del mes, contra el resto ÷ días abiertos | **Dato** |
| Días que abre | Horario oficial del catálogo (INAH, cholula.gob.mx) | **Dato** si ``horario_confirmado`` |
| Sábado, viernes, festivo y puente | ``PESOS_DIA``, ``F_PUENTE`` | Supuesto |
| Hora del día | ``CURVAS_HORA``: pico entre 12:00 y 15:00 en museos y zonas, y de nuevo al atardecer en calles y plazas | Supuesto (ver nota) |
| Eventos | Tabla ``evento``; solo los ``verificado = 1`` | Dato del calendario curado |
| Clima | Paso 3 (``f_clima``) | — |

Nota sobre la hora del día: no hay fuente pública de afluencia por hora en Puebla. La curva sigue lo
poco que reporta la literatura (museos con pico de 13:00 a 14:00, mañanas tranquilas y tardes que
bajan; p. ej. el reporte de visitas por hora del Jewish Museum of Maryland, 2013, y el estudio de
estancia por Bluetooth del Louvre, arXiv:1605.00108). Se presenta como supuesto y la corrigen los
reportes de los turistas (``reportes.fusionar``).

Los factores de día y hora se **normalizan** para que su promedio en las horas abiertas valga 1.
Así el promedio de un día sigue siendo la base del mes y los umbrales del semáforo
(``umbrales_desde_historia``) se calculan sobre la misma escala que la estimación.
"""

from __future__ import annotations

import calendar
import json
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from statistics import median
from typing import Literal

from turismo_core.semaforo import Umbrales, calcular_umbrales

DIAS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]
DOMINGO, SABADO, VIERNES = 6, 5, 4

FuenteBase = Literal["inah", "observatorio"]

# Años de referencia: completos en las dos fuentes y sin pandemia.
AÑOS_HISTORIA = (2023, 2024, 2025)

# ───────────── Supuestos documentados ─────────────

# Peso de cada día contra un día entre semana (= 1). El domingo de los recintos INAH se reemplaza
# por el que sale de sus datos (peso_domingo_inah).
PESOS_DIA = {VIERNES: 1.1, SABADO: 1.5, DOMINGO: 1.6}
F_PUENTE = 1.15          # sábado, domingo o lunes de un puente
DOMINGO_INAH_MAX = 5.0   # tope para meses raros (cierres parciales, un solo domingo con evento)

# Curvas por hora (inicio del bloque). Solo cuentan las horas en que el punto está abierto.
_CURVA_VISITA = {8: 0.3, 9: 0.5, 10: 0.7, 11: 1.0, 12: 1.3, 13: 1.4, 14: 1.3, 15: 1.1,
                 16: 0.8, 17: 0.5, 18: 0.3, 19: 0.2}
_CURVA_PASEO = {8: 0.3, 9: 0.4, 10: 0.6, 11: 0.8, 12: 1.0, 13: 1.2, 14: 1.2, 15: 1.1, 16: 1.1,
                17: 1.2, 18: 1.3, 19: 1.2, 20: 0.9, 21: 0.6}
_CURVA_TEMPLO = {7: 0.5, 8: 0.7, 9: 0.8, 10: 0.9, 11: 1.0, 12: 1.2, 13: 1.2, 14: 1.0, 15: 0.9,
                 16: 0.9, 17: 1.0, 18: 1.1, 19: 0.8, 20: 0.5}
CURVAS_HORA = {
    "museo": _CURVA_VISITA, "zona_arqueologica": _CURVA_VISITA, "parque": _CURVA_VISITA,
    "templo": _CURVA_TEMPLO,
    "calle": _CURVA_PASEO, "barrio": _CURVA_PASEO, "mercado": _CURVA_PASEO,
    "pueblo_magico": _CURVA_PASEO, "mirador": _CURVA_PASEO, "plaza": _CURVA_PASEO,
}

# Horario que se supone cuando el catálogo no tiene el oficial (``horario_confirmado = False``).
_TODOS = list(range(7))
HORARIO_SUPUESTO = {
    "museo": ([1, 2, 3, 4, 5, 6], (10, 18)),          # muchos museos cierran en lunes
    "zona_arqueologica": (_TODOS, (9, 17)),
    "parque": (_TODOS, (10, 18)),
    "templo": (_TODOS, (8, 20)),
    "calle": (_TODOS, (9, 22)), "barrio": (_TODOS, (9, 22)), "mercado": (_TODOS, (9, 21)),
    "pueblo_magico": (_TODOS, (9, 22)), "mirador": (_TODOS, (10, 22)), "plaza": (_TODOS, (0, 24)),
}

F_EVENTO = {"bajo": 1.1, "medio": 1.2, "alto": 1.4}


# ───────────── Horario ─────────────

# día (0 = lunes) -> turnos [(primera hora, hora en que ya cerró)], p. ej. [(9, 14), (15, 18)]
Horario = dict[int, list[tuple[int, int]]]


def _turno(rango: str) -> tuple[int, int]:
    """``'09:00-13:30'`` -> (9, 14): cuenta la hora de las 13 aunque cierre a la media."""
    ini, fin = (tuple(map(int, x.split(":"))) for x in rango.strip().split("-"))
    return ini[0], fin[0] + (1 if fin[1] else 0)


def leer_horario(texto: str | None, tipo: str) -> tuple[Horario, bool]:
    """``'{"jue": "10:00-17:00", "vie": "09:00-13:30,15:30-18:00"}'`` -> turnos por día, True.

    Sin horario en el catálogo: el supuesto del tipo, y False.
    """
    if texto:
        return {DIAS.index(dia): [_turno(r) for r in rangos.split(",")]
                for dia, rangos in json.loads(texto).items()}, True
    dias, turno = HORARIO_SUPUESTO.get(tipo, (_TODOS, (9, 18)))
    return {d: [turno] for d in dias}, False


def horas_abiertas(horario: Horario, dia_semana: int) -> list[int]:
    """Bloques de una hora en que el punto está abierto (``10-17`` -> 10, 11, …, 16)."""
    return sorted({h for ini, fin in horario.get(dia_semana, []) for h in range(ini, fin)})


def dias_abiertos(horario: Horario, anio: int, mes: int) -> list[date]:
    n = calendar.monthrange(anio, mes)[1]
    return [date(anio, mes, d) for d in range(1, n + 1) if date(anio, mes, d).weekday() in horario]


# ───────────── Perfil de cada punto ─────────────

@dataclass
class Perfil:
    punto_id: int
    clave: str
    tipo: str
    interior: bool
    fuente_base: FuenteBase
    mensual: dict[tuple[int, int], float]          # (año, mes) -> visitas del mes
    horario: Horario
    horario_confirmado: bool
    peso_domingo: float = PESOS_DIA[DOMINGO]
    domingo_es_dato: bool = False
    _nivel_mediano: float | None = field(default=None, repr=False)

    # Visitas por día abierto de un mes concreto de la historia.
    def nivel_diario(self, anio: int, mes: int) -> float | None:
        v = self.mensual.get((anio, mes))
        n = len(dias_abiertos(self.horario, anio, mes))
        return v / n if v and n else None

    def nivel_mediano(self) -> float | None:
        if self._nivel_mediano is None:
            niveles = [x for (a, m) in self.mensual if a in AÑOS_HISTORIA
                       if (x := self.nivel_diario(a, m))]
            self._nivel_mediano = median(niveles) if niveles else None
        return self._nivel_mediano

    def base_mes(self, anio: int, mes: int) -> float | None:
        """Base relativa de un mes: visitas por día abierto del mismo mes en la historia (desde
        2023, promedio de los años con dato) entre la mediana histórica del punto. Si el mes pedido
        no abre ningún día, no hay base."""
        med = self.nivel_mediano()
        niveles = [x for (a, m) in self.mensual if m == mes and a >= AÑOS_HISTORIA[0]
                   if (x := self.nivel_diario(a, m))]
        if not med or not niveles or not dias_abiertos(self.horario, anio, mes):
            return None
        return sum(niveles) / len(niveles) / med


@dataclass(frozen=True)
class Contexto:
    """Lo que cambia día con día y no depende del punto."""
    festivos: frozenset[date] = frozenset()
    puentes: frozenset[date] = frozenset()


@dataclass(frozen=True)
class EventoActivo:
    nombre: str
    impacto: str
    punto_id: int | None
    destino_id: int | None
    inicio: datetime
    fin: datetime


@dataclass(frozen=True)
class Estimacion:
    punto_id: int
    para_hora: datetime
    abierto: bool
    base: float | None
    f_dia_hora: float
    f_evento: float
    f_clima: float
    estimacion: float | None
    eventos: tuple[str, ...] = ()


# ───────────── Factores ─────────────

def peso_dia(p: Perfil, d: date, ctx: Contexto) -> float:
    """Peso del día contra un día entre semana. Un festivo cuenta como domingo, salvo en el INAH,
    donde la entrada gratis es solo en domingo; ahí cuenta como sábado."""
    dia = d.weekday()
    if dia == DOMINGO:
        w = p.peso_domingo
    elif d in ctx.festivos:
        w = PESOS_DIA[SABADO] if p.domingo_es_dato else PESOS_DIA[DOMINGO]
    else:
        w = PESOS_DIA.get(dia, 1.0)
    if d in ctx.puentes and dia in (SABADO, DOMINGO, 0):
        w *= F_PUENTE
    return w


def f_dia(p: Perfil, d: date, ctx: Contexto) -> float:
    """Peso del día ÷ peso promedio de los días abiertos de ese mes (promedio del mes = 1)."""
    abiertos = dias_abiertos(p.horario, d.year, d.month)
    if d not in abiertos:
        return 0.0
    prom = sum(peso_dia(p, x, ctx) for x in abiertos) / len(abiertos)
    return peso_dia(p, d, ctx) / prom


def f_hora(p: Perfil, momento: datetime) -> float:
    """Peso de la hora ÷ peso promedio de las horas abiertas de ese día (promedio del día = 1)."""
    horas = horas_abiertas(p.horario, momento.weekday())
    if momento.hour not in horas:
        return 0.0
    curva = CURVAS_HORA.get(p.tipo, _CURVA_VISITA)
    pesos = [curva.get(h, 0.2) for h in horas]
    return curva.get(momento.hour, 0.2) / (sum(pesos) / len(pesos))


def f_evento(p: Perfil, destino_id: int, momento: datetime, eventos: Iterable[EventoActivo]) -> tuple[float, tuple[str, ...]]:
    f, nombres = 1.0, []
    for e in eventos:
        aplica = e.punto_id == p.punto_id or (e.punto_id is None and e.destino_id in (destino_id, None))
        if aplica and e.inicio <= momento <= e.fin:
            f = max(f, F_EVENTO.get(e.impacto, 1.0))
            nombres.append(e.nombre)
    return f, tuple(nombres)


def estimar(p: Perfil, destino_id: int, momento: datetime, ctx: Contexto,
            eventos: Iterable[EventoActivo] = (), f_clima: float = 1.0) -> Estimacion:
    hora = momento.replace(minute=0, second=0, microsecond=0)
    base = p.base_mes(hora.year, hora.month)
    fd, fh = f_dia(p, hora.date(), ctx), f_hora(p, hora)
    abierto = fd > 0 and fh > 0
    fe, nombres = f_evento(p, destino_id, hora, eventos)
    valor = None if base is None or not abierto else round(base * fd * fh * fe * f_clima, 3)
    return Estimacion(p.punto_id, hora, abierto, base, round(fd * fh, 3), fe, f_clima, valor, nombres)


# ───────────── Umbrales desde la historia ─────────────

def serie_historica(p: Perfil, ctx: Contexto) -> Iterator[float]:
    """Cada hora abierta de los años de referencia, con el mes real (no el promedio):
    ``nivel del mes ÷ mediana × f_día × f_hora``. Es la distribución contra la que se compara
    la estimación, en la misma escala."""
    med = p.nivel_mediano()
    if not med:
        return
    for anio in AÑOS_HISTORIA:
        for mes in range(1, 13):
            nivel = p.nivel_diario(anio, mes)
            if not nivel:
                continue
            for d in dias_abiertos(p.horario, anio, mes):
                fd = f_dia(p, d, ctx)
                for h in horas_abiertas(p.horario, d.weekday()):
                    yield nivel / med * fd * f_hora(p, datetime(d.year, d.month, d.day, h))


def umbrales_desde_historia(p: Perfil, ctx: Contexto) -> Umbrales:
    return calcular_umbrales(list(serie_historica(p, ctx)))


# ───────────── Carga desde puebla.db ─────────────

def peso_domingo_inah(filas: Iterable[tuple[str, float, float]], horario: Horario) -> float | None:
    """Con las visitas de cada mes (periodo, 'Entrada dominical', resto) estima cuánto pesa un
    domingo contra otro día abierto: domingo = resto/día + dominical/domingo.

    Se toma la mediana de los meses con datos, con tope ``DOMINGO_INAH_MAX``.
    """
    razones = []
    for periodo, dominical, resto in filas:
        anio, mes = map(int, periodo.split("-"))
        abiertos = dias_abiertos(horario, anio, mes)
        domingos = sum(1 for d in abiertos if d.weekday() == DOMINGO)
        if dominical and resto and domingos and abiertos:
            por_dia = resto / len(abiertos)
            razones.append((por_dia + dominical / domingos) / por_dia)
    if not razones:
        return None
    return round(min(median(razones), DOMINGO_INAH_MAX), 2)


def cargar_perfiles(con: sqlite3.Connection) -> dict[int, Perfil]:
    """Un perfil por punto: INAH si el punto tiene recinto, si no, el Observatorio de su destino."""
    perfiles: dict[int, Perfil] = {}
    for r in con.execute("SELECT id, clave, tipo, interior, destino_id, horario FROM punto ORDER BY id"):
        horario, confirmado = leer_horario(r["horario"], r["tipo"])
        claves = [c[0] for c in con.execute(
            "SELECT clave_siinah FROM recinto_inah WHERE punto_id = ?", (r["id"],))]
        if claves:
            marcas = ",".join("?" * len(claves))
            mensual = {
                tuple(map(int, f[0].split("-"))): float(f[1]) for f in con.execute(
                    f"SELECT periodo, SUM(visitas) FROM hecho_inah WHERE clave_siinah IN ({marcas}) "
                    "GROUP BY periodo", claves)
            }
            dom = peso_domingo_inah(con.execute(
                f"SELECT periodo, SUM(CASE WHEN tipo_visitante = 'Entrada dominical' THEN visitas END), "
                f"SUM(CASE WHEN tipo_visitante <> 'Entrada dominical' THEN visitas END) "
                f"FROM hecho_inah WHERE clave_siinah IN ({marcas}) GROUP BY periodo", claves).fetchall(), horario)
            p = Perfil(r["id"], r["clave"], r["tipo"], bool(r["interior"]), "inah", mensual, horario, confirmado)
            if dom is not None and DOMINGO in horario:
                p.peso_domingo, p.domingo_es_dato = dom, True
        else:
            mensual = {
                tuple(map(int, f[0].split("-"))): float(f[1]) for f in con.execute(
                    "SELECT periodo, valor FROM hecho_observatorio WHERE destino_id = ? "
                    "AND indicador = 'afluencia' AND es_pandemia = 0", (r["destino_id"],))
            }
            p = Perfil(r["id"], r["clave"], r["tipo"], bool(r["interior"]), "observatorio", mensual,
                       horario, confirmado)
        perfiles[r["id"]] = p
    return perfiles


def cargar_contexto(con: sqlite3.Connection) -> Contexto:
    fest, puen = set(), set()
    for f in con.execute("SELECT fecha, es_festivo, es_puente FROM calendario WHERE es_festivo = 1 OR es_puente = 1"):
        d = date.fromisoformat(f["fecha"])
        if f["es_festivo"]:
            fest.add(d)
        if f["es_puente"]:
            puen.add(d)
    return Contexto(frozenset(fest), frozenset(puen))


def cargar_eventos(con: sqlite3.Connection, solo_verificados: bool = True) -> list[EventoActivo]:
    sql = "SELECT nombre, impacto, punto_id, destino_id, inicio, fin FROM evento"
    if solo_verificados:
        sql += " WHERE verificado = 1"
    return [EventoActivo(e["nombre"], e["impacto"], e["punto_id"], e["destino_id"],
                         datetime.fromisoformat(e["inicio"]), datetime.fromisoformat(e["fin"]))
            for e in con.execute(sql)]


def horas(desde: datetime, n: int) -> list[datetime]:
    inicio = desde.replace(minute=0, second=0, microsecond=0)
    return [inicio + timedelta(hours=i) for i in range(n)]


def resumen_fuentes(perfiles: dict[int, Perfil]) -> dict[str, int]:
    c: dict[str, int] = defaultdict(int)
    for p in perfiles.values():
        c[p.fuente_base] += 1
        c["horario_confirmado"] += p.horario_confirmado
        c["domingo_dato"] += p.domingo_es_dato
    return dict(c)
