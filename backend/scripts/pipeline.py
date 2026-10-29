"""Corre el pipeline completo en orden (docs/04 §7): de Downloads a puebla.db validada.

    uv run python -m scripts.pipeline [carpeta_origen]
"""

from __future__ import annotations

import sys
from pathlib import Path

from scripts import (
    actualizar_clima,
    actualizar_trafico,
    calcular_afluencia,
    calcular_traslados,
    cargar_bd,
    copiar_datos,
    extraer_observatorio,
    filtrar_denue,
    indexar_chroma,
    limpiar_inah,
    validar_bd,
)
from turismo_core.llm import SinOllama


def main() -> int:
    origen = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads"
    pasos = [
        ("1. Copiar datos", lambda: copiar_datos.main(origen)),
        ("2. Observatorio", extraer_observatorio.main),
        ("3. INAH", limpiar_inah.main),
        ("4. DENUE", filtrar_denue.main),
        ("7. Cargar BD", cargar_bd.main),
        ("6. Traslados (OpenRouteService)", calcular_traslados.main),
        ("6b. Tráfico (TomTom)", actualizar_trafico.main),
        ("7a. Clima (Open-Meteo)", actualizar_clima.main),
        ("7b. Umbrales y afluencia estimada", calcular_afluencia.main),
    ]
    for nombre, paso in pasos:
        print(f"\n== {nombre}")
        paso()
    print("\n== 8. Validar BD")
    resultado = validar_bd.main()
    print("\n== 9. ChromaDB (asistente)")
    try:
        indexar_chroma.main()
    except SinOllama as e:
        print(f"  AVISO sin Ollama no se indexa ChromaDB ({e}); el resto de la app funciona")
    return resultado


if __name__ == "__main__":
    sys.exit(main())
