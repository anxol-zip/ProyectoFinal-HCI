"""Paso 8: evaluación del asistente (docs/05b §12) con 15 preguntas + 5 sin respuesta en la base.

    uv run python -m scripts.evaluar_rag

Mide, a la hora del stand (vie 2026-10-16 13:00) y con la BD real:
- Recuperación: ¿el documento correcto (anotado a mano) está entre los recuperados?   Meta ≥ 80 %
- Fidelidad: ¿cada número de la respuesta aparece en lo que recibió el modelo?        Meta 100 %
- "No sé": en las 5 preguntas sin dato, ¿responde "No tengo ese dato"?
- Citas: ¿cita solo ids que se le dieron?
- Tiempo por respuesta (RNF_04: < 15 s; docs/05b pide < 8 s en la laptop).

Escribe el detalle en ``data/processed/evaluacion_rag.md`` (evidencia para la ficha del modelo).
"""

from __future__ import annotations

import re
import time
from datetime import datetime

from turismo_core import llm, rag
from turismo_core.bd import DATA, conectar
from turismo_core.situacion import situacion

MOMENTO = datetime(2026, 10, 16, 13, 0)
ZOCALO = 21

# (pregunta, origen_id, ids correctos: basta con que aparezca uno)
PREGUNTAS = [
    ("¿A qué hora abre la Biblioteca Palafoxiana y cuánto cuesta?", None, {"punto-3"}),
    ("¿Qué puedo visitar techado si llueve en el centro de Puebla?", None,
     {"punto-3", "punto-7", "punto-22", "punto-10", "punto-1", "punto-2"}),
    ("¿Cómo está la Pirámide de Cholula ahora?", None, {"punto-12"}),
    ("Estoy en el Zócalo y tengo 3 horas, ¿qué me recomiendas?", ZOCALO, {"punto-21"}),
    ("¿Cuándo es el Valle de Catrinas?", None, {"evento-1"}),
    ("¿Qué días hay funciones de Catrinia?", None, {"evento-2"}),
    ("¿Cuántos turistas llegan a Atlixco?", None, {"obs-2"}),
    ("¿Qué porcentaje de las visitas a recintos del INAH en Puebla tuvo la zona arqueológica de Cholula en 2025?",
     None, {"inah-3110009"}),
    ("¿Cómo sabe la app que un lugar está lleno?", None, {"metodo-semaforo"}),
    ("¿Para qué sirve el botón ¿Cómo está?", None, {"metodo-reportes"}),
    ("¿Qué hay para ir con niños?", None, {"punto-20", "punto-23", "punto-11", "punto-9"}),
    ("¿Abre hoy el Museo Amparo?", None, {"punto-4"}),
    ("¿Cuánto cuesta entrar a Africam Safari?", None, {"punto-20"}),
    ("¿Dónde puedo comprar artesanías y Talavera?", None, {"punto-6"}),
    ("¿De dónde salen los datos de la app?", None, {"fuentes"}),
    # Restaurantes y hoteles (DENUE): "denue-*" = cualquier establecimiento; el resto se revisa a mano
    ("¿Dónde puedo comer cerca de la Pirámide de Cholula?", None, {"denue-*"}),
    ("Estoy en el Zócalo, ¿dónde puedo desayunar?", ZOCALO, {"denue-*"}),
    ("¿Hay hoteles en el centro de Atlixco?", None, {"denue-*"}),
    ("¿Qué restaurante me recomiendas para comer mole?", None, {"denue-*"}),
    # Las 3 preguntas sugeridas del chat del frontend (frontend/src/i18n/textos.js), 2026-10-16
    ("Tengo 4 horas y va a llover, ¿qué hago?", None, {"punto-*"}),
    ("Tengo 4 horas y va a llover, ¿qué hago?", ZOCALO, {"punto-*"}),
    ("¿Qué hay tranquilo cerca de mí?", ZOCALO, {"punto-*"}),
    ("¿Cuándo conviene ir a la pirámide?", None, {"punto-12"}),
]
SIN_DATO = [
    "¿Cuánto cuesta un taxi del Zócalo a Cholula?",
    "¿Cuál es el restaurante mejor calificado de Puebla?",
    "¿A qué hora sale el último tren a Cholula?",
    "¿Hay estacionamiento en el Museo Amparo?",
    "¿Cuántas personas visitaron la Pirámide de Cholula el sábado pasado?",
]
# Además de la frase pedida, se aceptan dos variantes igual de honestas que el modelo usa
# ("No hay dato específico para…", "No se especifica el número…"); criterio ampliado el 2026-10-15.
NO_SE = ("no tengo ese dato", "no hay dato", "no se especifica")
NUMERO = re.compile(r"\d[\d,.:]*\d|\d")


def _norm(n: str) -> str:
    return n.replace(",", "").rstrip(".:")


def numeros_inventados(respuesta: str, prompt: str) -> list[str]:
    """Números de la respuesta que no están en el prompt (sin contar los ids citados)."""
    sin_ids = rag.CITA.sub("", respuesta)
    en_prompt = {_norm(n) for n in NUMERO.findall(prompt)}
    return [n for n in NUMERO.findall(sin_ids) if _norm(n) not in en_prompt]


# Frases sobre otra hora ("más tranquila a las 16:00", "regresa a las 20:00"): no se comparan con el color de ahora.
FUTURO = re.compile(r"regres|estar[aá]|ser[aá]|despu[eé]s|antes|m[aá]s tarde|hora m[aá]s|ma[nñ]ana|a las \d|"
                    r"del (lunes|martes|miercoles|jueves|viernes|sabado|domingo)", re.I)


