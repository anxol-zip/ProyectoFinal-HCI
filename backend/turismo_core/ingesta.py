"""Lectura y limpieza de las fuentes oficiales (docs/04, secciones 1 y 5).

Funciones puras: reciben texto o filas y devuelven filas limpias. Los scripts de
``scripts/`` las usan para escribir ``data/processed/`` y cargar ``puebla.db``.

- Observatorio Turístico: la tabla del PDF convertida a Markdown
  (``DatosOT a junio 2026 glosario.md``), una fila por centro, indicador y año.
- INAH: ``reporte_detallado_AAAA21.xls``, que en realidad es una página HTML.
- DENUE: el CSV dentro de ``denue_21_csv.zip``.
- Calendario: días festivos de la Ley Federal del Trabajo, art. 74.
"""

from __future__ import annotations

import csv
import html
import io
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, timedelta

# ───────────── Observatorio ─────────────

# Nombre en la tabla -> clave en hecho_observatorio.indicador
INDICADORES = {
    "Cuartos disponibles": "cuartos_disponibles",
    "Cuartos ocupados": "cuartos_ocupados",
    "Llegadas de turistas": "llegadas",
    "Turistas noche": "turistas_noche",
    "Porcentaje de ocupación": "ocupacion_pct",
    "Estadía promedio": "estadia_promedio",
    "Densidad de ocupación": "densidad_ocupacion",
    "Afluencia de visitantes": "afluencia",
    "Derrama económica": "derrama_mxn",
}

# Indicadores que se suman por mes (los demás son promedios o porcentajes).
SUMABLES = {
    "cuartos_disponibles", "cuartos_ocupados", "llegadas",
    "turistas_noche", "afluencia", "derrama_mxn",
}

# Nombres del Observatorio que se escriben distinto en el resto del proyecto.
NOMBRES_DESTINO = {"Cd.Puebla": "Cd. Puebla"}

# Filas que no son un lugar sino un total. 'Cholula' es exactamente San Pedro + San Andrés
# (verificado en la afluencia de 2025: 1,200,128 = 603,148 + 596,980); se guarda, pero no se suma.
AGREGADOS = {"Estado", "Resto del Estado", "Cholula"}
SUMA_DE = {"Cholula": ("San Pedro Cholula", "San Andrés Cholula")}

AÑOS_PANDEMIA = {2020, 2021}


@dataclass(frozen=True)
class FilaObservatorio:
    destino: str
    indicador: str            # clave de INDICADORES
    anio: int
    meses: tuple[float | None, ...]   # 12 valores, None = vacío
    acumulado: float | None


def numero(texto: str) -> float | None:
    """``'6,665.00'`` -> 6665.0; celda vacía -> None."""
    texto = texto.strip().replace(",", "")
    return float(texto) if texto else None


def _separar_centro_indicador(centro: str, indicador: str) -> tuple[str, str]:
    """La conversión del PDF a veces junta las dos celdas en una, en cualquiera de las dos:
    ``'|   | Izúcar de MatamorosCuartos ocupados |'`` o ``'| Tetela de OcampoTuristas noche |   |'``.
    """
    if centro and indicador in INDICADORES:
        return centro, indicador
    junto = f"{centro} {indicador}".strip()
    for nombre in sorted(INDICADORES, key=len, reverse=True):
        if junto.endswith(nombre):
            return junto[: -len(nombre)].strip(), nombre
    raise ValueError(f"Indicador desconocido: {junto!r}")


def _valores(celdas: list[str]) -> tuple[tuple[float | None, ...], float | None]:
    """12 meses + acumulado.

    En las filas con cifras muy anchas (derrama de Cd. Puebla y del Estado) la conversión del
    PDF corrió los números de columna y dejó varios en una celda: ``'| 965,328,136.00 10,358,462,534.00 |'``.
    En esas filas los números se leen en orden: los primeros son los meses desde enero y el
    último es el acumulado. ``revisar_acumulado`` confirma que la reparación cuadre.
    """
    if all(len(c.split()) <= 1 for c in celdas):
        return tuple(numero(c) for c in celdas[:12]), numero(celdas[12])
    seguidos = [numero(t) for c in celdas for t in c.split()]
    meses = seguidos[:-1]
    if len(meses) > 12:
        raise ValueError(f"Fila con {len(meses)} meses: {celdas}")
    return tuple(meses + [None] * (12 - len(meses))), seguidos[-1]


def leer_observatorio(lineas: Iterable[str]) -> Iterator[FilaObservatorio]:
    """Lee la tabla Markdown del Observatorio. Ignora encabezados repetidos y el glosario."""
    for linea in lineas:
        if not linea.startswith("|"):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) != 16 or not celdas[2].isdigit():
            continue  # encabezado, separador '---' o fila rota
        centro, indicador = _separar_centro_indicador(celdas[0], celdas[1])
        centro = NOMBRES_DESTINO.get(centro, centro)
        meses, acumulado = _valores(celdas[3:16])
        yield FilaObservatorio(
            destino=centro,
            indicador=INDICADORES[indicador],
            anio=int(celdas[2]),
            meses=meses,
            acumulado=acumulado,
        )


