"""Lo que ve y hace el turista, listo para la API (paso 7) y el servidor MCP (paso 9).

FastAPI y MCP solo traducen: toda la lógica y las consultas a la BD viven aquí, así que los dos
responden exactamente lo mismo (docs/05c §1). Las funciones reciben la conexión y la hora
``ahora`` (siempre la real en la API; en las pruebas se fija).

Devuelven diccionarios simples (fechas en ISO) para que se conviertan a JSON sin más.
"""

from __future__ import annotations

import json
import re
import secrets
import sqlite3
from collections.abc import Iterable
from datetime import datetime, timedelta

from turismo_core import clima, trafico
from turismo_core import recomendador as rec
from turismo_core.conveniencia import conveniencia
from turismo_core.reportes import ReportePrevio, VIDA_MAX, filtrar
from turismo_core.semaforo import color as color_de
from turismo_core.situacion import HORAS_TABLA, HORAS_VISITA, PuntoAhora, pronostico_punto, situacion, traslados


class NoEncontrado(LookupError):
    """La sesión, el punto o la búsqueda no existen (la API lo vuelve un 404)."""


# ───────────── Piezas ─────────────

def _iso(d: datetime | None) -> str | None:
    return None if d is None else d.isoformat(timespec="minutes")


def url_como_llegar(lat: float, lon: float) -> str:
    """Enlace a Google Maps sin API ni clave (docs/12, T4)."""
    return f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"


def razon_corta(p: PuntoAhora) -> str:
    """Una línea para la lista del mapa (RN_03): por qué tiene ese color."""
    if p.color == "cerrado":
        return "Cerrado a esta hora"
    e = p.estado
    partes = []
    if e.ajuste_manual:
        partes.append(f"Ajustado por la Secretaría: {e.ajuste_manual}")
    elif p.color == "rojo":
        partes.append(f"{p.nivel:.1f} veces lo normal; más lleno que el 85 % de sus horas")
    elif p.color == "amarillo":
        partes.append("Movimiento normal para este lugar")
    elif p.color == "verde":
        partes.append("Tranquilo para este lugar")
    else:
        partes.append("Sin dato de afluencia para esta hora")
    if not p.interior and p.lluvia != "sin":
        partes.append(f"lluvia {p.lluvia}, es al aire libre")
    if e.confianza == "confirmado por turistas":
        partes.append("confirmado por turistas")
    if p.eventos:
        partes.append("evento: " + ", ".join(p.eventos))
    return " · ".join(partes)


ORDEN_COLOR = {"verde": 0, "amarillo": 1, "rojo": 2}


def vs_normal(p: PuntoAhora) -> str | None:
    """¿Ahora está más o menos lleno que lo que daría el modelo solo? (los reportes o la Secretaría lo movieron).
    Como "live vs. forecast" de BestTime; None si no se puede comparar."""
    e = p.estado
    if e is None or p.color not in ORDEN_COLOR:
        return None
    normal = color_de(e.estimacion, e.umbrales)
    if normal not in ORDEN_COLOR:
        return None
    d = ORDEN_COLOR[p.color] - ORDEN_COLOR[normal]
    return "mas_lleno" if d > 0 else "menos_lleno" if d < 0 else "igual"


def punto_dict(p: PuntoAhora) -> dict:
    """Estado de un punto para el mapa y la tarjeta."""
    e = p.estado
    return {
        "id": p.id, "clave": p.clave, "nombre": p.nombre, "destino": p.destino, "tipo": p.tipo,
        "categorias": sorted(p.categorias), "interior": p.interior, "lat": p.lat, "lon": p.lon,
        "color": p.color,                          # verde · amarillo · rojo · sin_dato · cerrado
        "nivel": p.nivel,                          # 1.0 = una hora normal en ese lugar
        "exceso": p.exceso,                        # > 1 = rebasa su umbral rojo
        "confianza": e.confianza if e else None,   # estimado · confirmado por turistas (RN_09)
        "n_reportes": e.n_reportes if e else 0,
        "normalmente": color_de(e.estimacion, e.umbrales) if e else None,   # color sin reportes
        "vs_normal": vs_normal(p),                 # mas_lleno · menos_lleno · igual · None
        "ajuste_manual": e.ajuste_manual if e else None,                     # motivo (RN_16)
        "umbrales": {"bajo": e.umbrales.bajo, "alto": e.umbrales.alto, "metodo": e.umbrales.metodo} if e else None,
        "lluvia": p.lluvia, "eventos": list(p.eventos),
        "razon": razon_corta(p),
    }


