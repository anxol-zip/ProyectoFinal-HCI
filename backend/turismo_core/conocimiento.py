"""Textos que se indexan en ChromaDB (docs/05b §6), armados con plantillas desde nuestros datos.

Ningún texto lo escribe un LLM ni se inventa: cada uno sale del catálogo, de la tabla ``evento``,
de los hechos oficiales en SQLite (Observatorio e INAH) o de las constantes del propio código
(metodología). Cada documento lleva su ``fuente`` y, si existe, su ``url``.

Un documento es ``Doc(id, texto, metadatos)``; los metadatos nunca llevan ``None`` (ChromaDB no lo acepta).
"""

from __future__ import annotations

import json
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from turismo_core import conveniencia, recomendador, reportes

DIAS = ("lun", "mar", "mie", "jue", "vie", "sab", "dom")
DIAS_TEXTO = {"lun": "lunes", "mar": "martes", "mie": "miércoles", "jue": "jueves", "vie": "viernes",
              "sab": "sábado", "dom": "domingo"}
TIPOS = {"zona_arqueologica": "zona arqueológica", "pueblo_magico": "Pueblo Mágico"}
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")


@dataclass(frozen=True)
class Doc:
    id: str
    texto: str
    metadatos: dict = field(default_factory=dict)


def _limpio(m: dict) -> dict:
    return {k: v for k, v in m.items() if v is not None and v != []}


def _num(x: float) -> str:
    return f"{x:,.0f}"


def _periodo(p: str) -> str:
    anio, mes = p.split("-")
    return f"{MESES[int(mes) - 1]} {anio}"


# ───────────── Puntos ─────────────

def horario_texto(texto: str | None) -> str:
    """``{"mar": "10:00-17:00", …}`` -> "martes a domingo de 10:00 a 17:00" (agrupa días seguidos iguales)."""
    if not texto:
        return "horario por confirmar"
    h = json.loads(texto)
    if all(h.get(d) == "00:00-24:00" for d in DIAS):
        return "abierto las 24 horas"
    grupos: list[list] = []
    for d in DIAS:
        if d not in h:
            continue
        if grupos and grupos[-1][1] == h[d] and DIAS.index(d) == DIAS.index(grupos[-1][0][-1]) + 1:
            grupos[-1][0].append(d)
        else:
            grupos.append([[d], h[d]])
    partes = []
    for dias, rangos in grupos:
        cuando = DIAS_TEXTO[dias[0]] if len(dias) == 1 else f"{DIAS_TEXTO[dias[0]]} a {DIAS_TEXTO[dias[-1]]}"
        turnos = " y ".join(f"de {r.split('-')[0]} a {r.split('-')[1]}" for r in rangos.split(","))
        partes.append(f"{cuando} {turnos}")
    cerrados = [DIAS_TEXTO[d] for d in DIAS if d not in h]
    return "; ".join(partes) + (f"; cerrado {', '.join(cerrados)}" if cerrados else "")


def doc_punto(p: sqlite3.Row | dict) -> Doc:
    cats = [c.strip() for c in (p["categorias"] or "").split(",") if c.strip()]
    tipo = TIPOS.get(p["tipo"], (p["tipo"] or "lugar").replace("_", " "))
    # Lo que falta se dice ("sin dato") para que el modelo no lo rellene con el dato de otro punto
    # (evaluación del 2026-10-15: le puso al Acuario la duración de Africam).
    costo = ("entrada gratuita" if p["costo_mxn"] == 0 else
             f"entrada ${p['costo_mxn']:,.0f}" if p["costo_mxn"] else "sin dato")
    partes = [
        f"{p['nombre']}: {tipo} en {p['destino']} (municipio de {p['municipio']}).",
        p["ficha"] or "",
        f"Intereses: {recomendador._lista(cats)}.",
        "Es techado (sirve si llueve)." if p["interior"] else "Es al aire libre.",
        f"Horario: {horario_texto(p['horario'])}.",
        f"Costo: {costo}.",
        f"Visita sugerida: {p['duracion_sugerida'] or 'sin dato'}.",
    ]
    return Doc(f"punto-{p['id']}", " ".join(x for x in partes if x), _limpio({
        "punto_id": p["id"], "titulo": p["nombre"], "destino": p["destino"], "tipo": p["tipo"],
        "interior": bool(p["interior"]), "categorias": cats, "verificado": bool(p["verificado"]),
        "fuente": p["fuente_texto"] or "Catálogo de la zona piloto (equipo)",
    }))


