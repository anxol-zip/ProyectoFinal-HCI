from datetime import date

import pytest

from turismo_core.ingesta import (
    FilaObservatorio,
    calendario,
    complementar_con_pdf,
    decodificar,
    establecimiento,
    festivos,
    giro_scian,
    leer_inah,
    leer_observatorio,
    numero,
    quitar_meses_sin_publicar,
    revisar_acumulado,
)

# Filas copiadas tal cual de "DatosOT a junio 2026 glosario.md".
ENCABEZADO = (
    "| Centro Turístico | Indicador | Año | enero | febrero | marzo | abril | mayo | junio | julio "
    "| agosto | septiembre | octubre | noviembre | diciembre | Acumulado |\n"
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
)
NORMAL = (
    "| Atlixco | Porcentaje de ocupación | 2017 | 38.03 | 40.20 | 50.32 | 64.68 | 51.85 | 39.35 "
    "| 46.31 | 48.79 | 35.87 | 46.20 | 41.92 | 65.74 | 47.58 |\n"
)
JUNTO_EN_INDICADOR = (
    "|   | Izúcar de MatamorosCuartos ocupados | 2017 | 1,783.00 | 2,975.00 | 3,604.00 | 3,401.00 "
    "| 2,670.00 | 2,974.00 | 2,991.00 | 3,363.00 | 1,464.00 | 2,598.00 | 2,758.00 | 3,528.00 | 34,109.00 |\n"
)
JUNTO_EN_CENTRO = (
    "| Tetela de OcampoTuristas noche |   | 2017 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 78.00 |\n"
)
CORRIDA = (
    "| Cd.Puebla | Derrama económica | 2026 | 1,011,931,650.00 |   |   | 997,420,900.00 1,276,909,400.00 "
    "1,170,507,150.00 1,246,425,700.00 1,345,549,350.00 |   |   |   |   |   |   |   |   | 7,048,744,150.00 |\n"
)


def _leer(*lineas: str) -> list[FilaObservatorio]:
    return list(leer_observatorio((ENCABEZADO + "".join(lineas)).splitlines(keepends=True)))


def test_numero():
    assert numero("6,665.00") == 6665.0
    assert numero("   ") is None


def test_fila_normal_y_se_saltan_encabezados_y_texto():
    filas = _leer(NORMAL, "Indicador: Ocupación hotelera Unidad de medida: Porcentaje\n")
    assert len(filas) == 1
    f = filas[0]
    assert (f.destino, f.indicador, f.anio) == ("Atlixco", "ocupacion_pct", 2017)
    assert f.meses[0] == 38.03 and f.meses[11] == 65.74 and f.acumulado == 47.58


def test_centro_e_indicador_juntos_en_cualquiera_de_las_dos_celdas():
    a, b = _leer(JUNTO_EN_INDICADOR, JUNTO_EN_CENTRO)
    assert (a.destino, a.indicador) == ("Izúcar de Matamoros", "cuartos_ocupados")
    assert (b.destino, b.indicador) == ("Tetela de Ocampo", "turistas_noche")


def test_fila_con_numeros_corridos_se_lee_en_orden():
    (f,) = _leer(CORRIDA)
    assert f.destino == "Cd. Puebla"
    assert f.meses[:6] == (1011931650.0, 997420900.0, 1276909400.0, 1170507150.0, 1246425700.0, 1345549350.0)
    assert f.meses[6:] == (None,) * 6
    assert f.acumulado == 7048744150.0


def test_revisar_acumulado():
    (f,) = _leer(JUNTO_EN_INDICADOR)
    assert revisar_acumulado(f) is None
    mala = FilaObservatorio("X", "llegadas", 2020, (1.0,) * 12, 99.0)
    assert "acumulado" in revisar_acumulado(mala)
    # Promedios y filas incompletas no se revisan.
    assert revisar_acumulado(FilaObservatorio("X", "ocupacion_pct", 2020, (1.0,) * 12, 99.0)) is None
    assert revisar_acumulado(FilaObservatorio("X", "llegadas", 2026, (1.0,) + (None,) * 11, 99.0)) is None


def test_quitar_meses_sin_publicar_solo_en_el_ultimo_año():
    viejo = FilaObservatorio("A", "llegadas", 2025, (5.0,) * 11 + (0.0,), 55.0)
    a = FilaObservatorio("A", "llegadas", 2026, (1.0, 2.0, 0.0) + (0.0,) * 9, 3.0)
    b = FilaObservatorio("B", "llegadas", 2026, (1.0, 2.0, 3.0, 4.0) + (0.0,) * 8, 10.0)
    v, a2, b2 = quitar_meses_sin_publicar([viejo, a, b])
    assert v == viejo                       # el cero de un año anterior es un dato
    assert a2.meses == (1.0, 2.0, 0.0, 0.0) + (None,) * 8
    assert b2.meses == (1.0, 2.0, 3.0, 4.0) + (None,) * 8


