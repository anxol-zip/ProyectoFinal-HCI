"""Paso 6: matriz de traslados entre todos los puntos (OpenRouteService) -> matriz_traslado.

    uv run python -m scripts.calcular_traslados [--forzar]

Dos consultas (coche y a pie). La respuesta se guarda en ``data/raw/ors_matriz_<modo>.json`` y se
reutiliza mientras el catálogo no cambie; ``--forzar`` vuelve a consultar. Necesita
``ORS_API_KEY`` en ``backend/.env``.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
from datetime import date

from scripts import RAW
from turismo_core import traslados
from turismo_core.bd import conectar
from turismo_core.config import clave

FUENTE = "OpenRouteService (matriz de traslados)"


def huella(puntos) -> str:
    return hashlib.sha256(json.dumps([(p, round(a, 6), round(b, 6)) for p, a, b in puntos]).encode()).hexdigest()[:16]


def matriz(puntos, modo: str, forzar: bool) -> dict:
    cache = RAW / f"ors_matriz_{modo}.json"
    h = huella(puntos)
    if cache.exists() and not forzar:
        guardado = json.loads(cache.read_text(encoding="utf-8"))
        if guardado.get("huella_catalogo") == h:
            print(f"  {modo}: se reutiliza la consulta del {guardado['fecha']} (el catálogo no cambió)")
            return guardado["respuesta"]
    api_key = clave("ORS_API_KEY")
    if not api_key:
        raise SystemExit("Falta ORS_API_KEY en backend/.env")
    try:
        respuesta = traslados.consultar([(lat, lon) for _, lat, lon in puntos], modo, api_key)
    except (urllib.error.URLError, TimeoutError) as e:
        raise SinConexion(f"OpenRouteService no respondió ({e})") from e
    cache.write_text(json.dumps({"fecha": date.today().isoformat(), "huella_catalogo": h, "punto_ids": [p for p, _, _ in puntos],
                                 "respuesta": respuesta}, ensure_ascii=False), encoding="utf-8")
    print(f"  {modo}: consulta nueva a OpenRouteService ({len(puntos)}×{len(puntos)} pares)")
    return respuesta


class SinConexion(Exception):
    pass


def main(forzar: bool = False) -> None:
    with conectar() as con:
        puntos = [(r["id"], r["lat"], r["lon"]) for r in con.execute("SELECT id, lat, lon FROM punto ORDER BY id")]
        ids = [p for p, _, _ in puntos]
        try:
            coche = {(t.origen_id, t.destino_id): t for t in traslados.leer_matriz(matriz(puntos, "coche", forzar), ids)}
            pie = {(t.origen_id, t.destino_id): t for t in traslados.leer_matriz(matriz(puntos, "pie", forzar), ids)}
        except SinConexion as e:
            # Una consulta guardada de otro catálogo no cuadra con los puntos actuales: mejor no tocar la tabla.
            n = con.execute("SELECT COUNT(*) FROM matriz_traslado").fetchone()[0]
            print(f"  AVISO {e}; matriz_traslado se queda como estaba ({n} pares)")
            return

        crudos = [RAW / f"ors_matriz_{m}.json" for m in ("coche", "pie")]
        huella_crudos = hashlib.sha256(b"".join(r.read_bytes() for r in crudos)).hexdigest()
        con.execute(
            "INSERT INTO fuente (nombre, url, licencia, frecuencia, fecha_descarga, archivo, hash_archivo) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(nombre) DO UPDATE SET "
            "fecha_descarga = excluded.fecha_descarga, hash_archivo = excluded.hash_archivo",
            (FUENTE, "https://openrouteservice.org/", "Datos © colaboradores de OpenStreetMap (ODbL); servicio de HeiGIT",
             "única", json.loads(crudos[0].read_text(encoding="utf-8"))["fecha"],
             ", ".join(r.name for r in crudos), huella_crudos),
        )
        fuente_id = con.execute("SELECT id FROM fuente WHERE nombre = ?", (FUENTE,)).fetchone()[0]
        con.execute("DELETE FROM matriz_traslado")
        con.executemany(
            "INSERT INTO matriz_traslado (origen_id, destino_id, minutos_base, km, minutos_pie, km_pie, fuente_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(o, d, c.minutos, c.km, pie[(o, d)].minutos, pie[(o, d)].km, fuente_id) for (o, d), c in coche.items()],
        )
        sin_ruta = sum(t.minutos is None for t in [*coche.values(), *pie.values()])
        print(f"  {len(coche)} pares guardados; {sin_ruta} sin ruta")


if __name__ == "__main__":
    main(forzar="--forzar" in sys.argv)
