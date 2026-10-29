"""Partes del asistente que no necesitan Ollama: plantillas, citas, menciones e intereses."""

from turismo_core import conocimiento as cn
from turismo_core import llm, rag
from turismo_core import recomendador as rec
from turismo_core.estado import EstadoSemaforo
from turismo_core.semaforo import Umbrales
from turismo_core.situacion import PuntoAhora

from tests.test_api import cliente  # noqa: F401  (fixture con BD sintética)


def test_horario_agrupa_dias_y_dice_cerrados():
    assert cn.horario_texto(None) == "horario por confirmar"
    h = '{"mar": "10:00-17:00", "mie": "10:00-17:00", "jue": "10:00-17:00", "vie": "10:00-18:00"}'
    assert cn.horario_texto(h) == "martes a jueves de 10:00 a 17:00; viernes de 10:00 a 18:00; cerrado lunes, sábado, domingo"
    todo = "{" + ", ".join(f'"{d}": "00:00-24:00"' for d in cn.DIAS) + "}"
    assert cn.horario_texto(todo) == "abierto las 24 horas"


def test_ficha_dice_sin_dato_y_no_lleva_none():
    p = {"id": 23, "nombre": "Acuario", "tipo": "parque", "destino": "Cd. Puebla", "municipio": "Puebla",
         "ficha": "Acuario techado.", "categorias": "naturaleza,familia", "interior": 1, "horario": None,
         "costo_mxn": None, "duracion_sugerida": None, "verificado": 1, "fuente_texto": None}
    d = cn.doc_punto(p)
    assert "Visita sugerida: sin dato." in d.texto and "Costo: sin dato." in d.texto
    assert None not in d.metadatos.values() and d.metadatos["categorias"] == ["naturaleza", "familia"]
    assert cn.doc_punto(p | {"costo_mxn": 0.0}).texto.count("entrada gratuita") == 1


def test_citas_validas_e_invalidas():
    ok, malas = rag.citas("Abre a las 10:00 [punto-3] y [obs-9]; ver [punto-3] y [fuentes].", {"punto-3", "fuentes"})
    assert ok == ["punto-3", "fuentes"] and malas == ["obs-9"]


def _punto(pid, nombre):
    e = EstadoSemaforo(2.0, 2.0, 0, "rojo", "estimado", Umbrales(1.0, 1.4, "percentil", 1), None)
    return PuntoAhora(pid, f"p{pid}", nombre, "D", "plaza", frozenset(), False, 19.0, -98.2, True, e, "sin")


def test_menciona_por_palabra_distintiva_o_por_estar_ahi():
    zocalo, piramide = _punto(21, "Zócalo de Puebla"), _punto(12, "Zona Arqueológica de Cholula (Gran Pirámide)")
    assert rag.menciona("¿Cómo está el zocalo?", zocalo)
    assert rag.menciona("¿Vale la pena la Pirámide hoy?", piramide)
    assert not rag.menciona("¿Qué museo de Puebla me recomiendas?", zocalo)      # 'puebla' es genérica
    assert rag.menciona("¿Qué hago?", zocalo, origen_id=21)


def test_intereses_por_reglas():
    assert rag.intereses_de("¿Qué hay para ir con niños?") == {"familia"}
    assert rag.intereses_de("¿Dónde compro Talavera y como mole?") == {"compras", "gastronomia"}


def test_chat_sin_ollama_responde_503(cliente, monkeypatch):  # noqa: F811
    c, _ = cliente

    def caido(*_a, **_k):
        raise llm.SinOllama("Ollama no responde")

    monkeypatch.setattr(llm, "_post", caido)
    monkeypatch.setattr(rag.vector, "coleccion", lambda *_: (_ for _ in ()).throw(AssertionError("no debe llegar")))
    r = c.post("/api/chat", json={"pregunta": "¿Qué hago hoy?"})
    assert r.status_code == 503 and "no está disponible" in r.json()["detail"]
    assert c.post("/api/chat", json={"pregunta": "¿Qué hago?", "sesion_id": "no-existe"}).status_code == 404


def test_comer_o_dormir_por_palabras_completas():
    assert rag.giros_de("¿Dónde puedo desayunar cerca del Zócalo?") == ["alimentos"]
    assert rag.giros_de("¿Hay hoteles en Atlixco?") == ["hospedaje"]
    assert rag.giros_de("¿Qué hay en el Barrio del Artista y el Museo del Barroco?") == []   # no es "bar"


def test_nombre_y_distancia_del_denue():
    assert cn.nombre_legible("RESTAURANTE LA CASA DEL MOLE") == "Restaurante la Casa del Mole"
    assert 10_500 < cn.distancia_m(19.0434, -98.1981, 19.0576, -98.3017) < 11_500    # Zócalo – Pirámide ≈ 11 km
    assert cn.distancia_m(19.0, -98.0, 19.0, -98.0) == 0


def test_lluvia_y_opciones_con_todos_sus_datos():
    assert rag.habla_de_lluvia("Tengo 4 horas y va a llover, ¿qué hago?")
    assert not rag.habla_de_lluvia("¿Qué hay tranquilo cerca de mí?")
    techado, abierto = _punto(1, "Museo"), _punto(2, "Plaza")
    techado = techado.__class__(**{**techado.__dict__, "interior": True})
    cands = [rec.Candidato(p, None, None, 1.0, None, 1.0) for p in (techado, abierto)]
    texto = rag.opciones_texto(cands, None, {}, None, {1: "1 h"}, solo_techados=False)
    lineas = texto.splitlines()
    assert "techado" in lineas[1] and "visita sugerida: 1 h" in lineas[1]
    assert "al aire libre" in lineas[2] and "visita sugerida: sin dato" in lineas[2]
    assert "traslado: sin dato" in lineas[2]          # sin ubicación del turista no hay traslado
    assert "ROJO (lleno para ese lugar)" in lineas[1]


def test_revisor_de_atributos():
    from scripts.evaluar_rag import atributos_incorrectos
    plaza = _punto(2, "Plaza")                         # al aire libre y en rojo
    assert atributos_incorrectos("Ve a [punto-2] Plaza, techado y tranquilo.", {2: plaza}) == [
        "Plaza: dice techado y es al aire libre", "Plaza: dice tranquilo y está en rojo"]
    assert atributos_incorrectos("[punto-2] Plaza estará más tranquila a las 16:00.", {2: plaza}) == []


def test_lluvia_sin_techados_abiertos_lo_dice():
    # De noche no hay nada techado abierto: el contexto lo dice y no se deja al modelo rellenar (2026-10-16).
    assert rag.opciones_texto([], None, {}, None, {}, solo_techados=True) == rag.SIN_TECHADOS
    assert rag.opciones_texto([], None, {}, None, {}, solo_techados=False) is None
    assert "no hay lugares techados abiertos" in rag.instruccion_para([], [], sin_techados=True)
    assert rag.instruccion_para([], []) is None
