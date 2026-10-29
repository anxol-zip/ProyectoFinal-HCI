"""Paso 7b: umbrales del semáforo por punto y afluencia estimada por hora.

    uv run python -m scripts.calcular_afluencia [días]      # por defecto, hoy + 7 días

1. ``umbral_punto``: percentiles 60 y 85 de la historia de cada punto en la misma escala que la
   estimación (``afluencia.umbrales_desde_historia``). Los umbrales fijados a mano desde el
   panel (``metodo = 'manual'``) no se tocan.
2. ``afluencia_estimada``: una fila por punto y hora, con el último pronóstico de ``obs_clima``
   (``clima.f_clima``; sin pronóstico, 1.0). Las horas en que el punto está cerrado
   quedan con ``semaforo = 'cerrado'`` y sin estimación. Los reportes de turistas y los ajustes
   manuales se aplican al consultar el estado en vivo (API), no aquí.
"""

from __future__ import annotations

import sys
from datetime import datetime

from turismo_core import afluencia as af
from turismo_core import clima
from turismo_core.bd import conectar
from turismo_core.estado import evaluar
from turismo_core.semaforo import Umbrales


def guardar_umbrales(con, perfiles, ctx) -> dict[int, Umbrales]:
    manuales = {r["punto_id"]: Umbrales(r["bajo"], r["alto"], "manual", r["n_muestras"] or 0)
                for r in con.execute("SELECT * FROM umbral_punto WHERE metodo = 'manual'")}
    ahora = datetime.now().isoformat(timespec="seconds")
    umbrales = {}
    for pid, p in perfiles.items():
        if pid in manuales:
            umbrales[pid] = manuales[pid]
            continue
        u = af.umbrales_desde_historia(p, ctx)
        umbrales[pid] = u
        con.execute(
            "INSERT INTO umbral_punto VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(punto_id) DO UPDATE SET "
            "bajo=excluded.bajo, alto=excluded.alto, metodo=excluded.metodo, "
            "n_muestras=excluded.n_muestras, calculado_en=excluded.calculado_en",
            (pid, u.bajo, u.alto, u.metodo, u.n_muestras, ahora),
        )
    return umbrales


def guardar_estimaciones(con, perfiles, umbrales, ctx, eventos, desde: datetime, dias: int) -> int:
    destinos = {r["id"]: r["destino_id"] for r in con.execute("SELECT id, destino_id FROM punto")}
    horas = af.horas(desde, 24 * dias)
    pronostico = clima.ultimo_pronostico(con, horas[0], horas[-1])
    con.execute("DELETE FROM afluencia_estimada WHERE para_hora >= ?", (horas[0].strftime("%Y-%m-%d %H:00"),))
    filas = []
    for pid, p in perfiles.items():
        for h in horas:
            fc = clima.f_clima(p.interior, pronostico.get((pid, h)))
            e = af.estimar(p, destinos[pid], h, ctx, eventos, f_clima=fc)
            if not e.abierto:
                semaforo, valor, confianza = "cerrado", None, None
            else:
                est = evaluar(e.estimacion, umbrales[pid], [], h)
                semaforo, valor, confianza = est.semaforo, est.valor_final, est.confianza
            filas.append((pid, h.strftime("%Y-%m-%d %H:00"), e.base, e.f_dia_hora, e.f_evento, e.f_clima,
                          e.estimacion, 0, valor, semaforo, confianza))
    con.executemany("INSERT INTO afluencia_estimada VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", filas)
    return len(filas)


def main(dias: int = 7) -> None:
    with conectar() as con:
        perfiles = af.cargar_perfiles(con)
        ctx = af.cargar_contexto(con)
        eventos = af.cargar_eventos(con)
        umbrales = guardar_umbrales(con, perfiles, ctx)
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        n = guardar_estimaciones(con, perfiles, umbrales, ctx, eventos, hoy, dias)

        fuentes = af.resumen_fuentes(perfiles)
        print(f"Perfiles: {fuentes.get('inah', 0)} con base INAH, {fuentes.get('observatorio', 0)} con base del "
              f"Observatorio; {fuentes.get('horario_confirmado', 0)} con horario oficial; "
              f"{fuentes.get('domingo_dato', 0)} con domingo calculado de los datos del INAH")
        print(f"Eventos verificados en uso: {len(eventos)}")
        print(f"{'punto':<18} {'base':>5} {'bajo':>5} {'alto':>5} {'método':<10} domingo")
        for pid, p in perfiles.items():
            u = umbrales[pid]
            print(f"{p.clave:<18} {p.base_mes(hoy.year, hoy.month) or 0:>5.2f} {u.bajo:>5.2f} {u.alto:>5.2f} "
                  f"{u.metodo:<10} {p.peso_domingo:.2f}{' (dato INAH)' if p.domingo_es_dato else ''}")
        print(f"{n} horas estimadas desde {hoy:%Y-%m-%d} ({dias} días)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
