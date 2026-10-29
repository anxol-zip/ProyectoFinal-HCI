"""Actualización cada hora mientras corre la API (demo en vivo, paso 6), y tráfico cada 30 min (paso 10).

Al arrancar y luego cada hora (al minuto 5): clima de Open-Meteo, afluencia estimada de hoy + 7 días,
precarga de los modelos de Ollama (para que la primera pregunta no tarde ~84 s) y la bitácora de
reportes en ChromaDB. Corre en un hilo aparte para no frenar las peticiones. Sin internet, el clima
avisa y se usa el último pronóstico guardado (RNF_02); sin Ollama, el resto sigue igual.

Se apaga con ``PUEBLA_TAREAS=0`` (pruebas o desarrollo).
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta

from scripts import actualizar_clima, actualizar_trafico, calcular_afluencia, indexar_chroma
from turismo_core import conocimiento, llm
from turismo_core.bd import conectar
from turismo_core.config import clave

log = logging.getLogger("puebla.tareas")
MINUTO = 5
TRAFICO_MIN = int(clave("TRAFICO_MIN") or 30)                              # docs/04: cada 15–30 min
TRAFICO_HORAS = tuple(int(h) for h in (clave("TRAFICO_HORAS") or "8-20").split("-"))   # de 8:00 a 20:00


class Programador:
    def __init__(self) -> None:
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._ciclo, name="actualizar-cada-hora", daemon=True)
        self._hilo_trafico = threading.Thread(target=self._ciclo_trafico, name="trafico", daemon=True)
        self.ultima: dict = {"inicio": None, "fin": None, "clima_ok": None, "error": None}
        self.trafico: dict = {"consultado": None, "ok": None}

    def iniciar(self) -> None:
        self._hilo.start()
        self._hilo_trafico.start()

    def actualizar_trafico(self) -> None:
        try:
            self.trafico = {"consultado": datetime.now().isoformat(timespec="seconds"), "ok": actualizar_trafico.main()}
        except Exception as e:
            log.exception("Falló el tráfico")
            self.trafico = {"consultado": datetime.now().isoformat(timespec="seconds"), "ok": False, "error": repr(e)}

    def _ciclo_trafico(self) -> None:
        """Cada ``TRAFICO_MIN`` minutos dentro de ``TRAFICO_HORAS`` (≈ 720 consultas al día a TomTom)."""
        while not self._parar.is_set():
            if TRAFICO_HORAS[0] <= datetime.now().hour < TRAFICO_HORAS[1]:
                self.actualizar_trafico()
            self._parar.wait(TRAFICO_MIN * 60)

    def detener(self) -> None:
        self._parar.set()

    def actualizar(self) -> None:
        self.ultima = {"inicio": datetime.now().isoformat(timespec="seconds"), "fin": None, "clima_ok": None,
                       "modelos": None, "error": None}
        try:
            self.ultima["clima_ok"] = actualizar_clima.main()
            calcular_afluencia.main()
        except Exception as e:  # una falla no debe tumbar la API
            log.exception("Falló la actualización")
            self.ultima["error"] = repr(e)
        self.ultima["modelos"] = llm.precargar()
        if self.ultima["modelos"].get("embeddings") == "cargado":
            try:
                with conectar() as con:
                    bitacora = conocimiento.docs_bitacora(con, datetime.now().date() - timedelta(days=60))
                indexar_chroma.indexar({"bitacora": bitacora})
            except Exception as e:
                log.exception("Falló la bitácora")
                self.ultima["error"] = repr(e)
        self.ultima["fin"] = datetime.now().isoformat(timespec="seconds")

    def _ciclo(self) -> None:
        while not self._parar.is_set():
            self.actualizar()
            ahora = datetime.now()
            siguiente = ahora.replace(minute=MINUTO, second=0, microsecond=0)
            if siguiente <= ahora:
                siguiente += timedelta(hours=1)
            self._parar.wait((siguiente - ahora).total_seconds())