def _clave_texto(s: str) -> str:
    """Solo letras y números ASCII: el texto del PDF trae los acentos dañados ('ocupaci�n')."""
    return "".join(c for c in s.lower() if c.isascii() and c.isalnum())


_LINEA_PDF = re.compile(r"^(?P<nombre>.*?)\s(?P<anio>\d{4})\s(?P<valores>[\d,]+\.\d+(?:\s[\d,]+\.\d+)*)\s*$")


def complementar_con_pdf(filas: list[FilaObservatorio], lineas_pdf: Iterable[str]) -> tuple[list[FilaObservatorio], int]:
    """Rellena con el texto del PDF las filas que en el Markdown vienen **totalmente vacías** o que
    **no aparecen** (a Tepeaca la conversión le cortó 2023 a 2026).

    En el texto del PDF una celda vacía desaparece y ya no se sabe de qué mes era, así que solo se
    usa una línea si trae todos los meses: 12, o los publicados del último año. Devuelve las filas
    y cuántas se rellenaron o agregaron.
    """
    ultimo = max(f.anio for f in filas)
    publicados = max((m for f in filas if f.anio == ultimo for m, v in enumerate(f.meses, 1) if v), default=12)
    nombres = {f"{_clave_texto(d)}{_clave_texto(n)}": (d, c) for d in {f.destino for f in filas}
               for n, c in INDICADORES.items()}
    nombres |= {f"{_clave_texto(o)}{_clave_texto(n)}": (d, c) for o, d in NOMBRES_DESTINO.items()
                for n, c in INDICADORES.items()}
    del_pdf: dict[tuple[str, str, int], list[float]] = {}
    for linea in lineas_pdf:
        m = _LINEA_PDF.match(linea.strip())
        if not m or _clave_texto(m["nombre"]) not in nombres:
            continue
        destino, indicador = nombres[_clave_texto(m["nombre"])]
        del_pdf[(destino, indicador, int(m["anio"]))] = [numero(v) for v in m["valores"].split()]

    def del_pdf_completa(clave: tuple[str, str, int]) -> FilaObservatorio | None:
        valores = del_pdf.get(clave)
        esperados = publicados if clave[2] == ultimo else 12
        if not valores or len(valores) != esperados + 1:
            return None
        return FilaObservatorio(*clave, tuple(valores[:-1]) + (None,) * (12 - esperados), valores[-1])

    rellenas = 0
    salida = []
    for f in filas:
        if all(v is None for v in f.meses) and (nueva := del_pdf_completa((f.destino, f.indicador, f.anio))):
            f = nueva
            rellenas += 1
        salida.append(f)
    en_markdown = {(f.destino, f.indicador, f.anio) for f in filas}
    for clave in sorted(del_pdf.keys() - en_markdown):
        if nueva := del_pdf_completa(clave):
            salida.append(nueva)
            rellenas += 1
    return salida, rellenas


def quitar_meses_sin_publicar(filas: list[FilaObservatorio]) -> list[FilaObservatorio]:
    """En el último año, los meses aún no publicados vienen en 0.00 (2026: julio a diciembre).

    Se vuelven None a partir del primer mes en que **ningún** destino tiene un valor distinto de cero.
    """
    if not filas:
        return filas
    ultimo = max(f.anio for f in filas)
    del_ultimo = [f for f in filas if f.anio == ultimo]
    publicados = max(
        (m for f in del_ultimo for m, v in enumerate(f.meses, start=1) if v),
        default=0,
    )
    return [
        f if f.anio != ultimo else
        FilaObservatorio(f.destino, f.indicador, f.anio,
                         f.meses[:publicados] + (None,) * (12 - publicados), f.acumulado)
        for f in filas
    ]


def revisar_acumulado(fila: FilaObservatorio, tolerancia: float = 0.01) -> str | None:
    """Para indicadores sumables con los 12 meses, la suma debe dar el acumulado (±1 %)."""
    if fila.indicador not in SUMABLES or fila.acumulado is None or None in fila.meses:
        return None
    suma = sum(fila.meses)  # type: ignore[arg-type]
    if abs(suma - fila.acumulado) > tolerancia * max(abs(fila.acumulado), 1):
        return f"{fila.destino} {fila.indicador} {fila.anio}: meses suman {suma:,.0f}, acumulado {fila.acumulado:,.0f}"
    return None


# ───────────── INAH ─────────────

@dataclass(frozen=True)
class FilaInah:
    clave_siinah: str
    siglas: str
    recinto: str
    anio: int
    mes: int
    tipo_visitante: str
    nacionalidad: str        # 'nacional' / 'extranjero'
    visitas: int


def decodificar(datos: bytes) -> str:
    """El INAH y el DENUE no siempre vienen en UTF-8; si falla, se usa Windows-1252."""
    try:
        return datos.decode("utf-8")
    except UnicodeDecodeError:
        return datos.decode("cp1252")


_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_TD = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
_ETIQUETA = re.compile(r"<[^>]+>")