def docs_puntos(con: sqlite3.Connection) -> list[Doc]:
    return [doc_punto(r) for r in con.execute(
        "SELECT p.*, d.nombre AS destino FROM punto p JOIN destino d ON d.id = p.destino_id ORDER BY p.id")]


# ───────────── Eventos (solo verificados) ─────────────

def _fecha_int(texto: str) -> int:
    return int(texto[:10].replace("-", ""))


def docs_eventos(con: sqlite3.Connection) -> list[Doc]:
    """Un documento por evento; las funciones repetidas de un mismo evento (Catrinia) van juntas."""
    grupos: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for e in con.execute(
        "SELECT e.*, d.nombre AS destino, p.nombre AS punto FROM evento e LEFT JOIN destino d ON d.id = e.destino_id "
        "LEFT JOIN punto p ON p.id = e.punto_id WHERE e.verificado = 1 ORDER BY e.inicio"):
        grupos[e["nombre"].split(" (")[0]].append(e)
    salida = []
    for nombre, filas in grupos.items():
        e = filas[0]
        lugar = e["punto"] or e["destino"] or "zona piloto"
        if len(filas) == 1:
            cuando = f"del {e['inicio'][:10]} al {e['fin'][:10]}"
        else:
            cuando = "en estas fechas: " + ", ".join(f"{f['inicio'][:10]} de {f['inicio'][11:16]} a {f['fin'][11:16]}" for f in filas)
        texto = f"{nombre}, en {lugar} ({e['destino']}), {cuando}. Impacto esperado en la afluencia: {e['impacto']}. {e['nota'] or ''}"
        salida.append(Doc(f"evento-{e['id']}", texto.strip(), _limpio({
            "titulo": nombre, "destino": e["destino"], "punto_id": e["punto_id"],
            "inicio": min(_fecha_int(f["inicio"]) for f in filas), "fin": max(_fecha_int(f["fin"]) for f in filas),
            "impacto": e["impacto"], "url": e["fuente_url"], "fuente": e["fuente_url"],
        })))
    return salida


# ───────────── Conocimiento: Observatorio, INAH, metodología y fuentes ─────────────

INDICADORES = ("afluencia", "llegadas", "derrama_mxn", "ocupacion_pct", "estadia_promedio")


def docs_observatorio(con: sqlite3.Connection) -> list[Doc]:
    """Resumen de los últimos 12 meses publicados de cada destino (y del estado), contra los 12 anteriores."""
    url = con.execute("SELECT url FROM fuente WHERE nombre LIKE 'Observatorio%'").fetchone()
    url = url[0] if url else None
    fin = con.execute("SELECT MAX(periodo) FROM hecho_observatorio WHERE indicador = 'afluencia' AND valor > 0").fetchone()[0]
    anio, mes = map(int, fin.split("-"))
    meses = [f"{y}-{m + 1:02d}" for y, m in (divmod(anio * 12 + mes - 1 - i, 12) for i in range(24))][::-1]
    actual, previo = meses[12:], meses[:12]

    def serie(destino_id: int, indicador: str, periodos: list[str]) -> list[float]:
        return [r[0] for r in con.execute(
            f"SELECT valor FROM hecho_observatorio WHERE destino_id = ? AND indicador = ? AND periodo IN ({','.join('?' * len(periodos))}) "
            "AND valor IS NOT NULL", (destino_id, indicador, *periodos))]

    estado = con.execute("SELECT id FROM destino WHERE nombre = 'Estado'").fetchone()[0]
    tot = {i: sum(serie(estado, i, actual)) for i in ("afluencia", "llegadas", "derrama_mxn")}
    salida = []
    for d in con.execute("SELECT * FROM destino WHERE nombre NOT IN ('Cholula', 'Resto del Estado') ORDER BY id"):
        v = {i: serie(d["id"], i, actual) for i in INDICADORES}
        if not v["afluencia"]:
            continue
        afl, der = sum(v["afluencia"]), sum(v["derrama_mxn"])
        previos = [x for x in serie(d["id"], "afluencia", previo) if x > 0]
        # El cambio anual solo se da si los dos periodos tienen los 12 meses (Acatzingo y Tepeaca no los tienen).
        afl_prev = sum(previos) if len(previos) == 12 and len([x for x in v["afluencia"] if x > 0]) == 12 else 0
        proporcion = (f"Equivale al {100 * afl / tot['afluencia']:.1f} % de los visitantes, al "
                      f"{100 * sum(v['llegadas']) / tot['llegadas']:.1f} % de las llegadas de turistas y al "
                      f"{100 * der / tot['derrama_mxn']:.1f} % de la derrama del estado.")
        nombre = "el estado de Puebla (total)" if d["nombre"] == "Estado" else d["nombre"]
        partes = [
            f"{nombre}, según el Observatorio Turístico de Puebla, de {_periodo(actual[0])} a {_periodo(actual[-1])}:",
            f"{_num(afl)} visitantes (afluencia de visitantes),",
            f"{_num(sum(v['llegadas']))} llegadas de turistas,",
            f"derrama económica de ${_num(der)},",
            f"ocupación hotelera promedio de {sum(v['ocupacion_pct']) / len(v['ocupacion_pct']):.1f} %" if v["ocupacion_pct"] else "",
            f"y estadía promedio de {sum(v['estadia_promedio']) / len(v['estadia_promedio']):.2f} noches." if v["estadia_promedio"] else ".",
            f"Gasto por visitante (derrama ÷ visitantes): ${der / afl:,.0f}." if afl else "",
            proporcion if d["id"] != estado else "",
            f"Contra los 12 meses anteriores, los visitantes cambiaron {100 * (afl / afl_prev - 1):+.1f} %." if afl_prev else "",
        ]
        salida.append(Doc(f"obs-{d['id']}", " ".join(p for p in partes if p), _limpio({
            "titulo": f"Observatorio: {d['nombre']}", "destino": d["nombre"], "tipo_doc": "observatorio",
            "fecha": int(fin.replace("-", "") + "01"), "url": url, "fuente": "Observatorio Turístico de Puebla (Sectur Puebla)",
        })))
    return salida


