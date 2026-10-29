"""Asistente con RAG (docs/05b §9 y §10; RN_10): recuperar → estado en vivo → redactar → citar.

El backend hace todo lo que se puede decidir sin IA (búsqueda, filtros, estado en vivo, traslados y la
alternativa del recomendador); el modelo **solo redacta** con eso. Lección de la prueba del 2026-10-15:
con un contexto chico, qwen3:8b inventó una distancia; por eso las cifras le llegan ya escritas y la
instrucción es copiarlas, no calcularlas.

Las fuentes las arma el backend con los ``[id]`` que el modelo cita y que de verdad estaban en el
contexto; una cita a un id que no se le dio se reporta en ``citas_invalidas``.
"""

from __future__ import annotations

import re
import sqlite3
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime

from datetime import timedelta

from turismo_core import clima, conocimiento, llm, trafico, vector
from turismo_core import recomendador as rec
from turismo_core.conocimiento import DIAS, DIAS_TEXTO
from turismo_core.situacion import HORAS_VISITA, PuntoAhora, pronostico_punto, situacion, traslados

SISTEMA = """Eres el asistente turístico de "Puebla Ahora". Respondes en español, en máximo 6 líneas, amable y directo.
REGLAS:
1. Usa SOLO la información de CONTEXTO y ESTADO EN VIVO. Si la respuesta no está ahí, responde "No tengo ese dato." y, si ayuda, di qué sí puedes contestar.
2. Copia las cifras (horarios, precios, minutos, porcentajes, visitantes) tal como vienen escritas. No calcules, no estimes y no agregues distancias, tiempos ni precios que no estén escritos. Si no hay UBICACIÓN DEL TURISTA, no menciones traslados.
3. Después de cada dato pon entre corchetes el id de donde salió, por ejemplo [punto-12] o [obs-3]. Usa solo ids que aparecen abajo.
4. Nunca propongas como opción un lugar en ROJO o CERRADO, ni como segunda opción. Si preguntan por uno así, di su color y ofrece la alternativa que trae ESTADO EN VIVO.
5. Si preguntan qué hacer o qué les recomiendas, propone 2 o 3 de las "Opciones que la app recomienda ahora", copiando de su línea el color, si es techado o al aire libre, la visita sugerida y el traslado.
6. Cada dato pertenece al lugar de su línea: no pases la duración, el precio, el horario ni si es techado o al aire libre de un lugar a otro; no generalices con "ambos" o "todos". Di "techado" solo si la línea de ese lugar dice "techado". Si dice "sin dato", no lo menciones.
6b. El color significa lo que dice su línea: VERDE es tranquilo, AMARILLO es movimiento normal (nunca lo llames tranquilo), ROJO es lleno.
6c. Si preguntan cuándo conviene ir, usa solo las "Próximas horas" de ese lugar tal como vienen; si no vienen, responde "No tengo ese dato."
6d. Si preguntan por lluvia, di lo que indica el "Pronóstico de lluvia" y propone solo lugares techados.
7. De restaurantes y hoteles solo sabemos lo del DENUE: nombre, tipo, tamaño y distancia en línea recta. No digas que son buenos, baratos, que están abiertos o disponibles, ni deduzcas qué sirven por su nombre. No tenemos transporte público, tarifas de taxi, precios de comida ni calificaciones: para eso responde "No tengo ese dato."
8. Nombra los indicadores como vienen escritos (visitantes, llegadas de turistas, derrama) y di su periodo.
9. No inventes lugares, eventos, horarios ni fuentes."""

N_PUNTOS, N_EVENTOS, N_CONOCIMIENTO, N_BITACORA = 5, 2, 4, 2
CITA = re.compile(r"\[([a-z]+-[\w-]+|fuentes)\]")
COLOR_TEXTO = {"verde": "VERDE", "amarillo": "AMARILLO", "rojo": "ROJO", "sin_dato": "SIN DATO", "cerrado": "CERRADO"}


