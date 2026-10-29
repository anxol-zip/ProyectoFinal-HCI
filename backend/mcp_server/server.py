"""Servidor MCP de Puebla Ahora (paso 9; docs/05 "Servidor MCP"): la misma lógica que la API, para clientes MCP.

    cd backend
    uv run python -m mcp_server.server                                    # stdio (Claude Desktop, Claude Code)
    npx @modelcontextprotocol/inspector uv run python -m mcp_server.server   # probarlo en el navegador

FastMCP del SDK oficial (``mcp`` 1.x, fijado ``<2``: en la 2.x FastMCP se renombró a ``MCPServer``).
Cada tool llama a las mismas funciones de ``turismo_core`` que FastAPI, así que las dos puertas dicen lo
mismo. Las tools de consulta no escriben nada; solo ``puebla_reportar`` guarda (con los filtros antispam
de la app) y usa una sesión del servidor, marcada como demo si ``PUEBLA_DEMO=1`` (RN_11).

Los puntos se piden por id o por nombre libre ("la pirámide", "zócalo"); si el nombre es ambiguo, el
error dice cuáles son los candidatos.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from turismo_core import conocimiento, llm, panel, rag, servicio, trafico
from turismo_core.bd import DATA, conectar
from turismo_core.servicio import NoEncontrado

mcp = FastMCP(
    "puebla_ahora_mcp",
    instructions=(
        "Puebla Ahora: semáforo de afluencia en vivo de 23 atractivos de Puebla, Cholula, Atlixco y Huejotzingo, "
        "con alternativas ('mejor ve a…'), reportes de turistas, eventos verificados, restaurantes y hoteles "
        "(DENUE) y datos oficiales del Observatorio Turístico y del INAH. Todo dato trae su fuente. Los colores "
        "comparan cada lugar contra su propia historia; la afluencia por hora es una estimación (los factores "
        "de día y hora son supuestos documentados) que corrigen los reportes de los turistas."),
)

LECTURA = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
LECTURA_LLM = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=False)
ESCRITURA = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)

Punto = Annotated[str, Field(description="Id del punto (p. ej. '12') o su nombre libre ('la pirámide', 'zócalo de Puebla')")]
Intereses = Annotated[list[str], Field(description="historia, arte, cultura, arquitectura, naturaleza, familia, "
                                                   "gastronomia, compras, pueblos_magicos")]


@contextmanager
def _bd() -> Iterator[sqlite3.Connection]:
    con = conectar()
    try:
        yield con
    finally:
        con.close()


def _ahora() -> datetime:
    return datetime.now().replace(microsecond=0)


def _punto(con: sqlite3.Connection, valor: str | int | None) -> int | None:
    """Id del punto a partir de un id o un nombre libre; error claro si no existe o es ambiguo."""
    if valor is None or str(valor).strip() == "":
        return None
    candidatos = servicio.buscar_punto(con, valor)
    if not candidatos:
        raise NoEncontrado(f"No encontré el punto '{valor}'. Usa puebla_buscar_punto o lee datos://puntos.")
    if len(candidatos) > 1 and candidatos[0]["puntaje"] == candidatos[1]["puntaje"]:
        opciones = "; ".join(f"{c['id']} = {c['nombre']}" for c in candidatos[:5])
        raise ValueError(f"'{valor}' puede ser varios puntos: {opciones}. Repite con el id.")
    return candidatos[0]["id"]


# ───────────── Turista ─────────────

@mcp.tool(name="puebla_buscar_punto", title="Buscar un punto por nombre", annotations=LECTURA)
def buscar_punto(texto: Annotated[str, Field(description="Nombre libre, p. ej. 'la pirámide', 'Atlixco', 'catedral'", min_length=2)]) -> dict:
    """Encuentra los puntos del catálogo que corresponden a un nombre libre (mejores primero).
    Devuelve {"candidatos": [{id, clave, nombre, destino}]}; lista vacía si no hay ninguno."""
    with _bd() as con:
        return {"candidatos": servicio.buscar_punto(con, texto)[:5]}


@mcp.tool(name="puebla_que_hago_ahora", title="¿Qué me conviene ahora?", annotations=LECTURA)
def que_hago_ahora(origen: Annotated[str | None, Field(description="Dónde está el turista (id o nombre); opcional")] = None,
                   intereses: Intereses = [],
                   horas: Annotated[float | None, Field(description="Tiempo disponible en horas", gt=0, le=24)] = None) -> dict:
    """Los mejores lugares para ir AHORA según sus intereses: nunca en rojo ni cerrados, ordenados por
    conveniencia (afluencia, clima y traslado), con la razón en español y el traslado desde el origen."""
    with _bd() as con:
        origen_id = _punto(con, origen)
        r = servicio.calcular_recomendacion(con, _ahora(), None, origen_id, intereses, horas)
        return (servicio.recomendacion_dict(r, trafico.factores_vigentes(con, _ahora()), origen_id)
                | {"datos": servicio.frescura(con, _ahora())})


@mcp.tool(name="puebla_estado_punto", title="Estado de un punto", annotations=LECTURA)
def estado_punto(punto: Punto,
                 origen: Annotated[str | None, Field(description="Desde dónde calcular el traslado (opcional)")] = None) -> dict:
    """Semáforo ahora de un punto con su razón: color, nivel (1.0 = lo normal ahí), confianza (estimado o
    confirmado por turistas), umbrales, ajuste de la Secretaría, próximas 12 h, clima, traslado, horario,
    costo, eventos y fuente del dato."""
    with _bd() as con:
        return servicio.estado_punto(con, _punto(con, punto), _ahora(), _punto(con, origen))


@mcp.tool(name="puebla_semana_punto", title="¿Cuándo me conviene ir?", annotations=LECTURA)
def semana_punto(punto: Punto) -> dict:
    """Tabla día × hora de hoy y los días siguientes para un punto (estimación sin reportes), con la hora
    más tranquila y la más llena de cada día."""
    with _bd() as con:
        return servicio.semana_punto(con, _punto(con, punto), _ahora())


@mcp.tool(name="puebla_recomendar_alternativa", title="Mejor ve a…", annotations=LECTURA)
def recomendar_alternativa(punto: Punto,
                           origen: Annotated[str | None, Field(description="Dónde está el turista (opcional)")] = None,
                           intereses: Intereses = []) -> dict:
    """Si el punto está en rojo, cerrado o al aire libre con lluvia fuerte, propone una alternativa parecida,
    abierta, que no esté en rojo y a menos de 1 h, y otra hora para el mismo lugar. No guarda nada."""
    with _bd() as con:
        origen_id = _punto(con, origen)
        r = servicio.calcular_recomendacion(con, _ahora(), _punto(con, punto), origen_id, intereses)
        return servicio.recomendacion_dict(r, trafico.factores_vigentes(con, _ahora()), origen_id)


@mcp.tool(name="puebla_tiempo_traslado", title="Tiempo de traslado", annotations=LECTURA)
def tiempo_traslado(origen: Punto, destino: Punto) -> dict:
    """Minutos y km entre dos puntos: a pie y en coche con el tráfico actual de TomTom (y sin tráfico, para
    comparar). Rutas de OpenRouteService; si no hay tráfico vigente, factor_trafico es null."""
    with _bd() as con:
        return servicio.traslado_entre(con, _punto(con, origen), _punto(con, destino), _ahora())


@mcp.tool(name="puebla_eventos", title="Eventos verificados", annotations=LECTURA)
def eventos(destino: Annotated[str | None, Field(description="Destino del Observatorio, p. ej. 'Atlixco' (opcional)")] = None) -> dict:
    """Eventos con fuente oficial que todavía no terminan (solo los verificados afectan la afluencia)."""
    with _bd() as con:
        return {"eventos": servicio.eventos_vigentes(con, _ahora(), destino)}


_SESION: dict[str, str] = {}


@mcp.tool(name="puebla_reportar", title="¿Cómo está? (reportar)", annotations=ESCRITURA)
def reportar(punto: Punto,
             nivel: Annotated[Literal[1, 2, 3], Field(description="1 vacío, 2 normal, 3 lleno")],
             espera_min: Annotated[int | None, Field(description="Minutos de espera (opcional)", ge=0, le=300)] = None) -> dict:
    """Guarda un reporte con los mismos filtros antispam que la app (uno por punto cada 30 min, no si está
    cerrado; sin GPS vale la mitad) y devuelve el estado nuevo del punto. Escribe en la base de datos."""
    with _bd() as con:
        if "id" not in _SESION:
            _SESION["id"] = servicio.crear_sesion(con, _ahora(), es_demo=os.environ.get("PUEBLA_DEMO") == "1")["sesion_id"]
        return servicio.registrar_reporte(con, _ahora(), _SESION["id"], _punto(con, punto), nivel, espera_min)


# ───────────── Gobierno (solo agregados, RN_12) ─────────────

@mcp.tool(name="puebla_afluencia_zona", title="Afluencia de la zona piloto", annotations=LECTURA)
def afluencia_zona(incluir_demo: Annotated[bool, Field(description="Incluir las sesiones de demo del stand")] = False) -> dict:
    """Estado de los 23 puntos ahora y totales del día (reportes y redirecciones)."""
    with _bd() as con:
        return panel.afluencia(con, _ahora(), incluir_demo)


Fecha = Annotated[date | None, Field(description="YYYY-MM-DD; por defecto, hoy")]


@mcp.tool(name="puebla_redirecciones", title="Redirecciones", annotations=LECTURA)
def redirecciones(desde: Fecha = None, hasta: Fecha = None, incluir_demo: bool = False) -> dict:
    """De dónde a dónde se fueron los turistas y por qué (sugeridas, aceptadas e ignoradas)."""
    with _bd() as con:
        hoy = _ahora().date()
        return panel.redirecciones(con, desde or hoy, hasta or hoy, incluir_demo)


@mcp.tool(name="puebla_derrama", title="Derrama redistribuida y nueva", annotations=LECTURA)
def derrama(desde: Fecha = None, hasta: Fecha = None, incluir_demo: bool = False) -> dict:
    """Derrama redistribuida y nueva estimada (RN_14), con el gasto por visitante de cada destino
    (Observatorio) y el supuesto escrito."""
    with _bd() as con:
        hoy = _ahora().date()
        return panel.derrama(con, desde or hoy, hasta or hoy, incluir_demo)


@mcp.tool(name="puebla_semaforo_estatal", title="Semáforo estatal mensual", annotations=LECTURA)
def semaforo_estatal(mes: Annotated[int, Field(ge=1, le=12)], anio: Annotated[int, Field(ge=2017, le=2100)]) -> dict:
    """Los 20 destinos del Observatorio en un mes contra su propia historia (dato si ya se publicó; si no,
    promedio del mismo mes de los últimos 3 años, marcado como estimado)."""
    with _bd() as con:
        return panel.semaforo_estatal(con, mes, anio)


@mcp.tool(name="puebla_historico_destino", title="Serie del Observatorio", annotations=LECTURA)
def historico_destino(destino: Annotated[str, Field(description="Nombre exacto, p. ej. 'Atlixco', 'Cd. Puebla'")],
                      indicador: Annotated[str, Field(description="afluencia, llegadas, derrama_mxn, ocupacion_pct, estadia_promedio…")] = "afluencia",
                      desde: Annotated[str, Field(description="YYYY-MM", pattern=r"^\d{4}-\d{2}$")] = "2022-01",
                      hasta: Annotated[str, Field(description="YYYY-MM", pattern=r"^\d{4}-\d{2}$")] = "2100-12") -> dict:
    """Serie mensual de un indicador del Observatorio Turístico para un destino."""
    with _bd() as con:
        return panel.historico_destino(con, destino, indicador, desde, hasta)


# ───────────── Asistente (RAG) ─────────────

@mcp.tool(name="puebla_buscar_conocimiento", title="Buscar en la base de conocimiento", annotations=LECTURA)
def buscar_conocimiento(pregunta: Annotated[str, Field(min_length=3, max_length=500)],
                        coleccion: Annotated[Literal["puntos", "eventos", "conocimiento", "establecimientos", "bitacora"],
                                             Field(description="Dónde buscar")] = "conocimiento",
                        n: Annotated[int, Field(ge=1, le=10)] = 5) -> dict:
    """Fragmentos de ChromaDB más parecidos a la pregunta, con su fuente y URL (búsqueda por significado con
    bge-m3). Necesita Ollama."""
    docs = rag._buscar(coleccion, llm.embeber([pregunta])[0], n)
    return {"resultados": [{"id": d.id, "texto": d.texto, "fuente": d.metadatos.get("fuente"),
                            "url": d.metadatos.get("url"), "distancia": d.distancia} for d in docs]}


@mcp.tool(name="puebla_preguntar_asistente", title="Preguntar al asistente", annotations=LECTURA_LLM)
def preguntar_asistente(pregunta: Annotated[str, Field(min_length=3, max_length=500)],
                        origen: Annotated[str | None, Field(description="Dónde está el turista (opcional)")] = None) -> dict:
    """Respuesta completa del asistente (RAG con Qwen3 local): solo con nuestros datos, citando [ids], con las
    fuentes armadas por el backend y la tabla en vivo que recibió el modelo. Necesita Ollama."""
    with _bd() as con:
        r = rag.preguntar(con, _ahora(), pregunta, _punto(con, origen))
    r.pop("prompt", None)
    return r


# ───────────── Resources ─────────────

@mcp.resource("datos://puntos", name="puntos", title="Catálogo de la zona piloto", mime_type="application/json")
def recurso_puntos() -> str:
    """Los 23 puntos con horario, costo, ficha y la fuente de cada dato."""
    with _bd() as con:
        return json.dumps(servicio.catalogo(con), ensure_ascii=False)


@mcp.resource("datos://fuentes", name="fuentes", title="Fuentes y licencias", mime_type="text/plain")
def recurso_fuentes() -> str:
    """De dónde sale cada dato y con qué licencia."""
    with _bd() as con:
        return conocimiento.doc_fuentes(con).texto


@mcp.resource("datos://modelos", name="modelos", title="Ficha de los modelos", mime_type="text/markdown")
def recurso_modelos() -> str:
    """Cómo funcionan el semáforo, los reportes y el recomendador (supuestos incluidos) y la última
    evaluación del asistente."""
    partes = ["# Modelos de Puebla Ahora", ""] + [f"## {d.metadatos['titulo']}\n\n{d.texto}\n"
                                                  for d in conocimiento.docs_metodologia()]
    evaluacion = DATA / "processed" / "evaluacion_rag.md"
    if evaluacion.exists():
        resumen = evaluacion.read_text(encoding="utf-8").split("\n## 1.")[0]
        partes += ["## Evaluación del asistente", "", resumen]
    return "\n".join(partes)


# ───────────── Prompts ─────────────

@mcp.prompt(name="plan_turista", title="Plan para un turista")
def plan_turista(origen: str, intereses: str = "historia", horas: str = "4") -> str:
    """Arma un plan para un turista según dónde está, qué le gusta y cuánto tiempo tiene."""
    return (f"Un turista está en {origen}, le interesa {intereses} y tiene {horas} horas. "
            "Usa puebla_que_hago_ahora (con su origen e intereses) y puebla_estado_punto para los lugares que "
            "propongas; revisa puebla_eventos. Arma un plan de 2 a 4 paradas que no pase por lugares en rojo ni "
            "cerrados, con los traslados de puebla_tiempo_traslado. Cita la fuente de cada dato y di qué es "
            "estimado. Si te falta un dato, dilo.")


@mcp.prompt(name="reporte_fin_de_semana", title="Reporte para la Secretaría")
def reporte_fin_de_semana(desde: str, hasta: str) -> str:
    """Para la Secretaría: puntos saturados, redirecciones y derrama redistribuida de un periodo."""
    return (f"Prepara un reporte para la Secretaría de Turismo del {desde} al {hasta}. Usa puebla_afluencia_zona "
            f"(puntos en rojo y reportes), puebla_redirecciones y puebla_derrama con desde={desde} y hasta={hasta}. "
            "Incluye el supuesto de la derrama tal como viene, separa lo medido de lo estimado y no muestres "
            "reportes individuales (solo agregados).")


if __name__ == "__main__":
    mcp.run()
