"""Modelos Pydantic de entrada y salida: el contrato con el frontend (docs/05c §2.2, docs/12).

Swagger (``/docs``) los muestra con sus descripciones; Angel puede programar contra ellos.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Color = Literal["verde", "amarillo", "rojo", "sin_dato", "cerrado"]


# ───────────── Entradas ─────────────

class SesionIn(BaseModel):
    intereses: list[str] = Field(default=[], description="historia, arte, gastronomia, naturaleza, familia, compras, pueblos_magicos…")
    horas: float | None = Field(default=None, gt=0, le=24, description="Tiempo disponible en horas")
    origen_id: int | None = Field(default=None, description="Punto de la lista 'Estoy en…' (sin GPS)")


class RecomendarIn(BaseModel):
    sesion_id: str
    punto_id: int | None = Field(default=None, description="Punto que quiere visitar; sin él, el mejor lugar ahora")
    origen_id: int | None = Field(default=None, description="Dónde está; si falta, el de la sesión")
    intereses: list[str] | None = Field(default=None, description="Si faltan, los de la sesión")
    horas: float | None = Field(default=None, gt=0, le=24)


class RespuestaBusquedaIn(BaseModel):
    aceptada: bool = Field(default=True, description="true = 'Vamos'; false = 'Prefiero mi plan'")


class ReporteIn(BaseModel):
    sesion_id: str
    punto_id: int
    nivel: Literal[1, 2, 3] = Field(description="1 vacío, 2 normal, 3 lleno")
    espera_min: int | None = Field(default=None, ge=0, le=300)
    distancia_m: float | None = Field(default=None, ge=0, description="Distancia al punto si hubo GPS; la ubicación no se guarda (RN_07)")


class AjusteIn(BaseModel):
    punto_id: int
    color: Literal["verde", "amarillo", "rojo"]
    motivo: str = Field(min_length=3, max_length=200, description="Se muestra al turista (RN_16)")
    horas: float = Field(gt=0, le=72, description="Cuánto dura el ajuste")


# ───────────── Salidas ─────────────

class Umbral(BaseModel):
    bajo: float
    alto: float
    metodo: str


class Traslado(BaseModel):
    minutos: int
    modo: Literal["a pie", "en coche"]


class Datos(BaseModel):
    """Qué tan frescos son los datos en vivo (RNF_02)."""
    ahora: str
    clima_consultado_en: str | None
    clima_hace_min: int | None
    afluencia_calculada_hasta: str | None
    afluencia_cubre_esta_hora: bool
    trafico_consultado_en: str | None = None
    trafico_hace_min: int | None = None


class PuntoEstado(BaseModel):
    id: int
    clave: str
    nombre: str
    destino: str
    tipo: str | None
    categorias: list[str]
    interior: bool
    lat: float
    lon: float
    color: Color
    nivel: float | None = Field(description="Afluencia en escala del lugar: 1.0 = una hora normal ahí")
    exceso: float | None = Field(description="Nivel ÷ umbral rojo; > 1 es rojo")
    confianza: Literal["estimado", "confirmado por turistas"] | None
    n_reportes: int
    normalmente: Color | None = Field(description="Color que daría el modelo sin reportes ('normalmente … a esta hora')")
    vs_normal: Literal["mas_lleno", "menos_lleno", "igual"] | None = Field(
        default=None, description="Ahora contra lo normal: los reportes de turistas o la Secretaría lo movieron")
    ajuste_manual: str | None = Field(description="Motivo, si la Secretaría fijó el color (RN_16)")
    umbrales: Umbral | None
    lluvia: Literal["sin", "moderada", "fuerte"]
    eventos: list[str]
    razon: str = Field(description="Por qué tiene ese color (RN_03)")


class PuntoSemaforo(PuntoEstado):
    traslado: Traslado | None = Field(description="Desde origen_id, si se pidió")
    conveniencia: float | None = Field(description="0 a 1; la lista viene ordenada por esto")


class SemaforoOut(BaseModel):
    datos: Datos
    puntos: list[PuntoSemaforo]


class PuntoCatalogo(BaseModel):
    id: int
    clave: str
    nombre: str
    destino: str
    municipio: str | None
    tipo: str | None
    categorias: list[str]
    interior: bool
    lat: float
    lon: float
    horario: dict | str | None
    costo_mxn: float | None
    duracion_sugerida: str | None
    ficha: str | None
    es_inah: bool
    fuente: str | None = Field(description="De dónde salen la coordenada y el horario")
    verificado: bool


class HoraColor(BaseModel):
    hora: str
    color: Color
    nivel: float | None


class HoraClima(BaseModel):
    hora: str
    temp_c: float | None
    prob_lluvia_pct: float | None
    lluvia_mm: float | None
    lluvia: Literal["sin", "moderada", "fuerte"]


class TrasladoDesde(Traslado):
    desde: int


class Evento(BaseModel):
    nombre: str
    inicio: str
    fin: str
    impacto: str | None
    fuente_url: str


class HoraResumen(BaseModel):
    hora: str
    color: Color


class ResumenDia(BaseModel):
    mas_tranquila: HoraResumen
    mas_llena: HoraResumen
    horas_verdes: list[str]


class EsperaReportada(BaseModel):
    minutos: int = Field(description="Mediana de la espera reportada por turistas en las últimas 2 h")
    n_reportes: int
    ultima_hace_min: int


class HoraSemana(BaseModel):
    hora: str
    color: Color
    nivel: float | None
    pasada: bool


class DiaSemana(BaseModel):
    fecha: str
    dia: str
    abierto: bool
    horas: list[HoraSemana] = Field(description="Solo las horas en que abre")
    resumen: ResumenDia | None = Field(description="Hora más tranquila y más llena (de las que no han pasado)")


class SemanaOut(BaseModel):
    punto_id: int
    dias: list[DiaSemana]
    nota: str
    datos: Datos


class PuntoDetalle(PuntoEstado):
    municipio: str | None
    horario: dict | str | None
    costo_mxn: float | None
    duracion_sugerida: str | None
    ficha: str | None
    es_inah: bool
    fuente: str | None
    verificado: bool
    proximas_horas: list[HoraColor] = Field(description="Afluencia estimada de las próximas 12 h (sin reportes)")
    clima: list[HoraClima] = Field(description="Pronóstico de las próximas horas (Open-Meteo)")
    traslado: TrasladoDesde | None
    proximos_eventos: list[Evento]
    como_llegar_url: str
    hoy: ResumenDia | None = Field(description="Hora más tranquila y más llena del resto de hoy (estimado)")
    espera_reportada: EsperaReportada | None = Field(description="Espera que reportan los turistas (últimas 2 h)")
    datos: Datos


class SesionOut(BaseModel):
    sesion_id: str
    es_demo: bool
    perfil: dict


class Conveniencia(BaseModel):
    total: float
    afluencia: float
    clima: float
    traslado: float | None


class Candidato(PuntoEstado):
    traslado: Traslado | None
    similitud: float
    conveniencia: Conveniencia
    puntaje: float
    como_llegar_url: str


class OtraHora(BaseModel):
    hora: str
    color: Color
    nivel: float | None


class RecomendacionOut(BaseModel):
    busqueda_id: int = Field(description="Para POST /api/busquedas/{id}/aceptar")
    pedido: PuntoEstado | None
    motivo: Literal["afluencia", "lluvia", "cerrado"] | None = Field(description="Por qué cambiar; null = el pedido está bien")
    alternativa: Candidato | None
    otras: list[Candidato]
    otra_hora: OtraHora | None = Field(description="'O regresa a las …'")
    razon: str


class RespuestaBusquedaOut(BaseModel):
    busqueda_id: int
    aceptada: bool


class ReporteGuardado(BaseModel):
    id: int
    estado: Literal["valido", "dudoso", "descartado"]
    peso: float
    motivo: str | None
    mensaje: str = Field(description="Texto para mostrar al turista")


class ReporteOut(BaseModel):
    reporte: ReporteGuardado
    punto: PuntoEstado = Field(description="Estado del punto ya con el reporte")


class ChatIn(BaseModel):
    sesion_id: str | None = Field(default=None, description="Si viene, se usan el origen y los intereses de la sesión")
    pregunta: str = Field(min_length=3, max_length=500)
    origen_id: int | None = Field(default=None, description="Dónde está el turista (si no, el de la sesión)")


class FuenteCitada(BaseModel):
    id: str = Field(description="Id citado en la respuesta, p. ej. punto-12, obs-3, evento-1")
    titulo: str
    fuente: str | None
    url: str | None


class EstadoUsado(BaseModel):
    id: str
    nombre: str
    color: Color
    nivel: float | None
    confianza: str | None
    lluvia: str


class ChatOut(BaseModel):
    respuesta: str = Field(description="Texto del asistente, con las citas [id] (RN_10)")
    fuentes: list[FuenteCitada] = Field(description="Las arma el backend con las citas válidas, no el modelo")
    estado_usado: list[EstadoUsado] = Field(description="La tabla en vivo que recibió el modelo (desplegable en T6)")
    citas_invalidas: list[str] = Field(description="Ids que el modelo citó sin habérselos dado (se quitan del texto)")
    intereses: list[str]
    modelo: str
    segundos: dict