@dataclass(frozen=True)
class Recuperado:
    id: str
    coleccion: str
    texto: str
    metadatos: dict
    distancia: float


def _buscar(nombre: str, emb: list[float], n: int, where: dict | None = None) -> list[Recuperado]:
    col = vector.coleccion(nombre)
    if col.count() == 0:
        return []
    r = col.query(query_embeddings=[emb], n_results=min(n, col.count()), where=where)
    return [Recuperado(i, nombre, d, m or {}, round(dist, 3))
            for i, d, m, dist in zip(r["ids"][0], r["documents"][0], r["metadatas"][0], r["distances"][0])]


def recuperar(pregunta: str, ahora: datetime, llueve: bool, giros: list[str] = (),
              anclas: list[PuntoAhora] = ()) -> list[Recuperado]:
    emb = llm.embeber([pregunta])[0]
    if giros:      # pregunta de comer o dormir: solo el DENUE (los atractivos distraían al modelo) y 1 evento
        bares = bool(set(re.findall(r"\w+", _normal(pregunta))) & BARES)
        return (buscar_establecimientos(emb, list(giros), list(anclas), bares)
                + _buscar("eventos", emb, 1, {"fin": {"$gte": int(ahora.strftime("%Y%m%d"))}}))
    hoy = int(ahora.strftime("%Y%m%d"))
    docs = _buscar("puntos", emb, N_PUNTOS)
    if llueve:   # con lluvia, también los techados más parecidos (docs/05b §9, filtro por reglas)
        vistos = {d.id for d in docs}
        docs += [d for d in _buscar("puntos", emb, 3, {"interior": True}) if d.id not in vistos]
    docs += _buscar("eventos", emb, N_EVENTOS, {"fin": {"$gte": hoy}})
    docs += _buscar("conocimiento", emb, N_CONOCIMIENTO)
    docs += _buscar("bitacora", emb, N_BITACORA)
    return docs


GENERICAS = {"museo", "puebla", "templo", "centro", "barrio", "santa", "maria", "exconvento", "capilla",
             "santuario", "virgen", "calle", "callejon", "plaza", "parque", "internacional", "arqueologica",
             "hermanos", "francisco", "remedios", "real"}