def test_complementar_con_pdf_solo_usa_lineas_completas():
    vacia = FilaObservatorio("Tepeaca", "ocupacion_pct", 2025, (None,) * 12, 0.0)
    con_datos = FilaObservatorio("Atlixco", "llegadas", 2025, (1.0,) * 12, 12.0)
    ultimo = FilaObservatorio("Atlixco", "llegadas", 2026, (1.0, 1.0) + (None,) * 10, 2.0)
    pdf = [
        # Acentos dañados como los entrega el PDF.
        "Tepeaca Porcentaje de ocupaci�n 2025 26.60 25.56 27.12 40.32 30.05 27.84 31.04 31.32 28.12 29.57 29.93 29.43 29.76",
        "Atlixco Llegadas de turistas 2025 9.00 9.00",                   # el Markdown ya la tiene: no se toca
        "Tepeaca Llegadas de turistas 2026 4,724.00 3,725.00 8,449.00",   # no existe en el Markdown: se agrega
        "Tepeaca Turistas noche 2026 4,724.00 8,449.00",                  # le falta un mes: no se usa
    ]
    filas, n = complementar_con_pdf([vacia, con_datos, ultimo], pdf)
    assert n == 2
    assert filas[0].meses[0] == 26.60 and filas[0].acumulado == 29.76
    assert filas[1] == con_datos
    nueva = filas[3]
    assert (nueva.destino, nueva.indicador, nueva.anio) == ("Tepeaca", "llegadas", 2026)
    assert nueva.meses == (4724.0, 3725.0) + (None,) * 10 and nueva.acumulado == 8449.0


INAH_HTML = """
<table><tr><td>INSTITUTO NACIONAL DE ANTROPOLOG&Iacute;A</td></tr></table>
<table><tr><th>Estado</th><th>Clave SIINAH</th><th>Siglas</th><th>Centro de trabajo</th><th>A&ntilde;o</th>
<th>Mes</th><th>Tipo de visitantes</th><th>N&uacute;mero de visitas</th><th>Nacionalidad</th></tr>
<tr><td>Puebla</td><td>3110009</td><td>Z.A.</td><td>Z.A. de Cholula  con museo de sitio</td><td>2025</td>
<td>3</td><td>Boleto pagado</td><td>1,234</td><td>Nacional</td></tr>
<tr><td>Puebla</td><td>3110009</td><td>Z.A.</td><td>Z.A. de Cholula con museo de sitio</td><td>2025</td>
<td>3</td><td>Boleto pagado</td><td>56</td><td>Extranjeros</td></tr>
</table>
"""


def test_leer_inah():
    nac, ext = leer_inah(INAH_HTML)
    assert (nac.clave_siinah, nac.anio, nac.mes, nac.visitas) == ("3110009", 2025, 3, 1234)
    assert nac.recinto == "Z.A. de Cholula con museo de sitio"   # espacios dobles fuera
    assert (nac.nacionalidad, ext.nacionalidad, ext.visitas) == ("nacional", "extranjero", 56)


def test_decodificar_cae_a_windows_1252():
    assert decodificar("Mónica".encode("cp1252")) == "Mónica"
    assert decodificar("Mónica".encode("utf-8")) == "Mónica"


@pytest.mark.parametrize("codigo,giro", [
    ("712111", "museo_sitio"), ("721111", "hospedaje"), ("722511", "alimentos"),
    ("712190", "museo_sitio"), ("711111", None), ("461110", None),
])
def test_giro_scian(codigo, giro):
    assert giro_scian(codigo) == giro


def test_establecimiento_filtra_municipio_y_giro():
    f = {"clee": "X", "nom_estab": "  FONDA  LA  CHINA ", "codigo_act": "722511", "nombre_act": "Restaurantes",
         "per_ocu": "0 a 5 personas", "cve_mun": "019", "municipio": "Atlixco ",
         "latitud": "18.9", "longitud": "-98.43"}
    e = establecimiento(f, {"Atlixco"})
    assert e["nombre"] == "FONDA LA CHINA" and e["giro"] == "alimentos" and e["lat"] == 18.9
    assert establecimiento(f, {"Puebla"}) is None
    assert establecimiento({**f, "codigo_act": "461110"}, {"Atlixco"}) is None


def test_festivos_2026():
    assert festivos(2026) == {
        date(2026, 1, 1), date(2026, 2, 2), date(2026, 3, 16), date(2026, 5, 1),
        date(2026, 9, 16), date(2026, 11, 16), date(2026, 12, 25),
    }


def test_transmision_del_poder_ejecutivo():
    assert date(2024, 10, 1) in festivos(2024)
    assert date(2018, 12, 1) in festivos(2018)
    assert date(2025, 10, 1) not in festivos(2025)


def test_calendario_marca_el_puente_de_noviembre_2026():
    dias = {d["fecha"]: d for d in calendario(date(2026, 11, 13), date(2026, 11, 17))}
    assert [dias[f]["es_puente"] for f in sorted(dias)] == [0, 1, 1, 1, 0]
    assert dias["2026-11-16"]["es_festivo"] == 1 and dias["2026-11-16"]["dia_semana"] == 0