def docs_inah(con: sqlite3.Connection) -> list[Doc]:
    """Visitas por recinto del INAH en Puebla: último año completo y lo que va del actual."""
    url = con.execute("SELECT url FROM fuente WHERE nombre LIKE 'INAH%'").fetchone()
    url = url[0] if url else None
    ultimo = con.execute("SELECT MAX(periodo) FROM hecho_inah").fetchone()[0]
    anio_actual = int(ultimo[:4])
    completo = anio_actual - 1 if not ultimo.endswith("-12") else anio_actual
    total = con.execute("SELECT SUM(visitas) FROM hecho_inah WHERE periodo LIKE ?", (f"{completo}-%",)).fetchone()[0] or 0
    salida = []
    for r in con.execute(
        "SELECT r.clave_siinah, r.nombre, r.punto_id, "
        "SUM(CASE WHEN h.periodo LIKE ? THEN h.visitas END) AS anio, "
        "SUM(CASE WHEN h.periodo LIKE ? AND h.nacionalidad = 'extranjero' THEN h.visitas END) AS extranjeros, "
        "SUM(CASE WHEN h.periodo LIKE ? THEN h.visitas END) AS actual "
        "FROM recinto_inah r JOIN hecho_inah h ON h.clave_siinah = r.clave_siinah GROUP BY r.clave_siinah ORDER BY anio DESC",
            (f"{completo}-%", f"{completo}-%", f"{anio_actual}-%")):
        if not r["anio"]:
            continue
        partes = [
            f"{r['nombre']} (recinto del INAH en Puebla): {_num(r['anio'])} visitas en {completo},",
            f"el {100 * r['anio'] / total:.1f} % de las visitas a recintos del INAH en Puebla ese año;",
            f"el INAH registra {100 * (r['extranjeros'] or 0) / r['anio']:.1f} % de visitantes extranjeros.",
            # El periodo va pegado a la cifra: el modelo le cambiaba el periodo (evaluación 2026-10-15).
            f"En lo que va de {anio_actual} (de enero a {_periodo(ultimo)}) lleva {_num(r['actual'] or 0)} visitas."
            if anio_actual != completo else "",
        ]
        salida.append(Doc(f"inah-{r['clave_siinah']}", " ".join(p for p in partes if p), _limpio({
            "titulo": f"INAH: {r['nombre']}", "punto_id": r["punto_id"], "tipo_doc": "inah",
            "fecha": int(ultimo.replace("-", "") + "01"), "url": url, "fuente": "INAH, estadísticas de visitantes",
        })))
    return salida


