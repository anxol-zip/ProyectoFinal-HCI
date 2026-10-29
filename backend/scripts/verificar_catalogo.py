"""Propuesta de verificación del catálogo: busca cada punto en el DENUE y en OpenStreetMap.

    uv run python -m scripts.verificar_catalogo

No modifica el catálogo. Escribe ``data/processed/verificacion_catalogo.csv`` con la coordenada
actual, los candidatos del DENUE y de OSM, la distancia en metros y el horario que trae OSM,
para que el equipo revise y decida qué pasa a ``verificado = 1`` (docs/04 §5: se prefiere la
coordenada del DENUE y el horario de la fuente oficial).

Las respuestas de Nominatim (OSM) se guardan en ``data/raw/osm_catalogo.json`` para no volver
a consultar el servidor público (uso justo, máximo 1 consulta por segundo).
"""

from __future__ import annotations

import csv
import io
import json
import math
import time
import unicodedata
import urllib.parse
import urllib.request
import zipfile

from scripts import ARCHIVO_DENUE, CATALOGO, CSV_DENUE, PROCESSED, RAW

# Nominatim (buscador oficial de OSM). Overpass estuvo caído/bloqueado el 2026-10-15.
NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "PueblaAhora-hackathon-puebla-turistica-360/0.1"
CACHE_OSM = RAW / "osm_catalogo.json"
RADIO_M = 2500

# Búsquedas extra en OSM, además del nombre del catálogo.
BUSQUEDAS_OSM = {
    "catedral": ["Catedral de Puebla", "Zócalo de Puebla"],
    "capilla_rosario": ["Templo de Santo Domingo Puebla"],
    "fuertes": ["Fuerte de Loreto", "Fuerte de Guadalupe"],
    "museo_barroco": ["Museo Internacional del Barroco"],
    "zona_arq_cholula": ["Zona Arqueológica de Cholula", "Gran Pirámide de Cholula"],
    "remedios": ["Santuario de Nuestra Señora de los Remedios"],
    "san_gabriel": ["Convento de San Gabriel Cholula"],
    "tonantzintla": ["Iglesia de Santa María Tonantzintla"],
    "acatepec": ["Iglesia de San Francisco Acatepec"],
    "huejotzingo": ["Ex Convento de San Miguel Arcángel Huejotzingo"],
    "atlixco_centro": ["Zócalo de Atlixco", "Plaza de Armas Atlixco"],
    "cerro_san_miguel": ["Cerro de San Miguel Atlixco"],
}

# Palabras con las que se busca cada punto en el DENUE, sin acentos.
TERMINOS = {
    "catedral": ["catedral"],
    "capilla_rosario": ["capilla del rosario", "santo domingo"],
    "palafoxiana": ["palafoxiana"],
    "museo_amparo": ["amparo"],
    "callejon_sapos": ["sapos"],
    "barrio_artista": ["barrio del artista", "parian"],
    "casa_alfenique": ["alfenique"],
    "barrio_xanenetla": ["xanenetla"],
    "fuertes": ["fuerte de loreto", "fuerte de guadalupe", "fuertes"],
    "museo_barroco": ["barroco"],
    "estrella_puebla": ["estrella de puebla"],
    "zona_arq_cholula": ["zona arqueologica de cholula", "gran piramide", "tlachihualtepetl"],
    "remedios": ["remedios"],
    "san_gabriel": ["san gabriel", "capilla real"],
    "tonantzintla": ["tonantzintla"],
    "acatepec": ["acatepec"],
    "huejotzingo": ["convento", "huejotzingo"],
    "atlixco_centro": ["zocalo", "plaza de armas", "plaza central"],
    "cerro_san_miguel": ["cerro de san miguel", "san miguel"],
    "africam": ["africam"],
}


def plano(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).split())


def metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _coincide(texto: str, terminos: list[str]) -> bool:
    t = plano(texto)
    return any(term in t for term in terminos)