def atributos_incorrectos(respuesta: str, puntos: dict) -> list[str]:
    """Por cada frase que cita un solo lugar, compara lo que dice (techado, al aire libre, tranquilo, color)
    con el dato real de ese lugar. Revisión agregada el 2026-10-16: el filtro de números no veía estos errores."""
    errores = []
    for frase in re.split(r";|\n|(?<=[.!?])\s+|\s(?=\d\)\s)", respuesta):
        ids = set(re.findall(r"\[punto-(\d+)\]", frase))
        if len(ids) != 1:
            continue
        p = puntos.get(int(ids.pop()))
        if p is None:
            continue
        t = rag._normal(frase)
        if "techad" in t and not p.interior:
            errores.append(f"{p.nombre}: dice techado y es al aire libre")
        if "aire libre" in t and p.interior and "techad" not in t:
            errores.append(f"{p.nombre}: dice al aire libre y es techado")
        if FUTURO.search(t):          # "regresa a las 20:00, cuando estará en verde" habla de otra hora
            continue
        if "tranquil" in t and p.color != "verde":
            errores.append(f"{p.nombre}: dice tranquilo y está en {p.color}")
        for color, raiz in (("verde", "verde"), ("amarillo", "amarill"), ("rojo", "roj")):
            if re.search(rf"\b{raiz}", t) and p.color != color:
                errores.append(f"{p.nombre}: dice {color} y está en {p.color}")
    return errores


def main() -> None:
    print("Precarga:", llm.precargar(), "· modelo:", llm.MODELO)
    filas, lineas = [], [f"# Evaluación del asistente (RAG)\n\nModelo `{llm.MODELO}`, embeddings `{llm.EMBED}`, "
                         f"momento {MOMENTO:%Y-%m-%d %H:%M}, corrida {datetime.now():%Y-%m-%d %H:%M}.\n"]
    with conectar() as con:
        puntos = situacion(con, MOMENTO)
        casos = [(q, o, esp, False) for q, o, esp in PREGUNTAS] + [(q, None, set(), True) for q in SIN_DATO]
        for i, (q, origen, esperados, sin_dato) in enumerate(casos, 1):
            t = time.perf_counter()
            r = rag.preguntar(con, MOMENTO, q, origen)
            seg = time.perf_counter() - t
            recuperados = [d["id"] for d in r["documentos"]]
            hit = (any(r == e or (e.endswith("*") and r.startswith(e[:-1])) for e in esperados for r in recuperados)
                   if esperados else None)
            inventados = numeros_inventados(r["respuesta"], r["prompt"])
            atributos = atributos_incorrectos(r["respuesta"], puntos)
            dijo_no_se = any(x in r["respuesta"].lower() for x in NO_SE)
            filas.append({"hit": hit, "fiel": not inventados, "no_se": dijo_no_se if sin_dato else None,
                          "citas_ok": not r["citas_invalidas"], "atributos_ok": not atributos, "seg": seg})
            marca = ("✅" if hit else "❌") if hit is not None else ("✅" if dijo_no_se else "❌")
            print(f"{i:>2} {marca}{' ⚠️ ' + '; '.join(atributos) if atributos else ''} {seg:4.1f} s  {q}"
                  f"{'' if origen is None else ' (desde el Zócalo)'}")
            lineas += [f"## {i}. {q}", "",
                       f"- {'Sin dato en la base: ' + ('dijo No tengo ese dato' if dijo_no_se else '**NO lo dijo**') if sin_dato else 'Recuperación: ' + ('acierto' if hit else '**falla**') + f' (esperado {sorted(esperados)})'}",
                       f"- Números que no estaban en el contexto: {inventados or 'ninguno'}",
                       f"- Atributos incorrectos (techado, color, tranquilo): {atributos or 'ninguno'}",
                       f"- Citas inválidas: {r['citas_invalidas'] or 'ninguna'} · fuentes: {[f['id'] for f in r['fuentes']]}",
                       f"- Tiempo: {seg:.1f} s · recuperados: {recuperados}", "", "> " + r["respuesta"].replace("\n", "\n> "), ""]

    con_dato = [f for f in filas if f["hit"] is not None]
    sin = [f for f in filas if f["no_se"] is not None]
    resumen = [
        f"Recuperación (hit): {sum(f['hit'] for f in con_dato)}/{len(con_dato)}",
        f"Fidelidad (sin números inventados): {sum(f['fiel'] for f in filas)}/{len(filas)}",
        f"'No tengo ese dato' cuando no hay dato: {sum(f['no_se'] for f in sin)}/{len(sin)}",
        f"Citas válidas: {sum(f['citas_ok'] for f in filas)}/{len(filas)}",
        f"Atributos correctos (techado, color, tranquilo): {sum(f['atributos_ok'] for f in filas)}/{len(filas)}",
        f"Tiempo: promedio {sum(f['seg'] for f in filas) / len(filas):.1f} s, máximo {max(f['seg'] for f in filas):.1f} s",
    ]
    print("\n" + "\n".join(resumen))
    salida = DATA / "processed" / "evaluacion_rag.md"
    salida.write_text("\n".join(lineas[:1] + ["## Resumen", ""] + [f"- {x}" for x in resumen] + [""] + lineas[1:]),
                      encoding="utf-8")
    print(f"Detalle: {salida}")


if __name__ == "__main__":
    main()
