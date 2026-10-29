"""Servidor MCP contra la BD sintética de test_api (sin Ollama): tools, nombres libres y errores."""

import asyncio
import json

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from mcp_server.server import mcp
from tests.test_api import cliente  # noqa: F401  (crea la BD sintética)


@pytest.fixture
def bd(cliente, monkeypatch):  # noqa: F811
    _, reloj = cliente
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{reloj['ruta']}")
    return reloj["ruta"]


def llamar(nombre: str, args: dict) -> dict:
    r = asyncio.run(mcp.call_tool(nombre, args))
    return r[1] if isinstance(r, tuple) else json.loads(r[0].text)


def test_catalogo_de_tools_resources_y_prompts():
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    assert len(tools) == 15 and all(n.startswith("puebla_") for n in tools)
    assert tools["puebla_reportar"].annotations.readOnlyHint is False
    assert tools["puebla_estado_punto"].annotations.readOnlyHint is True
    assert {str(r.uri) for r in asyncio.run(mcp.list_resources())} == {"datos://puntos", "datos://fuentes", "datos://modelos"}
    assert {p.name for p in asyncio.run(mcp.list_prompts())} == {"plan_turista", "reporte_fin_de_semana"}


def test_puntos_por_id_o_nombre_y_traslado(bd):
    assert llamar("puebla_buscar_punto", {"texto": "punto 2"})["candidatos"][0]["id"] == 2
    t = llamar("puebla_tiempo_traslado", {"origen": "1", "destino": "Punto 3"})
    assert (t["origen_id"], t["destino_id"], t["coche_min"]) == (1, 3, 20)


def test_errores_claros(bd):
    with pytest.raises(ToolError, match="No encontré el punto"):
        llamar("puebla_estado_punto", {"punto": "Narnia"})
    with pytest.raises(ToolError, match="puede ser varios puntos"):
        llamar("puebla_estado_punto", {"punto": "punto"})       # 'Punto 1', 'Punto 2', 'Punto 3' empatan


def test_reportar_usa_los_filtros_de_la_app(bd):
    r = llamar("puebla_reportar", {"punto": "3", "nivel": 3})      # el mirador está cerrado
    assert r["reporte"]["estado"] == "descartado"
