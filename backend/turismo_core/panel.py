"""Vistas del panel de gobierno (CU_07): solo agregados por punto y hora, nunca reportes sueltos (RN_12).

Las sesiones de demo (``sesion.es_demo = 1``, evaluadores del stand) **sí** mueven el semáforo en vivo,
pero no entran a las estadísticas salvo que se pida ``incluir_demo`` (RN_11); la respuesta lo dice.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from statistics import median

from turismo_core.semaforo import AjusteManual, calcular_umbrales, color, serie_relativa
from turismo_core.servicio import NoEncontrado, frescura, punto_dict
from turismo_core.situacion import situacion

COLORES_AJUSTE = ("verde", "amarillo", "rojo")


def _dia(d: date) -> tuple[str, str]:
    return f"{d.isoformat()}T00:00:00", f"{d.isoformat()}T23:59:59"


def afluencia(con: sqlite3.Connection, ahora: datetime, incluir_demo: bool = False) -> dict:
    """Mapa de calor: el estado de cada punto ahora y los totales del día."""
    puntos = situacion(con, ahora)
    desde, hasta = _dia(ahora.date())
    reportes = {r["estado"]: r["n"] for r in con.execute(
        "SELECT r.estado, COUNT(*) AS n FROM reporte r JOIN sesion s ON s.id = r.sesion_id "
        "WHERE r.creado_en BETWEEN ? AND ? AND (? OR s.es_demo = 0) GROUP BY r.estado",
        (desde, hasta, int(incluir_demo)))}
    busq = con.execute(
        "SELECT COUNT(b.punto_sugerido) AS sugeridas, SUM(b.aceptada = 1) AS aceptadas FROM busqueda b "
        "JOIN sesion s ON s.id = b.sesion_id WHERE b.creada_en BETWEEN ? AND ? AND (? OR s.es_demo = 0)",
        (desde, hasta, int(incluir_demo))).fetchone()
    return {
        "incluye_demo": incluir_demo,
        "hoy": {
            "reportes": sum(reportes.values()),
            "reportes_por_estado": {k: reportes.get(k, 0) for k in ("valido", "dudoso", "descartado")},
            "redirecciones_sugeridas": busq["sugeridas"] or 0,
            "redirecciones_aceptadas": busq["aceptadas"] or 0,
        },
        "puntos": [punto_dict(p) for p in puntos.values()],
        "datos": frescura(con, ahora),
    }


def redirecciones(con: sqlite3.Connection, desde: date, hasta: date, incluir_demo: bool = False) -> dict:
    """De dónde a dónde y por qué: cuántas veces se sugirió cada cambio y cuántas se aceptaron."""
    filas = [dict(r) for r in con.execute(
        """SELECT b.punto_pedido AS desde_id, pp.nombre AS desde, b.punto_sugerido AS hacia_id, ps.nombre AS hacia,
                  b.motivo, COUNT(*) AS sugeridas, SUM(b.aceptada = 1) AS aceptadas, SUM(b.aceptada = 0) AS ignoradas
           FROM busqueda b JOIN sesion s ON s.id = b.sesion_id
           LEFT JOIN punto pp ON pp.id = b.punto_pedido JOIN punto ps ON ps.id = b.punto_sugerido
           WHERE b.creada_en BETWEEN ? AND ? AND (? OR s.es_demo = 0)
           GROUP BY b.punto_pedido, b.punto_sugerido, b.motivo ORDER BY aceptadas DESC, sugeridas DESC""",
        (_dia(desde)[0], _dia(hasta)[1], int(incluir_demo)))]
    for f in filas:
        f["aceptadas"] = f["aceptadas"] or 0
        f["ignoradas"] = f["ignoradas"] or 0
    return {
        "desde": desde.isoformat(), "hasta": hasta.isoformat(), "incluye_demo": incluir_demo,
        "total_sugeridas": sum(f["sugeridas"] for f in filas),
        "total_aceptadas": sum(f["aceptadas"] for f in filas),
        "filas": filas,
    }


# ───────────── Derrama (RN_14) ─────────────

SUPUESTO_DERRAMA = ("Cada redirección aceptada cuenta como 1 visitante que gasta lo que gasta en promedio un visitante "
                    "de ese destino (derrama ÷ afluencia de visitantes del Observatorio, últimos 12 meses publicados). "
                    "No vemos el ticket del turista ni el tamaño de su grupo. 'Nueva' = aceptó la alternativa y después "
                    "reportó desde el lugar que había pedido: esa parada se sumó a su plan.")


def gasto_por_visitante(con: sqlite3.Connection) -> dict[int, dict]:
    """Derrama ÷ visitantes de cada destino en los últimos 12 meses publicados (dato del Observatorio)."""
    fin = con.execute("SELECT MAX(periodo) FROM hecho_observatorio WHERE indicador = 'afluencia' AND valor > 0").fetchone()[0]
    anio, mes = map(int, fin.split("-"))
    inicio = f"{anio - 1}-{mes + 1:02d}" if mes < 12 else f"{anio}-01"
    salida = {}
    for r in con.execute(
        "SELECT destino_id, SUM(CASE WHEN indicador = 'derrama_mxn' THEN valor END) AS derrama, "
        "SUM(CASE WHEN indicador = 'afluencia' THEN valor END) AS visitantes FROM hecho_observatorio "
        "WHERE periodo BETWEEN ? AND ? GROUP BY destino_id", (inicio, fin)):
        if r["visitantes"]:
            salida[r["destino_id"]] = {"gasto_mxn": round(r["derrama"] / r["visitantes"], 2),
                                       "periodo": f"{inicio} a {fin}"}
    return salida


def derrama(con: sqlite3.Connection, desde: date, hasta: date, incluir_demo: bool = False) -> dict:
    """Derrama redistribuida y nueva estimada, siempre con su supuesto (RN_14)."""
    gasto = gasto_por_visitante(con)
    filas = con.execute(
        """SELECT b.id, b.sesion_id, b.creada_en, b.punto_pedido, b.punto_sugerido,
                  pp.destino_id AS destino_pedido, ps.destino_id AS destino_sugerido, ds.nombre AS destino,
                  EXISTS (SELECT 1 FROM reporte r WHERE r.sesion_id = b.sesion_id AND r.punto_id = b.punto_pedido
                          AND r.creado_en > b.creada_en AND r.estado <> 'descartado') AS volvio
           FROM busqueda b JOIN sesion s ON s.id = b.sesion_id
           JOIN punto ps ON ps.id = b.punto_sugerido JOIN destino ds ON ds.id = ps.destino_id
           LEFT JOIN punto pp ON pp.id = b.punto_pedido
           WHERE b.aceptada = 1 AND b.creada_en BETWEEN ? AND ? AND (? OR s.es_demo = 0)""",
        (_dia(desde)[0], _dia(hasta)[1], int(incluir_demo))).fetchall()

    redistribuida = nueva = entre_destinos = 0.0
    por_destino: dict[str, dict] = {}
    for f in filas:
        g = gasto.get(f["destino_sugerido"], {}).get("gasto_mxn", 0.0)
        d = por_destino.setdefault(f["destino"], {"destino": f["destino"], "aceptadas": 0, "redistribuida_mxn": 0.0,
                                                  "nueva_mxn": 0.0, "gasto_por_visitante_mxn": g})
        d["aceptadas"] += 1
        if f["volvio"]:
            nueva += g
            d["nueva_mxn"] += g
        else:
            redistribuida += g
            d["redistribuida_mxn"] += g
            if f["destino_pedido"] is not None and f["destino_pedido"] != f["destino_sugerido"]:
                entre_destinos += g
    return {
        "desde": desde.isoformat(), "hasta": hasta.isoformat(), "incluye_demo": incluir_demo,
        "redirecciones_aceptadas": len(filas),
        "redistribuida_mxn": round(redistribuida, 2),
        "redistribuida_entre_destinos_mxn": round(entre_destinos, 2),
        "nueva_estimada_mxn": round(nueva, 2),
        "por_destino": sorted(por_destino.values(), key=lambda d: -(d["redistribuida_mxn"] + d["nueva_mxn"])),
        "gasto_por_visitante": [{"destino_id": k, **v} for k, v in sorted(gasto.items())],
        "supuesto": SUPUESTO_DERRAMA,
        "fuente": "Observatorio Turístico de Puebla (derrama y afluencia de visitantes) + búsquedas de la app",
    }


# ───────────── Semáforo estatal mensual ─────────────

DESDE_HISTORIA = "2022-01"      # supuesto: solo después de la pandemia; varios destinos crecen y 2017 sesgaría la mediana
ANIOS_ESTIMADO = 3


def semaforo_estatal(con: sqlite3.Connection, mes: int, anio: int) -> dict:
    """Los destinos del Observatorio en un mes, cada uno contra su propia historia mensual (mismo método que
    los puntos: valor ÷ mediana y percentiles 60/85). Mes publicado: dato. Mes sin publicar: promedio del
    mismo mes de los últimos 3 años con dato, marcado como estimado (no es pronóstico)."""
    periodo = f"{anio}-{mes:02d}"
    salida = []
    for d in con.execute("SELECT id, nombre FROM destino WHERE es_agregado = 0 ORDER BY nombre"):
        serie = {r["periodo"]: r["valor"] for r in con.execute(
            "SELECT periodo, valor FROM hecho_observatorio WHERE destino_id = ? AND indicador = 'afluencia' "
            "AND periodo >= ? AND valor > 0 AND es_pandemia = 0 ORDER BY periodo", (d["id"], DESDE_HISTORIA))}
        if not serie:
            continue
        valores = list(serie.values())
        mediana = median(valores)
        u = calcular_umbrales(serie_relativa(valores))
        if periodo in serie:
            valor, tipo, base = serie[periodo], "dato", [periodo]
        else:
            mismos = sorted((p for p in serie if p.endswith(f"-{mes:02d}") and p < periodo), reverse=True)[:ANIOS_ESTIMADO]
            valor = sum(serie[p] for p in mismos) / len(mismos) if mismos else None
            tipo, base = ("estimado", mismos) if mismos else ("sin_dato", [])
        nivel = None if valor is None else round(valor / mediana, 3)
        salida.append({"destino_id": d["id"], "destino": d["nombre"], "tipo": tipo, "periodos_usados": sorted(base),
                       "visitantes": None if valor is None else round(valor), "nivel": nivel,
                       "color": color(nivel, u), "umbrales": {"bajo": u.bajo, "alto": u.alto, "metodo": u.metodo,
                                                              "n_meses": u.n_muestras}})
    salida.sort(key=lambda x: -(x["nivel"] or 0))
    return {"mes": mes, "anio": anio,
            "metodo": f"Afluencia de visitantes del destino ÷ su mediana mensual desde {DESDE_HISTORIA} (sin pandemia); "
                      f"umbrales en sus percentiles 60 y 85. Mes sin publicar: promedio del mismo mes de los últimos "
                      f"{ANIOS_ESTIMADO} años (estimado, no pronóstico).",
            "fuente": "Observatorio Turístico de Puebla",
            "destinos": salida}


INDICADORES_OBSERVATORIO = ("afluencia", "llegadas", "derrama_mxn", "ocupacion_pct", "estadia_promedio",
                            "turistas_noche", "cuartos_disponibles", "cuartos_ocupados", "densidad_ocupacion")


def historico_destino(con: sqlite3.Connection, destino: str, indicador: str = "afluencia",
                      desde: str = "2017-01", hasta: str = "2100-12") -> dict:
    """Serie mensual del Observatorio de un destino (``desde``/``hasta`` como 'YYYY-MM')."""
    if indicador not in INDICADORES_OBSERVATORIO:
        raise ValueError(f"Indicador inválido: {indicador}. Usa uno de: {', '.join(INDICADORES_OBSERVATORIO)}")
    d = con.execute("SELECT id, nombre FROM destino WHERE nombre = ?", (destino,)).fetchone()
    if d is None:
        nombres = [r[0] for r in con.execute("SELECT nombre FROM destino ORDER BY nombre")]
        raise NoEncontrado(f"No existe el destino '{destino}'. Destinos: {', '.join(nombres)}")
    serie = [{"periodo": r["periodo"], "valor": r["valor"], "pandemia": bool(r["es_pandemia"])} for r in con.execute(
        "SELECT periodo, valor, es_pandemia FROM hecho_observatorio WHERE destino_id = ? AND indicador = ? "
        "AND periodo BETWEEN ? AND ? ORDER BY periodo", (d["id"], indicador, desde, hasta))]
    return {"destino": d["nombre"], "indicador": indicador, "serie": serie,
            "fuente": "Observatorio Turístico de Puebla (Sectur Puebla)"}


def umbrales(con: sqlite3.Connection) -> list[dict]:
    """Umbrales ``bajo``/``alto`` de cada punto y cómo se calcularon (explica por qué tiene ese color)."""
    return [dict(r) for r in con.execute(
        "SELECT p.id AS punto_id, p.nombre, u.bajo, u.alto, u.metodo, u.n_muestras, u.calculado_en "
        "FROM punto p LEFT JOIN umbral_punto u ON u.punto_id = p.id ORDER BY p.id")]


def ajustes_vigentes(con: sqlite3.Connection, ahora: datetime) -> list[dict]:
    t = ahora.isoformat(timespec="seconds")
    return [dict(r) for r in con.execute(
        "SELECT a.id, a.punto_id, p.nombre, a.color, a.motivo, a.creado_en, a.hasta FROM ajuste_manual a "
        "JOIN punto p ON p.id = a.punto_id WHERE a.creado_en <= ? AND a.hasta > ? ORDER BY a.creado_en DESC", (t, t))]


def fijar_ajuste(con: sqlite3.Connection, ahora: datetime, punto_id: int, color: str, motivo: str,
                 horas: float) -> dict:
    """RN_16: el funcionario fija el color con un motivo y una hora de fin; gana sobre el cálculo mientras dure."""
    if con.execute("SELECT 1 FROM punto WHERE id = ?", (punto_id,)).fetchone() is None:
        raise NoEncontrado(f"No existe el punto {punto_id}")
    if color not in COLORES_AJUSTE:
        raise ValueError(f"Color inválido: {color}")
    ajuste = AjusteManual(color, motivo.strip(), ahora + timedelta(hours=horas))
    cur = con.execute(
        "INSERT INTO ajuste_manual (punto_id, color, motivo, creado_en, hasta) VALUES (?, ?, ?, ?, ?)",
        (punto_id, ajuste.color, ajuste.motivo, ahora.isoformat(timespec="seconds"),
         ajuste.hasta.isoformat(timespec="seconds")))
    con.commit()
    return {"ajuste_id": cur.lastrowid, "hasta": ajuste.hasta.isoformat(timespec="minutes"),
            "punto": punto_dict(situacion(con, ahora)[punto_id])}


def quitar_ajuste(con: sqlite3.Connection, ahora: datetime, ajuste_id: int) -> dict:
    """Termina un ajuste antes de tiempo (se conserva en la tabla, con ``hasta`` = ahora)."""
    fila = con.execute("SELECT punto_id FROM ajuste_manual WHERE id = ?", (ajuste_id,)).fetchone()
    if fila is None:
        raise NoEncontrado(f"No existe el ajuste {ajuste_id}")
    con.execute("UPDATE ajuste_manual SET hasta = ? WHERE id = ? AND hasta > ?",
                (ahora.isoformat(timespec="seconds"), ajuste_id, ahora.isoformat(timespec="seconds")))
    con.commit()
    return {"ajuste_id": ajuste_id, "punto": punto_dict(situacion(con, ahora)[fila["punto_id"]])}
