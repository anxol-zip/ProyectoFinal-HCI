"""Casos de prueba del recomendador contra la BD real (evidencia para el pitch y revisión de sentido).

    uv run python -m scripts.probar_recomendador
"""

from __future__ import annotations

from datetime import datetime

from turismo_core.bd import conectar
from turismo_core.recomendador import recomendar
from turismo_core.situacion import pronostico_punto, situacion, traslados


def caso(con, titulo, momento, pedido=None, intereses=(), horas=None):
    puntos = situacion(con, momento)
    ids = {p.clave: p.id for p in puntos.values()}
    pid = ids[pedido] if pedido else None
    r = recomendar(puntos, traslados(con), momento, pedido_id=pid, intereses=intereses, horas=horas,
                   pronostico_pedido=pronostico_punto(con, pid, momento) if pid else ())
    print(f"\n### {titulo} — {momento:%a %d/%m %H:%M}")
    print(f"  {r.razon}")
    if r.alternativa:
        a = r.alternativa
        print(f"  elegido: {a.punto.clave} puntaje {a.puntaje} (similitud {a.similitud}, conveniencia {a.conveniencia.total}: "
              f"afluencia {a.conveniencia.afluencia}, clima {a.conveniencia.clima}, traslado {a.conveniencia.traslado})")
    for o in r.otras:
        lejos = "" if o.minutos is None else f", {o.minutos} min {o.modo}"
        print(f"  otra opción: {o.punto.clave} ({o.punto.color}{lejos}, puntaje {o.puntaje})")


def main() -> None:
    with conectar() as con:
        caso(con, "Cholula lleno en domingo", datetime(2026, 10, 18, 13), "zona_arq_cholula")
        caso(con, "Cholula en la mañana", datetime(2026, 10, 18, 10), "zona_arq_cholula")
        caso(con, "Huejotzingo en domingo", datetime(2026, 10, 18, 12), "huejotzingo")
        caso(con, "Fuertes un miércoles (cerrado)", datetime(2026, 10, 21, 12), "fuertes")
        caso(con, "Museo Amparo un viernes (cerrado)", datetime(2026, 10, 16, 12), "museo_amparo")
        caso(con, "Sin lugar pedido, le gusta la historia, 3 h", datetime(2026, 10, 18, 13), None, ["historia"], 3)
        caso(con, "Sin lugar pedido, familia", datetime(2026, 10, 17, 16), None, ["familia", "naturaleza"])
        # El primer caso de lluvia fuerte en un punto al aire libre que dé el pronóstico de esta semana.
        fila = con.execute(
            "SELECT p.clave, o.valido_para FROM obs_clima o JOIN punto p ON p.id = o.punto_id "
            "JOIN afluencia_estimada a ON a.punto_id = o.punto_id AND a.para_hora = replace(o.valido_para, 'T', ' ') "
            "WHERE p.interior = 0 AND (o.prob_lluvia_pct >= 60 OR o.lluvia_mm >= 1) AND a.semaforo <> 'cerrado' "
            "AND o.consultado_en = (SELECT MAX(consultado_en) FROM obs_clima) ORDER BY o.valido_para LIMIT 1").fetchone()
        if fila:
            caso(con, f"Lluvia fuerte en {fila[0]}", datetime.fromisoformat(fila[1]), fila[0])


if __name__ == "__main__":
    main()
