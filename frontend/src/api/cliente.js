// Todas las llamadas a la API de Axel (backend/app, contrato en backend/app/schemas.py).
// Las respuestas llegan tal cual las da el backend: los componentes usan sus mismos nombres
// (id, clave, color, razon, nivel, traslado.minutos…). Swagger: http://localhost:8000/docs
//
// En desarrollo, Vite reenvía /api a localhost:8000 (vite.config.js). En el stand, FastAPI
// sirve este build en el mismo puerto, así que /api es del mismo origen.
const API = import.meta.env.VITE_API_URL ?? '/api'

async function pedir(ruta, opciones = {}) {
  let res
  try {
    res = await fetch(`${API}${ruta}`, { headers: { 'Content-Type': 'application/json' }, ...opciones })
  } catch {
    throw new Error('No hay conexión con el servidor. Revisa que estés en la misma red que la laptop.')
  }
  const cuerpo = await res.json().catch(() => null)
  if (!res.ok) {
    // FastAPI responde { detail: "…" }; en validaciones, detail es una lista.
    const detalle = typeof cuerpo?.detail === 'string' ? cuerpo.detail : null
    throw new Error(detalle ?? `El servidor respondió ${res.status} en ${ruta}`)
  }
  return cuerpo
}

const enviar = (ruta, cuerpo, metodo = 'POST') => pedir(ruta, { method: metodo, body: JSON.stringify(cuerpo) })
const consulta = (params) => {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v != null)).toString()
  return q ? `?${q}` : ''
}

export const api = {
  // CU_01 a CU_05: turista
  obtenerPuntos: () => pedir('/puntos'),
  obtenerSemaforo: (origenId) => pedir(`/semaforo${consulta({ origen_id: origenId })}`),
  obtenerEstadoPunto: (puntoId, origenId) => pedir(`/puntos/${puntoId}/estado${consulta({ origen_id: origenId })}`),
  obtenerSemana: (puntoId) => pedir(`/puntos/${puntoId}/semana`),
  crearSesion: ({ intereses, horas, origenId }) => enviar('/sesiones', { intereses, horas, origen_id: origenId }),
  // origenId va en cada llamada: si el GPS cambió el punto de partida, la sesión del backend no lo sabe.
  pedirRecomendacion: ({ sesionId, puntoId, origenId }) => enviar('/recomendar', { sesion_id: sesionId, punto_id: puntoId, origen_id: origenId }),
  responderBusqueda: (busquedaId, aceptada) => enviar(`/busquedas/${busquedaId}/aceptar`, { aceptada }),
  // distanciaM: solo la distancia al lugar, nunca la ubicación (RN_04 y RN_07); sin ella el reporte vale la mitad.
  enviarReporte: ({ sesionId, puntoId, nivel, distanciaM }) =>
    enviar('/reportes', { sesion_id: sesionId, punto_id: puntoId, nivel, distancia_m: distanciaM ?? null }),

  // CU_06: asistente (Ollama en la laptop; si no está, el backend responde 503 con el motivo)
  preguntarAsistente: ({ sesionId, pregunta, origenId }) => enviar('/chat', { sesion_id: sesionId, pregunta, origen_id: origenId }),

  // CU_07: panel de gobierno. incluirDemo suma la actividad de la demo del stand (RN_11).
  obtenerPanel: async ({ incluirDemo }) => {
    const q = consulta({ incluir_demo: incluirDemo })
    const [afluencia, redirecciones, derrama, estatal, umbrales, ajustes] = await Promise.all([
      pedir(`/panel/afluencia${q}`), pedir(`/panel/redirecciones${q}`), pedir(`/panel/derrama${q}`),
      pedir('/panel/semaforo-estatal'), pedir('/panel/umbrales'), pedir('/panel/ajustes'),
    ])
    return { afluencia, redirecciones, derrama, estatal, umbrales, ajustes }
  },
  fijarColor: ({ puntoId, color, motivo, horas }) => enviar('/panel/ajustes', { punto_id: puntoId, color, motivo, horas }),
  quitarAjuste: (ajusteId) => pedir(`/panel/ajustes/${ajusteId}`, { method: 'DELETE' }),
}