def candidatos_denue(puntos: list[dict]) -> dict[str, list[dict]]:
    """Una pasada por el DENUE completo, cualquier giro, en los municipios del catálogo."""
    municipios = {p["municipio"] for p in puntos}
    por_punto: dict[str, list[dict]] = {p["id"]: [] for p in puntos}
    with zipfile.ZipFile(RAW / ARCHIVO_DENUE) as z, z.open(CSV_DENUE) as b:
        for f in csv.DictReader(io.TextIOWrapper(b, encoding="cp1252", newline="")):
            mun = f["municipio"].strip()
            if mun not in municipios:
                continue
            nombre = f"{f['nom_estab']} {f['raz_social']}"
            for p in puntos:
                if p["municipio"] == mun and _coincide(nombre, TERMINOS[p["id"]]):
                    d = metros(float(p["lat"]), float(p["lon"]), float(f["latitud"]), float(f["longitud"]))
                    if d <= RADIO_M:
                        por_punto[p["id"]].append({
                            "nombre": " ".join(f["nom_estab"].split()), "actividad": f["nombre_act"].strip(),
                            "clee": f["clee"], "lat": float(f["latitud"]), "lon": float(f["longitud"]),
                            "dist_m": round(d),
                        })
    return {k: sorted(v, key=lambda c: c["dist_m"]) for k, v in por_punto.items()}


def consulta_osm(texto: str, p: dict) -> list[dict]:
    """Una búsqueda en Nominatim limitada a ~5 km alrededor de la coordenada actual."""
    lat, lon = float(p["lat"]), float(p["lon"])
    params = urllib.parse.urlencode({
        "q": texto, "format": "jsonv2", "limit": 5, "extratags": 1, "bounded": 1,
        "viewbox": f"{lon - 0.05},{lat + 0.05},{lon + 0.05},{lat - 0.05}",
    })
    req = urllib.request.Request(f"{NOMINATIM}?{params}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def candidatos_osm(puntos: list[dict]) -> dict[str, list[dict]]:
    cache = json.loads(CACHE_OSM.read_text(encoding="utf-8")) if CACHE_OSM.exists() else {}
    for p in puntos:
        for texto in [p["nombre"], *BUSQUEDAS_OSM.get(p["id"], [])]:
            clave = f"{p['id']}|{texto}"
            if clave in cache:
                continue
            cache[clave] = consulta_osm(texto, p)
            CACHE_OSM.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
            time.sleep(1.1)  # política de Nominatim: máximo 1 consulta por segundo
    salida = {}
    for p in puntos:
        vistos, cands = set(), []
        for clave, resultados in cache.items():
            if not clave.startswith(f"{p['id']}|"):
                continue
            for e in resultados:
                osm_id = f"{e['osm_type']}/{e['osm_id']}"
                if osm_id in vistos:
                    continue
                vistos.add(osm_id)
                lat, lon = float(e["lat"]), float(e["lon"])
                extra = e.get("extratags") or {}
                cands.append({
                    "nombre": e.get("name") or e["display_name"].split(",")[0], "osm_id": osm_id,
                    "tipo": f"{e['category']}={e['type']}", "lat": lat, "lon": lon,
                    "dist_m": round(metros(float(p["lat"]), float(p["lon"]), lat, lon)),
                    "horario": extra.get("opening_hours", ""),
                    "web": extra.get("website", extra.get("contact:website", "")),
                })
        salida[p["id"]] = sorted(cands, key=lambda c: c["dist_m"])
    return salida


def main() -> None:
    with CATALOGO.open(encoding="utf-8") as f:
        puntos = list(csv.DictReader(f))
    osm = candidatos_osm(puntos)
    denue = candidatos_denue(puntos)

    filas = []
    for p in puntos:
        d = denue[p["id"]][:3]
        o = osm[p["id"]][:3]
        filas.append({
            "id": p["id"], "nombre": p["nombre"], "lat": p["lat"], "lon": p["lon"],
            "denue": " || ".join(f"{c['nombre']} ({c['actividad']}) {c['lat']:.5f},{c['lon']:.5f} a {c['dist_m']} m clee={c['clee']}" for c in d),
            "osm": " || ".join(f"{c['nombre']} [{c['tipo']}] {c['lat']:.5f},{c['lon']:.5f} a {c['dist_m']} m {c['osm_id']}" for c in o),
            "horario_osm": " || ".join(c["horario"] for c in o if c["horario"]),
            "web_osm": " || ".join(c["web"] for c in o if c["web"]),
        })
    salida = PROCESSED / "verificacion_catalogo.csv"
    with salida.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    for r in filas:
        print(f"\n## {r['id']} — {r['nombre']}  (actual {r['lat']},{r['lon']})")
        print(f"  DENUE: {r['denue'] or '—'}")
        print(f"  OSM:   {r['osm'] or '—'}")
        if r["horario_osm"]:
            print(f"  Horario OSM: {r['horario_osm']}")
    print(f"\nPropuesta en {salida}")


if __name__ == "__main__":
    main()
