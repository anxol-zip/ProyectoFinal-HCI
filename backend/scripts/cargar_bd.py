"""Paso 7: data/processed + catálogo + eventos + calendario -> puebla.db.

Se puede correr las veces que sea: catálogos y hechos oficiales se reemplazan, pero las
tablas que llena la app (sesiones, reportes, búsquedas, ajustes) no se tocan. Los puntos
conservan su id (orden del catálogo) para no romper los reportes ya guardados.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from scripts import CATALOGO, EQUIVALENCIAS_INAH, EVENTOS, MANIFIESTO, PROCESSED
from turismo_core.bd import conectar, crear_esquema, ruta_bd
from turismo_core.ingesta import AGREGADOS, calendario

FUENTES = {
    "Observatorio Turístico de Puebla": {
        "url": "https://sectur.puebla.gob.mx/observatorioturistico/",
        "frecuencia": "mensual", "archivo": "DatosOT a junio 2026 glosario.md",
    },
    "INAH, reporte detallado Puebla": {
        "url": "https://www.estadisticas.inah.gob.mx/",
        "frecuencia": "mensual", "archivo": "reporte_detallado_202621.xls",
    },
    "DENUE (INEGI) 05/2026": {
        "url": "https://www.inegi.org.mx/contenidos/masiva/denue/denue_21_csv.zip",
        "licencia": "Términos de Libre Uso de la Información del INEGI",
        "frecuencia": "anual", "archivo": "denue_21_csv.zip",
    },
    "Catálogo de la zona piloto (equipo)": {
        "url": "catalogo/puntos_zona_piloto.csv", "frecuencia": "única",
    },
}

# Destino del Observatorio -> municipio del DENUE (cuando el nombre no es el mismo).
# 'Cholula' es la suma de dos municipios (ingesta.SUMA_DE), así que no lleva clave.
MUNICIPIO_DE_DESTINO = {"Cd. Puebla": "Puebla", "Cuetzalan": "Cuetzalan del Progreso", "Cholula": None}

CALENDARIO_DESDE, CALENDARIO_HASTA = date(2017, 1, 1), date(2027, 12, 31)


def _csv(ruta: Path) -> list[dict[str, str]]:
    with ruta.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _vacio(x: str) -> str | None:
    x = x.strip()
    return x or None


def cargar_fuentes(con) -> dict[str, int]:
    manifiesto = {f["archivo"]: f for f in _csv(MANIFIESTO)}
    ids = {}
    for nombre, meta in FUENTES.items():
        m = manifiesto.get(meta.get("archivo", ""), {})
        con.execute(
            """INSERT INTO fuente (nombre, url, licencia, frecuencia, fecha_descarga, archivo, hash_archivo)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(nombre) DO UPDATE SET url=excluded.url, licencia=excluded.licencia,
                 frecuencia=excluded.frecuencia, fecha_descarga=excluded.fecha_descarga,
                 archivo=excluded.archivo, hash_archivo=excluded.hash_archivo""",
            (nombre, meta.get("url"), meta.get("licencia"), meta["frecuencia"],
             m.get("fecha_copia"), meta.get("archivo"), m.get("sha256")),
        )
        ids[nombre] = con.execute("SELECT id FROM fuente WHERE nombre = ?", (nombre,)).fetchone()[0]
    return ids


def cargar_destinos(con, observatorio: list[dict], catalogo: list[dict]) -> dict[str, int]:
    claves = {f["municipio"]: f["cve_mun"] for f in _csv(PROCESSED / "municipios_denue.csv")}
    piloto = {p["destino"] for p in catalogo}
    for nombre in sorted({f["destino"] for f in observatorio}):
        municipio = MUNICIPIO_DE_DESTINO.get(nombre, nombre)
        con.execute(
            """INSERT INTO destino (nombre, cve_mun, es_piloto, es_agregado) VALUES (?, ?, ?, ?)
               ON CONFLICT(nombre) DO UPDATE SET cve_mun=excluded.cve_mun,
                 es_piloto=excluded.es_piloto, es_agregado=excluded.es_agregado""",
            (nombre, claves.get(municipio) if municipio else None,
             int(nombre in piloto), int(nombre in AGREGADOS)),
        )
    return {r["nombre"]: r["id"] for r in con.execute("SELECT id, nombre FROM destino")}


def cargar_puntos(con, catalogo: list[dict], destinos: dict[str, int], fuente_id: int) -> dict[str, int]:
    faltan = {p["destino"] for p in catalogo} - destinos.keys()
    if faltan:
        raise SystemExit(f"Destinos del catálogo que no están en el Observatorio: {sorted(faltan)}")
    for i, p in enumerate(catalogo, start=1):
        horario = _vacio(p["horario"])
        costo = _vacio(p["costo_mxn"])
        con.execute(
            """INSERT INTO punto (id, clave, nombre, destino_id, municipio, tipo, categorias, interior,
                 lat, lon, horario, costo_mxn, duracion_sugerida, ficha, es_inah, clee_denue, osm_id,
                 fuente_texto, fuente_id, verificado)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(clave) DO UPDATE SET nombre=excluded.nombre, destino_id=excluded.destino_id,
                 municipio=excluded.municipio, tipo=excluded.tipo, categorias=excluded.categorias,
                 interior=excluded.interior, lat=excluded.lat, lon=excluded.lon,
                 horario=excluded.horario, costo_mxn=excluded.costo_mxn,
                 duracion_sugerida=excluded.duracion_sugerida, ficha=excluded.ficha,
                 es_inah=excluded.es_inah, clee_denue=excluded.clee_denue, osm_id=excluded.osm_id,
                 fuente_texto=excluded.fuente_texto,
                 fuente_id=excluded.fuente_id, verificado=excluded.verificado""",
            (i, p["id"], p["nombre"], destinos[p["destino"]], p["municipio"], p["tipo"],
             p["categorias"], int(p["interior"] or 0), float(p["lat"]), float(p["lon"]),
             None if horario == "verificar" else horario, float(costo) if costo else None,
             _vacio(p["duracion_sugerida"]), _vacio(p["ficha"]), int(p["inah"] or 0),
             _vacio(p.get("clee_denue", "")), _vacio(p.get("osm_id", "")),
             _vacio(p["fuente"]), fuente_id, int(p["verificado"] or 0)),
        )
    return {r["clave"]: r["id"] for r in con.execute("SELECT id, clave FROM punto")}


def cargar_hechos(con, observatorio, destinos, puntos, fuentes) -> None:
    con.execute("DELETE FROM hecho_observatorio")
    con.executemany(
        "INSERT INTO hecho_observatorio VALUES (?, ?, ?, ?, ?, ?)",
        ((destinos[f["destino"]], f["periodo"], f["indicador"], float(f["valor"]),
          int(f["es_pandemia"]), fuentes["Observatorio Turístico de Puebla"]) for f in observatorio),
    )

    equivalencias = {e["clave_siinah"]: puntos[e["punto_clave"]] for e in _csv(EQUIVALENCIAS_INAH)}
    con.execute("DELETE FROM hecho_inah")
    con.execute("DELETE FROM recinto_inah")
    con.executemany(
        "INSERT INTO recinto_inah VALUES (?, ?, ?, ?)",
        ((r["clave_siinah"], r["nombre"], r["siglas"], equivalencias.get(r["clave_siinah"]))
         for r in _csv(PROCESSED / "recintos_inah.csv")),
    )
    fuente_inah = fuentes["INAH, reporte detallado Puebla"]
    con.executemany(
        "INSERT INTO hecho_inah VALUES (?, ?, ?, ?, ?, ?)",
        ((f["clave_siinah"], f["periodo"], f["tipo_visitante"], f["nacionalidad"], int(f["visitas"]),
          fuente_inah) for f in _csv(PROCESSED / "inah.csv")),
    )

    fuente_denue = fuentes["DENUE (INEGI) 05/2026"]
    con.execute("DELETE FROM establecimiento")
    con.executemany(
        "INSERT INTO establecimiento VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ((e["clee"], e["nombre"], e["codigo_act"], e["nombre_act"], e["giro"], e["per_ocu"],
          e["cve_mun"], e["municipio"], float(e["lat"]), float(e["lon"]), fuente_denue)
         for e in _csv(PROCESSED / "denue_zona_piloto.csv")),
    )


def cargar_eventos(con, destinos: dict[str, int], puntos: dict[str, int]) -> None:
    """Calendario curado (data/eventos.csv). Sin fuente no entra (docs/04 §3)."""
    con.execute("DELETE FROM evento")
    for e in _csv(EVENTOS):
        if not e["fuente_url"].strip():
            raise SystemExit(f"Evento sin fuente: {e['nombre']}")
        con.execute(
            "INSERT INTO evento (nombre, punto_id, destino_id, inicio, fin, impacto, fuente_url, verificado, nota) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (e["nombre"], puntos[e["punto_clave"]] if e["punto_clave"] else None,
             destinos[e["destino"]] if e["destino"] else None, e["inicio"], e["fin"], e["impacto"],
             e["fuente_url"], int(e["verificado"] or 0), _vacio(e["nota"])),
        )


def cargar_calendario(con) -> None:
    con.execute("DELETE FROM calendario")
    con.executemany(
        "INSERT INTO calendario VALUES (:fecha, :dia_semana, :es_festivo, :es_puente, :es_vacaciones)",
        calendario(CALENDARIO_DESDE, CALENDARIO_HASTA),
    )


def main() -> None:
    ruta = ruta_bd()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    observatorio = _csv(PROCESSED / "observatorio.csv")
    catalogo = _csv(CATALOGO)
    with conectar(ruta) as con:
        crear_esquema(con)
        fuentes = cargar_fuentes(con)
        destinos = cargar_destinos(con, observatorio, catalogo)
        puntos = cargar_puntos(con, catalogo, destinos, fuentes["Catálogo de la zona piloto (equipo)"])
        cargar_hechos(con, observatorio, destinos, puntos, fuentes)
        cargar_eventos(con, destinos, puntos)
        cargar_calendario(con)
        for tabla in ("fuente", "destino", "punto", "recinto_inah", "hecho_observatorio",
                      "hecho_inah", "establecimiento", "evento", "calendario"):
            n = con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            print(f"  {tabla:<20} {n:>7}")
    print(f"BD lista: {ruta}")


if __name__ == "__main__":
    main()
