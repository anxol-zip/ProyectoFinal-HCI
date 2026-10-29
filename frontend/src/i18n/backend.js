// El backend redacta en español. Sus frases son fijas (turismo_core/servicio.py y
// recomendador.py), así que en inglés se reconocen por patrón y se traducen aquí. Lo que no
// coincide con ningún patrón (motivos escritos por la Secretaría, nombres de eventos) se
// deja en español.
import { FICHAS_EN } from './fichas.en.js'

const RAZONES_EN = [
  [/^Cerrado a esta hora$/, () => 'Closed at this hour'],
  [/^Tranquilo para este lugar$/, () => 'Quiet for this place'],
  [/^Movimiento normal para este lugar$/, () => 'Usual crowds for this place'],
  [/^([\d.]+) veces lo normal; más lleno que el 85 % de sus horas$/, (m) => `${m[1]}× the usual; busier than 85% of its hours`],
  [/^Sin dato de afluencia para esta hora$/, () => 'No crowd data for this hour'],
  [/^lluvia moderada, es al aire libre$/, () => 'moderate rain, and it is outdoors'],
  [/^lluvia fuerte, es al aire libre$/, () => 'heavy rain, and it is outdoors'],
  [/^confirmado por turistas$/, () => 'confirmed by visitors'],
  [/^evento: (.*)$/, (m) => `event: ${m[1]}`],
  [/^Ajustado por la Secretaría: (.*)$/, (m) => `Set by the Tourism Office: ${m[1]}`],
]

export function traducirRazon(parte, idioma) {
  if (idioma !== 'en') return parte
  for (const [patron, traducir] of RAZONES_EN) {
    const m = parte.match(patron)
    if (m) return traducir(m)
  }
  return parte
}

export function ficha(clave, textoEs, idioma) {
  return idioma === 'en' ? (FICHAS_EN[clave] ?? textoEs) : textoEs
}

// Mensaje del reporte (servicio.registrar_reporte) a partir de su estado y motivo.
export function mensajeReporte(reporte, idioma) {
  if (idioma !== 'en') return reporte.mensaje
  if (reporte.estado === 'valido') return 'Thanks! Your report already helps whoever comes next.'
  if (reporte.estado === 'dudoso') return 'Thanks. Since you are far from the place, your report counts less.'
  if (reporte.motivo?.startsWith('repetido')) return `You already reported this place; you can report it again at ${reporte.motivo.split(' ').pop()}.`
  if (reporte.motivo === 'punto cerrado') return 'This place is closed right now, so it cannot be reported.'
  return 'We could not accept the report.'
}

// "Mejor ve a…" en inglés, armado con los mismos datos que usa recomendador.explicar.
export function explicacionRec(rec, t) {
  const { pedido, motivo, alternativa: alt } = rec
  const corto = (n) => n.split(' (')[0]
  if (!pedido) return alt ? `${corto(alt.nombre)} suits you right now.` : 'No open, uncrowded places near you right now.'
  const partes = []
  if (!motivo) return `${corto(pedido.nombre)} is fine right now: a good time to go.`
  if (motivo === 'afluencia') partes.push(`${corto(pedido.nombre)} is very busy right now${pedido.nivel ? ` (${pedido.nivel.toFixed(1)}× the usual)` : ''}.`)
  else if (motivo === 'cerrado') partes.push(`${corto(pedido.nombre)} is closed at this hour.`)
  else partes.push(`Heavy rain is expected and ${corto(pedido.nombre)} is outdoors.`)
  if (alt) {
    const traslado = alt.traslado ? `, ${alt.traslado.minutos} min away ${t(`modo.${alt.traslado.modo}`)}` : ''
    partes.push(`Go to ${corto(alt.nombre)} instead: it shows "${t(`sem.${alt.color}`)}"${traslado}.`)
  } else {
    partes.push('There is no similar open place within 1 hour that is not busy.')
  }
  return partes.join(' ')
}