def docs_metodologia() -> list[Doc]:
    """Cómo funciona la app, con las cifras de las constantes del código (no se desfasa del código)."""
    p = conveniencia.PESOS
    textos = {
        "metodo-semaforo": (
            "Cómo se decide el color del semáforo: no hay un contador de personas en vivo; la app estima la "
            "afluencia de cada lugar por hora a partir de datos oficiales mensuales (INAH para sus recintos y el "
            "Observatorio Turístico para los demás), con factores de día, hora, festivos, eventos verificados y "
            "lluvia. Cada lugar se compara contra su propia historia, no contra los demás: rojo significa que ahora "
            "está más lleno que en el 85 % de sus propias horas abiertas de 2023 a 2025; amarillo, más lleno que en "
            "el 60 % pero no que en el 85 %; verde, menos lleno que en el 60 % de sus horas. "
            "Los factores de día y hora son supuestos del equipo, porque no existe una fuente pública de afluencia "
            "por hora en Puebla; los reportes de los turistas los corrigen. Si la Secretaría fija un color a mano "
            "(por un cierre o una obra), ese color gana y se muestra el motivo."),
        "metodo-reportes": (
            "Cómo cuentan los reportes de los turistas (botón ¿Cómo está?): cada reporte (vacío, normal o lleno) se "
            "mezcla con la estimación; la estimación vale lo mismo que unos 2 reportes recientes. Un reporte pierde "
            "peso con el tiempo: a los 45 minutos vale cerca de un tercio y después de 3 horas ya no cuenta. Con 3 o "
            f"más reportes válidos en la última hora, el lugar dice 'confirmado por turistas'. Filtros: un reporte "
            f"por persona y lugar cada {int(reportes.ESPERA_REPETIDO.total_seconds() // 60)} minutos; no se aceptan "
            f"reportes de lugares cerrados; sin GPS el reporte vale la mitad y a más de {reportes.RADIO_M:.0f} m del "
            "lugar se marca como dudoso. No se guarda la ubicación del turista ni datos personales."),
        "metodo-recomendador": (
            "Cómo se elige la alternativa ('mejor ve a…'): si el lugar pedido está en rojo, cerrado o es al aire "
            "libre con lluvia fuerte, la app busca otro que nunca esté en rojo, que esté abierto, que se parezca "
            "(mismos intereses: historia, arte, naturaleza…) y que esté a menos de 1 hora de traslado. Con lluvia "
            "solo propone lugares techados. El puntaje combina parecido (30 %) y conveniencia (70 %); la "
            f"conveniencia pesa afluencia {p['afluencia']:.0%}, clima {p['clima']:.0%} y traslado {p['traslado']:.0%}. "
            "También propone otra hora para el mismo lugar ('o regresa a las …'). Los traslados en coche son sin "
            "tráfico (OpenRouteService); hasta 20 minutos caminando se sugiere ir a pie."),
    }
    return [Doc(k, v, {"titulo": k.replace("metodo-", "Método: "), "tipo_doc": "metodologia",
                       "fuente": "Metodología del equipo (código de turismo_core)"}) for k, v in textos.items()]


ATRIBUCIONES = ("Pronóstico del clima: Open-Meteo (open-meteo.com), licencia CC BY 4.0. "
                "Mapas y coordenadas: © colaboradores de OpenStreetMap, licencia ODbL. "
                "Tráfico en vivo: © TomTom (Routing API, plan gratuito), cada 30 min de 8:00 a 20:00.")


def doc_fuentes(con: sqlite3.Connection) -> Doc:
    filas = [f"{r['nombre']} ({r['url'] or 'sin URL'}{', ' + r['licencia'] if r['licencia'] else ''})"
             for r in con.execute("SELECT nombre, url, licencia FROM fuente ORDER BY id")]
    texto = "Fuentes de datos de la app: " + "; ".join(filas) + ". " + ATRIBUCIONES
    return Doc("fuentes", texto, {"titulo": "Fuentes y licencias", "tipo_doc": "fuentes", "fuente": "Tabla fuente de puebla.db"})


# ───────────── Establecimientos del DENUE: dónde comer y dónde dormir ─────────────

RADIO_ALIMENTOS_M = 1000
RADIO_HOSPEDAJE_M = 2000
# No son recomendación turística (decisión del 2026-10-15; el dato sigue en SQLite)
EXCLUIR_ACTIVIDADES = {"721113": "moteles", "722411": "centros nocturnos", "722310": "comedores de empresas",
                       "722320": "banquetes y eventos"}
_MINUSCULAS = {"de", "del", "la", "las", "los", "el", "y", "e", "en", "con", "a"}


def distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en línea recta (haversine), en metros."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(a))


def nombre_legible(nombre: str) -> str:
    """'RESTAURANTE LA CASA DEL MOLE' -> 'Restaurante la Casa del Mole'."""
    palabras = nombre.strip().split()
    return " ".join(w.lower() if i and w.lower() in _MINUSCULAS else w.capitalize() for i, w in enumerate(palabras))