def _celdas(fila_html: str) -> list[str]:
    return [" ".join(html.unescape(_ETIQUETA.sub("", c)).split()) for c in _TD.findall(fila_html)]


def leer_inah(texto_html: str) -> Iterator[FilaInah]:
    """Lee la tabla de datos del reporte detallado (la que empieza con 'Clave SIINAH')."""
    encabezado: list[str] | None = None
    for tr in _TR.findall(texto_html):
        celdas = _celdas(tr)
        if encabezado is None:
            if "Clave SIINAH" in celdas:
                encabezado = celdas
            continue
        if len(celdas) != len(encabezado):
            continue
        f = dict(zip(encabezado, celdas))
        nac = f["Nacionalidad"].lower()
        yield FilaInah(
            clave_siinah=f["Clave SIINAH"],
            siglas=f["Siglas"],
            recinto=f["Centro de trabajo"],
            anio=int(f["Año"]),
            mes=int(f["Mes"]),
            tipo_visitante=f["Tipo de visitantes"],
            nacionalidad="extranjero" if nac.startswith("extranj") else "nacional",
            visitas=int(f["Número de visitas"].replace(",", "") or 0),
        )


# ───────────── DENUE ─────────────

# docs/04 sección 4. Se filtra por prefijo del código SCIAN.
GIROS_SCIAN = {
    "7121": "museo_sitio",
    "721": "hospedaje",
    "722": "alimentos",
}


def giro_scian(codigo_act: str) -> str | None:
    for prefijo in sorted(GIROS_SCIAN, key=len, reverse=True):
        if codigo_act.startswith(prefijo):
            return GIROS_SCIAN[prefijo]
    return None


def establecimiento(f: dict[str, str], municipios: set[str]) -> dict | None:
    """Una fila del CSV del DENUE -> establecimiento turístico, o None si no es de la zona o del giro."""
    if f["municipio"].strip() not in municipios:
        return None
    giro = giro_scian(f["codigo_act"])
    if giro is None:
        return None
    return {
        "clee": f["clee"],
        "nombre": " ".join(f["nom_estab"].split()),
        "codigo_act": f["codigo_act"],
        "nombre_act": f["nombre_act"].strip(),
        "giro": giro,
        "per_ocu": f["per_ocu"],
        "cve_mun": f["cve_mun"],
        "municipio": f["municipio"].strip(),
        "lat": float(f["latitud"]),
        "lon": float(f["longitud"]),
    }


def leer_denue(texto: io.TextIOBase | Iterable[str], municipios: set[str]) -> tuple[list[dict], dict[str, str]]:
    """Una sola pasada por el CSV (217 MB): establecimientos de la zona y la clave de cada municipio.

    La clave sale del propio DENUE, no escrita de memoria (docs/04 §6).
    """
    filas: list[dict] = []
    claves: dict[str, str] = {}
    for f in csv.DictReader(texto):
        claves.setdefault(f["municipio"].strip(), f["cve_mun"])
        e = establecimiento(f, municipios)
        if e is not None:
            filas.append(e)
    return filas, claves


# ───────────── Calendario ─────────────

def _n_lunes(anio: int, mes: int, n: int) -> date:
    d = date(anio, mes, 1)
    d += timedelta(days=(7 - d.weekday()) % 7)  # primer lunes
    return d + timedelta(weeks=n - 1)


def festivos(anio: int) -> set[date]:
    """Descanso obligatorio, LFT art. 74 (con los lunes de la reforma de 2006)."""
    dias = {
        date(anio, 1, 1),
        _n_lunes(anio, 2, 1),    # Constitución
        _n_lunes(anio, 3, 3),    # Natalicio de Benito Juárez
        date(anio, 5, 1),
        date(anio, 9, 16),
        _n_lunes(anio, 11, 3),   # Revolución
        date(anio, 12, 25),
    }
    # Transmisión del Poder Ejecutivo: 1 de diciembre hasta 2018; 1 de octubre desde 2024.
    if anio >= 2024 and (anio - 2024) % 6 == 0:
        dias.add(date(anio, 10, 1))
    elif anio < 2024 and (anio - 2018) % 6 == 0:
        dias.add(date(anio, 12, 1))
    return dias


def calendario(desde: date, hasta: date) -> Iterator[dict]:
    """Una fila por día. Puente = festivo en lunes o viernes y el fin de semana pegado a él.

    ``es_vacaciones`` queda en 0: el calendario escolar de la SEP se captura aparte, con su fuente.
    """
    fest: set[date] = set()
    for anio in range(desde.year, hasta.year + 1):
        fest |= festivos(anio)
    puente: set[date] = set()
    for f in fest:
        if f.weekday() == 0:
            puente |= {f, f - timedelta(days=1), f - timedelta(days=2)}
        elif f.weekday() == 4:
            puente |= {f, f + timedelta(days=1), f + timedelta(days=2)}
    d = desde
    while d <= hasta:
        yield {
            "fecha": d.isoformat(),
            "dia_semana": d.weekday(),
            "es_festivo": int(d in fest),
            "es_puente": int(d in puente),
            "es_vacaciones": 0,
        }
        d += timedelta(days=1)
