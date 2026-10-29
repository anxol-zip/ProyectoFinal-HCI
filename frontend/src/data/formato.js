// Formatos de lo que manda el backend.
import { traducirRazon } from '../i18n/backend.js'

// "2026-10-16T13:00" o "2026-10-16 13:00" → "13:00"
export const hora = (iso) => (iso ? iso.slice(11, 16) : '')

// El backend explica el color en una línea con sus partes unidas por " · " (servicio.razon_corta);
// en pantalla va cada parte por separado, traducida si hace falta y con mayúscula inicial.
export function partesRazon(razon, idioma = 'es') {
  return (razon ?? '').split(' · ').filter(Boolean)
    .map((r) => traducirRazon(r, idioma))
    .map((r) => r.charAt(0).toUpperCase() + r.slice(1))
}

export const pesos = (n) => (n ?? 0).toLocaleString('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 0 })

const DIAS = ['dom', 'lun', 'mar', 'mie', 'jue', 'vie', 'sab']
export function horarioDeHoy(horario, t) {
  if (!horario) return t('ficha.porConfirmar')
  if (typeof horario === 'string') return horario
  return horario[DIAS[new Date().getDay()]] ?? t('ficha.cerradoHoy')
}

// El backend da 0 min cuando el lugar es el mismo punto de partida.
export function textoTraslado(traslado, t) {
  if (!traslado) return null
  return traslado.minutos === 0 ? t('traslado.aqui') : t('traslado.min', { min: traslado.minutos, modo: t(`modo.${traslado.modo}`) })
}

// "1 reporte", "3 reportes"
export const cuenta = (n, singular, plural) => `${n} ${n === 1 ? singular : plural}`
