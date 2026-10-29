"""Recomendador "¿a dónde voy ahora?" / "mejor ve a…" (docs/05, docs/10 RN_02 y RN_03).

Dos preguntas:

1. **Con un punto pedido**: si está en rojo, cerrado, o al aire libre con lluvia fuerte, propone
   una alternativa y, además, **otra hora** para el mismo lugar (también es redistribuir).
2. **Sin punto pedido**: los mejores lugares para ir ahora según los intereses del turista.

Reglas de una alternativa (RN_02): nunca está en rojo, está abierta, **se parece** al punto pedido
(o a los intereses) y está a menos de 1 h. Toda recomendación lleva su **razón** (RN_03).

    puntaje = 0.3 · similitud + 0.7 · conveniencia

La similitud es por ahora el coseno entre las **categorías** de los puntos (historia, arte,
naturaleza…). En el paso 8 se puede cambiar por la similitud de los embeddings de las fichas en
ChromaDB sin tocar el resto.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from turismo_core.conveniencia import MAX_MINUTOS, Conveniencia, conveniencia
from turismo_core.situacion import PuntoAhora

Motivo = Literal["afluencia", "lluvia", "cerrado"]
Modo = Literal["a pie", "en coche"]

PESO_SIMILITUD = 0.3
PESO_CONVENIENCIA = 0.7
MAX_A_PIE = 20.0       # hasta 20 min se sugiere caminar
MAX_ALTERNATIVAS = 3


@dataclass(frozen=True)
class Candidato:
    punto: PuntoAhora
    minutos: float | None
    modo: Modo | None
    similitud: float
    conveniencia: Conveniencia
    puntaje: float


@dataclass(frozen=True)
class OtraHora:
    hora: datetime
    color: str
    nivel: float | None


@dataclass(frozen=True)
class Recomendacion:
    pedido: PuntoAhora | None
    motivo: Motivo | None                       # None: el pedido está bien, no hace falta cambiar
    alternativa: Candidato | None
    otras: tuple[Candidato, ...] = ()
    otra_hora: OtraHora | None = None
    razon: str = ""


# ───────────── Piezas ─────────────

def similitud(a: Iterable[str], b: Iterable[str]) -> float:
    """Coseno entre conjuntos de categorías: |A ∩ B| / √(|A|·|B|)."""
    a, b = set(a), set(b)
    if not a or not b:
        return 0.0
    return round(len(a & b) / math.sqrt(len(a) * len(b)), 3)


def traslado(origen: int | None, destino: int, matriz: Mapping[tuple[int, int], tuple[float, float]]
             ) -> tuple[float | None, Modo | None]:
    """Caminando si son ≤ 20 min a pie; si no, en coche (sin tráfico hasta el paso 10)."""
    if origen is None:
        return None, None
    if origen == destino:
        return 0.0, "a pie"
    par = matriz.get((origen, destino))
    if par is None:
        return None, None
    coche, pie = par
    if pie is not None and pie <= MAX_A_PIE:
        return pie, "a pie"
    return coche, "en coche"


def motivo_de_cambio(p: PuntoAhora) -> Motivo | None:
    if not p.abierto or p.estado is None:
        return "cerrado"
    if p.color == "rojo":
        return "afluencia"
    if not p.interior and p.lluvia == "fuerte":
        return "lluvia"
    return None


def candidatos(puntos: Iterable[PuntoAhora], referencia: frozenset[str], origen: int | None,
               matriz: Mapping[tuple[int, int], tuple[float, float]], excluir: int | None = None,
               max_minutos: float = MAX_MINUTOS, preferir_techado: bool = False) -> list[Candidato]:
    salida = []
    for p in puntos:
        if p.id == excluir or not p.abierto or p.color in ("rojo", "cerrado"):
            continue
        sim = similitud(referencia, p.categorias) if referencia else 1.0
        if sim <= 0:
            continue
        if preferir_techado and not p.interior and p.lluvia != "sin":
            continue
        minutos, modo = traslado(origen, p.id, matriz)
        if origen is not None and (minutos is None or minutos > max_minutos):
            continue
        conv = conveniencia(p, minutos)
        salida.append(Candidato(p, minutos, modo, sim, conv,
                                round(PESO_SIMILITUD * sim + PESO_CONVENIENCIA * conv.total, 3)))
    return sorted(salida, key=lambda c: (-c.puntaje, c.minutos if c.minutos is not None else 0))


def mejor_hora(pronostico: Sequence[tuple[datetime, str, float | None]]) -> OtraHora | None:
    """La primera hora siguiente en que el punto no está en rojo ni cerrado (prefiere verde si hay)."""
    abiertas = [(h, c, n) for h, c, n in pronostico if c in ("verde", "amarillo")]
    if not abiertas:
        return None
    verde = next(((h, c, n) for h, c, n in abiertas if c == "verde"), None)
    h, c, n = abiertas[0] if verde is None or verde[0].date() != abiertas[0][0].date() else verde
    return OtraHora(h, c, n)


# ───────────── Texto (RN_03) ─────────────

ETIQUETAS = {"gastronomia": "gastronomía", "pueblos_magicos": "pueblos mágicos"}


def _lista(categorias: Iterable[str]) -> str:
    return ", ".join(ETIQUETAS.get(c, c) for c in sorted(categorias))


_COLOR = {"verde": "en verde", "amarillo": "en amarillo", "rojo": "en rojo", "cerrado": "cerrado", "sin_dato": "sin dato"}


def _nivel(p: PuntoAhora) -> str:
    return "" if p.nivel is None else f" ({p.nivel:.1f} veces lo normal para ese lugar)"


def _como_llegar(c: Candidato) -> str:
    if c.minutos is None:
        return ""
    if c.minutos == 0:
        return ", ahí mismo"
    return f", a {minutos_texto(c.minutos)} min {c.modo}"


def minutos_texto(minutos: float) -> int:
    """Redondea sin decir "0 min" de un lugar que no es el mismo (ORS da < 0.5 min entre vecinos)."""
    return max(1, round(minutos)) if minutos > 0 else 0


def _por_que_se_parece(pedido_cats: frozenset[str], c: Candidato) -> str:
    comunes = pedido_cats & c.punto.categorias
    return f" y también es de {_lista(comunes)}" if comunes else ""


def _hora_texto(o: OtraHora, momento: datetime) -> str:
    dia = "" if o.hora.date() == momento.date() else ("mañana " if (o.hora.date() - momento.date()).days == 1
                                                      else f"el {o.hora:%d/%m} ")
    return f"{dia}a las {o.hora:%H:%M}"


def explicar(pedido: PuntoAhora | None, motivo: Motivo | None, alt: Candidato | None,
             otra_hora: OtraHora | None, momento: datetime, intereses: frozenset[str] = frozenset()) -> str:
    partes = []
    if pedido is not None:
        if motivo is None:
            return f"{pedido.nombre} está {_COLOR[pedido.color]}{_nivel(pedido)}: buen momento para ir."
        if motivo == "afluencia":
            partes.append(f"{pedido.nombre} está en rojo{_nivel(pedido)}.")
        elif motivo == "cerrado":
            partes.append(f"{pedido.nombre} está cerrado a esta hora.")
        else:
            partes.append(f"Se pronostica lluvia fuerte y {pedido.nombre} es al aire libre.")
        if alt is not None:
            techado = " (techado)" if motivo == "lluvia" and alt.punto.interior else ""
            partes.append(f"Mejor ve a {alt.punto.nombre}{techado}: está {_COLOR[alt.punto.color]}"
                          f"{_como_llegar(alt)}{_por_que_se_parece(pedido.categorias, alt)}.")
        else:
            partes.append("No hay una alternativa parecida, abierta y a menos de 1 h que no esté en rojo.")
        if otra_hora is not None:
            partes.append(f"O regresa {_hora_texto(otra_hora, momento)}, cuando estará {_COLOR[otra_hora.color]}.")
        return " ".join(partes)
    if alt is None:
        return "No hay lugares abiertos que no estén en rojo cerca de ti."
    gusto = f" para quien busca {_lista(intereses & alt.punto.categorias)}" if intereses & alt.punto.categorias else ""
    return f"Ahora te conviene {alt.punto.nombre}{gusto}: está {_COLOR[alt.punto.color]}{_como_llegar(alt)}."


# ───────────── Recomendar ─────────────

def recomendar(puntos: Mapping[int, PuntoAhora], matriz: Mapping[tuple[int, int], tuple[float, float]],
               momento: datetime, pedido_id: int | None = None, origen_id: int | None = None,
               intereses: Iterable[str] = (), horas: float | None = None,
               pronostico_pedido: Sequence[tuple[datetime, str, float | None]] = ()) -> Recomendacion:
    """``puntos`` sale de ``situacion.situacion``; ``pronostico_pedido`` son las horas siguientes del
    punto pedido (hora, color, nivel), para proponer otra hora."""
    intereses = frozenset(i.strip() for i in intereses if i.strip())
    origen = origen_id if origen_id is not None else pedido_id
    # Con poco tiempo, el traslado no puede comerse más de un tercio de lo disponible.
    max_min = MAX_MINUTOS if not horas else max(15.0, min(MAX_MINUTOS, horas * 60 / 3))

    if pedido_id is None:
        lista = candidatos(puntos.values(), intereses, origen, max_minutos=max_min, matriz=matriz)
        alt = lista[0] if lista else None
        return Recomendacion(None, None, alt, tuple(lista[1:1 + MAX_ALTERNATIVAS]), None,
                             explicar(None, None, alt, None, momento, intereses))

    pedido = puntos[pedido_id]
    motivo = motivo_de_cambio(pedido)
    if motivo is None:
        return Recomendacion(pedido, None, None, (), None, explicar(pedido, None, None, None, momento))

    referencia = pedido.categorias | intereses
    lista = candidatos(puntos.values(), referencia, origen, matriz, excluir=pedido_id, max_minutos=max_min,
                       preferir_techado=(motivo == "lluvia"))
    alt = lista[0] if lista else None
    otra = mejor_hora(pronostico_pedido)
    return Recomendacion(pedido, motivo, alt, tuple(lista[1:1 + MAX_ALTERNATIVAS]), otra,
                         explicar(pedido, motivo, alt, otra, momento))