def docs_establecimientos(con: sqlite3.Connection) -> list[Doc]:
    """Comida a ≤ 1 km y hospedaje a ≤ 2 km de algún punto. El DENUE solo da nombre, actividad, tamaño y
    ubicación: no hay horario, precio, menú ni calificación, y el texto lo dice para que nadie lo invente."""
    puntos = [(r["id"], r["nombre"], r["lat"], r["lon"]) for r in con.execute("SELECT id, nombre, lat, lon FROM punto")]
    salida = []
    for e in con.execute("SELECT * FROM establecimiento WHERE giro IN ('alimentos', 'hospedaje') AND lat IS NOT NULL"):
        if e["codigo_act"] in EXCLUIR_ACTIVIDADES or not (e["nombre"] or "").strip():   # 9 sin nombre en el DENUE
            continue
        radio = RADIO_ALIMENTOS_M if e["giro"] == "alimentos" else RADIO_HOSPEDAJE_M
        cerca = sorted((distancia_m(e["lat"], e["lon"], la, lo), pid, nom) for pid, nom, la, lo in puntos)
        cerca = [c for c in cerca if c[0] <= radio]
        if not cerca:
            continue
        d, pid, nom = cerca[0]
        nombre = nombre_legible(e["nombre"])
        tipo = "Hospedaje" if e["giro"] == "hospedaje" else "Comida"
        texto = (f"{nombre}. {tipo}: {e['nombre_act'].lower()} ({e['per_ocu']}), en {e['municipio']}; "
                 f"a {d:.0f} m en línea recta de {nom}. El DENUE no publica horario, precios, menú ni calificaciones.")
        salida.append(Doc(f"denue-{e['clee']}", texto, {
            "titulo": nombre, "giro": e["giro"], "codigo_act": e["codigo_act"], "municipio": e["municipio"],
            "lat": e["lat"], "lon": e["lon"], "punto_cercano": pid, "cerca_de": [c[1] for c in cerca],
            "tipo_doc": "denue", "fuente": "DENUE 05/2026 (INEGI)",
            "url": "https://www.inegi.org.mx/app/mapa/denue/",
        }))
    return salida


# ───────────── Bitácora: resumen diario de los reportes (sin la demo) ─────────────

NIVEL = {1: "vacío", 2: "normal", 3: "lleno"}


def docs_bitacora(con: sqlite3.Connection, desde: date) -> list[Doc]:
    """Una línea por punto y día con reportes válidos o dudosos de sesiones reales (RN_11, RN_12: solo agregados)."""
    filas = con.execute(
        "SELECT r.punto_id, p.nombre, d.nombre AS destino, substr(r.creado_en, 1, 10) AS dia, "
        "CAST(substr(r.creado_en, 12, 2) AS INTEGER) AS hora, r.nivel FROM reporte r "
        "JOIN sesion s ON s.id = r.sesion_id JOIN punto p ON p.id = r.punto_id JOIN destino d ON d.id = p.destino_id "
        "WHERE s.es_demo = 0 AND r.estado <> 'descartado' AND r.creado_en >= ?", (desde.isoformat(),)).fetchall()
    grupos: dict[tuple, list] = defaultdict(list)
    for f in filas:
        grupos[(f["punto_id"], f["nombre"], f["destino"], f["dia"])].append((f["hora"], f["nivel"]))
    salida = []
    for (pid, nombre, destino, dia), rs in sorted(grupos.items()):
        cuenta = {n: sum(1 for _, x in rs if x == n) for n in NIVEL}
        mayoria = max(cuenta, key=cuenta.get)
        horas = sorted(h for h, x in rs if x == mayoria)
        d = date.fromisoformat(dia)
        texto = (f"{DIAS_TEXTO[DIAS[d.weekday()]].capitalize()} {dia}, {nombre}: {len(rs)} reportes de turistas "
                 f"({', '.join(f'{c} {NIVEL[n]}' for n, c in cuenta.items() if c)}); la mayoría dijo '{NIVEL[mayoria]}' "
                 f"entre las {horas[0]}:00 y las {horas[-1] + 1}:00.")
        salida.append(Doc(f"bitacora-{pid}-{dia.replace('-', '')}", texto, {
            "titulo": f"Reportes: {nombre} {dia}", "punto_id": pid, "destino": destino, "fecha": int(dia.replace("-", "")),
            "n_reportes": len(rs), "tipo_doc": "bitacora", "fuente": "Reportes de turistas en la app (agregados)"}))
    return salida
