"""Paso 8: revisiones de calidad de puebla.db (docs/04 §5 y §8). Si una falla, sale con error.

Las revisiones "informativas" no detienen el pipeline: muestran cifras para decidir a mano
(p. ej. si 'Cholula' del Observatorio es la suma de San Pedro y San Andrés).
"""

from __future__ import annotations

import sys

from turismo_core.bd import conectar

# Zona piloto Puebla–Cholula–Atlixco, con margen.
LAT = (18.80, 19.25)
LON = (-98.55, -98.05)

# (descripción, consulta que devuelve las filas con problema)
REVISIONES = [
    ("Ocupación hotelera entre 0 y 100 %",
     "SELECT destino_id, periodo, valor FROM hecho_observatorio "
     "WHERE indicador = 'ocupacion_pct' AND valor NOT BETWEEN 0 AND 100"),
    ("Sin valores negativos en el Observatorio",
     "SELECT destino_id, periodo, indicador, valor FROM hecho_observatorio WHERE valor < 0"),
    ("Sin visitas negativas en el INAH",
     "SELECT * FROM hecho_inah WHERE visitas < 0"),
    ("Periodos con formato YYYY-MM y mes válido",
     "SELECT periodo FROM hecho_observatorio WHERE periodo NOT GLOB '[0-9][0-9][0-9][0-9]-[01][0-9]' "
     "OR CAST(substr(periodo, 6) AS INTEGER) NOT BETWEEN 1 AND 12 "
     "UNION SELECT periodo FROM hecho_inah WHERE CAST(substr(periodo, 6) AS INTEGER) NOT BETWEEN 1 AND 12"),
    ("Cada punto tiene coordenadas dentro de la zona piloto",
     f"SELECT clave, lat, lon FROM punto WHERE lat NOT BETWEEN {LAT[0]} AND {LAT[1]} "
     f"OR lon NOT BETWEEN {LON[0]} AND {LON[1]}"),
    ("Cada punto pertenece a un destino piloto",
     "SELECT p.clave FROM punto p JOIN destino d ON d.id = p.destino_id WHERE d.es_piloto = 0"),
    ("No hay dos puntos del mismo tipo a menos de ~50 m",
     "SELECT a.clave, b.clave FROM punto a JOIN punto b ON a.id < b.id AND a.tipo = b.tipo "
     "WHERE abs(a.lat - b.lat) < 0.00045 AND abs(a.lon - b.lon) < 0.00045"),
    ("Los puntos marcados como INAH tienen su recinto en las estadísticas",
     "SELECT clave FROM punto WHERE es_inah = 1 "
     "AND id NOT IN (SELECT punto_id FROM recinto_inah WHERE punto_id IS NOT NULL)"),
    ("Cada destino piloto tiene afluencia de visitantes de 2025 completa",
     "SELECT d.nombre, COUNT(h.valor) FROM destino d LEFT JOIN hecho_observatorio h "
     "ON h.destino_id = d.id AND h.indicador = 'afluencia' AND h.periodo LIKE '2025-%' "
     "WHERE d.es_piloto = 1 GROUP BY d.id HAVING COUNT(h.valor) < 12"),
    ("Destinos que no son agregados tienen clave de municipio",
     "SELECT nombre FROM destino WHERE es_agregado = 0 AND cve_mun IS NULL"),
    ("'Cholula' = San Pedro + San Andrés en la afluencia de cada mes (±1 %)",
     "SELECT c.periodo, c.valor, s.valor FROM hecho_observatorio c "
     "JOIN (SELECT h.periodo, SUM(h.valor) AS valor FROM hecho_observatorio h JOIN destino d ON d.id = h.destino_id "
     "      WHERE h.indicador = 'afluencia' AND d.nombre IN ('San Pedro Cholula', 'San Andrés Cholula') "
     "      GROUP BY h.periodo HAVING COUNT(*) = 2) s ON s.periodo = c.periodo "
     "WHERE c.indicador = 'afluencia' AND c.destino_id = (SELECT id FROM destino WHERE nombre = 'Cholula') "
     "AND abs(c.valor - s.valor) > 0.01 * max(c.valor, 1)"),
    ("Sin datos de meses aún no publicados (ceros de relleno)",
     "SELECT periodo, COUNT(*) FROM hecho_observatorio GROUP BY periodo HAVING SUM(valor <> 0) = 0"),
    ("Cada evento tiene fuente y termina después de empezar",
     "SELECT nombre FROM evento WHERE fuente_url IS NULL OR fuente_url = '' OR fin < inicio"),
    ("Cada punto tiene umbrales del semáforo (bajo < alto)",
     "SELECT p.clave FROM punto p LEFT JOIN umbral_punto u ON u.punto_id = p.id "
     "WHERE u.punto_id IS NULL OR u.bajo >= u.alto"),
    ("Cada punto tiene afluencia estimada",
     "SELECT clave FROM punto WHERE id NOT IN (SELECT DISTINCT punto_id FROM afluencia_estimada)"),
    ("Horas cerradas sin estimación y horas abiertas con estimación > 0",
     "SELECT punto_id, para_hora, semaforo FROM afluencia_estimada "
     "WHERE (semaforo = 'cerrado' AND estimacion IS NOT NULL) "
     "OR (semaforo <> 'cerrado' AND (estimacion IS NULL OR estimacion <= 0))"),
    ("Clima en rangos válidos (lluvia 0–100 %, mm ≥ 0, temperatura −10 a 45 °C)",
     "SELECT punto_id, valido_para FROM obs_clima WHERE prob_lluvia_pct NOT BETWEEN 0 AND 100 "
     "OR lluvia_mm < 0 OR temp_c NOT BETWEEN -10 AND 45"),
    ("Matriz de traslados completa: todos los pares de puntos, en coche y a pie",
     "SELECT a.clave, b.clave FROM punto a CROSS JOIN punto b LEFT JOIN matriz_traslado m "
     "ON m.origen_id = a.id AND m.destino_id = b.id "
     "WHERE m.origen_id IS NULL OR m.minutos_base IS NULL OR m.minutos_pie IS NULL"),
    ("Traslados con sentido: 0 en la diagonal, > 0 fuera, a pie más lento que en coche si a pie son > 2 km",
     "SELECT origen_id, destino_id FROM matriz_traslado WHERE (origen_id = destino_id AND minutos_base <> 0) "
     "OR (origen_id <> destino_id AND (minutos_base <= 0 OR minutos_pie <= 0)) "
     "OR (km_pie > 2 AND minutos_pie < minutos_base)"),
    ("Cada fuente oficial tiene huella del archivo raw",
     "SELECT nombre FROM fuente WHERE archivo IS NOT NULL AND url NOT LIKE 'catalogo/%' AND hash_archivo IS NULL"),
]