def _normal(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def menciona(pregunta: str, p: PuntoAhora, origen_id: int | None = None) -> bool:
    """¿La pregunta es sobre este lugar? (por una palabra distintiva de su nombre, o porque el turista está ahí)."""
    if p.id == origen_id:
        return True
    palabras = set(re.findall(r"\w+", _normal(pregunta)))
    clave = {w for w in re.findall(r"\w+", _normal(p.nombre)) if len(w) >= 5 and w not in GENERICAS}
    return bool(palabras & clave)


# Intereses que se leen de la pregunta con reglas (docs/05b §9: filtros sin LLM); se suman a los de la sesión.
PALABRAS_INTERES = {
    "familia": ("nino", "ninos", "nina", "ninas", "familia", "hijos", "infantil"),
    "historia": ("historia", "historico", "historica", "prehispanic", "virreinal", "ruinas"),
    "arte": ("arte", "museo", "museos", "pintura", "murales", "barroco"),
    "naturaleza": ("naturaleza", "aire libre", "animales", "volcan", "vista", "mirador"),
    "compras": ("compras", "comprar", "artesania", "artesanias", "talavera", "antiguedades", "recuerdos"),
    "gastronomia": ("comer", "comida", "gastronomia", "dulces", "mole", "sidra"),
    "pueblos_magicos": ("pueblo magico", "pueblos magicos"),
}


def intereses_de(pregunta: str) -> set[str]:
    q = _normal(pregunta)
    return {i for i, palabras in PALABRAS_INTERES.items() if any(p in q for p in palabras)}


# Dónde comer o dormir: palabras completas (no "bar" dentro de "barrio" o "barroco").
COMER = {"comer", "comida", "comidas", "restaurante", "restaurantes", "cenar", "cena", "desayunar", "desayuno",
         "almorzar", "almuerzo", "cafe", "cafes", "cafeteria", "tacos", "antojitos", "mole", "fonda", "fondas",
         "mariscos", "pizza", "bar", "bares", "cantina", "helado", "helados", "nieve"}
DORMIR = {"hotel", "hoteles", "hospedaje", "hospedarme", "hospedarse", "dormir", "alojamiento", "hostal",
          "posada", "quedarme"}
N_ESTABLECIMIENTOS = 3      # con 5, las respuestas de comida tardaban 16–18 s (RNF_04 pide < 15 s), 2026-10-16


def giros_de(pregunta: str) -> list[str]:
    palabras = set(re.findall(r"\w+", _normal(pregunta)))
    return [g for g, claves in (("alimentos", COMER), ("hospedaje", DORMIR)) if palabras & claves]


def _y(*condiciones: dict) -> dict:
    """``$and`` de Chroma, que exige al menos dos condiciones."""
    condiciones = [c for c in condiciones if c]
    return condiciones[0] if len(condiciones) == 1 else {"$and": condiciones}


BARES = {"bar", "bares", "cantina", "cantinas"}
CODIGO_BARES = "722412"


def buscar_establecimientos(emb: list[float], giros: list[str], anclas: list[PuntoAhora],
                            bares: bool = False) -> list[Recuperado]:
    """Del DENUE, los más parecidos a la pregunta; si hay ancla, solo los que están cerca de ella.
    Bares y cantinas solo si la pregunta los pide. El texto se completa con la distancia en línea recta
    a la primera ancla (la calcula el backend)."""
    filtro_giro = {"giro": giros[0]} if len(giros) == 1 else {"giro": {"$in": giros}}
    filtro_giro = _y(filtro_giro, {"codigo_act": {"$eq" if bares else "$ne": CODIGO_BARES}})
    cerca = [{"cerca_de": {"$contains": a.id}} for a in anclas]
    filtro_cerca = None if not cerca else cerca[0] if len(cerca) == 1 else {"$or": cerca}
    docs = _buscar("establecimientos", emb, N_ESTABLECIMIENTOS, _y(filtro_giro, filtro_cerca))
    # El modelo les ponía "techado" o "al aire libre" a los restaurantes (2026-10-16): se dice que no se sabe.
    nota = " Tampoco se sabe si es techado o al aire libre."
    if not anclas:
        return [Recuperado(d.id, d.coleccion, d.texto + nota, d.metadatos, d.distancia) for d in docs]
    a = anclas[0]
    return [Recuperado(d.id, d.coleccion,
                       d.texto + nota + f" Está a {conocimiento.distancia_m(a.lat, a.lon, d.metadatos['lat'], d.metadatos['lon']):.0f} m "
                                        f"en línea recta de {a.nombre}.", d.metadatos, d.distancia)
            for d in docs]


def _cuando(ahora: datetime) -> str:
    return f"{DIAS_TEXTO[DIAS[ahora.weekday()]]} {ahora:%Y-%m-%d %H:%M}"


# Cada dato que el modelo pueda decir de un lugar va escrito en la propia línea de ese lugar; si falta,
# dice "sin dato". Evaluación del 2026-10-16: con huecos, qwen3:8b dijo que los Fuertes eran techados, le
# puso al Acuario la duración de Atlixco, llamó "tranquilo" a un lugar en amarillo e inventó que la
# Pirámide "se vuelve roja después de las 12:30".
SIGNIFICADO = {"verde": "VERDE (tranquilo para ese lugar)", "amarillo": "AMARILLO (movimiento normal para ese lugar)",
               "rojo": "ROJO (lleno para ese lugar)", "cerrado": "CERRADO", "sin_dato": "SIN DATO de afluencia"}
LLUVIA = {"llover", "lluvia", "llueve", "lloviendo", "lluvioso", "lluviosa", "llovizna", "lloviznando"}
N_OPCIONES = 4


def habla_de_lluvia(pregunta: str) -> bool:
    return bool(set(re.findall(r"\w+", _normal(pregunta))) & LLUVIA)


def _techo(p: PuntoAhora) -> str:
    return "techado" if p.interior else f"al aire libre (lluvia pronosticada ahora: {p.lluvia})"


def _traslado_txt(p: PuntoAhora, origen_id: int | None, matriz, factores: trafico.Factores | None) -> str:
    if origen_id is None:
        return "traslado: sin dato (no se sabe dónde está el turista)"
    minutos, modo = rec.traslado(origen_id, p.id, matriz)
    if minutos is None:
        return "traslado: sin dato"
    if minutos == 0:
        return "el turista está ahí"
    factor = factores.de(origen_id, p.id) if factores and modo == "en coche" else None
    trafico_txt = (f" con el tráfico actual (sin tráfico, {rec.minutos_texto(minutos / factor)} min)"
                   if factor and factor >= 1.1 else "")
    return f"desde la ubicación del turista: {rec.minutos_texto(minutos)} min {modo}{trafico_txt}"


def proximas_horas_txt(con: sqlite3.Connection, p: PuntoAhora, ahora: datetime) -> str:
    """Color estimado de las horas siguientes (hoy y mañana) y la hora más tranquila y la más llena de cada día.
    Sale de ``afluencia_estimada`` (sin reportes): lo mismo que la app muestra como pronóstico."""
    dias: dict = {}
    for h, c, nivel in pronostico_punto(con, p.id, ahora, 36):
        dias.setdefault(h.date(), []).append((h, c, nivel))
    partes = []
    for d, horas in list(dias.items())[:2]:
        nombre = ("hoy" if d == ahora.date() else "mañana") + f" {DIAS_TEXTO[DIAS[d.weekday()]]}"
        abiertas = [(h, c, n) for h, c, n in horas
                    if c not in ("cerrado", "sin_dato") and n is not None and h.hour in HORAS_VISITA]
        if not abiertas:
            partes.append(f"{nombre}: cerrado el resto del día" if d == ahora.date() else f"{nombre}: cerrado")
            continue
        lista = ", ".join(f"{h:%H:%M} {COLOR_TEXTO[c]}" for h, c, _ in abiertas)
        tranquila = min(abiertas, key=lambda x: x[2])
        llena = max(abiertas, key=lambda x: x[2])
        partes.append(f"{nombre}: {lista}; la hora más tranquila es las {tranquila[0]:%H:%M} ({COLOR_TEXTO[tranquila[1]]}) "
                      f"y la más llena las {llena[0]:%H:%M} ({COLOR_TEXTO[llena[1]]})")
    if not partes:
        return f"Próximas horas de [punto-{p.id}] {p.nombre}: sin dato."
    return f"Próximas horas de [punto-{p.id}] {p.nombre} (estimado, sin reportes) — " + " · ".join(partes) + "."


def pronostico_lluvia_txt(con: sqlite3.Connection, puntos: dict[int, PuntoAhora], ahora: datetime) -> str:
    """Lo que dice Open-Meteo para las próximas 3 h en los puntos de la zona (el último pronóstico guardado)."""
    hora = ahora.replace(minute=0, second=0, microsecond=0)
    pron = clima.ultimo_pronostico(con, hora, hora + timedelta(hours=3))
    peor: dict[int, str] = {}
    orden = {"sin": 0, "moderada": 1, "fuerte": 2}
    for (pid, _), pr in pron.items():
        nivel = clima.nivel_lluvia(pr.prob_lluvia_pct, pr.lluvia_mm)
        if orden[nivel] > orden[peor.get(pid, "sin")]:
            peor[pid] = nivel
        peor.setdefault(pid, nivel)
    if not pron:
        return "Pronóstico de lluvia (Open-Meteo): sin dato."
    con_lluvia = [(pid, n) for pid, n in peor.items() if n != "sin" and pid in puntos]
    if not con_lluvia:
        return "Pronóstico de lluvia (Open-Meteo) para las próximas 3 horas: sin lluvia en ningún lugar de la zona."
    return ("Pronóstico de lluvia (Open-Meteo) para las próximas 3 horas: " +
            ", ".join(f"lluvia {n} en {puntos[pid].nombre}" for pid, n in con_lluvia[:8]) + ".")


def linea_estado(p: PuntoAhora, origen_id: int | None, matriz, alternativa: str | None,
                 factores: trafico.Factores | None = None, duracion: str | None = None) -> str:
    partes = [f"[punto-{p.id}] {p.nombre}: {SIGNIFICADO[p.color]}"]
    if p.nivel is not None:
        partes[0] += f", {p.nivel:.1f} veces lo normal para ese lugar ({p.estado.confianza})"
    if p.estado and p.estado.ajuste_manual:
        partes.append(f"color fijado por la Secretaría: {p.estado.ajuste_manual}")
    partes.append(_techo(p))
    partes.append(f"visita sugerida: {duracion or 'sin dato'}")
    if p.eventos:
        partes.append("evento hoy: " + ", ".join(p.eventos))
    partes.append(_traslado_txt(p, origen_id, matriz, factores))
    if alternativa:
        partes.append(f'la app sugiere: "{alternativa}"')
    return "; ".join(partes) + "."


def opciones(puntos: dict[int, PuntoAhora], matriz, origen_id: int | None, intereses: list[str],
             solo_techados: bool) -> list[rec.Candidato]:
    """Las mejores opciones ahora (las mismas reglas del recomendador: nunca rojas ni cerradas, parecidas a
    los intereses y a menos de 1 h). Si preguntan por lluvia, solo techadas."""
    for refs in (frozenset(intereses), frozenset()):          # si los intereses no dejan nada, sin intereses
        lista = rec.candidatos(puntos.values(), refs, origen_id, matriz)
        if solo_techados:
            lista = [c for c in lista if c.punto.interior]
        if lista:
            return lista[:N_OPCIONES]
    return []


def opciones_texto(lista: list[rec.Candidato], origen_id: int | None, matriz, factores: trafico.Factores | None,
                   duraciones: dict[int, str | None], solo_techados: bool) -> str | None:
    """Una línea por opción, con todo lo que se puede decir de ella."""
    if not lista:
        # Sin esta línea, de noche (todo lo techado cerrado) el modelo llamó "techado" al Centro de Atlixco
        # y se inventó un "regresa a las 06:20" (2026-10-16, 02:20).
        return SIN_TECHADOS if solo_techados else None
    encabezado = ("Opciones que la app recomienda ahora" + (" (solo techadas, porque la pregunta es de lluvia)"
                                                              if solo_techados else "") + ":")
    lineas = [f"{i}) [punto-{c.punto.id}] {c.punto.nombre}: {SIGNIFICADO[c.punto.color]}; {_techo(c.punto)}; "
              f"visita sugerida: {duraciones.get(c.punto.id) or 'sin dato'}; "
              f"{_traslado_txt(c.punto, origen_id, matriz, factores)}."
              for i, c in enumerate(lista, 1)]
    return "\n".join([encabezado, *lineas])


SIN_TECHADOS = ("Opciones techadas abiertas ahora: ninguna (a esta hora todos los lugares techados de la zona "
                "están cerrados).")


def instruccion_para(giros: list[str], docs: list[Recuperado], sin_techados: bool = False) -> str | None:
    """Instrucción pegada a la pregunta según su tipo (un modelo chico la sigue mejor que una regla general)."""
    if not giros and sin_techados:
        return ("La pregunta es de lluvia y ahora no hay lugares techados abiertos: dilo así. No llames techado "
                "a ningún lugar que el ESTADO EN VIVO marque al aire libre y no des horas que no vengan ahí.")
    if not giros:
        return None
    que = " y ".join({"alimentos": "dónde comer", "hospedaje": "dónde dormir"}[g] for g in giros)
    if not any(d.coleccion == "establecimientos" for d in docs):
        return f"La pregunta es de {que} y no hay establecimientos en el CONTEXTO: responde \"No tengo ese dato.\""
    return (f"La pregunta es de {que}: responde con los establecimientos denue- del CONTEXTO, copiando su nombre, "
            "su tipo y su distancia tal como vienen. Como sí hay, no digas que no hay opciones. No les pongas techado, "
            "al aire libre, horario, precio ni visita sugerida, y no deduzcas qué sirven por su nombre.")


def armar_prompt(pregunta: str, ahora: datetime, origen: PuntoAhora | None, docs: list[Recuperado],
                 estado: list[str], mejor_ahora: str | None, instruccion: str | None = None) -> str:
    contexto = "\n".join(f"[{d.id}] {d.texto}" for d in docs) or "(sin documentos)"
    vivo = "\n".join(estado) or "(sin lugares en vivo)"
    if mejor_ahora:
        vivo += f"\n{mejor_ahora}"
    return (f"FECHA Y HORA: {_cuando(ahora)}\n"
            f"UBICACIÓN DEL TURISTA: {origen.nombre if origen else 'no la dio (no hay traslados)'}\n\n"
            f"CONTEXTO:\n{contexto}\n\nESTADO EN VIVO (calculado ahora por la app):\n{vivo}\n\n"
            + (f"INSTRUCCIÓN PARA ESTA PREGUNTA: {instruccion}\n\n" if instruccion else "")
            + f"PREGUNTA: {pregunta}")


def citas(texto: str, validos: set[str]) -> tuple[list[str], list[str]]:
    """Ids citados que sí estaban en el contexto (en orden, sin repetir) y los que no."""
    vistos = list(dict.fromkeys(CITA.findall(texto)))
    return [i for i in vistos if i in validos], [i for i in vistos if i not in validos]


def preguntar(con: sqlite3.Connection, ahora: datetime, pregunta: str, origen_id: int | None = None,
              intereses: list[str] | None = None) -> dict:
    t0 = time.perf_counter()
    intereses = sorted(set(intereses or ()) | intereses_de(pregunta))
    puntos = situacion(con, ahora)
    matriz = traslados(con, ahora)
    factores = trafico.factores_vigentes(con, ahora)
    origen = puntos.get(origen_id) if origen_id else None
    lluvia_pregunta = habla_de_lluvia(pregunta)
    llueve = lluvia_pregunta or ((origen.lluvia != "sin") if origen else
                                 sum(p.lluvia != "sin" for p in puntos.values()) > len(puntos) / 2)
    duraciones = {r["id"]: r["duracion_sugerida"] for r in con.execute("SELECT id, duracion_sugerida FROM punto")}

    giros = giros_de(pregunta)
    anclas = ([origen] if origen else []) + [p for p in puntos.values() if p.id != origen_id and menciona(pregunta, p)]
    docs = recuperar(pregunta, ahora, llueve, giros, anclas)
    # Un lugar en rojo, cerrado o al aire libre con lluvia fuerte solo entra si la pregunta es sobre él:
    # si no, el modelo de 8B lo recomendaba igual o le pasaba sus cifras a otro lugar (evaluación 2026-10-15).
    fuera = {pid for pid, p in puntos.items()
             if rec.motivo_de_cambio(p) is not None and not menciona(pregunta, p, origen_id)}
    docs = [d for d in docs if not (d.coleccion == "puntos" and d.metadatos.get("punto_id") in fuera)]
    ids_puntos = list(dict.fromkeys(
        int(d.metadatos["punto_id"]) for d in docs
        if d.metadatos.get("punto_id") is not None and d.metadatos["punto_id"] not in fuera))
    estado, usados = [], []
    for pid in ids_puntos:
        p = puntos[pid]
        alternativa = None
        if rec.motivo_de_cambio(p) is not None:
            alternativa = rec.recomendar(puntos, matriz, ahora, pedido_id=pid, origen_id=origen_id,
                                         intereses=intereses or (),
                                         pronostico_pedido=pronostico_punto(con, pid, ahora)).razon
        estado.append(linea_estado(p, origen_id, matriz, alternativa, factores, duraciones.get(pid)))
        usados.append({"id": f"punto-{pid}", "nombre": p.nombre, "color": p.color, "nivel": p.nivel,
                       "confianza": p.estado.confianza if p.estado else None, "lluvia": p.lluvia})
    # Las próximas horas solo de los lugares que la pregunta nombra (para "¿cuándo conviene ir a…?").
    for p in anclas:
        if p.id != origen_id:
            estado.append(proximas_horas_txt(con, p, ahora))
    if llueve:
        estado.append(pronostico_lluvia_txt(con, puntos, ahora))
    # En preguntas de comer o dormir no van las opciones de atractivos: distraían al modelo de los
    # restaurantes del DENUE (respondió "en el Zócalo no hay opciones de desayuno", 2026-10-16).
    lista = [] if giros else opciones(puntos, matriz, origen_id, intereses, solo_techados=lluvia_pregunta)
    mejor = opciones_texto(lista, origen_id, matriz, factores, duraciones, lluvia_pregunta)
    for c in lista:
        if f"punto-{c.punto.id}" not in {u["id"] for u in usados}:
            usados.append({"id": f"punto-{c.punto.id}", "nombre": c.punto.nombre, "color": c.punto.color,
                           "nivel": c.punto.nivel, "confianza": c.punto.estado.confianza, "lluvia": c.punto.lluvia})

    sin_techados = lluvia_pregunta and not giros and not lista
    prompt = armar_prompt(pregunta, ahora, origen, docs, estado, mejor,
                          instruccion_para(giros, docs, sin_techados=sin_techados))
    t1 = time.perf_counter()
    if sin_techados:
        # Lluvia y nada techado abierto (de noche): respuesta fija con los datos, sin el modelo. Aun con la
        # instrucción, el modelo de 8B llamó "techado" al Zócalo y propuso la Catedral cerrada (2026-10-16).
        texto = ("Ahora no hay lugares techados abiertos en la zona: a esta hora todos están cerrados. "
                 + pronostico_lluvia_txt(con, puntos, ahora))
        r = {"texto": texto, "modelo": "sin modelo (respuesta fija)", "tokens_prompt": None,
             "contexto_cerca_del_limite": False}
        usados = []
    else:
        r = llm.chatear(SISTEMA, prompt)
    validos = {d.id for d in docs} | {u["id"] for u in usados}
    citadas, invalidas = citas(r["texto"], validos)
    texto = r["texto"]
    for i in invalidas:      # el turista no debe ver una cita que no lleva a ninguna fuente
        texto = texto.replace(f" [{i}]", "").replace(f"[{i}]", "")
    por_id = {d.id: d for d in docs}
    fuentes = []
    for i in citadas:
        d = por_id.get(i)
        if d is None:     # citó la línea de estado en vivo de un punto que no venía como documento
            fuentes.append({"id": i, "titulo": next(u["nombre"] for u in usados if u["id"] == i),
                            "fuente": "Estado en vivo calculado por la app", "url": None})
        else:
            fuentes.append({"id": i, "titulo": d.metadatos.get("titulo", i), "fuente": d.metadatos.get("fuente"),
                            "url": d.metadatos.get("url")})
    return {
        "respuesta": texto,
        "intereses": intereses,
        "fuentes": fuentes,
        "citas_invalidas": invalidas,
        "estado_usado": usados,
        "documentos": [{"id": d.id, "coleccion": d.coleccion, "distancia": d.distancia} for d in docs],
        "modelo": r["modelo"],
        "segundos": {"recuperar": round(t1 - t0, 2), "modelo": round(time.perf_counter() - t1, 2),
                     "total": round(time.perf_counter() - t0, 2),
                     "tokens_prompt": r["tokens_prompt"], "contexto_cerca_del_limite": r["contexto_cerca_del_limite"]},
        "prompt": prompt,
    }