def traslado_dict(minutos: float | None, modo: str | None, factor: float | None, desde: int | None = None) -> dict | None:
    """Traslado para la API. En coche dice el factor de tráfico vigente y los minutos sin tráfico (paso 10);
    ``factor_trafico`` = None significa "sin tráfico en vivo" (misma zona, de noche o sin consulta reciente)."""
    if minutos is None:
        return None
    d = {"minutos": rec.minutos_texto(minutos), "modo": modo}
    if desde is not None:
        d = {"desde": desde} | d
    if modo == "en coche":
        d |= {"factor_trafico": factor, "sin_trafico_min": rec.minutos_texto(minutos / (factor or 1.0))}
    return d


def frescura(con: sqlite3.Connection, ahora: datetime) -> dict:
    """Qué tan viejos son los datos en vivo (RNF_02: "dato de hace X min")."""
    trafico_en = con.execute("SELECT MAX(consultado_en) FROM obs_trafico").fetchone()[0]
    trafico_dt = datetime.fromisoformat(trafico_en) if trafico_en else None
    clima_en = con.execute("SELECT MAX(consultado_en) FROM obs_clima").fetchone()[0]
    hasta = con.execute("SELECT MAX(para_hora) FROM afluencia_estimada").fetchone()[0]
    hora = ahora.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:00")
    cubre = con.execute("SELECT COUNT(*) FROM afluencia_estimada WHERE para_hora = ?", (hora,)).fetchone()[0] > 0
    clima_dt = datetime.fromisoformat(clima_en) if clima_en else None
    return {
        "ahora": _iso(ahora),
        "clima_consultado_en": _iso(clima_dt),
        "clima_hace_min": None if clima_dt is None else int((ahora - clima_dt).total_seconds() // 60),
        "afluencia_calculada_hasta": hasta,
        "afluencia_cubre_esta_hora": cubre,
        "trafico_consultado_en": _iso(trafico_dt),
        "trafico_hace_min": None if trafico_dt is None else int((ahora - trafico_dt).total_seconds() // 60),
    }


def _existe_punto(con: sqlite3.Connection, punto_id: int) -> None:
    if con.execute("SELECT 1 FROM punto WHERE id = ?", (punto_id,)).fetchone() is None:
        raise NoEncontrado(f"No existe el punto {punto_id}")


def _sesion(con: sqlite3.Connection, sesion_id: str) -> sqlite3.Row:
    s = con.execute("SELECT * FROM sesion WHERE id = ?", (sesion_id,)).fetchone()
    if s is None:
        raise NoEncontrado("Sesión no encontrada: pide una nueva con POST /api/sesiones")
    return s


# ───────────── Catálogo y semáforo (CU_02, CU_03) ─────────────

def catalogo(con: sqlite3.Connection, destino: str | None = None, tipo: str | None = None) -> list[dict]:
    sql = ("SELECT p.*, d.nombre AS destino FROM punto p JOIN destino d ON d.id = p.destino_id "
           "WHERE (? IS NULL OR d.nombre = ?) AND (? IS NULL OR p.tipo = ?) ORDER BY p.id")
    salida = []
    for r in con.execute(sql, (destino, destino, tipo, tipo)):
        salida.append({
            "id": r["id"], "clave": r["clave"], "nombre": r["nombre"], "destino": r["destino"],
            "municipio": r["municipio"], "tipo": r["tipo"],
            "categorias": [c.strip() for c in (r["categorias"] or "").split(",") if c.strip()],
            "interior": bool(r["interior"]), "lat": r["lat"], "lon": r["lon"],
            "horario": _horario(r["horario"]), "costo_mxn": r["costo_mxn"],
            "duracion_sugerida": r["duracion_sugerida"], "ficha": r["ficha"], "es_inah": bool(r["es_inah"]),
            "fuente": r["fuente_texto"], "verificado": bool(r["verificado"]),
        })
    return salida


def _horario(texto: str | None) -> dict | str | None:
    if not texto:
        return None
    try:
        return json.loads(texto)
    except ValueError:
        return texto


def semaforo(con: sqlite3.Connection, ahora: datetime, origen_id: int | None = None) -> dict:
    """Todos los puntos, ordenados por conveniencia (los cerrados al final)."""
    if origen_id is not None:
        _existe_punto(con, origen_id)
    puntos = situacion(con, ahora)
    matriz = traslados(con, ahora)
    f = trafico.factores_vigentes(con, ahora)
    filas = []
    for p in puntos.values():
        minutos, modo = rec.traslado(origen_id, p.id, matriz)
        d = punto_dict(p)
        d["traslado"] = traslado_dict(minutos, modo, f.de(origen_id, p.id) if origen_id else None)
        d["conveniencia"] = None if not p.abierto else conveniencia(p, minutos).total
        filas.append(d)
    filas.sort(key=lambda d: (d["conveniencia"] is None, -(d["conveniencia"] or 0)))
    return {"datos": frescura(con, ahora), "puntos": filas}


def estado_punto(con: sqlite3.Connection, punto_id: int, ahora: datetime, origen_id: int | None = None) -> dict:
    """Todo lo de la tarjeta del punto (T3)."""
    _existe_punto(con, punto_id)
    p = situacion(con, ahora)[punto_id]
    ficha = next(c for c in catalogo(con) if c["id"] == punto_id)
    salida = punto_dict(p) | {k: ficha[k] for k in ("municipio", "horario", "costo_mxn", "duracion_sugerida",
                                                     "ficha", "es_inah", "fuente", "verificado")}

    hora = ahora.replace(minute=0, second=0, microsecond=0)
    salida["proximas_horas"] = [
        {"hora": _iso(h), "color": c, "nivel": n} for h, c, n in pronostico_punto(con, punto_id, ahora, 12)]
    pron = clima.ultimo_pronostico(con, hora, hora + timedelta(hours=6))
    salida["clima"] = [
        {"hora": _iso(pr.valido_para), "temp_c": pr.temp_c, "prob_lluvia_pct": pr.prob_lluvia_pct,
         "lluvia_mm": pr.lluvia_mm, "lluvia": clima.nivel_lluvia(pr.prob_lluvia_pct, pr.lluvia_mm)}
        for (pid, _), pr in sorted(pron.items(), key=lambda kv: kv[0][1]) if pid == punto_id]
    if origen_id is not None:
        _existe_punto(con, origen_id)
        minutos, modo = rec.traslado(origen_id, punto_id, traslados(con, ahora))
        salida["traslado"] = traslado_dict(minutos, modo, trafico.factores_vigentes(con, ahora).de(origen_id, punto_id),
                                           desde=origen_id)
    else:
        salida["traslado"] = None
    salida["proximos_eventos"] = [dict(r) for r in con.execute(
        "SELECT e.nombre, e.inicio, e.fin, e.impacto, e.fuente_url FROM evento e JOIN punto p ON p.id = ? "
        "WHERE e.verificado = 1 AND e.fin >= ? AND (e.punto_id = p.id OR (e.punto_id IS NULL AND e.destino_id = p.destino_id)) "
        "ORDER BY e.inicio LIMIT 3", (punto_id, ahora.strftime("%Y-%m-%d %H:%M")))]
    salida["como_llegar_url"] = url_como_llegar(p.lat, p.lon)
    hoy = next((d for d in semana_punto(con, punto_id, ahora)["dias"] if d["fecha"] == ahora.date().isoformat()), None)
    salida["hoy"] = hoy["resumen"] if hoy else None          # hora más tranquila y más llena del resto de hoy
    salida["espera_reportada"] = espera_reportada(con, punto_id, ahora)
    salida["datos"] = frescura(con, ahora)
    return salida


def buscar_punto(con: sqlite3.Connection, texto: str | int) -> list[dict]:
    """Del nombre libre ("la pirámide", "el zócalo", "12") a los puntos del catálogo, mejores primero.

    Por id, por nombre o clave exactos, o por palabras distintivas del nombre (las mismas reglas que usa
    el asistente para saber de qué lugar se habla). Sin coincidencias devuelve lista vacía.
    """
    from turismo_core.rag import GENERICAS, _normal   # import local: rag carga ChromaDB

    texto = str(texto).strip()
    filas = [dict(r) for r in con.execute(
        "SELECT p.id, p.clave, p.nombre, d.nombre AS destino FROM punto p JOIN destino d ON d.id = p.destino_id")]
    if texto.isdigit():
        return [f | {"puntaje": 100} for f in filas if f["id"] == int(texto)]
    q = _normal(texto)
    exactos = [f | {"puntaje": 100} for f in filas if q in (_normal(f["nombre"]), f["clave"])]
    if exactos:
        return exactos
    palabras = set(re.findall(r"\w+", q))
    puntuados = []
    for f in filas:
        claves = {w for w in re.findall(r"\w+", _normal(f["nombre"]) + " " + _normal(f["destino"]))
                  if len(w) >= 4 and w not in GENERICAS}
        if palabras & claves:
            puntuados.append(f | {"puntaje": len(palabras & claves)})
    return sorted(puntuados, key=lambda f: -f["puntaje"])


def traslado_entre(con: sqlite3.Connection, origen_id: int, destino_id: int, ahora: datetime) -> dict:
    """Matriz de OpenRouteService (en coche sin tráfico y a pie) y, si hay dato vigente, el tráfico de TomTom."""
    for pid in (origen_id, destino_id):
        _existe_punto(con, pid)
    if origen_id == destino_id:
        return {"origen_id": origen_id, "destino_id": destino_id, "coche_min": 0, "coche_km": 0, "pie_min": 0, "pie_km": 0}
    r = con.execute("SELECT * FROM matriz_traslado WHERE origen_id = ? AND destino_id = ?", (origen_id, destino_id)).fetchone()
    if r is None:
        raise NoEncontrado("No hay traslado calculado entre esos puntos (corre scripts.calcular_traslados)")
    f = trafico.factores_vigentes(con, ahora)
    factor = f.de(origen_id, destino_id)
    return {"origen_id": origen_id, "destino_id": destino_id,
            "coche_min": rec.minutos_texto(r["minutos_base"] * (factor or 1.0)),
            "coche_sin_trafico_min": rec.minutos_texto(r["minutos_base"]), "factor_trafico": factor,
            "coche_km": round(r["km"], 1),
            "pie_min": rec.minutos_texto(r["minutos_pie"]), "pie_km": round(r["km_pie"], 1),
            "nota": (f"En coche con el tráfico de TomTom de las {f.consultado_en:%H:%M} (× {factor}); rutas de "
                     "OpenRouteService." if factor else "En coche sin tráfico en vivo (misma zona o sin consulta "
                     "reciente de TomTom); rutas de OpenRouteService.")}


def eventos_vigentes(con: sqlite3.Connection, ahora: datetime, destino: str | None = None) -> list[dict]:
    """Eventos verificados que no han terminado, con su fuente oficial."""
    return [dict(r) for r in con.execute(
        "SELECT e.nombre, d.nombre AS destino, p.nombre AS punto, e.inicio, e.fin, e.impacto, e.fuente_url "
        "FROM evento e LEFT JOIN destino d ON d.id = e.destino_id LEFT JOIN punto p ON p.id = e.punto_id "
        "WHERE e.verificado = 1 AND e.fin >= ? AND (? IS NULL OR d.nombre = ?) ORDER BY e.inicio",
        (ahora.strftime("%Y-%m-%d %H:%M"), destino, destino))]


# ───────────── ¿Cuándo me conviene ir? (benchmarking con REA, 2026-10-16) ─────────────

DIAS_ES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
VENTANA_ESPERA = timedelta(hours=2)


def _extremos(horas: list[dict]) -> dict | None:
    """La hora más tranquila y la más llena entre las horas abiertas en horario de visita (por nivel estimado)."""
    abiertas = [h for h in horas if h["nivel"] is not None and h["color"] in ORDEN_COLOR
                and int(h["hora"][:2]) in HORAS_VISITA]
    if not abiertas:
        return None
    tranquila = min(abiertas, key=lambda h: h["nivel"])
    llena = max(abiertas, key=lambda h: h["nivel"])
    return {"mas_tranquila": {"hora": tranquila["hora"], "color": tranquila["color"]},
            "mas_llena": {"hora": llena["hora"], "color": llena["color"]},
            "horas_verdes": [h["hora"] for h in abiertas if h["color"] == "verde"]}


def semana_punto(con: sqlite3.Connection, punto_id: int, ahora: datetime) -> dict:
    """Tabla día × hora de los próximos días (como Kioto) desde ``afluencia_estimada``: es la estimación sin
    reportes, la misma que da "normalmente". Las horas que ya pasaron de hoy se marcan."""
    _existe_punto(con, punto_id)
    hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    dias: dict[str, list[dict]] = {}
    for r in con.execute(
        "SELECT para_hora, semaforo, valor_final FROM afluencia_estimada WHERE punto_id = ? AND para_hora >= ? "
        "ORDER BY para_hora", (punto_id, hoy.strftime("%Y-%m-%d %H:00"))):
        h = datetime.strptime(r["para_hora"], "%Y-%m-%d %H:%M")
        if h.hour not in HORAS_TABLA:
            continue
        dias.setdefault(h.date().isoformat(), []).append({
            "hora": f"{h:%H:00}", "color": r["semaforo"], "nivel": r["valor_final"],
            "pasada": h + timedelta(hours=1) <= ahora})
    salida = []
    for fecha, horas in dias.items():
        d = datetime.fromisoformat(fecha)
        abiertas = [h for h in horas if h["color"] != "cerrado"]
        salida.append({"fecha": fecha, "dia": DIAS_ES[d.weekday()], "abierto": bool(abiertas),
                       "horas": abiertas, "resumen": _extremos([h for h in abiertas if not h["pasada"]])})
    return {"punto_id": punto_id, "dias": salida,
            "nota": "Estimación con datos oficiales mensuales (INAH u Observatorio) y factores de día y hora; "
                    "no incluye reportes de turistas.",
            "datos": frescura(con, ahora)}


def espera_reportada(con: sqlite3.Connection, punto_id: int, ahora: datetime) -> dict | None:
    """Mediana de la espera que reportaron los turistas en las últimas 2 h (como Affluences). Solo reportes
    válidos o dudosos que traen espera; None si no hay."""
    filas = [r for r in con.execute(
        "SELECT espera_min, creado_en FROM reporte WHERE punto_id = ? AND estado <> 'descartado' "
        "AND espera_min IS NOT NULL AND creado_en BETWEEN ? AND ? ORDER BY creado_en",
        (punto_id, (ahora - VENTANA_ESPERA).isoformat(timespec="seconds"), ahora.isoformat(timespec="seconds")))]
    if not filas:
        return None
    esperas = sorted(r["espera_min"] for r in filas)
    mitad = len(esperas) // 2
    mediana = esperas[mitad] if len(esperas) % 2 else (esperas[mitad - 1] + esperas[mitad]) / 2
    ultima = datetime.fromisoformat(filas[-1]["creado_en"])
    return {"minutos": round(mediana), "n_reportes": len(esperas),
            "ultima_hace_min": int((ahora - ultima).total_seconds() // 60)}


# ───────────── Sesiones (CU_01) ─────────────

def crear_sesion(con: sqlite3.Connection, ahora: datetime, intereses: Iterable[str] = (),
                 horas: float | None = None, origen_id: int | None = None, es_demo: bool = False) -> dict:
    """El identificador lo genera el servidor: en http:// por IP el celular no tiene ``crypto.randomUUID`` (docs/05c §4).
    Sin datos personales (RN_07): solo intereses, tiempo y el punto de partida elegido de la lista."""
    if origen_id is not None:
        _existe_punto(con, origen_id)
    sesion_id = secrets.token_urlsafe(12)
    perfil = {"intereses": sorted({i.strip() for i in intereses if i.strip()}), "horas": horas, "origen_id": origen_id}
    con.execute("INSERT INTO sesion (id, creada_en, perfil, es_demo) VALUES (?, ?, ?, ?)",
                (sesion_id, ahora.isoformat(timespec="seconds"), json.dumps(perfil, ensure_ascii=False), int(es_demo)))
    con.commit()
    return {"sesion_id": sesion_id, "es_demo": es_demo, "perfil": perfil}


# ───────────── "Mejor ve a…" (CU_04) ─────────────

def _candidato_dict(c: rec.Candidato, factor: float | None = None) -> dict:
    return punto_dict(c.punto) | {
        "traslado": traslado_dict(c.minutos, c.modo, factor),
        "similitud": c.similitud,
        "conveniencia": {"total": c.conveniencia.total, "afluencia": c.conveniencia.afluencia,
                         "clima": c.conveniencia.clima, "traslado": c.conveniencia.traslado},
        "puntaje": c.puntaje,
        "como_llegar_url": url_como_llegar(c.punto.lat, c.punto.lon),
    }


def calcular_recomendacion(con: sqlite3.Connection, ahora: datetime, punto_id: int | None = None,
                           origen_id: int | None = None, intereses: Iterable[str] = (),
                           horas: float | None = None) -> rec.Recomendacion:
    """Solo calcula (no guarda nada): la usan la API (que sí guarda la búsqueda) y el servidor MCP."""
    for pid in (punto_id, origen_id):
        if pid is not None:
            _existe_punto(con, pid)
    return rec.recomendar(situacion(con, ahora), traslados(con, ahora), ahora, pedido_id=punto_id, origen_id=origen_id,
                          intereses=list(intereses), horas=horas,
                          pronostico_pedido=pronostico_punto(con, punto_id, ahora) if punto_id else ())


def recomendacion_dict(r: rec.Recomendacion, factores: trafico.Factores | None = None,
                       origen_id: int | None = None) -> dict:
    origen = origen_id if origen_id is not None else (r.pedido.id if r.pedido else None)

    def factor(c: rec.Candidato) -> float | None:
        return factores.de(origen, c.punto.id) if factores and origen is not None else None

    return {
        "pedido": punto_dict(r.pedido) if r.pedido else None,
        "motivo": r.motivo,                       # afluencia · lluvia · cerrado · None (no hace falta cambiar)
        "alternativa": _candidato_dict(r.alternativa, factor(r.alternativa)) if r.alternativa else None,
        "otras": [_candidato_dict(c, factor(c)) for c in r.otras],
        "otra_hora": None if r.otra_hora is None else {
            "hora": _iso(r.otra_hora.hora), "color": r.otra_hora.color, "nivel": r.otra_hora.nivel},
        "razon": r.razon,
    }


def recomendar(con: sqlite3.Connection, ahora: datetime, sesion_id: str, punto_id: int | None = None,
               origen_id: int | None = None, intereses: Iterable[str] | None = None,
               horas: float | None = None) -> dict:
    """Lo que no venga en la petición se toma del perfil de la sesión. Cada consulta se guarda en ``busqueda``."""
    s = _sesion(con, sesion_id)
    perfil = json.loads(s["perfil"] or "{}")
    intereses = list(intereses) if intereses else perfil.get("intereses", [])
    horas = horas if horas is not None else perfil.get("horas")
    origen_id = origen_id if origen_id is not None else perfil.get("origen_id")
    r = calcular_recomendacion(con, ahora, punto_id, origen_id, intereses, horas)

    motivo = r.motivo or ("intereses" if punto_id is None else "sin_cambio")
    cur = con.execute(
        "INSERT INTO busqueda (sesion_id, creada_en, punto_pedido, punto_sugerido, motivo) VALUES (?, ?, ?, ?, ?)",
        (sesion_id, ahora.isoformat(timespec="seconds"), punto_id,
         r.alternativa.punto.id if r.alternativa else None, motivo))
    con.commit()
    return {"busqueda_id": cur.lastrowid} | recomendacion_dict(r, trafico.factores_vigentes(con, ahora), origen_id)


def responder_busqueda(con: sqlite3.Connection, busqueda_id: int, aceptada: bool = True) -> dict:
    """"Vamos" (aceptada) o "Prefiero mi plan" (ignorada)."""
    cur = con.execute("UPDATE busqueda SET aceptada = ? WHERE id = ?", (int(aceptada), busqueda_id))
    if cur.rowcount == 0:
        raise NoEncontrado(f"No existe la búsqueda {busqueda_id}")
    con.commit()
    return {"busqueda_id": busqueda_id, "aceptada": aceptada}


# ───────────── "¿Cómo está?" (CU_05) ─────────────

MENSAJES = {
    "valido": "¡Gracias! Tu reporte ya ayuda a quien viene detrás.",
    "dudoso": "Gracias. Como estás lejos del lugar, tu reporte cuenta menos.",
}


def registrar_reporte(con: sqlite3.Connection, ahora: datetime, sesion_id: str, punto_id: int, nivel: int,
                      espera_min: int | None = None, distancia_m: float | None = None) -> dict:
    """Aplica los filtros antispam (``reportes.filtrar``), guarda el reporte y devuelve el estado nuevo del punto."""
    s = _sesion(con, sesion_id)
    _existe_punto(con, punto_id)
    es_demo = bool(s["es_demo"])
    p = situacion(con, ahora)[punto_id]
    desde = (ahora - VIDA_MAX).isoformat(timespec="seconds")

    if con.execute("SELECT 1 FROM reporte WHERE sesion_id = ? AND motivo LIKE 'velocidad imposible%'",
                   (sesion_id,)).fetchone():
        estado, peso, motivo, descartar = "descartado", 0.0, "sesión descartada por velocidad imposible", False
    else:
        previos = [ReportePrevio(r["punto_id"], datetime.fromisoformat(r["creado_en"])) for r in con.execute(
            "SELECT punto_id, creado_en FROM reporte WHERE sesion_id = ? AND estado <> 'descartado' AND creado_en >= ?",
            (sesion_id, desde))]
        matriz = traslados(con)
        f = filtrar(punto_id, ahora, p.abierto, distancia_m, previos,
                    lambda a, b: (matriz.get((a, b)) or (None, None))[0], es_demo=es_demo)
        estado, peso, motivo, descartar = f.estado, f.peso, f.motivo, f.descartar_sesion

    cur = con.execute(
        "INSERT INTO reporte (sesion_id, punto_id, creado_en, nivel, espera_min, distancia_m, peso, estado, motivo) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (sesion_id, punto_id, ahora.isoformat(timespec="seconds"), nivel, espera_min,
         None if distancia_m is None else round(distancia_m), peso, estado, motivo))
    if descartar:
        con.execute("UPDATE reporte SET estado = 'descartado', peso = 0 WHERE sesion_id = ?", (sesion_id,))
    con.commit()

    if estado == "descartado":
        if motivo and motivo.startswith("repetido"):
            mensaje = f"Ya reportaste este lugar; podrás volver a hacerlo a las {motivo.rsplit(' ', 1)[1]}."
        elif motivo == "punto cerrado":
            mensaje = "Este lugar está cerrado a esta hora; no se puede reportar."
        else:
            mensaje = "No pudimos aceptar el reporte."
    else:
        mensaje = MENSAJES[estado]
    return {
        "reporte": {"id": cur.lastrowid, "estado": estado, "peso": peso, "motivo": motivo, "mensaje": mensaje},
        "punto": punto_dict(situacion(con, ahora)[punto_id]),
    }