INFORMATIVAS = [
    ("Puntos verificados a mano",
     "SELECT SUM(verificado) || ' de ' || COUNT(*) FROM punto"),
    ("Afluencia 2025: 'Estado' vs. destinos + 'Resto del Estado'",
     "SELECT CASE WHEN d.nombre = 'Estado' THEN 'Estado' ELSE 'Suma' END, CAST(SUM(h.valor) AS INTEGER) "
     "FROM hecho_observatorio h JOIN destino d ON d.id = h.destino_id "
     "WHERE h.indicador = 'afluencia' AND h.periodo LIKE '2025-%' "
     "AND (d.es_agregado = 0 OR d.nombre IN ('Estado', 'Resto del Estado')) GROUP BY 1"),
    ("Destinos con datos del Observatorio",
     "SELECT COUNT(DISTINCT destino_id) FROM hecho_observatorio"),
    ("Visitas INAH 2025 a la Z.A. de Cholula / total INAH Puebla",
     "SELECT ROUND(100.0 * SUM(CASE WHEN clave_siinah = '3110009' THEN visitas END) / SUM(visitas), 1) || ' %' "
     "FROM hecho_inah WHERE periodo LIKE '2025-%'"),
    ("Eventos (verificados / solo prensa)",
     "SELECT SUM(verificado) || ' / ' || SUM(1 - verificado) FROM evento"),
    ("Umbrales por método",
     "SELECT metodo, COUNT(*) FROM umbral_punto GROUP BY metodo"),
    ("Horas estimadas por color",
     "SELECT semaforo, COUNT(*) FROM afluencia_estimada GROUP BY semaforo"),
    ("Última consulta de clima (horas guardadas)",
     "SELECT MAX(consultado_en) || ' (' || COUNT(*) || ')' FROM obs_clima"),
    ("Horas estimadas con efecto de lluvia",
     "SELECT COUNT(*) FROM afluencia_estimada WHERE f_clima <> 1"),
    ("Traslados en coche: máximo y pares a más de 60 min",
     "SELECT MAX(minutos_base) || ' min; ' || SUM(minutos_base > 60) FROM matriz_traslado"),
    ("Último mes con datos",
     "SELECT 'Observatorio ' || MAX(periodo) FROM hecho_observatorio "
     "UNION ALL SELECT 'INAH ' || MAX(periodo) FROM hecho_inah"),
]


def main() -> int:
    fallas = 0
    with conectar() as con:
        for descripcion, sql in REVISIONES:
            filas = con.execute(sql).fetchall()
            print(f"  {'OK   ' if not filas else 'FALLA'} {descripcion}")
            for f in filas[:5]:
                print(f"          {tuple(f)}")
            fallas += bool(filas)
        print("\nInformativas:")
        for descripcion, sql in INFORMATIVAS:
            filas = [" = ".join(map(str, tuple(f))) for f in con.execute(sql)]
            print(f"  · {descripcion}: {'; '.join(filas)}")
    print(f"\n{len(REVISIONES) - fallas} de {len(REVISIONES)} revisiones pasaron")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
